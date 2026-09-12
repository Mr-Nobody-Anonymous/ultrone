# Copyright (c) Ultrone Contributors. All rights reserved.
"""Drift Detection — detects feature distribution and prediction drift."""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.DriftDetection")


@dataclass
class DriftConfig:
    """Configuration for drift detection."""
    method: str = "ks"            # ks (Kolmogorov-Smirnov), psi, mean_shift
    threshold: float = 0.05
    reference_size: int = 100


class DriftDetector:
    """Detects drift between reference and current distributions."""

    def __init__(self, config: Optional[DriftConfig] = None):
        self.config = config or DriftConfig()
        self._reference: Dict[str, List[float]] = {}
        self._drift_events: List[Dict[str, Any]] = []

    def set_reference(self, reference: Dict[str, List[float]]) -> None:
        """Set the reference distribution."""
        self._reference = {k: list(v) for k, v in reference.items()}

    def check(self, current: Dict[str, List[float]]) -> Dict[str, Any]:
        """Check for drift against the reference."""
        if not self._reference:
            return {"drifted": False, "message": "No reference distribution set", "features": {}}

        feature_results: Dict[str, Any] = {}
        global_drift = False
        for feature, ref_values in self._reference.items():
            cur_values = current.get(feature, [])
            if not cur_values:
                continue
            if self.config.method == "ks":
                p_value = self._ks_test(ref_values, cur_values)
                # Combine KS p-value with a mean-shift heuristic for small samples,
                # where the asymptotic KS approximation is unreliable.
                mean_diff = abs(statistics.mean(ref_values) - statistics.mean(cur_values))
                mean_scale = max(statistics.stdev(ref_values) if len(ref_values) > 1 else 1.0, 1e-9)
                normalized_shift = mean_diff / mean_scale
                drifted = p_value < self.config.threshold or normalized_shift > 3.0
            elif self.config.method == "psi":
                psi = self._psi(ref_values, cur_values)
                drifted = psi > 0.25
            else:  # mean_shift
                diff = abs(statistics.mean(ref_values) - statistics.mean(cur_values))
                drifted = diff > self.config.threshold
            feature_results[feature] = {
                "drifted": drifted,
                "p_value": p_value if self.config.method == "ks" else None,
                "method": self.config.method,
            }
            if drifted:
                global_drift = True

        report = {"drifted": global_drift, "features": feature_results}
        if global_drift:
            event = {"features": [k for k, v in feature_results.items() if v["drifted"]],
                     "method": self.config.method, "timestamp": __import__("time").time()}
            self._drift_events.append(event)
            report["event"] = event
        return report

    def _ks_test(self, a: List[float], b: List[float]) -> float:
        """Approximate two-sample Kolmogorov-Smirnov p-value."""
        a_sorted = sorted(a)
        b_sorted = sorted(b)
        all_sorted = sorted(a + b)
        d = 0.0
        for x in all_sorted:
            cdf_a = sum(1 for v in a_sorted if v <= x) / len(a_sorted)
            cdf_b = sum(1 for v in b_sorted if v <= x) / len(b_sorted)
            d = max(d, abs(cdf_a - cdf_b))
        # Smirnov approximation: p ≈ 1 - KS_cdf(sqrt(n)*D)
        import math
        n = (len(a_sorted) * len(b_sorted)) / (len(a_sorted) + len(b_sorted))
        lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * d
        p = self._ks_cdf(lam)
        return max(0.0, min(1.0, p))

    @staticmethod
    def _ks_cdf(lam: float) -> float:
        """Kolmogorov distribution CDF approximation."""
        import math
        if lam == 0:
            return 1.0
        total = 0.0
        for k in range(1, 20):
            total += (-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam)
        return 1.0 - 2.0 * total

    @staticmethod
    def _psi(reference: List[float], current: List[float]) -> float:
        """Population Stability Index."""
        # Create 10 quantile bins
        ref_min, ref_max = min(reference), max(reference)
        if ref_min == ref_max:
            ref_max += 1.0
        bins = 10
        edges = [ref_min + (ref_max - ref_min) * i / bins for i in range(bins + 1)]
        psi = 0.0
        for i in range(bins):
            r_count = sum(1 for v in reference if edges[i] <= v < (edges[i + 1] if i < bins - 1 else ref_max + 1))
            c_count = sum(1 for v in current if edges[i] <= v < (edges[i + 1] if i < bins - 1 else ref_max + 1))
            r_pct = (r_count + 1e-6) / (len(reference) + 1e-6)
            c_pct = (c_count + 1e-6) / (len(current) + 1e-6)
            psi += (r_pct - c_pct) * __import__("math").log(r_pct / c_pct)
        return psi

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "DriftDetector",
            "method": self.config.method,
            "reference_features": len(self._reference),
            "drift_events": len(self._drift_events),
        }


