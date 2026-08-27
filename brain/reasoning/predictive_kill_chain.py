# Copyright (c) Ultrone Contributors. All rights reserved.
"""Predictive Kill-Chain Optimization.

Predicts the most likely outcome of every F2T2EA phase, given
historical engagement data and the current target/threat state.

Architecture
------------
``PhaseOutcome``       — discrete outcome label for a single phase.
``PhasePrediction``    — per-phase probabilistic forecast.
``KillChainPrediction``— multi-phase aggregate forecast.
``PredictiveModel``    — abstract base; pluggable models.
``MarkovPredictiveModel`` — transition-matrix model trained on logs.
``TimeSeriesPredictiveModel`` — exponential-smoothing time series.
``EnsemblePredictiveModel``   — weighted blend of multiple models.
``PredictiveKillChain``       — top-level orchestrator.
"""

from __future__ import annotations

import math
import time
import uuid
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Reasoning.PredictiveKillChain")


class PhaseOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


# F2T2EA phases in order
PHASE_ORDER = ("find", "fix", "track", "target", "engage", "assess")


@dataclass
class PhasePrediction:
    """Probabilistic forecast for a single kill-chain phase."""
    phase: str
    timestamp: float = field(default_factory=time.time)
    predicted_duration_sec: float = 0.0
    success_probability: float = 0.5
    failure_probability: float = 0.3
    timeout_probability: float = 0.15
    aborted_probability: float = 0.05
    most_likely: PhaseOutcome = PhaseOutcome.SUCCESS
    confidence: float = 0.5
    recommended_accelerations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "predicted_duration_sec": self.predicted_duration_sec,
            "success_probability": self.success_probability,
            "failure_probability": self.failure_probability,
            "timeout_probability": self.timeout_probability,
            "aborted_probability": self.aborted_probability,
            "most_likely": self.most_likely.value,
            "confidence": self.confidence,
            "recommended_accelerations": self.recommended_accelerations,
        }


@dataclass
class KillChainPrediction:
    """Multi-phase kill-chain forecast."""
    target_id: str
    predictions: Dict[str, PhasePrediction] = field(default_factory=dict)
    overall_success_probability: float = 0.0
    predicted_total_duration_sec: float = 0.0
    predicted_bottleneck_phase: Optional[str] = None
    estimated_remaining_threat_time_sec: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    model_version: str = "1.0"
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "target_id": self.target_id,
            "predictions": {k: v.to_dict() for k, v in self.predictions.items()},
            "overall_success_probability": self.overall_success_probability,
            "predicted_total_duration_sec": self.predicted_total_duration_sec,
            "predicted_bottleneck_phase": self.predicted_bottleneck_phase,
            "estimated_remaining_threat_time_sec": self.estimated_remaining_threat_time_sec,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "model_version": self.model_version,
            "metadata": self.metadata,
        }


class PredictiveModel:
    """Abstract base for kill-chain predictive models."""

    def predict_phase(self, phase: str, context: Dict) -> PhasePrediction:
        raise NotImplementedError

    def update(self, phase: str, duration_sec: float, outcome: PhaseOutcome) -> None:
        raise NotImplementedError

    def get_phase_stats(self, phase: str) -> Dict:
        raise NotImplementedError


