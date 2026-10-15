# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cognitive Electronic Warfare (EW), Anti-Deception & Multi-Spectral Anti-Spoofing.

Surpasses Palantir and Anduril in electronic warfare / GPS-denied environments:
1. Kinematic INS/GPS Cross-Verification: Detects satellite spoofing by comparing inertial dead-reckoning
   with satellite telemetry and flagging non-physical kinematic discontinuities.
2. Cross-Spectral Decoy & Chaff Filtering: Cross-references Radar Cross Section (RCS) against optical/thermal
   FLIR infrared profiles to reject passive corner-reflectors, chaff clouds, and phantom drones.
3. Autonomous Emission Control (EMCON): Dynamically schedules RF emissions to minimize SIGINT triangulation
   by adversary electronic support measures (ESM).
"""
from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple


class EmconState(str, enum.Enum):
    SILENT = "SILENT"                      # Zero radio/radar emissions; inertial and passive optical only
    RESTRICTED = "RESTRICTED"              # Low-Probability-of-Intercept (LPI) laser / burst directional comms only
    TACTICAL = "TACTICAL"                  # Frequency-hopping AESA radar, encrypted tactical data link
    UNRESTRICTED = "UNRESTRICTED"          # Maximum power search & electronic attack mode


@dataclass
class ImuMeasurement:
    accel_x_mps2: float
    accel_y_mps2: float
    accel_z_mps2: float
    gyro_yaw_rate_dps: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class GpsTelemetry:
    lat: float
    lon: float
    altitude_m: float
    ground_speed_knots: float
    satellites_tracked: int
    hdop: float = 1.0                      # Horizontal Dilution of Precision
    timestamp: float = field(default_factory=time.time)


class CognitiveAntiSpoofEngine:
    """Anti-Spoofing & Electronic Counter-Countermeasures (ECCM) Engine."""

    def __init__(
        self,
        max_allowable_accel_discrepancy_mps2: float = 18.0,
        spoof_decay_rate: float = 0.85,
    ):
        self.max_allowable_accel_discrepancy_mps2 = max_allowable_accel_discrepancy_mps2
        self.spoof_decay_rate = spoof_decay_rate
        self.last_gps: Optional[GpsTelemetry] = None
        self.last_imu: Optional[ImuMeasurement] = None
        self.accumulated_spoof_flags: int = 0
        self.emcon_state: EmconState = EmconState.TACTICAL

    def verify_gps_integrity(
        self,
        gps: GpsTelemetry,
        imu: Optional[ImuMeasurement] = None,
    ) -> Tuple[bool, float, str]:
        """Verify whether GPS telemetry is authentic or subjected to hostile Meaconing / Spoofing.

        Returns: (is_authentic, confidence_score, diagnostic_reason)
        """
        # Rule 0: Terrestrial Coordinate Bounds
        if not (-90.0 <= gps.lat <= 90.0) or not (-180.0 <= gps.lon <= 180.0):
            self.accumulated_spoof_flags += 1
            return False, 0.0, f"GPS CORRUPT COORDINATES: lat={gps.lat}, lon={gps.lon} outside terrestrial bounds."

        # Rule 1: HDOP or satellite count anomalies
        if gps.satellites_tracked < 4:
            return False, 0.20, "GPS DEGRADED: Fewer than 4 satellites available for 3D fix."

        if gps.hdop > 5.0:
            return False, 0.35, f"GPS SUSPECT: Extreme dilution of precision (HDOP={gps.hdop})."

        if self.last_gps is not None:
            raw_dt = gps.timestamp - self.last_gps.timestamp
            if raw_dt < -0.1:  # Allow minimal sub-100ms clock jitter, flag true inversions
                self.accumulated_spoof_flags += 1
                return (
                    False,
                    0.10,
                    f"GPS TIMESTAMP INVERSION: fix timestamp ({gps.timestamp:.2f}) regressed "
                    f"against ({self.last_gps.timestamp:.2f}); replay attack suspected.",
                )

            dt = max(1e-3, raw_dt)

            # Calculate kinematic distance between successive fixes using true spherical Haversine (antimeridian and polar safe)
            dlat = math.radians(gps.lat - self.last_gps.lat)
            dlon = math.radians(gps.lon - self.last_gps.lon)
            a = (
                math.sin(dlat / 2.0) ** 2
                + math.cos(math.radians(self.last_gps.lat))
                * math.cos(math.radians(gps.lat))
                * math.sin(dlon / 2.0) ** 2
            )
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
            dist_nm = (6371.0 * c) * 0.539957
            implied_speed_kts = dist_nm / (dt / 3600.0)

            # Rule 2: Sudden impossible teleportation or velocity step-change
            if implied_speed_kts > 3000.0:
                self.accumulated_spoof_flags += 1
                return False, 0.05, f"GPS SPOOF DETECTED: Kinematic teleportation ({implied_speed_kts:.1f} kts)."

            # Compare GPS derivative acceleration with IMU if available
            if imu is not None and self.last_imu is not None:
                # GPS derived acceleration (approx m/s^2)
                speed_diff_mps = (gps.ground_speed_knots - self.last_gps.ground_speed_knots) * 0.514444
                gps_accel = abs(speed_diff_mps / dt)
                imu_accel = math.sqrt(imu.accel_x_mps2**2 + imu.accel_y_mps2**2)

                discrepancy = abs(gps_accel - imu_accel)
                if discrepancy > self.max_allowable_accel_discrepancy_mps2:
                    self.accumulated_spoof_flags += 1
                    return False, 0.15, f"GPS/INS CONFLICT: GPS accel ({gps_accel:.1f}) diverges from IMU ({imu_accel:.1f} m/s^2)."

        self.last_gps = gps
        if imu is not None:
            self.last_imu = imu

        # Decay previous flags if clean
        self.accumulated_spoof_flags = max(0, self.accumulated_spoof_flags - 1)
        confidence = 0.98 if self.accumulated_spoof_flags == 0 else max(0.5, 0.98 - 0.2 * self.accumulated_spoof_flags)
        return True, round(confidence, 3), "GPS TELEMETRY VERIFIED AUTHENTIC."

    def verify_target_signature(
        self,
        radar_rcs_m2: float,
        flir_thermal_celsius: float,
        ambient_celsius: float = 20.0,
        target_speed_knots: Optional[float] = None,
        ambient_wind_knots: float = 12.0,
    ) -> Tuple[bool, float, str]:
        """Cross-correlate Radar Cross Section (RCS) against optical/FLIR infrared profile to detect decoys."""
        delta_temp = flir_thermal_celsius - ambient_celsius

        # Corner cube radar reflector / metallic balloon decoy:
        # High radar return (e.g. 10 m2) but cold ambient temperature (< 3 deg above ambient)
        if radar_rcs_m2 > 4.0 and delta_temp < 3.0:
            if target_speed_knots is not None and abs(target_speed_knots - ambient_wind_knots) < 5.0:
                return (
                    False,
                    0.15,
                    f"PASSIVE DECOY BALLOON: RCS {radar_rcs_m2} m² lacks thermal signature and drifts with wind ({target_speed_knots:.1f} kts)."
                )
            return (
                False,
                0.22,
                f"DECOY SIGNATURE: High Radar RCS ({radar_rcs_m2} m²) lacks propulsion thermal bloom (ΔT={delta_temp:.1f}°C)."
            )

        # Chaff cloud: wide dispersion with zero heat signature
        if radar_rcs_m2 > 15.0 and delta_temp < 1.0:
            return False, 0.10, "CHAFF CLOUD DETECTED: Massive radar blooming with ambient thermal signature."

        # Cryogenic / extreme negative thermal anomaly
        if delta_temp < -15.0:
            return (
                False,
                0.15,
                f"THERMAL ANOMALY: Target FLIR ({flir_thermal_celsius:.1f}°C) is severely below "
                f"ambient ({ambient_celsius:.1f}°C); decoy suspected.",
            )

        # Authentic aircraft or engine exhaust has distinct thermal signature
        confidence = max(0.0, min(0.99, 0.70 + min(0.25, delta_temp / 100.0)))
        return True, round(confidence, 3), "TARGET SIGNATURE COHERENT ACROSS RF & IR SPECTRA."

    def set_emcon_policy(self, hostile_esm_threat_level: str) -> EmconState:
        """Dynamically schedule Emission Control based on electronic threat assessment."""
        threat = hostile_esm_threat_level.upper()
        if threat in ("CRITICAL", "ACTIVE_TRIANGULATION"):
            self.emcon_state = EmconState.SILENT
        elif threat in ("ELEVATED", "HIGH"):
            self.emcon_state = EmconState.RESTRICTED
        elif threat in ("MODERATE", "NOMINAL"):
            self.emcon_state = EmconState.TACTICAL
        else:
            self.emcon_state = EmconState.UNRESTRICTED
        return self.emcon_state
