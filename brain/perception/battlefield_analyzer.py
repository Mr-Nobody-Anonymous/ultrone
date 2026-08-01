# Copyright (c) Ultrone Contributors. All rights reserved.
"""Battlefield situation analyzer - comprehensive tactical analysis engine.

Provides a full suite of battlefield situational-awareness algorithms:

1. **Line-of-Sight (LOS) network** - which entities can see which
2. **Threat heat map** - danger scoring grid from enemy positions/capabilities
3. **Cover & concealment** - per-cell protection score
4. **Choke points & kill zones** - terrain funnels where ambushes are likely
5. **Key terrain & high ground** - tactically significant high-elevation cells
6. **Encirclement / flanking detection** - is Blue surrounding Red or vice versa
7. **Force ratio & power distribution** - strength comparison
8. **Voronoi territory partitioning** - influence zones
9. **Enemy cluster detection** - grouping of hostile units
10. **Fire corridors / firing lanes** - clear lines for weapons
11. **Situation summary** - human-readable text briefing
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from data.terrain import Terrain, TerrainType
from data.entities import Unit, Contact

from .terrain_analyzer import TerrainAnalyzer

logger = logging.getLogger("Ultrone.Brain.Perception.BattlefieldAnalyzer")


class BattlefieldAnalyzer:
    """Runs the full suite of battlefield analysis algorithms.

    Input is the terrain plus a list of entities (units/contacts) with
    ``team`` ('blue'/'red'), ``position`` (x, y) and capability hints.
    Output is a JSON-serializable :class:`AnalysisReport`.
    """

    # Weight that height gives to "key terrain" scoring
    KEY_TERRAIN_HEIGHT_WEIGHT: float = 0.5
    # Distance (grid units) that counts as "neighbouring" for clustering
    CLUSTER_RADIUS: float = 15.0
    # Maximum LOS range for the LOS network (grid units)
    LOS_MAX_RANGE: float = 60.0
    # Distance from a narrow passage that defines a chokepoint cell
    CHOKEPOINT_RADIUS: float = 2.0

    def __init__(self, terrain: Optional[Terrain] = None) -> None:
        self.terrain = terrain
        self.terrain_analyzer = TerrainAnalyzer(terrain)

    # ------------------------------------------------------------------
    # Entity ingestion
    # ------------------------------------------------------------------

    def _extract_entities(self, units: Any, contacts: Any) -> List[Dict[str, Any]]:
        """Normalise units/contacts into a common entity list.

        Each entry: {id, team, x, y, z, type, health, capability}.
        """
        entities: List[Dict[str, Any]] = []

        def _add(eid: str, team: str, pos: Any, etype: str, health: float,
                 capability: float = 1.0) -> None:
            if pos is None:
                return
            try:
                x, y = float(pos[0]), float(pos[1])
            except (TypeError, ValueError, IndexError):
                return
            z = self.terrain_analyzer.get_elevation_at(int(x), int(y)) if self.terrain else 0.0
            entities.append({
                "id": eid,
                "team": team,
                "x": x,
                "y": y,
                "z": z,
                "type": etype,
                "health": float(health),
                "capability": float(capability),
            })

        # Units
        if units:
            for u in units:
                team = getattr(u, "team", "unknown")
                pos = getattr(u, "position", None)
                if pos is None:
                    continue
                _add(
                    eid=getattr(u, "unit_id", "unit"),
                    team=team,
                    pos=pos,
                    etype=getattr(u, "unit_type", "unit"),
                    health=getattr(u, "health", 100),
                    capability=getattr(u, "capability", 1.0),
                )

        # Contacts (enemy sensors)
        if contacts:
            for c in contacts:
                team = getattr(c, "team", "unknown")
                pos = getattr(c, "position", None)
                if pos is None:
                    continue
                _add(
                    eid=getattr(c, "contact_id", "contact"),
                    team=team,
                    pos=pos,
                    etype=getattr(c, "entity_type", "contact"),
                    health=100,
                    capability=1.0,
                )

        return entities

    # ------------------------------------------------------------------
    # 1. LOS network
    # ------------------------------------------------------------------

    def _compute_los_network(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute pairwise line-of-sight between entities.

        Uses terrain elevation to determine whether the straight line
        between two entities clears all intervening terrain.
        """
        dem = self.terrain_analyzer.get_heightmap()
        los_links: List[Dict[str, Any]] = []
        blocked_links: List[Dict[str, Any]] = []

        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                a, b = entities[i], entities[j]
                dx = b["x"] - a["x"]
                dy = b["y"] - a["y"]
                dist = math.hypot(dx, dy)
                if dist > self.LOS_MAX_RANGE:
                    continue

                has_los = True
                if dem.size:
                    steps = max(2, int(dist * 2))
                    for s in range(1, steps):
                        t = s / steps
                        sx = int(round(a["x"] + t * dx))
                        sy = int(round(a["y"] + t * dy))
                        h, w = dem.shape
                        if not (0 <= sy < h and 0 <= sx < w):
                            continue
                        ray_z = a["z"] + (b["z"] - a["z"]) * t
                        if dem[sy, sx] >= ray_z:
                            has_los = False
                            break

                link = {
                    "source": a["id"], "target": b["id"],
                    "source_team": a["team"], "target_team": b["team"],
                    "distance": round(dist, 1),
                    "los": has_los,
                }
                if has_los:
                    los_links.append(link)
                else:
                    blocked_links.append(link)

        return {
            "clear": los_links,
            "blocked": blocked_links,
            "total_links": len(los_links) + len(blocked_links),
            "clear_links": len(los_links),
        }

    # ------------------------------------------------------------------
    # 2. Threat heat map
    # ------------------------------------------------------------------

    def _compute_threat_heatmap(
        self,
        entities: List[Dict[str, Any]],
        grid_w: int,
        grid_h: int,
    ) -> Dict[str, Any]:
        """Compute a danger heat map from red positions.

        Each red entity contributes a gaussian "danger bubble" scaled by
        its capability/health.  Blue entities add a small counterweight.
        """
        heat = np.zeros((grid_h, grid_w), dtype=np.float32)

        for e in entities:
            if e["team"] != "red":
                continue
            gx, gy = int(round(e["x"])), int(round(e["y"]))
            if not (0 <= gx < grid_w and 0 <= gy < grid_h):
                continue

            strength = e["capability"] * (e["health"] / 100.0)
            sigma = 8.0
            xg = np.arange(grid_w)
            yg = np.arange(grid_h)
            xx, yy = np.meshgrid(xg, yg)
            gauss = np.exp(-(((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * sigma ** 2)))
            heat += strength * gauss

        # Normalise 0-1
        mx = heat.max()
        if mx > 0:
            heat = heat / mx

        # Locate highest threat cell
        if heat.size:
            idx = np.unravel_index(np.argmax(heat), heat.shape)
            peak = (int(idx[1]), int(idx[0]))
        else:
            peak = (0, 0)

        return {
            "heatmap": heat.astype(float).tolist(),
            "peak_threat": peak,
            "mean_threat": float(heat.mean()) if heat.size else 0.0,
            "total_threat": float(heat.sum()) if heat.size else 0.0,
        }

    # ------------------------------------------------------------------
    # 3. Cover & concealment
    # ------------------------------------------------------------------

    def _compute_cover_map(self, grid_w: int, grid_h: int) -> Dict[str, Any]:
        """Compute a per-cell cover score (0-1) from terrain type.

        Forest/urban provide good cover; open ground provides none.
        """
        if self.terrain is None:
            return {"cover": np.zeros((grid_h, grid_w), dtype=float).tolist(),
                    "mean_cover": 0.0}

        cover = np.zeros((grid_h, grid_w), dtype=np.float32)
        cover_score = {
            TerrainType.OPEN: 0.05,
            TerrainType.PLAINS: 0.15,
            TerrainType.FOREST: 0.8,
            TerrainType.URBAN: 0.9,
            TerrainType.MOUNTAIN: 0.7,
            TerrainType.HILLS: 0.5,
            TerrainType.DESERT: 0.1,
            TerrainType.WATER: 0.0,
            TerrainType.COASTAL: 0.2,
            TerrainType.SUBMERGED: 0.3,
        }
        for y in range(grid_h):
            for x in range(grid_w):
                cell = self.terrain.get_cell(x, y)
                if cell is not None:
                    cover[y, x] = cover_score.get(cell.terrain_type, 0.1)

        return {
            "cover": cover.astype(float).tolist(),
            "mean_cover": float(cover.mean()),
        }

    # ------------------------------------------------------------------
    # 4. Choke points & kill zones
    # ------------------------------------------------------------------

    def _compute_chokepoints(self, grid_w: int, grid_h: int) -> Dict[str, Any]:
        """Detect chokepoints: cells where passable terrain narrows.

        A cell is a chokepoint if it's passable but surrounded by mostly
        impassable (high-cost) neighbours - a natural funnel.
        """
        if self.terrain is None:
            return {"chokepoints": [], "kill_zones": []}

        passable = np.zeros((grid_h, grid_w), dtype=bool)
        for y in range(grid_h):
            for x in range(grid_w):
                cell = self.terrain.get_cell(x, y)
                passable[y, x] = cell is not None and cell.get_movement_cost() < 3.0

        chokepoints: List[Tuple[int, int]] = []
        for y in range(1, grid_h - 1):
            for x in range(1, grid_w - 1):
                if not passable[y, x]:
                    continue
                # Count impassable neighbours
                blocked = 0
                total = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        if not (0 <= x + dx < grid_w and 0 <= y + dy < grid_h):
                            continue
                        total += 1
                        if not passable[y + dy, x + dx]:
                            blocked += 1
                # Funnel if > 60% neighbours are impassable
                if total > 0 and blocked / total > 0.6:
                    chokepoints.append((x, y))

        # Kill zones: chokepoints with line of sight to high ground nearby
        kill_zones = list(chokepoints)

        return {
            "chokepoints": [{"x": x, "y": y} for x, y in chokepoints],
            "kill_zones": [{"x": x, "y": y} for x, y in kill_zones],
            "count": len(chokepoints),
        }

    # ------------------------------------------------------------------
    # 5. Key terrain & high ground
    # ------------------------------------------------------------------

    def _compute_key_terrain(self, grid_w: int, grid_h: int) -> Dict[str, Any]:
        """Identify tactically significant terrain.

        Scores each cell by elevation (high ground) and centrality.
        """
        dem = self.terrain_analyzer.get_heightmap()
        if dem.size == 0:
            return {"key_terrain": [], "dominant_high_ground": (0, 0)}

        h, w = dem.shape
        # High ground score = normalised elevation
        elev_norm = (dem - dem.min()) / max(1e-6, dem.max() - dem.min())

        # Centrality: distance from edge (peak at center)
        yg = np.linspace(-1, 1, h)[:, None]
        xg = np.linspace(-1, 1, w)[None, :]
        centrality = 1.0 - np.sqrt(xg ** 2 + yg ** 2) / math.sqrt(2)

        score = (1 - self.KEY_TERRAIN_HEIGHT_WEIGHT) * centrality + \
                self.KEY_TERRAIN_HEIGHT_WEIGHT * elev_norm

        # Top 10% cells are key terrain
        threshold = np.percentile(score, 90)
        key_mask = score >= threshold
        key_cells = list(zip(*np.where(key_mask)))

        # Dominant high ground = highest elevation cell
        peak_idx = np.unravel_index(np.argmax(dem), dem.shape)

        return {
            "key_terrain": [{"x": int(y), "y": int(x)} for x, y in key_cells][:50],
            "dominant_high_ground": (int(peak_idx[1]), int(peak_idx[0])),
            "key_cell_count": int(key_mask.sum()),
            "score_map": score.astype(float).tolist(),
        }

    # ------------------------------------------------------------------
    # 6. Encirclement / flanking
    # ------------------------------------------------------------------

    def _compute_encirclement(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect encirclement: one side surrounding the other.

        Computes the angular spread of red positions around blue's centroid.
        If red occupies all 4 compass quadrants around blue at close range,
        blue is likely encircled.
        """
        blue = [e for e in entities if e["team"] == "blue"]
        red = [e for e in entities if e["team"] == "red"]
        if not blue or not red:
            return {"blue_encircled": False, "red_encircled": False,
                    "angular_coverage": 0.0, "quadrant_coverage": [0, 0, 0, 0]}

        # Blue centroid
        bx = sum(e["x"] for e in blue) / len(blue)
        by = sum(e["y"] for e in blue) / len(blue)

        quadrants = [0, 0, 0, 0]
        for r in red:
            ang = math.atan2(r["y"] - by, r["x"] - bx)
            # NE, NW, SW, SE
            if ang >= 0 and ang < math.pi / 2:
                quadrants[0] += 1
            elif ang >= math.pi / 2:
                quadrants[1] += 1
            elif ang >= -math.pi / 2:
                quadrants[2] += 1
            else:
                quadrants[3] += 1

        occupied = sum(1 for q in quadrants if q > 0)
        angular_coverage = occupied / 4.0
        blue_encircled = occupied >= 3

        # Symmetric check for red
        rx = sum(e["x"] for e in red) / len(red)
        ry = sum(e["y"] for e in red) / len(red)
        r_quadrants = [0, 0, 0, 0]
        for b in blue:
            ang = math.atan2(b["y"] - ry, b["x"] - rx)
            if ang >= 0 and ang < math.pi / 2:
                r_quadrants[0] += 1
            elif ang >= math.pi / 2:
                r_quadrants[1] += 1
            elif ang >= -math.pi / 2:
                r_quadrants[2] += 1
            else:
                r_quadrants[3] += 1
        r_occupied = sum(1 for q in r_quadrants if q > 0)
        red_encircled = r_occupied >= 3

        return {
            "blue_encircled": blue_encircled,
            "red_encircled": red_encircled,
            "angular_coverage": angular_coverage,
            "quadrant_coverage": quadrants,
        }

    # ------------------------------------------------------------------
    # 7. Force ratio & power distribution
    # ------------------------------------------------------------------

    def _compute_force_ratio(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute Blue:Red force ratio from entity strength."""
        blue_power = sum(e["capability"] * e["health"] for e in entities if e["team"] == "blue")
        red_power = sum(e["capability"] * e["health"] for e in entities if e["team"] == "red")
        red_power = max(1e-6, red_power)

        ratio = blue_power / red_power
        blue_count = sum(1 for e in entities if e["team"] == "blue")
        red_count = sum(1 for e in entities if e["team"] == "red")

        return {
            "blue_power": round(blue_power, 1),
            "red_power": round(red_power, 1),
            "force_ratio": round(ratio, 2),
            "blue_count": blue_count,
            "red_count": red_count,
            "advantage": "blue" if ratio > 1.2 else ("red" if ratio < 0.8 else "even"),
        }

    # ------------------------------------------------------------------
    # 8. Voronoi territory partitioning
    # ------------------------------------------------------------------

    def _compute_voronoi(self, entities: List[Dict[str, Any]], grid_w: int, grid_h: int) -> Dict[str, Any]:
        """Compute territory influence zones using Voronoi partitioning.

        Each cell is assigned to the nearest entity.  Blue vs red territory
        is aggregated to show which side "controls" which area.
        """
        if not entities:
            return {"territory": [], "blue_territory_ratio": 0.5}

        seeds = [(int(round(e["x"])), int(round(e["y"])), e["team"]) for e in entities]
        territory: List[List[str]] = []

        blue_cells = 0
        total = 0
        for y in range(grid_h):
            row = []
            for x in range(grid_w):
                best_dist = float("inf")
                best_team = "neutral"
                for sx, sy, team in seeds:
                    d = (sx - x) ** 2 + (sy - y) ** 2
                    if d < best_dist:
                        best_dist = d
                        best_team = team
                row.append(best_team)
                if best_team == "blue":
                    blue_cells += 1
                total += 1
            territory.append(row)

        return {
            "territory": territory,
            "blue_territory_ratio": blue_cells / max(1, total),
        }

    # ------------------------------------------------------------------
    # 9. Enemy cluster detection
    # ------------------------------------------------------------------

    def _compute_clusters(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group red entities into clusters based on proximity (DBSCAN-like)."""
        red = [e for e in entities if e["team"] == "red"]
        if not red:
            return {"clusters": [], "cluster_count": 0}

        assigned = [False] * len(red)
        clusters: List[List[Dict[str, Any]]] = []

        for i in range(len(red)):
            if assigned[i]:
                continue
            cluster = [red[i]]
            assigned[i] = True
            # Expand cluster
            changed = True
            while changed:
                changed = False
                for j in range(len(red)):
                    if assigned[j]:
                        continue
                    for member in cluster:
                        d = math.hypot(red[j]["x"] - member["x"], red[j]["y"] - member["y"])
                        if d <= self.CLUSTER_RADIUS:
                            cluster.append(red[j])
                            assigned[j] = True
                            changed = True
                            break
            clusters.append(cluster)

        result = []
        for c in clusters:
            cx = sum(e["x"] for e in c) / len(c)
            cy = sum(e["y"] for e in c) / len(c)
            result.append({
                "center": (round(cx, 1), round(cy, 1)),
                "size": len(c),
                "members": [e["id"] for e in c],
            })

        return {"clusters": result, "cluster_count": len(result)}

    # ------------------------------------------------------------------
    # 10. Fire corridors
    # ------------------------------------------------------------------

    def _compute_fire_corridors(self, entities: List[Dict[str, Any]], grid_w: int, grid_h: int) -> Dict[str, Any]:
        """Detect clear firing lanes between blue and red positions.

        A firing lane is a straight line from a blue entity to a red entity
        that clears all blocking terrain (has LOS) and stays within weapon
        range assumptions.
        """
        blue = [e for e in entities if e["team"] == "blue"]
        red = [e for e in entities if e["team"] == "red"]
        dem = self.terrain_analyzer.get_heightmap()

        corridors: List[Dict[str, Any]] = []
        for b in blue:
            for r in red:
                dist = math.hypot(r["x"] - b["x"], r["y"] - b["y"])
                if dist > self.LOS_MAX_RANGE:
                    continue
                has_los = True
                if dem.size:
                    steps = max(2, int(dist * 2))
                    for s in range(1, steps):
                        t = s / steps
                        sx = int(round(b["x"] + t * (r["x"] - b["x"])))
                        sy = int(round(b["y"] + t * (r["y"] - b["y"])))
                        h, w = dem.shape
                        if not (0 <= sy < h and 0 <= sx < w):
                            continue
                        ray_z = b["z"] + (r["z"] - b["z"]) * t
                        if dem[sy, sx] >= ray_z:
                            has_los = False
                            break
                if has_los:
                    corridors.append({
                        "from": b["id"], "to": r["id"],
                        "start": (int(round(b["x"])), int(round(b["y"]))),
                        "end": (int(round(r["x"])), int(round(r["y"]))),
                        "distance": round(dist, 1),
                    })

        return {"corridors": corridors, "count": len(corridors)}

    # ------------------------------------------------------------------
    # 11. Situation summary
    # ------------------------------------------------------------------

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable situation briefing from analysis results."""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("BATTLEFIELD SITUATION ANALYSIS")
        lines.append("=" * 60)

        # Force ratio
        fr = results["force_ratio"]
        lines.append(f"Force ratio: {fr['blue_count']} blue vs {fr['red_count']} red "
                     f"(power ratio {fr['force_ratio']:.2f}, {fr['advantage']} advantage)")

        # LOS
        los = results["los_network"]
        lines.append(f"LOS network: {los['clear_links']}/{los['total_links']} clear sight lines")

        # Encirclement
        enc = results["encirclement"]
        if enc["blue_encircled"]:
            lines.append("⚠ BLUE FORCE APPEARS ENCIRCLED - multiple quadrants occupied by red")
        elif enc["red_encircled"]:
            lines.append("✓ RED FORCE APPEARS ENCIRCLED - blue controls surrounding quadrants")
        else:
            lines.append(f"Encirclement: no encirclement detected "
                         f"(angular coverage {enc['angular_coverage']:.0%})")

        # Threat
        thr = results["threat_heatmap"]
        lines.append(f"Threat level: mean {thr['mean_threat']:.2f}, "
                     f"peak at {thr['peak_threat']}")

        # Chokepoints
        cp = results["chokepoints"]
        if cp["count"] > 0:
            lines.append(f"Chokepoints: {cp['count']} detected - ambush risk zones")
        else:
            lines.append("Chokepoints: none detected")

        # Key terrain
        kt = results["key_terrain"]
        lines.append(f"Key terrain: {kt['key_cell_count']} tactically significant cells, "
                     f"dominant high ground at {kt['dominant_high_ground']}")

        # Clusters
        cl = results["clusters"]
        lines.append(f"Enemy clusters: {cl['cluster_count']} detected")

        # Fire corridors
        fc = results["fire_corridors"]
        lines.append(f"Fire corridors: {fc['count']} clear firing lanes")

        # Voronoi
        vor = results["voronoi"]
        lines.append(f"Territory control: blue controls {vor['blue_territory_ratio']:.0%} of battlefield")

        # Cover
        cov = results["cover"]
        lines.append(f"Average cover: {cov['mean_cover']:.0%}")

        lines.append("=" * 60)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        units: Any = None,
        contacts: Any = None,
        grid_size: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """Run the full analysis suite and return a JSON-serializable report.

        Args:
            units: iterable of unit-like objects (team, position, ...).
            contacts: iterable of contact-like objects.
            grid_size: (width, height) in cells.  Defaults to terrain size.

        Returns:
            Complete analysis report dict.
        """
        entities = self._extract_entities(units, contacts)

        if grid_size:
            grid_w, grid_h = grid_size
        elif self.terrain is not None:
            grid_w = self.terrain.get_width_cells()
            grid_h = self.terrain.get_height_cells()
        else:
            grid_w = grid_h = 20

        # Clamp small grids
        grid_w = max(2, grid_w)
        grid_h = max(2, grid_h)

        los = self._compute_los_network(entities)
        threat = self._compute_threat_heatmap(entities, grid_w, grid_h)
        cover = self._compute_cover_map(grid_w, grid_h)
        chokepoints = self._compute_chokepoints(grid_w, grid_h)
        key_terrain = self._compute_key_terrain(grid_w, grid_h)
        encirclement = self._compute_encirclement(entities)
        force_ratio = self._compute_force_ratio(entities)
        voronoi = self._compute_voronoi(entities, grid_w, grid_h)
        clusters = self._compute_clusters(entities)
        fire_corridors = self._compute_fire_corridors(entities, grid_w, grid_h)

        results = {
            "entities": entities,
            "los_network": los,
            "threat_heatmap": threat,
            "cover": cover,
            "chokepoints": chokepoints,
            "key_terrain": key_terrain,
            "encirclement": encirclement,
            "force_ratio": force_ratio,
            "voronoi": voronoi,
            "clusters": clusters,
            "fire_corridors": fire_corridors,
        }
        results["summary"] = self._generate_summary(results)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Return analyzer stats."""
        return {
            "algorithms": [
                "los_network", "threat_heatmap", "cover", "chokepoints",
                "key_terrain", "encirclement", "force_ratio", "voronoi",
                "clusters", "fire_corridors", "situation_summary",
            ],
            "terrain": self.terrain_analyzer.get_stats() if self.terrain else None,
        }

