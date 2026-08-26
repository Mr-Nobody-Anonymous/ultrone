# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the general-world prediction benchmark (Sprint D flagship)."""

import pytest

from sandbox.prediction import (
    BayesianBeliefAgent,
    PredictionBenchmark,
    UniformAgent,
    expected_calibration_error,
    make_bayesian,
    recovery_ticks,
    steady_records,
    summarize,
)

EMISSIONS = {
    "calm":  {"alpha": 0.85, "beta": 0.12, "gamma": 0.03},
    "storm": {"alpha": 0.05, "beta": 0.13, "gamma": 0.82},
    "drift": {"alpha": 0.22, "beta": 0.72, "gamma": 0.06},
}
SWITCHES = ((25, "storm"), (45, "drift"))
SW_TICKS = [s for s, _ in SWITCHES]


def _run(factory, seed=7, ticks=70):
    bench = PredictionBenchmark(
        factory, EMISSIONS, seed=seed, n_ticks=ticks,
        dropout_probability=0.15, switches=SWITCHES,
    )
    return bench.run()


class TestCalibration:
    @pytest.fixture(scope="module")
    def records(self):
        return _run(make_bayesian(EMISSIONS))

    def test_beats_uniform_baseline(self, records):
        informed = summarize(records)
        naive = summarize(_run(lambda: UniformAgent(sorted(EMISSIONS))))
        assert informed["brier_mean"] < naive["brier_mean"]

    def test_predictions_are_calibrated_when_settled(self, records):
        """Steady-state confidence must track accuracy (transients excluded:
        right after a surprise miscalibration is expected and is scored by
        recovery_ticks instead)."""
        steady = steady_records(records, switch_ticks=SW_TICKS)
        assert expected_calibration_error(steady) < 0.20

    def test_accuracy_is_high_between_switches(self, records):
        steady = steady_records(records, switch_ticks=SW_TICKS)
        acc = sum(1 for r in steady if r.correct) / len(steady)
        assert acc > 0.80

    def test_dropout_preserves_beliefs(self):
        agent = BayesianBeliefAgent(sorted(EMISSIONS), EMISSIONS)
        before = agent.predict()
        agent.observe(None)  # lost packet
        assert agent.predict() == before


class TestRecovery:
    def test_recovers_from_regime_switches(self):
        records = _run(make_bayesian(EMISSIONS))
        for tick, _target in SWITCHES:
            rec = recovery_ticks(records, tick)
            assert rec is not None
            assert rec <= 12

    def test_recovery_recorded_in_summary(self):
        summary = summarize(
            _run(make_bayesian(EMISSIONS)), switch_ticks=SW_TICKS,
        )
        assert summary["recovery_after_25"] is not None
        assert summary["recovery_after_45"] is not None


class TestNovelRegime:
    def test_unseen_regime_degrades_gracefully(self):
        """Agent never told 'drift' exists must not collapse."""
        records = _run(make_bayesian(EMISSIONS, exclude="drift"))
        post = [r for r in records if r.tick > 45]
        mean_brier = sum(r.brier for r in post) / len(post)
        # Bounded loss: far from worst-case, no crash, beliefs stay sane.
        assert mean_brier < 1.2
        assert all(0.0 <= r.confidence <= 1.0 for r in post)


class TestDeterminism:
    def test_same_seed_identical_episode(self):
        a = _run(make_bayesian(EMISSIONS), seed=99)
        b = _run(make_bayesian(EMISSIONS), seed=99)
        assert [(r.tick, r.observed, r.top_hypothesis, r.brier) for r in a] \
            == [(r.tick, r.observed, r.top_hypothesis, r.brier) for r in b]

    def test_different_seed_different_draws(self):
        a = _run(make_bayesian(EMISSIONS), seed=1)
        b = _run(make_bayesian(EMISSIONS), seed=2)
        assert [r.observed for r in a] != [r.observed for r in b]
