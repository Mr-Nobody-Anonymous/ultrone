# Copyright (c) Ultrone Contributors. All rights reserved.
"""Geospatial visualization, layers, 3D terrain/tiles, tracks, and spatial indexing."""
from packages.geospatial.layers import (
    LayerCategory,
    LayerType,
    LayerDefinition,
    LayerRegistry,
    CANONICAL_LAYERS,
)
from packages.geospatial.terrain import TerrainProvider, ElevationMesh
from packages.geospatial.imagery import ImageryProvider, WMSClient
from packages.geospatial.tiles3d import Tileset3D, Tile3DNode, BoundingVolume
from packages.geospatial.vector_tiles import VectorFeature, VectorTileLayer, MVTDecoder
from packages.geospatial.tracks import Waypoint, TrackHistory, TrackManager
from packages.geospatial.spatial_index import BoundingBox, SpatialIndex

__all__ = [
    "LayerCategory",
    "LayerType",
    "LayerDefinition",
    "LayerRegistry",
    "CANONICAL_LAYERS",
    "TerrainProvider",
    "ElevationMesh",
    "ImageryProvider",
    "WMSClient",
    "Tileset3D",
    "Tile3DNode",
    "BoundingVolume",
    "VectorFeature",
    "VectorTileLayer",
    "MVTDecoder",
    "Waypoint",
    "TrackHistory",
    "TrackManager",
    "BoundingBox",
    "SpatialIndex",
]
