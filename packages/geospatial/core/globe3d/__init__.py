# Copyright (c) Ultrone Contributors. All rights reserved.
"""3D Globe Engine definitions (CesiumJS / WebGL)."""
from dataclasses import dataclass


@dataclass
class Globe3DConfig:
    enable_terrain: bool = True
    enable_3d_buildings: bool = True
    ion_asset_id: int = 1  # Cesium World Terrain
    default_camera_pitch: float = 45.0
    default_camera_heading: float = 0.0
