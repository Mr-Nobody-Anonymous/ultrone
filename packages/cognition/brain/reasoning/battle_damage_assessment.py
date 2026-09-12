# Copyright (c) Ultrone Contributors. All rights reserved.
"""Battle Damage Assessment (BDA) — post-engagement damage evaluation."""

from __future__ import annotations

import math
import time
import uuid
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Reasoning.BDA")


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class BDASeverity(Enum):
    NONE = "none"; LIGHT = "light"; MODERATE = "moderate"
    HEAVY = "heavy"; DESTROYED = "destroyed"


class BDAConfidence(Enum):
    VERY_LOW = "very_low"; LOW = "low"; MEDIUM = "medium"
    HIGH = "high"; VERY_HIGH = "very_high"


class DamageIndicator(Enum):
    VISUAL = "visual"; THERMAL = "thermal"; RADAR = "radar"; SIGINT = "sigint"
    HUMINT = "humint"; ELINT = "elint"; SAR_IMAGERY = "sar_imagery"
    ACOUSTIC = "acoustic"; EMS_EMISSION = "ems_emission"
    LOGISTICS_TEL = "logistics_telemetry"; OTHERSOURCE = "other"


class ReEngagementRecommendation(Enum):
    IMMEDIATE = "immediate"; SCHEDULED = "scheduled"; HUNT = "hunt"
    STAND_DOWN = "stand_down"; UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class BDAResult:
    result_id: str = field(default_factory=lambda: f"bda_{uuid.uuid4().hex[:12]}")
    target_id: str = ""
    engagement_id: str = ""
    timestamp: float = field(default_factory=time.time)
    severity: BDASeverity = BDASeverity.NONE
    damage_fraction: float = 0.0
    confidence: BDAConfidence = BDAConfidence.VERY_LOW
    indicators: Dict[DamageIndicator, Any] = field(default_factory=dict)
    structural_damage: float = 0.0
    functional_damage: float = 0.0
    mobility_damage: float = 0.0
    still_threatening: bool = False
    reengagement: ReEngagementRecommendation = ReEngagementRecommendation.STAND_DOWN
    notes: str = ""; assessor_id: str = "bda_engine"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id, "target_id": self.target_id,
            "engagement_id": self.engagement_id, "timestamp": self.timestamp,
            "severity": self.severity.value, "damage_fraction": self.damage_fraction,
            "confidence": self.confidence.value,
            "indicators": {k.value: v for k, v in self.indicators.items()},
            "structural_damage": self.structural_damage,
            "functional_damage": self.functional_damage,
            "mobility_damage": self.mobility_damage,
            "still_threatening": self.still_threatening,
            "reengagement": self.reengagement.value,
            "notes": self.notes, "assessor_id": self.assessor_id,
            "metadata": self.metadata,
        }

    def n_samples_indicator(self) -> int:
        """Return count of distinct damage indicators that produced this result."""
        return len([v for v in self.indicators.values() if v is not None])


