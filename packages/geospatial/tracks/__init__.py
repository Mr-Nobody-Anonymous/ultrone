"""ULTRONE Geospatial - Track management, kinematic dead reckoning, and trajectory history."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Waypoint:
    lat: float
    lon: float
    altitude_m: float = 0.0
    heading_deg: float = 0.0
    speed_mps: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitude_m": self.altitude_m,
            "heading_deg": self.heading_deg,
            "speed_mps": self.speed_mps,
            "timestamp": self.timestamp,
        }


@dataclass
class TrackHistory:
    entity_id: str
    max_history: int = 100
    waypoints: List[Waypoint] = field(default_factory=list)

    def add_waypoint(self, wp: Waypoint) -> None:
        self.waypoints.append(wp)
        if len(self.waypoints) > self.max_history:
            self.waypoints.pop(0)

    def to_line_string(self) -> List[Tuple[float, float]]:
        return [(wp.lon, wp.lat) for wp in self.waypoints]

    def predict_future_position(self, delta_seconds: float) -> Tuple[float, float, float]:
        """Kinematic dead reckoning projection based on latest waypoint velocity & heading."""
        if not self.waypoints:
            return (0.0, 0.0, 0.0)
        latest = self.waypoints[-1]
        dist_m = latest.speed_mps * delta_seconds
        # Approx 111,111 meters per degree latitude
        rad = math.radians(latest.heading_deg)
        d_lat = (dist_m * math.cos(rad)) / 111111.0
        d_lon = (dist_m * math.sin(rad)) / (111111.0 * max(0.1, math.cos(math.radians(latest.lat))))
        return (latest.lat + d_lat, latest.lon + d_lon, latest.altitude_m)


class TrackManager:
    """Manages active tracks and kinematic buffers for all monitored entities."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self._tracks: Dict[str, TrackHistory] = {}

    def update_track(self, entity_id: str, wp: Waypoint) -> TrackHistory:
        if entity_id not in self._tracks:
            self._tracks[entity_id] = TrackHistory(entity_id=entity_id, max_history=self.max_history)
        th = self._tracks[entity_id]
        th.add_waypoint(wp)
        return th

    def get_track(self, entity_id: str) -> Optional[TrackHistory]:
        return self._tracks.get(entity_id)

    def get_all_tracks(self) -> Dict[str, TrackHistory]:
        return self._tracks


__all__ = ["Waypoint", "TrackHistory", "TrackManager"]
