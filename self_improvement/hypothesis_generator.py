# Copyright (c) Ultrone Contributors. All rights reserved.
"""Hypothesis Generator — generates improvement hypotheses from telemetry
weaknesses and research findings.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.SelfImprovement.Hypothesis")


class HypothesisGenerator:
    """Generates improvement hypotheses from identified weaknesses."""

    def __init__(self):
        self._hypotheses: List[Dict[str, Any]] = []

    def generate_from_weaknesses(self, weaknesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate hypotheses from identified weaknesses."""
        hypotheses = []
        for weakness in weaknesses:
            hypothesis = self._create_hypothesis(weakness)
            if hypothesis:
                hypotheses.append(hypothesis)
                self._hypotheses.append(hypothesis)
        return hypotheses

    def generate_from_research(self, papers: List[Any]) -> List[Dict[str, Any]]:
        """Generate hypotheses from research papers."""
        hypotheses = []
        for paper in papers:
            if not paper.algorithms:
                continue
            hypothesis = {
                "hypothesis_id": f"H-{uuid.uuid4().hex[:8]}",
                "title": f"Adopt {', '.join(paper.algorithms[:2])} from '{paper.title}'",
                "description": "Implement algorithms from paper to improve platform capabilities",
                "source": "research",
                "paper_id": paper.paper_id,
                "algorithms": paper.algorithms,
                "confidence": paper.confidence_score,
                "created_at": time.time(),
                "status": "proposed",
            }
            hypotheses.append(hypothesis)
            self._hypotheses.append(hypothesis)
        return hypotheses

    def _create_hypothesis(self, weakness: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a hypothesis from a weakness."""
        wtype = weakness.get("type")
        component = weakness.get("component", "unknown")
        severity = weakness.get("severity", "medium")

        if wtype == "high_failure_rate":
            return {
                "hypothesis_id": f"H-{uuid.uuid4().hex[:8]}",
                "title": f"Reduce failure rate in {component}",
                "description": f"Component '{component}' has high failure rate. "
                f"Hypothesis: adding error recovery and retry logic will reduce failures.",
                "source": "telemetry",
                "component": component,
                "severity": severity,
                "confidence": 0.6,
                "created_at": time.time(),
                "status": "proposed",
            }
        elif wtype == "performance_degradation":
            metric = weakness.get("metric", "unknown")
            return {
                "hypothesis_id": f"H-{uuid.uuid4().hex[:8]}",
                "title": f"Improve {metric} performance",
                "description": f"Metric '{metric}' shows degradation. "
                f"Hypothesis: optimizing the implementation will restore performance.",
                "source": "telemetry",
                "metric": metric,
                "severity": severity,
                "confidence": 0.5,
                "created_at": time.time(),
                "status": "proposed",
            }
        elif wtype == "excessive_warnings":
            return {
                "hypothesis_id": f"H-{uuid.uuid4().hex[:8]}",
                "title": "Reduce warning noise",
                "description": "Excessive warnings detected. "
                "Hypothesis: improving error handling will reduce warning noise.",
                "source": "telemetry",
                "severity": severity,
                "confidence": 0.4,
                "created_at": time.time(),
                "status": "proposed",
            }
        return None

    def get_hypotheses(self) -> List[Dict[str, Any]]:
        """Get all generated hypotheses."""
        return self._hypotheses

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "HypothesisGenerator",
            "hypotheses_generated": len(self._hypotheses),
        }
