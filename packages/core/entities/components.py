# Copyright (c) Ultrone Contributors. All rights reserved.
"""Composable Entity Component Definitions.

Inspired by Anduril Lattice entity component architecture.
Entities are composed of modular state components with confidence
and provenance tracking on every field.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpatialComponent:
    """Geospatial coordinates and orientation."""
    lat: float = 0.0
    lng: float = 0.0
    alt: float = 0.0          # Altitude in meters / feet
    heading: float = 0.0      # Heading in degrees [0, 360)
    pitch: float = 0.0
    roll: float = 0.0
    confidence: float = 1.0


@dataclass
class KinematicComponent:
    """Velocity, speed, and trajectory kinematics."""
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    speed_knots: float = 0.0
    acceleration: float = 0.0
    confidence: float = 1.0


@dataclass
class SensorComponent:
    """Sensor payloads and coverage parameters."""
    sensors: List[str] = field(default_factory=list)
    active_radars: List[str] = field(default_factory=list)
    sweep_rate_hz: float = 1.0
    coverage_azimuth: float = 360.0
    range_nm: float = 150.0
    confidence: float = 1.0


@dataclass
class IdentityComponent:
    """Identification Friend or Foe (IFF), callsign, and classification."""
    callsign: str = "UNKNOWN"
    iff_mode: str = "MODE_4"  # FRIEND, HOSTILE, NEUTRAL, UNKNOWN
    classification: str = "UNCLASSIFIED"
    domain: str = "AIR"       # AIR, GROUND, MARITIME, SPACE, CYBER
    confidence: float = 1.0


@dataclass
class ProvenanceComponent:
    """Lineage and derivation trail for auditability and human trust."""
    sources: List[str] = field(default_factory=list)
    pipeline_stage: str = "sensor_fusion_v2"
    fusion_model: str = "bayesian_filter"
    data_age_sec: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class OntologyComponent:
    """Palantir-inspired object links and actionable capabilities."""
    object_type: str = "Asset"
    links: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[str] = field(default_factory=lambda: [
        "Open Simulation",
        "Add to Investigation",
        "Annotate",
        "Export Trace",
    ])
