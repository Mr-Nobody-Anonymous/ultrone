# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the frontier benchmark harness.

Covers the harness (solver-driven evaluation), the benchmark runners
(GSM8K, MMLU, HumanEval, MBPP), the history tracker (never overwrites runs),
and the graph generator.
"""

from __future__ import annotations

import os

import pytest

from benchmarks.harness import BenchmarkHarness, BenchmarkProblem, BenchmarkRun
from benchmarks.runners import gsm8k_runner, mmlu_runner, human_eval_runner, mbpp_runner, get_runner
from benchmarks.history import BenchmarkHistory, HistoricalRun
from benchmarks.graph import BenchmarkGraph


# ---------------------------------------------------------------------------
# Test solvers
# ---------------------------------------------------------------------------
class MathSolver:
    """A solver that evaluates simple arithmetic from the prompt."""

    def __call__(self, prompt: str):
        import re

        m = re.search(r"(\d+)\s*([+\-*/x])\s*(\d+)", prompt)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                return str(a + b)
            if op == "-":
                return str(a - b)
            if op in ("*", "x"):
                return str(a * b)
            if op == "/":
                return str(a // b)
        return "0"


class MMLUSolver:
    """A solver that returns the parenthesized option for a MCQ."""

    def __call__(self, prompt: str):
        import re

        m = re.search(r"\(([A-D])\)", prompt)
        return m.group(1) if m else "A"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------
class TestBenchmarkHarness:
    def test_run_arithmetic(self):
        solver = MathSolver()
        harness = BenchmarkHarness(solver=solver)
        problems = [
            BenchmarkProblem(prompt="What is 2 + 3?", expected=5),
            BenchmarkProblem(prompt="What is 4 + 6?", expected=10),
        ]
        run = harness.run("arithmetic", problems)
        assert isinstance(run, BenchmarkRun)
        assert run.accuracy == 1.0
        assert len(run.results) == 2

    def test_run_with_custom_judge(self):
        def judge(solution, problem):
            return True, 1.0

        solver = lambda prompt: "anything"  # noqa: E731
        harness = BenchmarkHarness(solver=solver, judge=judge)
        run = harness.run("judged", [BenchmarkProblem(prompt="q", expected="x")])
        assert run.accuracy == 1.0

    def test_no_results_accuracy_zero(self):
        harness = BenchmarkHarness(solver=lambda p: "")
        run = harness.run("empty", [])
        assert run.accuracy == 0.0

    def test_get_stats(self):
        harness = BenchmarkHarness(solver=MathSolver())
        harness.run("a", [BenchmarkProblem(prompt="2 + 2", expected=4)])
        stats = harness.get_stats()
        assert stats["runs"] == 1
        assert stats["avg_accuracy"] == 1.0


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------
class TestRunners:
    def test_gsm8k_runner(self):
        problems = gsm8k_runner(limit=5)
        assert len(problems) == 5
        assert all(isinstance(p, BenchmarkProblem) for p in problems)

    def test_mmlu_runner(self):
        problems = mmlu_runner(limit=10)
        assert len(problems) == 10
        assert all(p.expected is not None for p in problems)

    def test_human_eval_runner(self):
        problems = human_eval_runner(limit=3)
        assert len(problems) == 3

    def test_mbpp_runner(self):
        problems = mbpp_runner(limit=5)
        assert len(problems) == 5

    def test_get_runner_unknown(self):
        with pytest.raises(KeyError):
            get_runner("does_not_exist")

    def test_get_runner(self):
        factory = get_runner("gsm8k")
        problems = factory()
        assert len(problems) >= 1


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class TestBenchmarkHistory:
    def test_record_never_overwrites(self, tmp_path):
        path = str(tmp_path / "history.json")
        history = BenchmarkHistory(ledger_path=path)
        history.record("gsm8k", 0.5, 10)
        history.record("gsm8k", 0.7, 10)
        runs = history.get_runs("gsm8k")
        assert len(runs) == 2
        assert runs[0].accuracy == 0.5
        assert runs[1].accuracy == 0.7

    def test_get_latest_and_best(self, tmp_path):
        path = str(tmp_path / "history.json")
        history = BenchmarkHistory(ledger_path=path)
        history.record("mmlu", 0.4, 10)
        history.record("mmlu", 0.9, 10)
        history.record("mmlu", 0.6, 10)
        assert history.get_latest("mmlu").accuracy == 0.6
        assert history.get_best("mmlu").accuracy == 0.9

    def test_get_improvement(self, tmp_path):
        path = str(tmp_path / "history.json")
        history = BenchmarkHistory(ledger_path=path)
        history.record("gsm8k", 0.5, 10)
        history.record("gsm8k", 0.8, 10)
        assert history.get_improvement("gsm8k") == pytest.approx(0.3)

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "history.json")
        history = BenchmarkHistory(ledger_path=path)
        history.record("humaneval", 0.6, 5)
        # New instance loads the same ledger.
        reloaded = BenchmarkHistory(ledger_path=path)
        assert len(reloaded.get_runs("humaneval")) == 1

    def test_get_timeseries(self, tmp_path):
        path = str(tmp_path / "history.json")
        history = BenchmarkHistory(ledger_path=path)
        history.record("x", 0.5, 5)
        history.record("x", 0.8, 5)
        timestamps, accuracies = history.get_timeseries("x")
        assert len(timestamps) == 2
        assert accuracies == [0.5, 0.8]


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
class TestBenchmarkGraph:
    def test_plot_generates_file(self, tmp_path):
        history = BenchmarkHistory(ledger_path=str(tmp_path / "hist.json"))
        history.record("gsm8k", 0.5, 10)
        history.record("gsm8k", 0.8, 10)
        graph = BenchmarkGraph(history=history)
        out = str(tmp_path / "plot.png")
        saved = graph.plot(["gsm8k"], output_path=out)
        assert os.path.exists(saved)

    def test_plot_no_history(self, tmp_path):
        history = BenchmarkHistory(ledger_path=str(tmp_path / "hist.json"))
        graph = BenchmarkGraph(history=history)
        out = graph.plot(["nonexistent"], output_path=str(tmp_path / "p.png"))
        assert out == ""