class MarkovPredictiveModel(PredictiveModel):
    """First-order Markov chain model trained on log transitions."""

    def __init__(self) -> None:
        self._durations: Dict[str, List[float]] = defaultdict(list)
        self._outcomes: Dict[str, Dict[PhaseOutcome, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._transitions: Dict = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        self._last_outcome: Dict[str, PhaseOutcome] = {}
        self._lock = threading.RLock()

    def predict_phase(self, phase: str, context: Dict) -> PhasePrediction:
        with self._lock:
            durations = self._durations.get(phase, [])
            dur = float(context.get("duration_sec", 0))
            if durations:
                base_dur = sum(durations) / len(durations)
                alpha = 0.3
                dur = alpha * dur + (1 - alpha) * base_dur if dur else base_dur
            else:
                dur = dur or 60.0

            outcomes = self._outcomes.get(phase, {})
            total = sum(outcomes.values()) or 1
            last = self._last_outcome.get(phase)
            trans = self._transitions.get(phase, {}).get(last, {}) if last else {}
            trans_total = sum(trans.values()) or total

            probs: Dict = {}
            for outcome in PhaseOutcome:
                base = outcomes.get(outcome, 0) / total
                if last and trans:
                    trans_prob = trans.get(outcome, 0) / trans_total
                    probs[outcome] = 0.6 * trans_prob + 0.4 * base
                else:
                    probs[outcome] = base

            total_p = sum(probs.values()) or 1.0
            for o in probs:
                probs[o] /= total_p

            ml = max(PhaseOutcome, key=lambda o: probs.get(o, 0))
            confidence = min(1.0, sum(outcomes.values()) / 20.0)
            accel = self._suggest_accelerations(phase, probs, durations)

            return PhasePrediction(
                phase=phase, predicted_duration_sec=dur,
                success_probability=probs.get(PhaseOutcome.SUCCESS, 0),
                failure_probability=probs.get(PhaseOutcome.FAILURE, 0),
                timeout_probability=probs.get(PhaseOutcome.TIMEOUT, 0),
                aborted_probability=probs.get(PhaseOutcome.ABORTED, 0),
                most_likely=ml, confidence=confidence,
                recommended_accelerations=accel,
            )

    def update(self, phase: str, duration_sec: float, outcome: PhaseOutcome) -> None:
        with self._lock:
            self._durations[phase].append(duration_sec)
            if len(self._durations[phase]) > 200:
                self._durations[phase] = self._durations[phase][-200:]
            prev = self._last_outcome.get(phase)
            self._outcomes[phase][outcome] += 1
            if prev is not None:
                self._transitions[phase][prev][outcome] += 1
            self._last_outcome[phase] = outcome

    def _bounded_total(self, phase: str) -> int:
        """Return bounded sample count (matches durations cap)."""
        return min(sum(self._outcomes.get(phase, {}).values()), 200)

    def get_phase_stats(self, phase: str) -> Dict:
        with self._lock:
            durations = self._durations.get(phase, [])
            outcomes = self._outcomes.get(phase, {})
            total = self._bounded_total(phase) or 1
            return {
                "phase": phase,
                "n_samples": total,
                "avg_duration_sec": sum(durations) / len(durations) if durations else 0.0,
                "min_duration_sec": min(durations) if durations else 0.0,
                "max_duration_sec": max(durations) if durations else 0.0,
                "success_rate": outcomes.get(PhaseOutcome.SUCCESS, 0) / total,
                "failure_rate": outcomes.get(PhaseOutcome.FAILURE, 0) / total,
                "timeout_rate": outcomes.get(PhaseOutcome.TIMEOUT, 0) / total,
                "aborted_rate": outcomes.get(PhaseOutcome.ABORTED, 0) / total,
            }

    @staticmethod
    def _suggest_accelerations(phase: str, probs: Dict, durations: List) -> List[str]:
        accel = []
        if probs.get(PhaseOutcome.TIMEOUT, 0) > 0.2:
            accel.append("increase_sensor_refresh_rate")
        if durations and sum(durations) / len(durations) > 90:
            accel.append("deploy_additional_tracking_assets")
        if phase == "find":
            accel.append("activate_all_sensors")
        elif phase == "engage":
            accel.append("pre_position_weapons")
        return accel


class TimeSeriesPredictiveModel(PredictiveModel):
    """Exponential-smoothing model per phase for duration and success rate."""

    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = alpha
        self._ema_duration: Dict[str, float] = {}
        self._ema_success: Dict[str, float] = {}
        self._counts: Dict[str, int] = defaultdict(int)

    def predict_phase(self, phase: str, context: Dict) -> PhasePrediction:
        dur = float(context.get("duration_sec", self._ema_duration.get(phase, 60.0)))
        base_p = self._ema_success.get(phase, 0.5)
        count = self._counts.get(phase, 0)
        confidence = min(1.0, count / 30.0)
        ml = PhaseOutcome.SUCCESS if base_p >= 0.5 else PhaseOutcome.FAILURE
        return PhasePrediction(
            phase=phase, predicted_duration_sec=dur,
            success_probability=base_p, failure_probability=1.0 - base_p,
            timeout_probability=0.0, aborted_probability=0.0,
            most_likely=ml, confidence=confidence,
            recommended_accelerations=["optimise_allocation"] if count > 5 else [],
        )

    def update(self, phase: str, duration_sec: float, outcome: PhaseOutcome) -> None:
        alpha = self.alpha
        prev_dur = self._ema_duration.get(phase, duration_sec)
        prev_suc = self._ema_success.get(phase, 0.5)
        self._ema_duration[phase] = alpha * duration_sec + (1 - alpha) * prev_dur
        is_success = 1.0 if outcome == PhaseOutcome.SUCCESS else 0.0
        self._ema_success[phase] = alpha * is_success + (1 - alpha) * prev_suc
        self._counts[phase] += 1

    def get_phase_stats(self, phase: str) -> Dict:
        return {
            "phase": phase,
            "ema_duration_sec": self._ema_duration.get(phase, 0.0),
            "ema_success_rate": self._ema_success.get(phase, 0.5),
            "n_samples": self._counts.get(phase, 0),
        }


class EnsemblePredictiveModel(PredictiveModel):
    """Weighted ensemble of multiple predictive models."""

    def __init__(self) -> None:
        self._models: List[Tuple[PredictiveModel, float]] = []
        self._total_weight: float = 0.0

    def add_model(self, model: PredictiveModel, weight: float = 1.0) -> None:
        self._models.append((model, weight))
        self._total_weight += weight

    def predict_phase(self, phase: str, context: Dict) -> PhasePrediction:
        if not self._models:
            return PhasePrediction(phase=phase)
        weighted_dur = 0.0
        weighted_success = 0.0
        weighted_failure = 0.0
        weighted_timeout = 0.0
        weighted_aborted = 0.0
        confidences = []
        for model, weight in self._models:
            p = model.predict_phase(phase, context)
            w = weight / self._total_weight
            weighted_dur += p.predicted_duration_sec * w
            weighted_success += p.success_probability * w
            weighted_failure += p.failure_probability * w
            weighted_timeout += p.timeout_probability * w
            weighted_aborted += p.aborted_probability * w
            confidences.append(p.confidence)
        total = weighted_success + weighted_failure + weighted_timeout + weighted_aborted
        if total > 0:
            scale = 1.0 / total
            weighted_success *= scale; weighted_failure *= scale
            weighted_timeout *= scale; weighted_aborted *= scale
        probs = {
            PhaseOutcome.SUCCESS: weighted_success,
            PhaseOutcome.FAILURE: weighted_failure,
            PhaseOutcome.TIMEOUT: weighted_timeout,
            PhaseOutcome.ABORTED: weighted_aborted,
        }
        ml = max(probs, key=probs.get)
        confidence = sum(confidences) / len(confidences) if confidences else 0.5
        return PhasePrediction(
            phase=phase, predicted_duration_sec=weighted_dur,
            success_probability=weighted_success,
            failure_probability=weighted_failure,
            timeout_probability=weighted_timeout,
            aborted_probability=weighted_aborted,
            most_likely=ml, confidence=confidence,
            recommended_accelerations=["evaluate_individual_models"] if len(self._models) > 1 else [],
        )

    def update(self, phase: str, duration_sec: float, outcome: PhaseOutcome) -> None:
        for model, _ in self._models:
            model.update(phase, duration_sec, outcome)

    def get_phase_stats(self, phase: str) -> Dict:
        return {f"model_{i}": m[0].get_phase_stats(phase)
                for i, m in enumerate(self._models)}


class PredictiveKillChain:
    """Top-level predictive kill-chain orchestrator."""

    def __init__(self) -> None:
        self._model: PredictiveModel = EnsemblePredictiveModel()
        self._history: List[Dict] = []
        self._lock = threading.RLock()
        self._callbacks: List = []
        self._model.add_model(MarkovPredictiveModel(), weight=1.0)
        self._model.add_model(TimeSeriesPredictiveModel(alpha=0.3), weight=0.5)

    def set_model(self, model: PredictiveModel) -> None:
        self._model = model

    def predict_target(self, target_id, current_phase, context=None) -> KillChainPrediction:
        context = context or {}
        predictions: Dict[str, PhasePrediction] = {}
        total_dur = 0.0
        bottleneck_phase: Optional[str] = None
        bottleneck_score = 0.0
        all_recommendations: List[str] = []
        phase_idx = PHASE_ORDER.index(current_phase) if current_phase in PHASE_ORDER else 0
        for phase in PHASE_ORDER:
            phase_context = dict(context)
            phase_context["duration_sec"] = phase_context.get(f"{phase}_duration_sec", 60.0)
            pred = self._model.predict_phase(phase, phase_context)
            predictions[phase] = pred
            if PHASE_ORDER.index(phase) >= phase_idx:
                total_dur += pred.predicted_duration_sec
                timeout_risk = pred.timeout_probability + pred.failure_probability
                if timeout_risk > bottleneck_score:
                    bottleneck_score = timeout_risk
                    bottleneck_phase = phase
                all_recommendations.extend(pred.recommended_accelerations)
        overall_success = 1.0
        for phase, pred in predictions.items():
            if PHASE_ORDER.index(phase) >= phase_idx:
                overall_success *= pred.success_probability
        return KillChainPrediction(
            target_id=target_id, predictions=predictions,
            overall_success_probability=overall_success,
            predicted_total_duration_sec=total_dur,
            predicted_bottleneck_phase=bottleneck_phase,
            estimated_remaining_threat_time_sec=total_dur,
            recommendations=list(set(all_recommendations)),
            metadata={"current_phase": current_phase},
        )

    def record_outcome(self, phase, duration_sec, outcome) -> None:
        with self._lock:
            self._model.update(phase, duration_sec, outcome)
            self._history.append({
                "phase": phase, "duration_sec": duration_sec,
                "outcome": outcome.value, "ts": time.time(),
            })
            if len(self._history) > 5000:
                self._history = self._history[-5000:]

    def get_history(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            return list(self._history[-limit:])

    def get_phase_stats(self, phase: str) -> Dict:
        return self._model.get_phase_stats(phase)

    def get_all_phase_stats(self) -> Dict:
        return {phase: self.get_phase_stats(phase) for phase in PHASE_ORDER}

    def on_prediction(self, callback) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def stats(self) -> Dict:
        with self._lock:
            return {
                "n_history": len(self._history),
                "model_type": type(self._model).__name__,
                "n_models": len(getattr(self._model, "_models", [])),
                "phases": self.get_all_phase_stats(),
            }
