# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-Improvement Loop — the core continuous improvement engine.

Implements the full Observe → Hypothesize → Experiment → Validate → Adopt
cycle for the ULTRONE autonomous research platform.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from knowledge_engine.memory_manager import KnowledgeMemoryManager
from research_db.store import ResearchDatabase
from .telemetry import TelemetryCollector
from .hypothesis_generator import HypothesisGenerator
from .literature_search import LiteratureSearch
from .experiment_runner import ExperimentRunner

logger = logging.getLogger("Ultrone.SelfImprovement.Loop")


class SelfImprovementLoop:
    """Continuous self-improvement engine.

    Cycle:
    1. Observe: collect telemetry, identify weaknesses
    2. Hypothesize: generate improvement hypotheses
    3. Research: search for relevant literature and implementations
    4. Experiment: design and run experiments
    5. Validate: benchmark against previous versions
    6. Adopt/Reject: recommend adoption or rejection
    7. Archive: archive every experiment
    """

    def __init__(
        self,
        knowledge: Optional[KnowledgeMemoryManager] = None,
        research_db: Optional[ResearchDatabase] = None,
        min_benchmark_gain: float = 0.02,
        experiment_runner: Optional[ExperimentRunner] = None,
    ):
        self.knowledge = knowledge or KnowledgeMemoryManager()
        self.research_db = research_db or ResearchDatabase()
        self.telemetry = TelemetryCollector()
        self.hypothesis_generator = HypothesisGenerator()
        self.literature_search = LiteratureSearch(knowledge=self.knowledge, research_db=self.research_db)
        self.min_benchmark_gain = min_benchmark_gain
        self.experiment_runner = experiment_runner or ExperimentRunner(min_improvement=min_benchmark_gain)
        self._cycle_count = 0
        self._adopted: List[Dict[str, Any]] = []
        self._rejected: List[Dict[str, Any]] = []

    async def run_cycle(self) -> Dict[str, Any]:
        """Execute one full self-improvement cycle."""
        self._cycle_count += 1
        cycle_start = time.time()

        # Phase 1: Observe
        weaknesses = self.telemetry.identify_weaknesses()
        self.telemetry.record_event("observe", {"weaknesses": len(weaknesses)})

        # Phase 2: Hypothesize
        hypotheses = self.hypothesis_generator.generate_from_weaknesses(weaknesses)
        papers = self.research_db.list_papers()
        research_hypotheses = self.hypothesis_generator.generate_from_research(papers)
        all_hypotheses = hypotheses + research_hypotheses

        # Phase 3: Research
        research_results = []
        for hypothesis in all_hypotheses[:5]:  # Limit concurrent improvements
            related = self.literature_search.find_related_research(hypothesis)
            research_results.append(
                {
                    "hypothesis": hypothesis,
                    "related": related,
                }
            )

        # Phase 4: Experiment
        experiment_results = []
        for result in research_results:
            experiment = self._run_experiment(result["hypothesis"])
            experiment_results.append(experiment)

        # Phase 5: Validate
        validation_results = []
        for experiment in experiment_results:
            validation = self._validate_experiment(experiment)
            validation_results.append(validation)

        # Phase 6: Adopt/Reject
        for validation in validation_results:
            if validation["adopt"]:
                self._adopted.append(validation)
            else:
                self._rejected.append(validation)

        # Phase 7: Archive
        self._archive_cycle(
            {
                "cycle": self._cycle_count,
                "weaknesses": weaknesses,
                "hypotheses": all_hypotheses,
                "experiments": experiment_results,
                "validations": validation_results,
                "duration_seconds": time.time() - cycle_start,
            }
        )

        return {
            "cycle": self._cycle_count,
            "weaknesses_identified": len(weaknesses),
            "hypotheses_generated": len(all_hypotheses),
            "experiments_run": len(experiment_results),
            "adopted": len(self._adopted),
            "rejected": len(self._rejected),
            "duration_seconds": time.time() - cycle_start,
        }

    def _run_experiment(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Run a real experiment for a hypothesis.

        Uses the ExperimentRunner which compares baseline vs candidate via
        actual evaluation functions. No random numbers — improvements are
        measured, not simulated.
        """
        from research_db.schema import ExperimentRecord

        experiment = ExperimentRecord(
            hypothesis=hypothesis.get("title", ""),
            research_motivation=hypothesis.get("description", ""),
            implementation="Candidate implementation in isolated branch",
            dataset="standard_benchmark",
            success_criteria=f"Improvement >= {self.min_benchmark_gain:.0%}",
            status="running",
        )
        self.research_db.save_experiment(experiment)

        # Run the real experiment (baseline vs candidate comparison).
        # If no real evaluation functions are configured, this will raise
        # rather than fabricate results.
        try:
            result = self.experiment_runner.run(hypothesis)
        except ValueError as exc:
            # No real evaluation configured: record the experiment as needing
            # configuration rather than fabricating a result.
            experiment.status = "needs_configuration"
            experiment.conclusion = f"Experiment requires real evaluation functions: {exc}"
            experiment.recommendation = "reject"
            experiment.updated_at = time.time()
            self.research_db.save_experiment(experiment)
            return {
                "experiment_id": experiment.experiment_id,
                "hypothesis": hypothesis,
                "metrics": {},
                "recommendation": "reject",
                "error": str(exc),
            }

        improvement = result.improvement
        metrics = result.metrics

        experiment.status = "completed"
        experiment.evaluation_metrics = metrics
        experiment.conclusion = (
            f"Experiment achieved {improvement:.2%} improvement. "
            f"{'Passes' if result.passed else 'Does not pass'} adoption threshold "
            f"of {self.min_benchmark_gain:.0%} with confidence {result.statistical_confidence:.2f}."
        )
        experiment.recommendation = "adopt" if result.passed else "reject"
        experiment.updated_at = time.time()
        self.research_db.save_experiment(experiment)

        return {
            "experiment_id": experiment.experiment_id,
            "hypothesis": hypothesis,
            "metrics": metrics,
            "recommendation": experiment.recommendation,
            "statistical_confidence": result.statistical_confidence,
        }

    def _validate_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an experiment result."""
        metrics = experiment.get("metrics", {})
        improvement = metrics.get("improvement", 0.0)
        adopt = improvement >= self.min_benchmark_gain

        return {
            "experiment_id": experiment.get("experiment_id"),
            "hypothesis": experiment.get("hypothesis", {}),
            "improvement": improvement,
            "threshold": self.min_benchmark_gain,
            "adopt": adopt,
            "reason": (
                f"Improvement {improvement:.2%} {'meets' if adopt else 'does not meet'} "
                f"threshold {self.min_benchmark_gain:.0%}"
            ),
        }

    def _archive_cycle(self, cycle_data: Dict[str, Any]) -> None:
        """Archive a cycle in the knowledge engine."""
        self.knowledge.store_auto_categorized(
            content=f"Self-improvement cycle {cycle_data['cycle']} completed: "
            f"{len(cycle_data['hypotheses'])} hypotheses, "
            f"{len(cycle_data['experiments'])} experiments, "
            f"{len(cycle_data['validations'])} validations",
            tags=["self_improvement", "cycle"],
            entities=[f"cycle-{cycle_data['cycle']}"],
            confidence_score=0.9,
            layer="episodic",
            metadata=cycle_data,
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "SelfImprovementLoop",
            "cycles_run": self._cycle_count,
            "adopted": len(self._adopted),
            "rejected": len(self._rejected),
            "telemetry": self.telemetry.get_stats(),
            "hypothesis_generator": self.hypothesis_generator.get_stats(),
            "literature_search": self.literature_search.get_stats(),
        }
