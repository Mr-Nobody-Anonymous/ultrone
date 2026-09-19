# Copyright (c) Ultrone Contributors. All rights reserved.
"""EdgeFailsafeController: Embedded deterministic anti-jamming and degraded operations engine.

Executes strictly rule-based failsafe autonomy on edge nodes when centralized
comms or clearance tokens drop, guaranteeing zero unmanaged kinetic action.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Edge.Failsafe")


class EdgeFailsafeState(str, Enum):
    """Operational states of the edge platform."""

    NOMINAL = "NOMINAL"
    COMMS_DEGRADED = "COMMS_DEGRADED"
    CLEARANCE_EXPIRED = "CLEARANCE_EXPIRED"
    SAFE_ORBIT = "SAFE_ORBIT"
    EMERGENCY_RTL = "EMERGENCY_RTL"


@dataclass
class RallyPoint:
    """Pre-cleared geographic rally/safe-orbit location."""

    rally_id: str
    lat: float
    lon: float
    alt_m: float = 2500.0
    radius_m: float = 400.0


class EdgeFailsafeController:
    """Embedded deterministic fallback engine for contested/jammed environments."""

    def __init__(
        self,
        unit_id: str,
        home_base_pos: Tuple[float, float, float],  # (lat, lon, alt_m)
        rally_point: Optional[RallyPoint] = None,
        comms_timeout_s: float = 3.0,
        token_default_ttl_s: float = 5.0,
        rtl_battery_threshold_pct: float = 20.0,
    ) -> None:
        self.unit_id = unit_id
        self.home_base_pos = home_base_pos
        self.rally_point = rally_point or RallyPoint(
            rally_id="RALLY-ALPHA",
            lat=home_base_pos[0] + 0.01,
            lon=home_base_pos[1] + 0.01,
            alt_m=home_base_pos[2] + 500.0,
        )
        self.comms_timeout_s = comms_timeout_s
        self.token_default_ttl_s = token_default_ttl_s
        self.rtl_battery_threshold = rtl_battery_threshold_pct

        self.current_state: EdgeFailsafeState = EdgeFailsafeState.NOMINAL
        self.last_heartbeat_time: float = time.time()
        self.active_clearance_token: Optional[str] = None
        self.token_expiry_time: float = 0.0
        self.weapons_armed: bool = False
        self.events_log: List[Dict[str, Any]] = []

    def receive_heartbeat(self, timestamp: Optional[float] = None) -> None:
        """Central orchestrator heartbeat pulse received."""
        self.last_heartbeat_time = timestamp or time.time()
        if self.current_state in (EdgeFailsafeState.COMMS_DEGRADED, EdgeFailsafeState.SAFE_ORBIT):
            logger.info("Comms restored on unit '%s'. Returning to NOMINAL.", self.unit_id)
            self._transition_to(EdgeFailsafeState.NOMINAL, "Comms heartbeat restored")

    def load_clearance_token(self, token: str, ttl_seconds: Optional[float] = None) -> bool:
        """Load an authorized ROE clearance token with strict Time-To-Live (TTL)."""
        ttl = ttl_seconds or self.token_default_ttl_s
        now = time.time()

        # Parse embedded TTL if present in token: ROE-CLEARED-<uuid>-EXP<epoch>
        if "-EXP" in token:
            try:
                parts = token.split("-EXP")
                expiry = float(parts[-1])
                if now >= expiry:
                    logger.error("Token already expired at load time: %s", token)
                    return False
                self.token_expiry_time = expiry
            except Exception:
                self.token_expiry_time = now + ttl
        else:
            self.token_expiry_time = now + ttl

        self.active_clearance_token = token
        self.weapons_armed = True
        logger.info("Unit '%s' loaded clearance token (valid for %.1fs)", self.unit_id, self.token_expiry_time - now)
        return True

    def verify_authorization(self, now: Optional[float] = None) -> Tuple[bool, str]:
        """Pre-action authorization check. Strictly returns False if token expired or comms dropped."""
        t_now = now or time.time()

        # 1. Comms timeout check
        if t_now - self.last_heartbeat_time > self.comms_timeout_s:
            self.disarm_weapons("Comms link lost")
            self._transition_to(EdgeFailsafeState.COMMS_DEGRADED, "Heartbeat timeout exceeded")
            return False, "DENIED: Comms blackout detected. Operating in degraded failsafe mode."

        # 2. Token expiration check
        if not self.active_clearance_token or t_now >= self.token_expiry_time:
            self.disarm_weapons("Clearance token expired")
            self._transition_to(EdgeFailsafeState.CLEARANCE_EXPIRED, "Token TTL lapsed")
            return False, "DENIED: Clearance token expired. Strike authorization revoked."

        if not self.weapons_armed:
            return False, "DENIED: Weapons are safe/disarmed."

        return True, "AUTHORIZED"

    def disarm_weapons(self, reason: str) -> None:
        """Immediately and irrevocably disarm weapons locally."""
        if self.weapons_armed:
            logger.warning("WEAPONS DISARMED on unit '%s'. Reason: %s", self.unit_id, reason)
            self.weapons_armed = False
            self.active_clearance_token = None

    def evaluate_failsafe(self, battery_pct: float = 100.0, now: Optional[float] = None) -> Dict[str, Any]:
        """Periodic deterministic assessment running at 10Hz on edge CPU without LLM."""
        t_now = now or time.time()
        comms_age = t_now - self.last_heartbeat_time

        # 1. Critical battery failsafe -> RTL
        if battery_pct <= self.rtl_battery_threshold:
            self.disarm_weapons("Low battery threshold reached")
            self._transition_to(EdgeFailsafeState.EMERGENCY_RTL, f"Battery at {battery_pct:.1f}%")
            return {
                "action": "RTL",
                "target_pos": self.home_base_pos,
                "state": self.current_state.value,
            }

        # 2. Sustained comms loss -> Transition to Safe Orbit at Rally Point
        if comms_age > self.comms_timeout_s:
            self.disarm_weapons(f"Comms blackout ({comms_age:.1f}s)")
            if comms_age > (self.comms_timeout_s * 3.0):
                # Protracted jamming > 9s -> Autonomous RTL
                self._transition_to(EdgeFailsafeState.EMERGENCY_RTL, "Protracted comms blackout")
                return {
                    "action": "RTL",
                    "target_pos": self.home_base_pos,
                    "state": self.current_state.value,
                }
            else:
                self._transition_to(EdgeFailsafeState.SAFE_ORBIT, "Holding rally orbit")
                return {
                    "action": "HOLD_ORBIT",
                    "target_pos": (self.rally_point.lat, self.rally_point.lon, self.rally_point.alt_m),
                    "radius_m": self.rally_point.radius_m,
                    "state": self.current_state.value,
                }

        # 3. Token expired while nominal
        if self.weapons_armed and t_now >= self.token_expiry_time:
            self.disarm_weapons("Token TTL exceeded")
            self._transition_to(EdgeFailsafeState.CLEARANCE_EXPIRED, "Token expired")

        return {"action": "MAINTAIN_CURRENT", "state": self.current_state.value}

    def _transition_to(self, new_state: EdgeFailsafeState, reason: str) -> None:
        if self.current_state != new_state:
            logger.info("Edge unit '%s' state: %s -> %s (%s)", self.unit_id, self.current_state.value, new_state.value, reason)
            self.current_state = new_state
            self.events_log.append({
                "timestamp": time.time(),
                "new_state": new_state.value,
                "reason": reason,
            })
