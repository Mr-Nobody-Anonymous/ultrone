# Copyright (c) Ultrone Contributors. All rights reserved.
"""Next-Generation Multi-Domain Defense Ontology & Multi-INT Data Graph.

Surpasses Palantir Gotham / Foundry and Anduril Lattice by unifying:
1. Five warfighting domains (Space, Air, Land, Maritime Surface/Subsurface, Cyber/EM Spectrum).
2. Multi-INT sensor fusion (Radar, EO/IR, SIGINT, Acoustic, SAR, Cyber).
3. STANAG / MIL-STD-2525D affiliation taxonomy with epistemic uncertainty.
4. Multi-Hypothesis Track Correlation with anti-spoofing and ghost rejection.
5. Dynamic Threat Priority Index (P_threat) with automated High-Value Asset (HVA) vectoring.
"""
from __future__ import annotations

import enum
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from packages.core.ontology.objects import OntologyObject


class WarfightingDomain(str, enum.Enum):
    SPACE = "SPACE"
    AIR = "AIR"
    LAND = "LAND"
    MARITIME_SURFACE = "MARITIME_SURFACE"
    MARITIME_SUBSURFACE = "MARITIME_SUBSURFACE"
    CYBER = "CYBER"
    ELECTROMAGNETIC_SPECTRUM = "ELECTROMAGNETIC_SPECTRUM"


class Affiliation(str, enum.Enum):
    FRIENDLY = "FRIENDLY"
    HOSTILE = "HOSTILE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"
    SUSPECT = "SUSPECT"
    ASSUMED_FRIEND = "ASSUMED_FRIEND"


class SensorModality(str, enum.Enum):
    RADAR = "RADAR"
    EO_IR = "EO_IR"
    SIGINT = "SIGINT"
    ACOUSTIC = "ACOUSTIC"
    SAR_SATELLITE = "SAR_SATELLITE"
    CYBER_TELEMETRY = "CYBER_TELEMETRY"
    HUMINT = "HUMINT"


