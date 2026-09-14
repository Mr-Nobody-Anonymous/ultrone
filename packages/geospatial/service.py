# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE geospatial service: world model + simulation -> globe entities.

Phase 1 of the ULTRONE Global Eye (``apps/globe``): this module turns the
canonical :class:`world_model.WorldModel` state and the grid-based
:class:`sim.battlefield_env.BattlefieldEnv` simulation into geo-registered
entities (lat/lon/alt + kinematics) that the Cesium globe consumes via
:mod:`packages.geospatial.api`.

Design notes:

- The world model stores positions as composable ``position`` components.
  Several shapes are accepted (``{"lat","lon"}``, ``{"latitude",
  "longitude"}``, ``[lon, lat]``); anything without a parseable position
  is skipped (it still exists in the world model, it just has no map fix).
- The battlefield sim lives on a 100x100 grid. Grid cells are mapped into
  a configurable demo-theater bounding box (anchor + span, overridable via
  ``ULTRONE_GEO_*`` env vars). This mapping is explicitly synthetic --
  real sensor geolocation arrives with the intel adapters (Phase 2).
- An empty store is seeded with a small deterministic demo theater so the
  globe shows ULTRONE-native layers out of the box. Seeding is disabled
  with ``ULTRONE_GEO_SEED=0``. Seeded entities drift kinematically so the
  live stream visibly moves.
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from packages.geospatial.tracks import TrackManager, Waypoint

# ---------------------------------------------------------------------------
# Theater mapping (grid <-> geo). Overridable via environment.
# ---------------------------------------------------------------------------


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


#: Default demo theater: Gulf of Aden / Horn of Africa.
ANCHOR_LAT = _env_float("ULTRONE_GEO_ANCHOR_LAT", 11.5)
ANCHOR_LON = _env_float("ULTRONE_GEO_ANCHOR_LON", 44.0)
THEATER_SPAN_DEG = _env_float("ULTRONE_GEO_SPAN_DEG", 10.0)
GRID_SIZE = 100


def grid_to_geo(x: float, y: float) -> Tuple[float, float]:
    """Map sim grid cell (0..GRID_SIZE) to (lat, lon) in the theater box."""
    half = THEATER_SPAN_DEG / 2.0
    lon = ANCHOR_LON - half + (x / GRID_SIZE) * THEATER_SPAN_DEG
    lat = ANCHOR_LAT - half + (y / GRID_SIZE) * THEATER_SPAN_DEG
    return (lat, lon)


def geo_to_grid(lat: float, lon: float) -> Tuple[float, float]:
    """Inverse of :func:`grid_to_geo` (clamped to the grid)."""
    half = THEATER_SPAN_DEG / 2.0
    x = (lon - (ANCHOR_LON - half)) / THEATER_SPAN_DEG * GRID_SIZE
    y = (lat - (ANCHOR_LAT - half)) / THEATER_SPAN_DEG * GRID_SIZE
    return (min(max(x, 0.0), GRID_SIZE), min(max(y, 0.0), GRID_SIZE))


# ---------------------------------------------------------------------------
# Geo entity model
# ---------------------------------------------------------------------------

#: Canonical globe kinds. Unknown world-model types fall back to "unknown".
KINDS = ("air", "land", "sea", "space", "cyber", "facility", "unknown")

_TYPE_TO_KIND = (
    (("air", "aircraft", "drone", "uav", "fighter", "missile", "jammer"), "air"),
    (("vessel", "ship", "submarine", "boat", "naval"), "sea"),
    (("satellite", "orbital", "space"), "space"),
    (("cyber", "network", "server"), "cyber"),
    (("supply", "base", "facility", "installation", "depot"), "facility"),
    (("armor", "artillery", "infantry", "tank", "vehicle", "ground"), "land"),
)


def kind_for(entity_type: str) -> str:
    lowered = (entity_type or "").lower()
    for needles, kind in _TYPE_TO_KIND:
        if any(n in lowered for n in needles):
            return kind
    return "unknown"


