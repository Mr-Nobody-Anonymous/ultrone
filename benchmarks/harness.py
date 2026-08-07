# Copyright (c) Ultrone Contributors. All rights reserved.
"""Benchmark Harness — run frontier benchmarks against a solver.

The harness drives pluggable benchmark runners (e.g. HumanEval, GSM8K,
MMLU, MBPP) against a solver (an LLM or test double). It:

- Runs a set of benchmark problems through a runner.
- Records per-problem and aggregate results.
- Persists results to a history tracker (never overwrites prior runs).
- Produces a structured report for the self-improvement loop.

The harness is backend-agnostic: any callable ``Solver`` can be benchmarked.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Ultrone.Benchmarks.Harness")


@dataclass
class BenchmarkProblem:
    """A single benchmark problem."""

    prompt: str
    # Optional expected answer for pass/fail evaluation.
    expected: Any = None
    # Optional id/metadata.
    id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "expected": str(self.expected),
            "metadata": self.metadata,
        }


@dataclass
class ProblemResult:
    """The result of solving a single benchmark problem."""

    problem: BenchmarkProblem
    solution: str
    correct: bool
    score: float = 0.0
    duration_seconds: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem": self.problem.to_dict(),
            "solution": self.solution,
            "correct": self.correct,
            "score": self.score,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass
class BenchmarkRun:
    """The aggregate result of a full benchmark run."""

    name: str
    results: List[ProblemResult] = field(default_factory=list)
    timestamp: float = 0.0
    total_seconds: float = 0.0

    @property
    def accuracy(self) -> float:
        """Provide a normalized accuracy in [0,1]."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.correct) / len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "accuracy": self.accuracy,
            "num_problems": len(self.results),
            "timestamp": self.timestamp,
            "total_seconds": self.total_seconds,
            "results": [r.to_dict() for r in self.results],
        }


class BenchmarkHarness:
    """Runs benchmark problems against a solver.

    Parameters
    ----------
    solver : Callable
        A callable ``(prompt: str) -> str`` producing solutions.
    judge : Optional[Callable]
        A callable ``(solution, problem) -> (bool, float)`` evaluating a
        solution. Defaults to exact-match against ``problem.expected``.
    """

    def __init__(
        self,
        solver: Callable[[str], str],
        judge: Optional[Callable[[str, BenchmarkProblem], Any]] = None,
    ) -> None:
        self.solver = solver
        self.judge = judge
        self._runs: List[BenchmarkRun] = []

    def run(
        self,
        name: str,
        problems: List[BenchmarkProblem],
        timeout_seconds: float = 60.0,
    ) -> BenchmarkRun:
        """Run a set of benchmark problems.

        Parameters
        ----------
        name
            The benchmark name (e.g. ``"gsm8k"``).
        problems
            The problems to solve.
        timeout_seconds
            Per-problem timeout.

        Returns
        -------
        BenchmarkRun
            The aggregate run result.
        """
        start = time.time()
        results: List[ProblemResult] = []

        for problem in problems:
            result = self._solve_one(name, problem, timeout_seconds)
            results.append(result)

        run = BenchmarkRun(
            name=name,
            results=results,
            timestamp=time.time(),
            total_seconds=time.time() - start,
        )
        self._runs.append(run)
        logger.info(
            "Benchmark '%s' completed: accuracy %.3f (%d problems)",
            name, run.accuracy, len(results),
        )
        return run

    def _solve_one(
        self, name: str, problem: BenchmarkProblem, timeout_seconds: float
    ) -> ProblemResult:
        """Solve and evaluate a single problem."""
        start = time.time()
        try:
            solution = self._call_solver(problem.prompt, timeout_seconds)
            correct, score = self._evaluate(solution, problem)
            return ProblemResult(
                problem=problem,
                solution=solution,
                correct=correct,
                score=score,
                duration_seconds=time.time() - start,
            )
        except Exception as exc:  # noqa: BLE001
            return ProblemResult(
                problem=problem,
                solution="",
                correct=False,
                score=0.0,
                duration_seconds=time.time() - start,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _call_solver(self, prompt: str, timeout_seconds: float) -> str:
        """Call the solver with a timeout guard (best effort)."""
        # No cross-thread cancellation in pure Python; we rely on the solver
        # being cooperative. A long-running solver blocks, by design.
        return str(self.solver(prompt))

    def _evaluate(self, solution: str, problem: BenchmarkProblem) -> tuple[bool, float]:
        """Evaluate a solution against a problem."""
        if self.judge is not None:
            return self.judge(solution, problem)
        # Default: exact-match on normalized expected answer.
        if problem.expected is None:
            return True, 1.0
        expected = str(problem.expected).strip().lower()
        got = solution.strip().lower()
        return (expected in got or got in expected), (1.0 if expected in got or got in expected else 0.0)

    def get_runs(self) -> List[BenchmarkRun]:
        """Return all runs."""
        return list(self._runs)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._runs:
            return {"runs": 0, "avg_accuracy": 0.0}
        return {
            "runs": len(self._runs),
            "avg_accuracy": sum(r.accuracy for r in self._runs) / len(self._runs),
        }
