# Copyright (c) Ultrone Contributors. All rights reserved.
"""Geographic, coordinate, and boundary schemas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class GeoPoint:
    lat: float
    lng: float
    alt_m: float = 0.0


@dataclass
class BoundingBox:
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float

    def contains(self, point: GeoPoint) -> bool:
        return (
            self.min_lat <= point.lat <= self.max_lat
            and self.min_lng <= point.lng <= self.max_lng
        )


@dataclass
class GeoPolygon:
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    name: str = ""