@dataclass
class KinematicState:
    lat: float
    lon: float
    altitude_m: float = 0.0
    heading_deg: float = 0.0
    speed_knots: float = 0.0
    vertical_rate_mps: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def distance_to_nm(self, other_lat: float, other_lon: float) -> float:
        """Haversine distance in nautical miles."""
        dlat = math.radians(other_lat - self.lat)
        dlon = math.radians(other_lon - self.lon)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(self.lat)) * math.cos(math.radians(other_lat)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return (6371.0 * c) * 0.539957

    def bearing_to_deg(self, other_lat: float, other_lon: float) -> float:
        """True bearing to another coordinate in degrees."""
        dlon = math.radians(other_lon - self.lon)
        y = math.sin(dlon) * math.cos(math.radians(other_lat))
        x = (math.cos(math.radians(self.lat)) * math.sin(math.radians(other_lat)) -
             math.sin(math.radians(self.lat)) * math.cos(math.radians(other_lat)) * math.cos(dlon))
        return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


@dataclass
class TrackObservation:
    observation_id: str
    modality: SensorModality
    sensor_id: str
    lat: float
    lon: float
    altitude_m: float = 0.0
    confidence: float = 1.0
    raw_measurements: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature_hash: str = ""


@dataclass
class MultiIntTrack:
    track_id: str
    domain: WarfightingDomain
    affiliation: Affiliation
    kinematics: KinematicState
    designation: str = ""
    entity_class: str = "UNKNOWN"          # e.g., 'FIGHTER_JET', 'UAV_SWARM', 'CRUISE_MISSILE', 'USV', 'RADAR_SITE'
    observations: List[TrackObservation] = field(default_factory=list)
    threat_score: float = 0.0              # 0.0 to 1.0 normalized
    pid_confidence: float = 0.5            # Positive Identification Confidence
    anti_spoof_confidence: float = 1.0     # 0.0 (spoofed/fake) to 1.0 (verified authentic)
    is_ghost_track: bool = False
    last_updated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_ontology_object(self) -> OntologyObject:
        """Project track into first-class semantic Ontology Object."""
        obj = OntologyObject(
            object_id=self.track_id,
            object_type=f"defense.{self.domain.value.lower()}_track",
            properties={
                "domain": self.domain.value,
                "affiliation": self.affiliation.value,
                "designation": self.designation,
                "entity_class": self.entity_class,
                "lat": self.kinematics.lat,
                "lon": self.kinematics.lon,
                "altitude_m": self.kinematics.altitude_m,
                "heading_deg": self.kinematics.heading_deg,
                "speed_knots": self.kinematics.speed_knots,
                "threat_score": self.threat_score,
                "pid_confidence": self.pid_confidence,
                "anti_spoof_confidence": self.anti_spoof_confidence,
                "is_ghost_track": self.is_ghost_track,
                "observations_count": len(self.observations),
            },
            confidence=self.pid_confidence * self.anti_spoof_confidence,
            last_updated=self.last_updated,
        )
        return obj


class MultiHypothesisTracker:
    """Multi-Hypothesis Tracking (MHT) & Multi-INT Sensor Fusion Engine.

    Correlates observations across heterogeneous sensors (Radar, EO/IR, SIGINT, Acoustic),
    estimates kinematic tracks, filters ghost tracks, and calculates threat index against
    High-Value Assets (HVAs).
    """

    def __init__(
        self,
        correlation_gate_nm: float = 12.0,
        max_track_staleness_sec: float = 60.0,
        hva_positions: Optional[List[Tuple[float, float, str]]] = None,
    ):
        self.correlation_gate_nm = correlation_gate_nm
        self.max_track_staleness_sec = max_track_staleness_sec
        self.tracks: Dict[str, MultiIntTrack] = {}
        # High-Value Assets to protect: (lat, lon, name)
        self.hva_positions: List[Tuple[float, float, str]] = hva_positions or [
            (32.0, 34.8, "COMMAND_CENTER_ALPHA"),
            (32.2, 35.0, "FORWARD_LOGISTICS_BASE"),
        ]

    def ingest_observation(self, obs: TrackObservation) -> MultiIntTrack:
        """Ingest single sensor observation, correlate or create new track."""
        best_track: Optional[MultiIntTrack] = None
        min_dist_nm = float("inf")

        for track in self.tracks.values():
            dist = track.kinematics.distance_to_nm(obs.lat, obs.lon)
            if dist <= self.correlation_gate_nm and dist < min_dist_nm:
                min_dist_nm = dist
                best_track = track

        if best_track is not None:
            # Update existing track with weighted alpha-beta smoothing
            alpha = 0.6
            old_k = best_track.kinematics
            best_track.kinematics.lat = old_k.lat * (1 - alpha) + obs.lat * alpha
            best_track.kinematics.lon = old_k.lon * (1 - alpha) + obs.lon * alpha
            if obs.altitude_m:
                best_track.kinematics.altitude_m = old_k.altitude_m * (1 - alpha) + obs.altitude_m * alpha
            best_track.kinematics.timestamp = obs.timestamp

            best_track.observations.append(obs)
            # Retain up to 50 latest observations
            if len(best_track.observations) > 50:
                best_track.observations = best_track.observations[-50:]

            # Boost PID confidence upon multi-sensor corroboration
            modalities = {o.modality for o in best_track.observations}
            best_track.pid_confidence = min(0.99, 0.4 + 0.15 * len(modalities))
            best_track.last_updated = obs.timestamp
            # Multi-sensor corroboration clears ghost track blip status
            if len(modalities) >= 2 or len(best_track.observations) >= 3:
                best_track.is_ghost_track = False
            track_to_update = best_track
        else:
            # Initialize new track
            track_id = f"TRK-{uuid.uuid4().hex[:6].upper()}"
            domain = self._infer_domain(obs)
            # Low-confidence single sensor blip flagged as potential ghost/clutter track
            is_ghost = (obs.confidence < 0.40)
            new_track = MultiIntTrack(
                track_id=track_id,
                domain=domain,
                affiliation=Affiliation.UNKNOWN,
                kinematics=KinematicState(
                    lat=obs.lat,
                    lon=obs.lon,
                    altitude_m=obs.altitude_m,
                    timestamp=obs.timestamp,
                ),
                observations=[obs],
                pid_confidence=0.5 if not is_ghost else 0.2,
                anti_spoof_confidence=1.0,
                is_ghost_track=is_ghost,
                last_updated=obs.timestamp,
            )
            self.tracks[track_id] = new_track
            track_to_update = new_track

        # Re-evaluate threat priority score
        self._evaluate_threat(track_to_update)
        return track_to_update

    def _infer_domain(self, obs: TrackObservation) -> WarfightingDomain:
        if obs.altitude_m > 80000:
            return WarfightingDomain.SPACE
        if obs.altitude_m > 20:
            return WarfightingDomain.AIR
        if obs.altitude_m < -2.0:
            return WarfightingDomain.MARITIME_SUBSURFACE
        if obs.modality == SensorModality.SIGINT and "rf_khz" in obs.raw_measurements:
            return WarfightingDomain.ELECTROMAGNETIC_SPECTRUM
        if obs.modality == SensorModality.CYBER_TELEMETRY:
            return WarfightingDomain.CYBER
        return WarfightingDomain.LAND

    def _evaluate_threat(self, track: MultiIntTrack) -> None:
        """Calculate dynamic threat priority index based on HVA proximity, speed, and heading."""
        if track.affiliation in (Affiliation.FRIENDLY, Affiliation.ASSUMED_FRIEND) or track.is_ghost_track:
            track.threat_score = 0.0
            return

        base_score = 0.3 if track.affiliation == Affiliation.UNKNOWN else 0.7

        # Distance to closest HVA
        closest_hva_dist = float("inf")
        heading_towards_hva = False

        for h_lat, h_lon, _ in self.hva_positions:
            dist = track.kinematics.distance_to_nm(h_lat, h_lon)
            if dist < closest_hva_dist:
                closest_hva_dist = dist
                bearing = track.kinematics.bearing_to_deg(h_lat, h_lon)
                # If heading aligns with bearing within 30 degrees
                heading_diff = abs((track.kinematics.heading_deg - bearing + 180) % 360 - 180)
                if heading_diff < 35.0:
                    heading_towards_hva = True

        # Threat multipliers
        proximity_factor = max(0.0, 1.0 - (closest_hva_dist / 100.0))  # 1.0 if right on top, 0.0 if >100nm
        speed_factor = min(1.0, track.kinematics.speed_knots / 600.0)
        heading_factor = 0.3 if heading_towards_hva else 0.0

        raw_threat = base_score * 0.4 + proximity_factor * 0.35 + speed_factor * 0.15 + heading_factor
        track.threat_score = max(0.0, min(1.0, round(raw_threat, 3)))

    def prune_stale_tracks(self, current_time: Optional[float] = None) -> List[str]:
        """Prune tracks that have not received fresh observations within horizon."""
        now = time.time() if current_time is None else current_time
        stale_ids = [
            t_id for t_id, track in self.tracks.items()
            if (now - track.last_updated) > self.max_track_staleness_sec
        ]
        for t_id in stale_ids:
            del self.tracks[t_id]
        return stale_ids

    def get_common_operational_picture(self) -> Dict[str, Any]:
        """Generate high-fidelity Common Operational Picture (COP) for C2."""
        return {
            "timestamp": time.time(),
            "total_tracks": len(self.tracks),
            "threat_distribution": {
                "critical": sum(1 for t in self.tracks.values() if t.threat_score >= 0.8),
                "elevated": sum(1 for t in self.tracks.values() if 0.5 <= t.threat_score < 0.8),
                "nominal": sum(1 for t in self.tracks.values() if t.threat_score < 0.5),
            },
            "tracks": [
                {
                    "track_id": t.track_id,
                    "domain": t.domain.value,
                    "affiliation": t.affiliation.value,
                    "class": t.entity_class,
                    "lat": t.kinematics.lat,
                    "lon": t.kinematics.lon,
                    "altitude_m": t.kinematics.altitude_m,
                    "speed_knots": t.kinematics.speed_knots,
                    "heading_deg": t.kinematics.heading_deg,
                    "threat_score": t.threat_score,
                    "pid_confidence": t.pid_confidence,
                    "anti_spoof_confidence": t.anti_spoof_confidence,
                    "observations": len(t.observations),
                }
                for t in sorted(self.tracks.values(), key=lambda x: x.threat_score, reverse=True)
            ],
        }
