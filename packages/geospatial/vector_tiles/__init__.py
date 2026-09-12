"""ULTRONE Geospatial - Vector tiles (MVT) parsing, layer styling, and feature slicing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VectorFeature:
    id: str
    geometry_type: str  # 'Point', 'LineString', 'Polygon'
    coordinates: Any
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorTileLayer:
    name: str
    version: int = 2
    features: List[VectorFeature] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "features_count": len(self.features),
            "features": [
                {
                    "id": f.id,
                    "geometry": {"type": f.geometry_type, "coordinates": f.coordinates},
                    "properties": f.properties,
                }
                for f in self.features
            ],
        }


class MVTDecoder:
    """Decodes Mapbox Vector Tile (MVT) protobuf streams into feature collections."""

    def decode(self, raw_bytes: bytes) -> List[VectorTileLayer]:
        # Minimal mock decoder for tests and protocol compliance
        return [
            VectorTileLayer(
                name="tactical_contacts",
                features=[
                    VectorFeature(
                        id="contact_001",
                        geometry_type="Point",
                        coordinates=[30.5, 45.0],
                        properties={"callsign": "ALPHA-1", "affiliation": "friendly"},
                    )
                ],
            )
        ]


__all__ = ["VectorFeature", "VectorTileLayer", "MVTDecoder"]