class BattleDamageAssessment:
    """Stateless damage model for a single engagement."""

    INDICATOR_WEIGHTS: Dict[DamageIndicator, float] = {
        DamageIndicator.VISUAL: 0.95, DamageIndicator.SAR_IMAGERY: 0.90,
        DamageIndicator.THERMAL: 0.85, DamageIndicator.RADAR: 0.80,
        DamageIndicator.ELINT: 0.75, DamageIndicator.EMS_EMISSION: 0.70,
        DamageIndicator.ACOUSTIC: 0.65, DamageIndicator.SIGINT: 0.60,
        DamageIndicator.LOGISTICS_TEL: 0.55, DamageIndicator.HUMINT: 0.40,
        DamageIndicator.OTHERSOURCE: 0.20,
    }
    THREAT_THRESHOLD_DAMAGE = 0.40
    THREAT_THRESHOLD_MOBILITY = 0.70

    def __init__(self, bda_rigor: float = 0.85) -> None:
        self.bda_rigor = max(0.0, min(1.0, bda_rigor))

    def assess(self, target_id, engagement_id, sensor_reports,
               pre_engagement_state=None, metadata=None) -> BDAResult:
        weighted_scores: List = []
        structural_parts: List = []
        functional_parts: List = []
        mobility_parts: List = []

        for indicator, report in sensor_reports.items():
            if report is None:
                continue
            weight = self.INDICATOR_WEIGHTS.get(indicator, 0.3)
            score = max(0.0, min(1.0, float(report.get("damage_score", 0.0))))
            weighted_scores.append((score, weight))
            structural_parts.append(float(report.get("structural", score)))
            functional_parts.append(float(report.get("functional", score)))
            mobility_parts.append(float(report.get("mobility", score)))

        total_weight = sum(w for _, w in weighted_scores)
        if total_weight <= 0:
            damage_fraction = structural_damage = functional_damage = mobility_damage = 0.0
            confidence = BDAConfidence.VERY_LOW
        else:
            damage_fraction = sum(s * w for s, w in weighted_scores) / total_weight
            structural_damage = _mean(structural_parts) or damage_fraction
            functional_damage = _mean(functional_parts) or damage_fraction
            mobility_damage = _mean(mobility_parts) or damage_fraction
            confidence = self._compute_confidence(weighted_scores, total_weight)

        if self.bda_rigor < 1.0:
            confidence = self._degrade_confidence(confidence)

        severity = self._severity_from_fraction(damage_fraction)
        still_threatening = (
            functional_damage < self.THREAT_THRESHOLD_DAMAGE
            and mobility_damage < self.THREAT_THRESHOLD_MOBILITY
        )
        reengagement = self._recommend_reengagement(
            damage_fraction, functional_damage, mobility_damage, still_threatening, confidence
        )

        return BDAResult(
            result_id=f"bda_{uuid.uuid4().hex[:12]}",
            target_id=target_id, engagement_id=engagement_id,
            severity=severity, damage_fraction=damage_fraction,
            confidence=confidence, indicators=dict(sensor_reports),
            structural_damage=structural_damage,
            functional_damage=functional_damage,
            mobility_damage=mobility_damage,
            still_threatening=still_threatening,
            reengagement=reengagement,
            notes=f"Severity={severity.value} (damage~{damage_fraction:.0%}); Confidence={confidence.value}",
            metadata=metadata or {},
        )

    @staticmethod
    def _severity_from_fraction(d: float) -> BDASeverity:
        if d < 0.05: return BDASeverity.NONE
        if d < 0.25: return BDASeverity.LIGHT
        if d < 0.60: return BDASeverity.MODERATE
        if d < 0.90: return BDASeverity.HEAVY
        return BDASeverity.DESTROYED

    def _compute_confidence(self, scores, total_weight) -> BDAConfidence:
        n_sources = len(scores)
        if n_sources < 2:
            avg_agree = 0.0
        else:
            mean_score = sum(s for s, _ in scores) / n_sources
            variance = sum((s - mean_score) ** 2 for s, _ in scores) / n_sources
            avg_agree = 1.0 - math.sqrt(variance)
        weight_normalised = min(1.0, total_weight / 5.0)
        source_bonus = min(1.0, n_sources / 4.0)
        quality = (weight_normalised + source_bonus + avg_agree) / 3.0
        if quality >= 0.90: return BDAConfidence.VERY_HIGH
        if quality >= 0.75: return BDAConfidence.HIGH
        if quality >= 0.60: return BDAConfidence.MEDIUM
        if quality >= 0.40: return BDAConfidence.LOW
        return BDAConfidence.VERY_LOW

    def _degrade_confidence(self, conf) -> BDAConfidence:
        table = {
            BDAConfidence.VERY_HIGH: BDAConfidence.HIGH,
            BDAConfidence.HIGH: BDAConfidence.MEDIUM,
            BDAConfidence.MEDIUM: BDAConfidence.LOW,
            BDAConfidence.LOW: BDAConfidence.VERY_LOW,
            BDAConfidence.VERY_LOW: BDAConfidence.VERY_LOW,
        }
        return table.get(conf, conf)

    @staticmethod
    def _recommend_reengagement(damage, functional, mobility, still_threatening, confidence):
        # Decisive damage overrides low confidence — make the obvious call.
        if damage >= 0.80:
            return ReEngagementRecommendation.STAND_DOWN
        if damage <= 0.30 and mobility < 0.40:
            return ReEngagementRecommendation.HUNT
        if still_threatening and damage < 0.50:
            # We have a known threat: don't say UNCERTAIN just because confidence is low.
            if confidence in (BDAConfidence.HIGH, BDAConfidence.VERY_HIGH):
                return ReEngagementRecommendation.IMMEDIATE
            return ReEngagementRecommendation.SCHEDULED
        if confidence == BDAConfidence.VERY_LOW:
            return ReEngagementRecommendation.UNCERTAIN
        if functional < 0.25 and mobility < 0.50:
            return ReEngagementRecommendation.HUNT
        if functional < 0.60:
            return ReEngagementRecommendation.SCHEDULED
        return ReEngagementRecommendation.STAND_DOWN


