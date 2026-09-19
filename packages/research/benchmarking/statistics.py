"""Statistical comparison and hypothesis testing across multiple benchmark seeds."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


import random
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class StatisticalComparison:
    """Rigorous paired statistical comparison between baseline and candidate across N seeds."""
    n_samples: int
    mean_baseline: float
    std_baseline: float
    mean_candidate: float
    std_candidate: float
    delta_mean: float
    ci_lower_95: float
    ci_upper_95: float
    cohens_d: float
    is_significant: bool
    bootstrap_ci_95: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "n_samples": self.n_samples,
            "mean_baseline": round(self.mean_baseline, 4),
            "std_baseline": round(self.std_baseline, 4),
            "mean_candidate": round(self.mean_candidate, 4),
            "std_candidate": round(self.std_candidate, 4),
            "delta_mean": round(self.delta_mean, 4),
            "ci_95": [round(self.ci_lower_95, 4), round(self.ci_upper_95, 4)],
            "cohens_d": round(self.cohens_d, 4),
            "is_significant": self.is_significant,
        }
        if self.bootstrap_ci_95 is not None:
            d["bootstrap_ci_95"] = [round(self.bootstrap_ci_95[0], 4), round(self.bootstrap_ci_95[1], 4)]
        return d


def compute_bootstrap_ci(
    diffs: Sequence[float],
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float]:
    """Computes non-parametric bootstrap confidence interval over paired differences."""
    rng = random.Random(seed)
    n = len(diffs)
    resample_means: List[float] = []

    for _ in range(n_resamples):
        sample = [rng.choice(diffs) for _ in range(n)]
        resample_means.append(sum(sample) / n)

    resample_means.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(math.floor(alpha / 2.0 * n_resamples))
    upper_idx = int(math.ceil((1.0 - alpha / 2.0) * n_resamples)) - 1
    lower_idx = max(0, min(lower_idx, n_resamples - 1))
    upper_idx = max(0, min(upper_idx, n_resamples - 1))

    return resample_means[lower_idx], resample_means[upper_idx]


def compute_paired_statistics(
    baseline_scores: Sequence[float],
    candidate_scores: Sequence[float],
    compute_bootstrap: bool = True,
) -> StatisticalComparison:
    """Computes paired differences, paired 95% confidence interval, paired Cohen's d_z, and bootstrap CI."""
    n = len(baseline_scores)
    if n < 2 or len(candidate_scores) != n:
        raise ValueError(f"At least 2 paired seed observations required (got {n} and {len(candidate_scores)})")

    m_base = sum(baseline_scores) / n
    m_cand = sum(candidate_scores) / n

    var_base = sum((x - m_base) ** 2 for x in baseline_scores) / (n - 1)
    var_cand = sum((x - m_cand) ** 2 for x in candidate_scores) / (n - 1)
    std_base = math.sqrt(var_base)
    std_cand = math.sqrt(var_cand)

    # Paired differences: D_i = candidate_i - baseline_i
    diffs = [c - b for b, c in zip(baseline_scores, candidate_scores)]
    mean_diff = sum(diffs) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
    std_diff = math.sqrt(var_diff)
    sem_diff = std_diff / math.sqrt(n)

    # 95% Student's t distribution approximation over paired differences
    t_crit = 2.262 if n <= 10 else 1.96
    margin = t_crit * sem_diff
    ci_lower = mean_diff - margin
    ci_upper = mean_diff + margin

    # True paired effect size: Cohen's d_z = mean(diff) / std(diff)
    cohens_d_z = mean_diff / (std_diff if std_diff > 1e-9 else 1e-9)

    # Non-parametric bootstrap CI
    boot_ci = compute_bootstrap_ci(diffs) if compute_bootstrap else None

    # Significant if 95% CI excludes zero and paired effect size |d_z| >= 0.2
    is_sig = (ci_lower > 0 or ci_upper < 0) and abs(cohens_d_z) >= 0.2

    return StatisticalComparison(
        n_samples=n,
        mean_baseline=m_base,
        std_baseline=std_base,
        mean_candidate=m_cand,
        std_candidate=std_cand,
        delta_mean=mean_diff,
        ci_lower_95=ci_lower,
        ci_upper_95=ci_upper,
        cohens_d=cohens_d_z,
        is_significant=is_sig,
        bootstrap_ci_95=boot_ci,
    )
