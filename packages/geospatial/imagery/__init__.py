"""ULTRONE Geospatial - Imagery providers, tile cascades, and WMS/XYZ endpoints."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImageryTile:
    z: int
    x: int
    y: int
    url: str
    content_type: str = "image/png"


class ImageryProvider:
    """Configures raster imagery feeds (OSM, Sentinel, MapTiler, PMTiles, Cesium Ion)."""

    def __init__(
        self,
        name: str = "open_street_map",
        tile_url_template: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        max_zoom: int = 19,
        min_zoom: int = 0,
        attribution: str = "© OpenStreetMap contributors",
    ):
        self.name = name
        self.tile_url_template = tile_url_template
        self.max_zoom = max_zoom
        self.min_zoom = min_zoom
        self.attribution = attribution

    def get_tile_url(self, z: int, x: int, y: int) -> str:
        return self.tile_url_template.format(z=z, x=x, y=y)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url_template": self.tile_url_template,
            "max_zoom": self.max_zoom,
            "min_zoom": self.min_zoom,
            "attribution": self.attribution,
        }


class WMSClient:
    """Client for OGC Web Map Service (WMS) layers."""

    def __init__(self, endpoint: str, layer_name: str, crs: str = "EPSG:3857"):
        self.endpoint = endpoint
        self.layer_name = layer_name
        self.crs = crs

    def build_get_map_url(self, bbox: tuple[float, float, float, float], width: int = 256, height: int = 256) -> str:
        b_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        return (
            f"{self.endpoint}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            f"&LAYERS={self.layer_name}&CRS={self.crs}&BBOX={b_str}"
            f"&WIDTH={width}&HEIGHT={height}&FORMAT=image/png"
        )


__all__ = ["ImageryTile", "ImageryProvider", "WMSClient"]
