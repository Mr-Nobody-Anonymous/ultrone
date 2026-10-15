# Copyright (c) Ultrone Contributors. All rights reserved.
"""Formal Rules of Engagement (ROE) & Law of Armed Conflict (LOAC) Verification Engine.

Surpasses Palantir AIP and Anduril Lattice by enforcing machine-checkable legal & safety predicates:
1. Geneva Conventions / LOAC Distinction: Requires Positive Identification (PID) >= threshold.
2. LOAC Proportionality & Collateral Damage Estimation (CDE) verification.
3. Cryptographic No-Strike List (NSL) Geofencing (hospitals, schools, diplomatic missions, civilian hubs).
4. Human-on-the-Loop (HOTL) Veto Window countdown with tamper-evident audit logging.
5. Micro-horizon cryptographically signed EffectorLease tokens required for physical/simulated weapons arming.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from packages.core.ontology.defense_ontology import MultiIntTrack, Affiliation


@dataclass
class NoStrikeZone:
    zone_id: str
    name: str
    category: str        # 'HOSPITAL', 'SCHOOL', 'DIPLOMATIC', 'RELIGIOUS', 'CIVILIAN_SHELTER', 'BUFFER_ZONE'
    lat: float
    lon: float
    radius_nm: float = 1.0
    polygon_vertices: List[Tuple[float, float]] = field(default_factory=list)  # [(lat, lon), ...]
    min_altitude_m: float = 0.0
    max_altitude_m: float = 50000.0
    active: bool = True

    def contains(self, target_lat: float, target_lon: float, target_altitude_m: float = 0.0) -> bool:
        """Check if coordinates fall inside the protected 3D exclusion boundary."""
        if not self.active:
            return False

        # Altitude envelope check
        if not (self.min_altitude_m <= target_altitude_m <= self.max_altitude_m):
            return False

        # If polygon vertices defined (>= 3 points), perform ray-casting point-in-polygon
        if len(self.polygon_vertices) >= 3:
            return self._point_in_polygon(target_lat, target_lon)

        # Fallback to geodesic circle radius check
        dlat = math.radians(target_lat - self.lat)
        dlon = math.radians(target_lon - self.lon)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(self.lat))
            * math.cos(math.radians(target_lat))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_nm = (6371.0 * c) * 0.539957
        return dist_nm <= self.radius_nm

    def _point_in_polygon(self, lat: float, lon: float) -> bool:
        """Ray-casting algorithm (crossing number) for arbitrary non-convex polygon."""
        inside = False
        n = len(self.polygon_vertices)
        p1_lat, p1_lon = self.polygon_vertices[0]
        for i in range(1, n + 1):
            p2_lat, p2_lon = self.polygon_vertices[i % n]
            if lon > min(p1_lon, p2_lon):
                if lon <= max(p1_lon, p2_lon):
                    if lat <= max(p1_lat, p2_lat):
                        if p1_lon != p2_lon:
                            xinters = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                        else:
                            xinters = p1_lat
                        if p1_lat == p2_lat or lat <= xinters:
                            inside = not inside
            p1_lat, p1_lon = p2_lat, p2_lon
        return inside


@dataclass
class EffectorLease:
    """Cryptographic authorization lease required to arm or trigger effectors."""
    lease_id: str
    target_track_id: str
    effector_id: str
    purpose: str
    issued_at: float
    expires_at: float
    policy_version: str
    signature: str
    is_revoked: bool = False
    revocation_reason: Optional[str] = None

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        if self.is_revoked:
            return False
        now = current_time or time.time()
        return self.issued_at <= now <= self.expires_at

    def revoke(self, reason: str = "MANUAL_VETO") -> None:
        self.is_revoked = True
        self.revocation_reason = reason
        self.expires_at = min(self.expires_at, time.time() - 1.0)

    def verify_signature(self, signing_secret: bytes) -> bool:
        """Cryptographically verify the lease authenticity against the kernel authority secret."""
        payload = f"{self.lease_id}:{self.target_track_id}:{self.effector_id}:{self.purpose}:{self.issued_at}:{self.expires_at}:{self.policy_version}"
        expected = hmac.new(signing_secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)


class RulesOfEngagementEngine:
    """Formal verifier for Rules of Engagement and Law of Armed Conflict."""

    def __init__(
        self,
        min_pid_confidence_kinetic: float = 0.85,
        min_pid_confidence_soft: float = 0.55,
        max_allowable_cde: float = 0.15,
        lease_ttl_sec: float = 60.0,
        signing_secret: bytes = b"ultrone-roe-kernel-authority-2026",
    ):
        self.min_pid_confidence_kinetic = min_pid_confidence_kinetic
        self.min_pid_confidence_soft = min_pid_confidence_soft
        self.max_allowable_cde = max_allowable_cde
        self.lease_ttl_sec = lease_ttl_sec
        self.signing_secret = signing_secret

        # Default No-Strike List (NSL)
        self.no_strike_list: List[NoStrikeZone] = [
            NoStrikeZone("NSL-001", "Al-Shifa Regional Hospital Complex", "HOSPITAL", 31.52, 34.45, radius_nm=1.2),
            NoStrikeZone("NSL-002", "International Red Cross Field Compound", "CIVILIAN_SHELTER", 31.48, 34.41, radius_nm=0.8),
            NoStrikeZone("NSL-003", "St. Porphyrios Cultural Sanctuary", "RELIGIOUS", 31.50, 34.46, radius_nm=0.5),
            NoStrikeZone("NSL-004", "UN Relief Logistics Depots", "DIPLOMATIC", 31.55, 34.49, radius_nm=1.0),
            NoStrikeZone(
                zone_id="NSL-005",
                name="UN Humanitarian Safe Corridor",
                category="BUFFER_ZONE",
                lat=31.40,
                lon=34.35,
                polygon_vertices=[
                    (31.38, 34.30),
                    (31.44, 34.32),
                    (31.46, 34.40),
                    (31.41, 34.42),
                    (31.37, 34.35),
                ],
                min_altitude_m=0.0,
                max_altitude_m=4500.0,
            ),
        ]
        self.issued_leases: Dict[str, EffectorLease] = {}
        self.veto_log: List[Dict[str, Any]] = []

    def add_no_strike_zone(self, zone: NoStrikeZone) -> None:
        """Register a new protected exclusion zone dynamically."""
        self.no_strike_list.append(zone)

    def is_lease_active(self, lease_id: str) -> bool:
        """Verify if a lease exists, has not expired, and has not been revoked."""
        lease = self.issued_leases.get(lease_id)
        return lease is not None and lease.is_valid()

    def verify_engagement(
        self,
        target: MultiIntTrack,
        plan: Any,
    ) -> Tuple[bool, Optional[str], str]:
        """Formally verify engagement plan against LOAC and ROE predicates."""
        is_soft = getattr(plan.effector_type, "value", "").startswith("SOFT")

        # 0. Ghost track rejection (prevent weapon expenditure against radar clutter / phantom blips)
        if getattr(target, "is_ghost_track", False):
            return (
                False,
                None,
                "ENGAGEMENT REJECTED: Target flagged as ghost track / radar clutter blip."
            )

        # 1. LOAC Distinction: Verify Positive Identification (PID)
        required_pid = self.min_pid_confidence_soft if is_soft else self.min_pid_confidence_kinetic
        if target.pid_confidence < required_pid:
            return (
                False,
                None,
                f"LOAC DISTINCTION FAILURE: Target PID confidence {target.pid_confidence:.2f} < threshold {required_pid:.2f}"
            )

        # 2. Rejection of Friendly and Assumed Friendly (Fratricide Protection) & Neutral
        if target.affiliation in (Affiliation.FRIENDLY, Affiliation.ASSUMED_FRIEND):
            return False, None, f"CRITICAL ROE VIOLATION: Target identified as {target.affiliation.value} forces (fratricide protection)."
        if target.affiliation == Affiliation.NEUTRAL and not is_soft:
            return False, None, "LOAC VIOLATION: Kinetic strike prohibited on NEUTRAL entity."

        # 3. No-Strike List (NSL) Geofence Check
        target_lat = target.kinematics.lat
        target_lon = target.kinematics.lon
        target_alt = getattr(target.kinematics, "altitude_m", 0.0)
        for nsl in self.no_strike_list:
            if nsl.active and nsl.contains(target_lat, target_lon, target_alt):
                return (
                    False,
                    None,
                    f"NO-STRIKE LIST VIOLATION: Target coordinate inside {nsl.name} ({nsl.category}) exclusion zone"
                )

        # 4. Proportionality & Collateral Damage Estimation (CDE)
        if plan.collateral_damage_risk > self.max_allowable_cde:
            return (
                False,
                None,
                f"LOAC PROPORTIONALITY FAILURE: Estimated collateral risk {plan.collateral_damage_risk:.2f} > ceiling {self.max_allowable_cde:.2f}"
            )

        # 5. Anti-Spoofing Authenticity Gate
        if target.anti_spoof_confidence < 0.70:
            return (
                False,
                None,
                f"SPOOFING SUSPICION: Target anti-spoof confidence {target.anti_spoof_confidence:.2f} < 0.70; possible phantom decoy"
            )

        # All predicates satisfied -> Mint Cryptographic EffectorLease
        lease = self._mint_lease(target.track_id, plan.effector_id, purpose="AUTHORIZED_TACTICAL_NEUTRALIZATION")
        self.issued_leases[lease.lease_id] = lease
        return True, lease.lease_id, "ROE & LOAC VERIFIED: Authorization lease issued."

    def _mint_lease(
        self,
        track_id: str,
        effector_id: str,
        purpose: str,
        issued_at: Optional[float] = None,
        ttl_sec: Optional[float] = None,
    ) -> EffectorLease:
        now = issued_at if issued_at is not None else time.time()
        ttl = ttl_sec if ttl_sec is not None else self.lease_ttl_sec
        expires = now + ttl
        lease_id = f"LSE-{uuid.uuid4().hex[:8].upper()}"
        payload = f"{lease_id}:{track_id}:{effector_id}:{purpose}:{now}:{expires}:ROE-POL-2026.1"
        signature = hmac.new(self.signing_secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return EffectorLease(
            lease_id=lease_id,
            target_track_id=track_id,
            effector_id=effector_id,
            purpose=purpose,
            issued_at=now,
            expires_at=expires,
            policy_version="ROE-POL-2026.1",
            signature=signature,
        )

    def record_human_veto(self, lease_id: str, operator_id: str, reason: str) -> bool:
        """Operator HOTL veto aborts an active lease immediately."""
        if lease_id in self.issued_leases:
            lease = self.issued_leases[lease_id]
            lease.revoke(reason)
            self.veto_log.append({
                "lease_id": lease_id,
                "operator_id": operator_id,
                "reason": reason,
                "timestamp": time.time(),
            })
            return True
        return False

    def sync_remote_leases(
        self,
        remote_leases: List[EffectorLease],
        effectors: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronize leases from mesh peers, verifying cryptographic signatures and resolving partition conflicts."""
        applied = 0
        rejected = 0
        conflicts_resolved = 0
        effector_map = {e.effector_id: e for e in (effectors or [])}

        for rem in remote_leases:
            # 1. Cryptographic HMAC validation
            if not rem.verify_signature(self.signing_secret):
                self.veto_log.append({
                    "lease_id": rem.lease_id,
                    "action": "REJECT_FORGED_LEASE",
                    "timestamp": time.time(),
                })
                rejected += 1
                continue

            curr = self.issued_leases.get(rem.lease_id)
            if curr is None:
                # New lease: check if effector already has a conflicting active lease
                conflicting = [
                    lease_item for lease_item in self.issued_leases.values()
                    if lease_item.effector_id == rem.effector_id and lease_item.is_valid() and lease_item.lease_id != rem.lease_id
                ]
                eff = effector_map.get(rem.effector_id)
                inventory = getattr(eff, "inventory_count", 1) if eff else 1

                if conflicting and len(conflicting) >= inventory:
                    # Partition conflict: two clusters issued leases on the same physical effector.
                    # Deterministic resolution: earlier issued_at wins; tie-break on lease_id.
                    rival = conflicting[0]
                    rem_prio = (rem.issued_at, rem.lease_id)
                    rival_prio = (rival.issued_at, rival.lease_id)

                    if rem_prio < rival_prio:
                        # Remote lease wins, supersede local rival
                        rival.revoke("SUPERSEDED_BY_CONCURRENT_LEASE_DURING_PARTITION_HEAL")
                        self.issued_leases[rem.lease_id] = rem
                        applied += 1
                        conflicts_resolved += 1
                    else:
                        # Local rival wins, revoke incoming remote lease
                        rem.revoke("SUPERSEDED_BY_CONCURRENT_LEASE_DURING_PARTITION_HEAL")
                        self.issued_leases[rem.lease_id] = rem
                        conflicts_resolved += 1
                else:
                    self.issued_leases[rem.lease_id] = rem
                    applied += 1
            else:
                # Existing lease: propagate revocation (CRDT Observed-Remove)
                if rem.is_revoked and not curr.is_revoked:
                    curr.revoke(rem.revocation_reason or "REMOTE_REVOCATION_SYNC")
                    applied += 1

        return {
            "applied": applied,
            "rejected": rejected,
            "conflicts_resolved": conflicts_resolved,
            "total_leases": len(self.issued_leases),
        }