class DamageAssessmentEngine:
    """Stateful BDA engine — manages live assessments, sensor fusion, re-engagement scheduling."""

    def __init__(self, bda_rigor: float = 0.85) -> None:
        self._bda_rigor = bda_rigor
        self._assessments: Dict[str, BDAResult] = {}
        self._target_history: Dict[str, List[BDAResult]] = {}
        self._pending_reengagement: Dict[str, Dict] = {}
        self._callbacks: List[Callable] = []
        self._lock = threading.RLock()
        self._bda = BattleDamageAssessment(bda_rigor)

    def assess(self, target_id: str, engagement_id: str,
               sensor_reports: Dict, metadata: Dict = None) -> BDAResult:
        with self._lock:
            latest = self._get_latest(target_id)
            fused_reports = dict(sensor_reports)
            if latest is not None:
                fused_reports = self._fuse_with_history(fused_reports, latest)
            result = self._bda.assess(
                target_id, engagement_id, fused_reports, metadata=metadata
            )
            self._store_result(result)
            self._update_reengagement(result)
            self._fire_callbacks(result)
            return result

    assess_multi_sensor = assess  # Alias for readability

    def get_assessment(self, result_id: str) -> Optional[BDAResult]:
        with self._lock: return self._assessments.get(result_id)

    def get_target_history(self, target_id: str) -> List[BDAResult]:
        with self._lock: return list(self._target_history.get(target_id, []))

    def get_latest_assessment(self, target_id: str) -> Optional[BDAResult]:
        with self._lock: return self._get_latest(target_id)

    def get_reengagement_plan(self, target_id: str) -> Optional[Dict]:
        with self._lock: return self._pending_reengagement.get(target_id)

    def get_all_pending_reengagements(self) -> Dict[str, Dict]:
        with self._lock: return dict(self._pending_reengagement)

    def dismiss_reengagement(self, target_id: str) -> None:
        with self._lock: self._pending_reengagement.pop(target_id, None)

    def on_assessment(self, callback: Callable) -> None:
        with self._lock: self._callbacks.append(callback)

    def clear(self) -> None:
        with self._lock:
            self._assessments.clear()
            self._target_history.clear()
            self._pending_reengagement.clear()

    def stats(self) -> Dict:
        with self._lock:
            by_severity: Dict[str, int] = {}
            for r in self._assessments.values():
                by_severity[r.severity.value] = by_severity.get(r.severity.value, 0) + 1
            return {
                "total_assessments": len(self._assessments),
                "assessed_targets": len(self._target_history),
                "pending_reengagements": len(self._pending_reengagement),
                "by_severity": by_severity,
                "bda_rigor": self._bda_rigor,
            }

    def _get_latest(self, target_id: str) -> Optional[BDAResult]:
        hist = self._target_history.get(target_id)
        return hist[-1] if hist else None

    def _store_result(self, result: BDAResult) -> None:
        self._assessments[result.result_id] = result
        hist = self._target_history.setdefault(result.target_id, [])
        hist.append(result)
        if len(hist) > 50:
            self._target_history[result.target_id] = hist[-50:]

    def _fuse_with_history(self, reports: Dict, latest: BDAResult) -> Dict:
        conf_map = {
            BDAConfidence.VERY_HIGH: 0.95, BDAConfidence.HIGH: 0.80,
            BDAConfidence.MEDIUM: 0.60, BDAConfidence.LOW: 0.35,
            BDAConfidence.VERY_LOW: 0.15,
        }
        bayes_weight = conf_map.get(latest.confidence, 0.3)
        fused = dict(reports)
        fused[DamageIndicator.SIGINT] = {
            "damage_score": latest.damage_fraction,
            "confidence": bayes_weight,
            "structural": latest.structural_damage,
            "functional": latest.functional_damage,
            "mobility": latest.mobility_damage,
        }
        return fused

    def _update_reengagement(self, result: BDAResult) -> None:
        tid = result.target_id
        if result.reengagement == ReEngagementRecommendation.STAND_DOWN:
            self._pending_reengagement.pop(tid, None)
        elif result.reengagement == ReEngagementRecommendation.UNCERTAIN:
            pass
        else:
            self._pending_reengagement[tid] = {
                "result_id": result.result_id,
                "recommendation": result.reengagement.value,
                "damage_fraction": result.damage_fraction,
                "scheduled_at": time.time() + (
                    300 if result.reengagement == ReEngagementRecommendation.SCHEDULED else 0
                ),
                "hunt": result.reengagement == ReEngagementRecommendation.HUNT,
            }

    def _fire_callbacks(self, result: BDAResult) -> None:
        for cb in self._callbacks:
            try: cb(result)
            except Exception as exc: logger.error("BDA callback error: %s", exc)

