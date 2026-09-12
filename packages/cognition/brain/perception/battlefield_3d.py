# Copyright (c) Ultrone Contributors. All rights reserved.
"""3D battlefield scene exporter - converts analysis into a Three.js scene.

Builds a JSON-serializable 3D scene that the frontend ``Terrain3DMap``
component renders with Three.js:

- Terrain mesh (heightmap + hillshade colour)
- Entity markers (blue/red with altitude)
- Line-of-sight lines
- Threat-zone cones/rings
- Chokepoint & key-terrain markers
- Fire-corridor lines
- Voronoi territory overlay colours
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .terrain_analyzer import TerrainAnalyzer
from .battlefield_analyzer import BattlefieldAnalyzer

logger = logging.getLogger("Ultrone.Brain.Perception.Battlefield3D")


class Battlefield3DExporter:
    """Builds a Three.js-compatible 3D scene from battlefield state."""

    # Entity marker colours
    BLUE_COLOR = "#3b82f6"
    RED_COLOR = "#ef4444"
    NEUTRAL_COLOR = "#94a3b8"
    SUPPLY_COLOR = "#22c55e"

    # Scene scaling factors
    HEIGHT_SCALE = 2.0        # Vertical exaggeration for terrain
    GRID_TO_WORLD = 1.0       # 1 grid cell = 1 world unit

    def __init__(
        self,
        terrain_analyzer: Optional[TerrainAnalyzer] = None,
        battlefield_analyzer: Optional[BattlefieldAnalyzer] = None,
    ) -> None:
        self.terrain_analyzer = terrain_analyzer or TerrainAnalyzer()
        self.battlefield_analyzer = battlefield_analyzer or BattlefieldAnalyzer(
            self.terrain_analyzer.terrain
        )

    # ------------------------------------------------------------------
    # Terrain mesh
    # ------------------------------------------------------------------

    def _build_terrain_mesh(self) -> Dict[str, Any]:
        """Build the terrain mesh data for Three.js."""
        dem = self.terrain_analyzer.get_heightmap()
        hillshade = self.terrain_analyzer.get_hillshade()

        if dem.size == 0:
            return {"width": 20, "height": 20, "heights": [], "colors": []}

        h, w = dem.shape
        # Heights as flat list (row-major)
        heights = (dem * self.HEIGHT_SCALE).astype(float).tolist()

        # Colour per vertex from hillshade + elevation gradient
        colors = []
        elev_min = float(dem.min())
        elev_max = float(dem.max())
        elev_range = max(1e-6, elev_max - elev_min)

        for y in range(h):
            for x in range(w):
                # Normalised elevation for colour ramp (green -> brown -> white)
                norm = (dem[y, x] - elev_min) / elev_range
                shade = hillshade[y, x] / 255.0

                if norm < 0.33:
                    r, g, b = 34, 120, 60       # green
                elif norm < 0.66:
                    r, g, b = 124, 94, 58       # brown
                else:
                    r, g, b = 190, 190, 200     # rocky / snow

                # Apply hillshade
                r = int(r * (0.5 + 0.5 * shade))
                g = int(g * (0.5 + 0.5 * shade))
                b = int(b * (0.5 + 0.5 * shade))

                colors.append(f"rgb({r},{g},{b})")

        return {
            "width": w,
            "height": h,
            "heights": heights,
            "colors": colors,
            "height_scale": self.HEIGHT_SCALE,
        }

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def _build_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert entities into 3D marker definitions."""
        markers = []
        for e in entities:
            team = e.get("team", "unknown")
            color = {
                "blue": self.BLUE_COLOR,
                "red": self.RED_COLOR,
            }.get(team, self.NEUTRAL_COLOR)

            etype = e.get("type", "entity")
            if "supply" in str(etype):
                color = self.SUPPLY_COLOR

            markers.append({
                "id": e["id"],
                "team": team,
                "type": etype,
                "position": [e["x"], e["z"] * self.HEIGHT_SCALE, e["y"]],
                "color": color,
                "health": e.get("health", 100),
                "label": e["id"],
            })
        return markers

    # ------------------------------------------------------------------
    # LOS lines
    # ------------------------------------------------------------------

    def _build_los_lines(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert LOS links into 3D line segments."""
        lines = []
        los = analysis.get("los_network", {})
        entity_pos = {e["id"]: (e["x"], e["z"], e["y"]) for e in analysis.get("entities", [])}

        for link in los.get("clear", []):
            src = entity_pos.get(link["source"])
            tgt = entity_pos.get(link["target"])
            if src and tgt:
                lines.append({
                    "type": "los",
                    "start": [src[0], src[1] * self.HEIGHT_SCALE + 3, src[2]],
                    "end": [tgt[0], tgt[1] * self.HEIGHT_SCALE + 3, tgt[2]],
                    "color": "#22c55e",
                    "opacity": 0.4,
                    "team_pair": f"{link['source_team']}-{link['target_team']}",
                })
        return lines

    # ------------------------------------------------------------------
    # Fire corridors
    # ------------------------------------------------------------------

    def _build_fire_corridors(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert fire corridors into 3D line segments."""
        lines = []
        corridors = analysis.get("fire_corridors", {}).get("corridors", [])

        for c in corridors:
            sx, sy = c["start"]
            ex, ey = c["end"]
            sz = self.terrain_analyzer.get_elevation_at(sx, sy) * self.HEIGHT_SCALE
            ez = self.terrain_analyzer.get_elevation_at(ex, ey) * self.HEIGHT_SCALE
            lines.append({
                "type": "fire_corridor",
                "start": [sx, sz + 2, sy],
                "end": [ex, ez + 2, ey],
                "color": "#f59e0b",
                "opacity": 0.6,
            })
        return lines

    # ------------------------------------------------------------------
    # Threat zones
    # ------------------------------------------------------------------

    def _build_threat_zones(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert threat heatmap into 3D rings at high-threat cells."""
        zones = []
        heat = analysis.get("threat_heatmap", {})
        heatmap = heat.get("heatmap", [])
        if not heatmap:
            return zones

        arr = np.array(heatmap, dtype=float)
        if arr.size == 0:
            return zones

        # Find cells above 80th percentile as threat zones
        threshold = np.percentile(arr, 80) if arr.max() > 0 else 1.0
        idx = np.argwhere(arr >= threshold)

        # Limit to top 20 zones
        for y, x in idx[:20]:
            if arr[y, x] <= 0:
                continue
            z = self.terrain_analyzer.get_elevation_at(int(x), int(y)) * self.HEIGHT_SCALE
            zones.append({
                "position": [int(x), z + 1, int(y)],
                "radius": 3 + 3 * float(arr[y, x]),
                "intensity": float(arr[y, x]),
                "color": "#ef4444",
            })
        return zones

    # ------------------------------------------------------------------
    # Chokepoints & key terrain
    # ------------------------------------------------------------------

    def _build_chokepoints(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert chokepoints into 3D markers."""
        markers = []
        cps = analysis.get("chokepoints", {}).get("chokepoints", [])
        for cp in cps:
            x, y = cp["x"], cp["y"]
            z = self.terrain_analyzer.get_elevation_at(x, y) * self.HEIGHT_SCALE
            markers.append({
                "position": [x, z + 2, y],
                "color": "#8b5cf6",
                "label": f"CHOKE ({x},{y})",
            })
        return markers

    def _build_key_terrain(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert key terrain cells into 3D markers."""
        markers = []
        kt = analysis.get("key_terrain", {}).get("key_terrain", [])
        for cell in kt[:20]:
            x, y = cell["x"], cell["y"]
            z = self.terrain_analyzer.get_elevation_at(x, y) * self.HEIGHT_SCALE
            markers.append({
                "position": [x, z + 2, y],
                "color": "#facc15",
                "label": f"KEY ({x},{y})",
            })
        return markers

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def export_scene(
        self,
        units: Any = None,
        contacts: Any = None,
        grid_size: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """Build the complete 3D scene for the frontend.

        Returns a JSON-serializable dict:
        {
            terrain: {...}, entities: [...], los_lines: [...],
            fire_corridors: [...], threat_zones: [...],
            chokepoints: [...], key_terrain: [...], analysis: {...}
        }
        """
        analysis = self.battlefield_analyzer.analyze(units, contacts, grid_size)

        scene = {
            "terrain": self._build_terrain_mesh(),
            "entities": self._build_entities(analysis["entities"]),
            "los_lines": self._build_los_lines(analysis),
            "fire_corridors": self._build_fire_corridors(analysis),
            "threat_zones": self._build_threat_zones(analysis),
            "chokepoints": self._build_chokepoints(analysis),
            "key_terrain": self._build_key_terrain(analysis),
            "analysis": analysis,
        }
        return scene

    def get_stats(self) -> Dict[str, Any]:
        """Return exporter stats."""
        return {
            "type": "Battlefield3DExporter",
            "scene_components": [
                "terrain", "entities", "los_lines", "fire_corridors",
                "threat_zones", "chokepoints", "key_terrain", "analysis",
            ],
        }