@dataclass
class GeoEntity:
    """One geo-registered entity for the globe."""

    id: str
    name: str
    kind: str = "unknown"
    lat: float = 0.0
    lon: float = 0.0
    alt_m: float = 0.0
    heading_deg: float = 0.0
    speed_mps: float = 0.0
    status: str = "active"
    team: str = "unknown"  # blue | red | neutral | unknown
    confidence: float = 1.0
    source: str = "world_model"  # world_model | simulation | demo
    updated_at: float = field(default_factory=time.time)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = d["kind"] if d["kind"] in KINDS else "unknown"
        return d


def parse_position(value: Any) -> Optional[Tuple[float, float, float]]:
    """Parse a world-model position component -> (lat, lon, alt_m)."""
    alt = 0.0
    if isinstance(value, dict):
        lat = value.get("lat", value.get("latitude"))
        lon = value.get("lon", value.get("lng", value.get("longitude")))
        alt = value.get("alt", value.get("alt_m", value.get("altitude_m", 0.0)))
        if lat is None or lon is None:
            return None
        try:
            return (float(lat), float(lon), float(alt))
        except (TypeError, ValueError):
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        # GeoJSON order: [lon, lat, (alt?)].
        try:
            lon, lat = float(value[0]), float(value[1])
            if len(value) >= 3:
                alt = float(value[2])
            return (lat, lon, float(alt))
        except (TypeError, ValueError):
            return None
    return None


def _parse_kinematics(entity: Any) -> Tuple[float, float, float]:
    """Best-effort (heading_deg, speed_mps, alt_m) from known components."""
    heading, speed, alt = 0.0, 0.0, 0.0
    get = getattr(entity, "get", None)
    if not callable(get):
        return (heading, speed, alt)
    for key in ("kinematics", "velocity", "motion"):
        kin = get(key)
        if isinstance(kin, dict):
            heading = float(kin.get("heading_deg", kin.get("heading", heading)) or 0.0)
            speed = float(kin.get("speed_mps", kin.get("speed", speed)) or 0.0)
            alt = float(kin.get("alt_m", kin.get("alt", alt)) or 0.0)
    pos = get("position")
    if isinstance(pos, dict):
        heading = float(pos.get("heading_deg", pos.get("heading", heading)) or 0.0)
        speed = float(pos.get("speed_mps", pos.get("speed", speed)) or 0.0)
        alt = float(pos.get("alt_m", pos.get("alt", alt)) or 0.0)
    return (heading, speed, alt)


# ---------------------------------------------------------------------------
# Snapshot service
# ---------------------------------------------------------------------------


