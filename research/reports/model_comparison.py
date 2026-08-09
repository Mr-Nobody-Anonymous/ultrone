# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model comparison report generator.

Generates markdown reports comparing candidate models against baselines,
including accuracy, reasoning accuracy, calibration, hallucination rate,
retrieval accuracy, latency, tokens/sec, memory usage, and robustness.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Research.Reports")


@dataclass
class ModelResult:
    """Evaluation results for a single model."""
    model_name: str
    model_version: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    evaluated_at: float = field(default_factory=lambda: time.time())
    dataset: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "evaluated_at": self.evaluated_at,
            "dataset": self.dataset,
        }


# Metrics tracked for every model comparison
TRACKED_METRICS = [
    "accuracy",
    "reasoning_accuracy",
    "calibration",
    "hallucination_rate",
    "retrieval_accuracy",
    "coding_success",
    "tool_use_success",
    "latency_ms",
    "tokens_per_sec",
    "memory_usage_gb",
    "gpu_utilization",
    "cost_per_1000_tokens",
    "robustness_score",
    "regression_rate",
]


class ModelComparisonReport:
    """Generates comparison reports between candidate and baseline models."""

    def __init__(self, output_dir: str = "./research/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        candidate: ModelResult,
        baseline: Optional[ModelResult] = None,
        additional_baselines: Optional[List[ModelResult]] = None,
    ) -> str:
        """Generate a markdown model comparison report.

        Parameters
        ----------
        candidate : ModelResult
            The candidate model results.
        baseline : Optional[ModelResult]
            The baseline model to compare against.
        additional_baselines : Optional[List[ModelResult]]
            Additional baseline models for comparison.

        Returns
        -------
        str
            Path to the generated report file.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            self.output_dir, f"model_comparison_{timestamp}.md"
        )

        all_models = [candidate]
        if baseline:
            all_models.append(baseline)
        if additional_baselines:
            all_models.extend(additional_baselines)

        content = self._render_report(candidate, all_models)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Generated comparison report: %s", report_path)

        # Also save JSON version
        json_path = report_path.replace(".md", ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "candidate": candidate.to_dict(),
                    "baselines": [m.to_dict() for m in all_models[1:]],
                    "generated_at": timestamp,
                },
                f,
                indent=2,
                default=str,
            )

        return report_path

    def _render_report(self, candidate: ModelResult, all_models: List[ModelResult]) -> str:
        """Render the markdown report content."""
        lines = []
        lines.append("# Model Comparison Report\n")
        lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        lines.append(f"**Candidate:** {candidate.model_name} v{candidate.model_version}\n")
        lines.append(f"**Dataset:** {candidate.dataset}\n")

        # Summary table
        lines.append("\n## Summary\n")
        lines.append("| Model | Version | Overall Score | Regression | Status |")
        lines.append("|-------|---------|---------------|------------|--------|")

        for model in all_models:
            overall = self._compute_overall_score(model.metrics)
            if model is candidate:
                status = "**CANDIDATE**"
            elif baseline := (all_models[1] if len(all_models) > 1 else None):
                if model is baseline:
                    status = "Baseline"
                else:
                    status = "Baseline"
            else:
                status = "Baseline"
            regression = "—"
            if model is not candidate and len(all_models) > 1:
                baseline_model = all_models[1] if len(all_models) > 1 else None
                if baseline_model:
                    reg_metrics = self._compute_regressions(candidate.metrics, baseline_model.metrics)
                    regression = f"{len(reg_metrics)} regressions" if reg_metrics else "None"

            lines.append(
                f"| {model.model_name} | {model.model_version} | "
                f"{overall:.4f} | {regression} | {status} |"
            )

        # Detailed metrics
        lines.append("\n## Detailed Metrics\n")
        header = "| Metric | " + " | ".join(m.model_name + " v" + m.model_version for m in all_models) + " |"
        sep = "|--------|" + "|".join(["--------" for _ in all_models]) + "|"
        lines.append(header)
        lines.append(sep)

        for metric in TRACKED_METRICS:
            row = f"| {metric} |"
            for model in all_models:
                val = model.metrics.get(metric)
                if val is not None:
                    row += f" {val:.4f} |"
                else:
                    row += " N/A |"
            lines.append(row)

        # Improvements/regressions
        if len(all_models) > 1:
            baseline = all_models[1]
            lines.append("\n## Improvements vs Baseline\n")
            improvements = self._compute_improvements(candidate.metrics, baseline.metrics)
            regressions = self._compute_regressions(candidate.metrics, baseline.metrics)

            if improvements:
                lines.append("\n**Improvements:**\n")
                for metric, change in improvements.items():
                    lines.append(f"- **{metric}**: {change:+.4f}")
            else:
                lines.append("\nNo improvements found.\n")

            if regressions:
                lines.append("\n**Regressions:**\n")
                for metric, change in regressions.items():
                    lines.append(f"- **{metric}**: {change:+.4f} ⚠️")
            else:
                lines.append("\nNo regressions found.\n")

        # Recommendation
        lines.append("\n## Recommendation\n")
        if len(all_models) > 1:
            final_regressions = self._compute_regressions(candidate.metrics, all_models[1].metrics)
        else:
            final_regressions = {}
        final_improvements = self._compute_improvements(candidate.metrics, all_models[1].metrics) if len(all_models) > 1 else {}
        approved = len(final_regressions) == 0 and len(final_improvements) > 0
        if approved:
            lines.append("**APPROVED** — Candidate shows improvement with no regressions.")
        else:
            lines.append("**REQUIRES REVIEW** — Candidate needs further evaluation before deployment.")

        # Metadata
        lines.append("\n## Metadata\n")
        lines.append("```json")
        lines.append(json.dumps(candidate.to_dict(), indent=2, default=str))
        lines.append("```")

        return "\n".join(lines)

    def _compute_overall_score(self, metrics: Dict[str, float]) -> float:
        """Compute a weighted overall score from metrics."""
        weights = {
            "accuracy": 0.3,
            "reasoning_accuracy": 0.2,
            "calibration": 0.1,
            "retrieval_accuracy": 0.1,
            "tool_use_success": 0.1,
            "robustness_score": 0.2,
        }
        score = 0.0
        total_weight = 0.0
        for metric, weight in weights.items():
            val = metrics.get(metric)
            if val is not None:
                score += val * weight
                total_weight += weight
        return score / max(total_weight, 1e-8)

    def _compute_improvements(self, candidate: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
        """Compute metric improvements (candidate - baseline)."""
        return {
            m: candidate.get(m, 0) - baseline.get(m, 0)
            for m in TRACKED_METRICS
            if m in candidate and m in baseline and candidate[m] > baseline[m]
        }

    def _compute_regressions(self, candidate: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, float]:
        """Compute metric regressions (candidate < baseline)."""
        return {
            m: candidate.get(m, 0) - baseline.get(m, 0)
            for m in TRACKED_METRICS
            if m in candidate and m in baseline and candidate[m] < baseline[m]
        }

    def list_reports(self) -> List[str]:
        """List all generated report files."""
        reports = []
        for f in sorted(os.listdir(self.output_dir)):
            if f.startswith("model_comparison_") and f.endswith(".md"):
                reports.append(f)
        return reports
