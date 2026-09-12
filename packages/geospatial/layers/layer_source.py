# Copyright (c) Ultrone Contributors. All rights reserved.
"""Layer data sources and provider configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class MapProviderConfig:
    """Configurable map provider (OSM, MapTiler, PMTiles, Cesium ion)."""
    provider_name: str = "osm"
    style_url: str = ""
    tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    cesium_ion_token: str = ""

    @classmethod
    def from_env(cls) -> MapProviderConfig:
        return cls(
            provider_name=os.environ.get("ULTRONE_MAP_PROVIDER", "osm"),
            style_url=os.environ.get("ULTRONE_MAP_STYLE", ""),
            tile_url=os.environ.get("ULTRONE_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
            cesium_ion_token=os.environ.get("CESIUM_ION_TOKEN", ""),
        )