class GeoService:
    """Builds globe snapshots from the world model (+ optional sim)."""

    def __init__(
        self,
        world_model: Any = None,
        track_history: int = 60,
        seed_demo: Optional[bool] = None,
    ) -> None:
        if world_model is None:
            from world_model import default_world_model

            world_model = default_world_model
        self.world_model = world_model
        self.tracks = TrackManager(max_history=track_history)
        self.sim: Any = None
        if seed_demo is None:
            seed_demo = os.environ.get("ULTRONE_GEO_SEED", "1") != "0"
        self._seed_demo = seed_demo
        self._seeded = False
        self._last_tick = time.time()

    # -- demo theater ----------------------------------------------------
    def _ensure_seeded(self) -> None:
        if self._seeded or not self._seed_demo:
            return
        self._seeded = True
        if self.world_model.find():
            return  # real state wins; never seed over it
        from world_model import Entity

        rng = random.Random(20260914)
        specs = [
            ("air_asset", "blue", 6, 9000.0, 120.0),
            ("air_asset", "red", 4, 7500.0, 140.0),
            ("vessel", "neutral", 5, 0.0, 8.0),
            ("ground_unit", "blue", 4, 0.0, 0.0),
            ("facility", "neutral", 2, 0.0, 0.0),
        ]
        n = 0
        for etype, team, count, alt, speed in specs:
            for _ in range(count):
                n += 1
                lat = ANCHOR_LAT + rng.uniform(-4.0, 4.0)
                lon = ANCHOR_LON + rng.uniform(-4.0, 4.0)
                heading = rng.uniform(0, 360)
                entity = Entity(entity_id=f"demo-{n:03d}", type=etype, status="active")
                entity.set("position", {"lat": lat, "lon": lon}, confidence=0.9)
                entity.set(
                    "kinematics",
                    {
                        "heading_deg": heading,
                        "speed_mps": speed * rng.uniform(0.7, 1.0),
                        "alt_m": alt,
                    },
                    confidence=0.9,
                )
                entity.set("team", team, confidence=1.0)
                entity.set("demo", True, confidence=1.0)
                self.world_model.upsert(entity)

    def tick(self, now: Optional[float] = None) -> float:
        """Advance demo-entity dead reckoning; returns elapsed seconds."""
        now = time.time() if now is None else now
        dt = max(0.0, now - self._last_tick)
        self._last_tick = now
        if dt <= 0.0:
            return 0.0
        for entity in self.world_model.find():
            if not entity.get("demo"):
                continue
            pos = parse_position(entity.get("position"))
            if pos is None:
                continue
            heading, speed, _ = _parse_kinematics(entity)
            if speed <= 0:
                continue
            # Move along heading; bounce off the theater box edges.
            dist_m = speed * min(dt, 5.0)
            rad = math.radians(heading)
            d_lat = (dist_m * math.cos(rad)) / 111111.0
            cos_lat = max(0.1, math.cos(math.radians(pos[0])))
            d_lon = (dist_m * math.sin(rad)) / (111111.0 * cos_lat)
            new_lat, new_lon = pos[0] + d_lat, pos[1] + d_lon
            half = THEATER_SPAN_DEG / 2.0
            if abs(new_lat - ANCHOR_LAT) > half or abs(new_lon - ANCHOR_LON) > half:
                heading = (heading + 180.0) % 360.0
                new_lat = min(max(new_lat, ANCHOR_LAT - half), ANCHOR_LAT + half)
                new_lon = min(max(new_lon, ANCHOR_LON - half), ANCHOR_LON + half)
                kin = dict(entity.get("kinematics") or {})
                kin["heading_deg"] = heading
                entity.set("kinematics", kin, confidence=0.9)
            entity.set("position", {"lat": new_lat, "lon": new_lon}, confidence=0.9)
        return dt

    # -- sim attach ------------------------------------------------------
    def attach_sim(self, env: Any = None) -> Any:
        """Attach a (grid) sim env; creates + resets one when omitted.

        ``battlefield_env`` is loaded by file path on purpose: importing it
        through the ``sim`` package would execute ``sim/__init__`` and drag in
        the perception/model stack (network weight downloads). The module
        itself only needs stdlib + numpy.
        """
        if env is None:
            import importlib.util

            env_path = (
                Path(__file__).resolve().parents[2]
                / "simulation"
                / "sim"
                / "battlefield_env.py"
            )
            spec = importlib.util.spec_from_file_location(
                "ultrone_battlefield_env", env_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load sim env from {env_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules["ultrone_battlefield_env"] = module
            spec.loader.exec_module(module)
            env = module.BattlefieldEnv()
            env.reset()
        self.sim = env
        return env

    def step_sim(self, steps: int = 1) -> Dict[str, Any]:
        if self.sim is None:
            self.attach_sim()
        obs: Dict[str, Any] = {}
        reward = 0.0
        done = False
        info: Dict[str, Any] = {}
        for _ in range(max(1, steps)):
            # No COA: advance the world clock / red drift only. Callers
            # drive real actions through the pipeline or /sim/command.
            obs, reward, done, info = self.sim.step()
            if done:
                break
        return {
            "step_count": getattr(self.sim, "step_count", None),
            "done": done,
            "reward": reward,
            "info": info,
            "observation_keys": sorted(obs.keys()) if isinstance(obs, dict) else [],
        }

    # -- snapshot --------------------------------------------------------
    def _from_world_model(self) -> List[GeoEntity]:
        entities: List[GeoEntity] = []
        for e in self.world_model.find():
            pos = parse_position(e.get("position"))
            if pos is None:
                continue
            heading, speed, alt = _parse_kinematics(e)
            team = str(e.get("team", e.get("side", "unknown")) or "unknown").lower()
            if team not in ("blue", "red", "neutral"):
                team = "unknown"
            entities.append(
                GeoEntity(
                    id=e.entity_id,
                    name=str(e.get("name", e.entity_id)),
                    kind=kind_for(e.type),
                    lat=pos[0],
                    lon=pos[1],
                    alt_m=alt,
                    heading_deg=heading,
                    speed_mps=speed,
                    status=e.status,
                    team=team,
                    confidence=1.0,
                    source="demo" if e.get("demo") else "world_model",
                    updated_at=e.updated_at,
                    properties={"type": e.type},
                )
            )
        return entities

    def _from_sim(self) -> List[GeoEntity]:
        if self.sim is None:
            return []
        entities: List[GeoEntity] = []

        def emit(
            eid: str,
            name: str,
            etype: str,
            team: str,
            gx: float,
            gy: float,
            extra: Optional[Dict[str, Any]] = None,
        ) -> None:
            lat, lon = grid_to_geo(gx, gy)
            props = {"grid": [gx, gy], "type": etype}
            if extra:
                props.update(extra)
            entities.append(
                GeoEntity(
                    id=eid,
                    name=name,
                    kind=kind_for(etype),
                    lat=lat,
                    lon=lon,
                    status="active",
                    team=team,
                    confidence=0.85,
                    source="simulation",
                    properties=props,
                )
            )

        red = getattr(self.sim, "red_force", None)
        if isinstance(red, dict) and "position" in red:
            gx, gy = red["position"]
            rtype = str(red.get("type", "armor"))
            ent_heading = float(red.get("heading", 0.0) or 0.0)
            lat, lon = grid_to_geo(gx, gy)
            entities.append(
                GeoEntity(
                    id="sim-red-force",
                    name=f"RED {rtype}",
                    kind=kind_for(rtype),
                    lat=lat,
                    lon=lon,
                    heading_deg=ent_heading,
                    status="active",
                    team="red",
                    confidence=0.85,
                    source="simulation",
                    properties={
                        "grid": [gx, gy],
                        "type": rtype,
                        "health": red.get("health"),
                    },
                )
            )
        for asset_type, items in (getattr(self.sim, "blue_assets", {}) or {}).items():
            for i, asset in enumerate(items or []):
                pos = asset.get("position") if isinstance(asset, dict) else None
                if not pos:
                    continue
                emit(
                    f"sim-blue-{asset_type}-{i}",
                    f"BLUE {asset_type} {i+1}",
                    asset_type,
                    "blue",
                    pos[0],
                    pos[1],
                    {"ammo": asset.get("ammo"), "fuel": asset.get("fuel")},
                )
        for node_id, node in (getattr(self.sim, "supply_nodes", {}) or {}).items():
            pos = node.get("position") if isinstance(node, dict) else None
            if not pos:
                continue
            emit(
                f"sim-{node_id}",
                node_id.replace("_", " ").upper(),
                "supply",
                str(node.get("team", "neutral")),
                pos[0],
                pos[1],
                {"alive": node.get("alive")},
            )
        return entities

    def snapshot(self, advance: bool = True) -> Dict[str, Any]:
        """Full globe snapshot: entities + recent tracks."""
        self._ensure_seeded()
        if advance:
            self.tick()
        entities = self._from_world_model() + self._from_sim()
        now = time.time()
        for ent in entities:
            self.tracks.update_track(
                ent.id,
                Waypoint(
                    lat=ent.lat,
                    lon=ent.lon,
                    altitude_m=ent.alt_m,
                    heading_deg=ent.heading_deg,
                    speed_mps=ent.speed_mps,
                    timestamp=now,
                ),
            )
        tracks = {
            eid: [wp.to_dict() for wp in th.waypoints[-20:]]
            for eid, th in self.tracks.get_all_tracks().items()
        }
        return {
            "generated_at": now,
            "count": len(entities),
            "theater": {
                "anchor_lat": ANCHOR_LAT,
                "anchor_lon": ANCHOR_LON,
                "span_deg": THEATER_SPAN_DEG,
            },
            "entities": [e.to_dict() for e in entities],
            "tracks": tracks,
        }


__all__ = [
    "ANCHOR_LAT",
    "ANCHOR_LON",
    "THEATER_SPAN_DEG",
    "GeoEntity",
    "GeoService",
    "geo_to_grid",
    "grid_to_geo",
    "kind_for",
    "parse_position",
]
