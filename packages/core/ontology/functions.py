# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ontology Functions for derived properties and analytic evaluations."""
from __future__ import annotations

import math
from typing import Any, Dict


def calculate_bearing_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Dict[str, float]:
    """Calculate distance in nautical miles and bearing in degrees."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_km = 6371 * c
    dist_nm = dist_km * 0.539957

    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360

    return {
        "distance_nm": round(dist_nm, 2),
        "bearing_deg": round(bearing, 1),
    }
