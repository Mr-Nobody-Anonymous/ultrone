"""ULTRONE Geospatial - 3D Tiles 1.1 hierarchical bounding volumes, b3dm, and urban structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BoundingVolume:
    """Bounding volume hierarchy (box, sphere, or region)."""
    volume_type: str = "region"  # 'region', 'box', 'sphere'
    coords: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {self.volume_type: self.coords}


@dataclass
class Tile3DNode:
    """Single node in a 3D Tiles spatial index."""
    geometric_error: float
    bounding_volume: BoundingVolume
    content_uri: Optional[str] = None
    refine: str = "ADD"  # or 'REPLACE'
    children: List["Tile3DNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "geometricError": self.geometric_error,
            "boundingVolume": self.bounding_volume.to_dict(),
            "refine": self.refine,
        }
        if self.content_uri:
            res["content"] = {"uri": self.content_uri}
        if self.children:
            res["children"] = [c.to_dict() for c in self.children]
        return res


class Tileset3D:
    """Container for 3D Tiles 1.1 specification."""

    def __init__(self, root: Tile3DNode, asset_version: str = "1.1"):
        self.root = root
        self.asset_version = asset_version

    def to_json(self) -> Dict[str, Any]:
        return {
            "asset": {"version": self.asset_version, "generator": "ULTRONE 3D Tiles Engine"},
            "geometricError": self.root.geometric_error,
            "root": self.root.to_dict(),
        }


__all__ = ["BoundingVolume", "Tile3DNode", "Tileset3D"]
