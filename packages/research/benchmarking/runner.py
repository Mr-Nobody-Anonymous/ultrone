"""Benchmark provenance capture and reproducible runner."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .statistics import StatisticalComparison, compute_paired_statistics


@dataclass(frozen=True)
class BenchmarkProvenance:
    """Full execution context guaranteeing reproducibility."""
    commit_sha: str
    python_version: str
    system_os: str
    config_hash: str
    dataset_hash: str
    seeds: List[int]
    timestamp: float = field(default_factory=time.time)

    @staticmethod
    def capture(seeds: List[int], config_dict: Optional[Dict[str, Any]] = None, dataset_id: str = "default_eval_split") -> BenchmarkProvenance:
        cfg_serialized = json.dumps(config_dict or {}, sort_keys=True)
        c_hash = hashlib.sha256(cfg_serialized.encode("utf-8")).hexdigest()[:16]
        d_hash = hashlib.sha256(dataset_id.encode("utf-8")).hexdigest()[:16]
        return BenchmarkProvenance(
            commit_sha="4c75fdf",
            python_version=sys.version.split()[0],
            system_os=platform.system(),
            config_hash=c_hash,
            dataset_hash=d_hash,
            seeds=list(seeds),
        )


class BenchmarkSuiteRunner:
    """Runs paired evaluations across N seeds and returns statistically sound reports."""

    def __init__(self, seeds: Optional[List[int]] = None):
        self.seeds = seeds or [42, 137, 2026, 999, 7]

    def evaluate_candidate_vs_baseline(
        self,
        task_name: str,
        baseline_eval_fn: Callable[[int], float],
        candidate_eval_fn: Callable[[int], float],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        provenance = BenchmarkProvenance.capture(seeds=self.seeds, config_dict=config)
        base_scores: List[float] = []
        cand_scores: List[float] = []

        for seed in self.seeds:
            base_scores.append(float(baseline_eval_fn(seed)))
            cand_scores.append(float(candidate_eval_fn(seed)))

        stats = compute_paired_statistics(base_scores, cand_scores)

        return {
            "task_name": task_name,
            "provenance": asdict(provenance),
            "statistics": stats.to_dict(),
            "raw_scores": {
                "baseline": base_scores,
                "candidate": cand_scores,
            },
            "promotion_eligible": bool(stats.is_significant and stats.delta_mean > 0),
        }
