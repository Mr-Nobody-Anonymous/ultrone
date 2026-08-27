"""Tests for Battle Damage Assessment and Predictive Kill-Chain modules."""
from __future__ import annotations

import pytest

from brain.reasoning.battle_damage_assessment import (
    BattleDamageAssessment,
    BDAConfidence,
    BDAResult,
    BDASeverity,
    DamageAssessmentEngine,
    DamageIndicator,
    ReEngagementRecommendation,
)
from brain.reasoning.predictive_kill_chain import (
    EnsemblePredictiveModel,
    KillChainPrediction,
    MarkovPredictiveModel,
    PhaseOutcome,
    PhasePrediction,
    PredictiveKillChain,
    PredictiveModel,
    TimeSeriesPredictiveModel,
    PHASE_ORDER,
)


class TestBDAResult:
    def test_construction(self):
        r = BDAResult(target_id="T1", engagement_id="E1")
        assert r.target_id == "T1"
        assert r.severity == BDASeverity.NONE
        assert r.damage_fraction == 0.0
        assert r.confidence == BDAConfidence.VERY_LOW

    def test_to_dict_serializable(self):
        r = BDAResult(target_id="T1", engagement_id="E1",
                      severity=BDASeverity.HEAVY, damage_fraction=0.8)
        d = r.to_dict()
        assert d["severity"] == "heavy"
        assert d["damage_fraction"] == 0.8
        assert "result_id" in d
        assert "timestamp" in d

    def test_n_samples_indicator(self):
        r = BDAResult(
            target_id="T1", engagement_id="E1",
            indicators={DamageIndicator.VISUAL: {"score": 0.5},
                        DamageIndicator.RADAR: {"score": 0.4}}
        )
        assert r.n_samples_indicator() == 2


class TestBattleDamageAssessment:
    def test_empty_reports_yields_zero(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={})
        assert r.damage_fraction == 0.0
        assert r.severity == BDASeverity.NONE
        assert r.confidence == BDAConfidence.VERY_LOW

    def test_visual_damage_heavy(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {"damage_score": 0.95}
        })
        assert r.damage_fraction > 0.8
        assert r.severity == BDASeverity.DESTROYED
        assert r.reengagement == ReEngagementRecommendation.STAND_DOWN

    def test_partial_damage(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {"damage_score": 0.4},
            DamageIndicator.SAR_IMAGERY: {"damage_score": 0.5},
        })
        assert 0.3 < r.damage_fraction < 0.6
        assert r.severity == BDASeverity.MODERATE

    def test_structural_functional_breakdown(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {
                "damage_score": 0.6,
                "structural": 0.9, "functional": 0.3, "mobility": 0.5,
            }
        })
        assert r.structural_damage > r.functional_damage
        assert 0.0 <= r.damage_fraction <= 1.0

    def test_score_clamping(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {"damage_score": 5.0}
        })
        assert r.damage_fraction <= 1.0

    def test_recommendation_stand_down_for_destroyed(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {"damage_score": 0.99}
        })
        assert r.reengagement == ReEngagementRecommendation.STAND_DOWN

    def test_recommendation_immediate_for_threat(self):
        bda = BattleDamageAssessment()
        r = bda.assess("T1", "E1", sensor_reports={
            DamageIndicator.VISUAL: {"damage_score": 0.20,
                                     "structural": 0.2,
                                     "functional": 0.2, "mobility": 0.2}
        })
        assert r.still_threatening is True
        assert r.reengagement in (ReEngagementRecommendation.IMMEDIATE,
                                  ReEngagementRecommendation.SCHEDULED,
                                  ReEngagementRecommendation.HUNT)


class TestDamageAssessmentEngine:
    def test_initial_state(self):
        e = DamageAssessmentEngine()
        assert e.stats()["total_assessments"] == 0

    def test_record_and_retrieve(self):
        e = DamageAssessmentEngine()
        r = e.assess("T1", "E1", {DamageIndicator.VISUAL: {"damage_score": 0.7}})
        assert e.get_assessment(r.result_id) is r
        assert e.get_latest_assessment("T1") is r
        assert e.get_target_history("T1") == [r]

    def test_pending_reengagement_for_threat(self):
        e = DamageAssessmentEngine()
        e.assess("T1", "E1", {DamageIndicator.VISUAL: {
            "damage_score": 0.2, "structural": 0.2,
            "functional": 0.2, "mobility": 0.2
        }})
        assert e.get_reengagement_plan("T1") is not None

    def test_dismiss_reengagement(self):
        e = DamageAssessmentEngine()
        e.assess("T1", "E1", {DamageIndicator.VISUAL: {
            "damage_score": 0.2, "structural": 0.2,
            "functional": 0.2, "mobility": 0.2
        }})
        e.dismiss_reengagement("T1")
        assert e.get_reengagement_plan("T1") is None

    def test_callback_fires(self):
        e = DamageAssessmentEngine()
        seen = []
        e.on_assessment(lambda r: seen.append(r))
        e.assess("T1", "E1", {DamageIndicator.VISUAL: {"damage_score": 0.5}})
        assert len(seen) == 1

    def test_clear(self):
        e = DamageAssessmentEngine()
        e.assess("T1", "E1", {DamageIndicator.VISUAL: {"damage_score": 0.5}})
        e.clear()
        assert e.stats()["total_assessments"] == 0

    def test_history_bounded(self):
        e = DamageAssessmentEngine()
        for i in range(60):
            e.assess("T1", f"E{i}", {DamageIndicator.VISUAL: {"damage_score": 0.5}})
        assert len(e.get_target_history("T1")) <= 50


class TestPhasePrediction:
    def test_construction(self):
        p = PhasePrediction(phase="find")
        assert p.phase == "find"
        assert p.most_likely == PhaseOutcome.SUCCESS

    def test_to_dict(self):
        p = PhasePrediction(phase="engage", success_probability=0.7)
        d = p.to_dict()
        assert d["phase"] == "engage"
        assert d["success_probability"] == 0.7


class TestMarkovPredictiveModel:
    def test_cold_start(self):
        m = MarkovPredictiveModel()
        p = m.predict_phase("find", {"duration_sec": 30})
        assert p.phase == "find"
        assert p.predicted_duration_sec == 30

    def test_update_and_predict(self):
        m = MarkovPredictiveModel()
        for _ in range(10):
            m.update("find", 60.0, PhaseOutcome.SUCCESS)
        p = m.predict_phase("find", {"duration_sec": 60})
        assert p.success_probability > 0.5

    def test_stats_after_updates(self):
        m = MarkovPredictiveModel()
        m.update("engage", 90.0, PhaseOutcome.SUCCESS)
        m.update("engage", 80.0, PhaseOutcome.FAILURE)
        s = m.get_phase_stats("engage")
        assert s["n_samples"] == 2
        assert s["success_rate"] == 0.5
        assert s["avg_duration_sec"] == 85.0

    def test_bounded_memory(self):
        m = MarkovPredictiveModel()
        for i in range(300):
            m.update("track", float(i), PhaseOutcome.SUCCESS)
        s = m.get_phase_stats("track")
        assert s["n_samples"] <= 200


class TestTimeSeriesPredictiveModel:
    def test_cold_start(self):
        m = TimeSeriesPredictiveModel()
        p = m.predict_phase("find", {"duration_sec": 45})
        assert p.predicted_duration_sec == 45

    def test_update_changes_ema(self):
        m = TimeSeriesPredictiveModel(alpha=0.5)
        m.update("find", 100.0, PhaseOutcome.SUCCESS)
        p = m.predict_phase("find", {})
        assert p.predicted_duration_sec == 100.0

    def test_success_rate_updates(self):
        m = TimeSeriesPredictiveModel(alpha=0.5)
        m.update("engage", 10.0, PhaseOutcome.SUCCESS)
        m.update("engage", 10.0, PhaseOutcome.SUCCESS)
        p = m.predict_phase("engage", {})
        # alpha=0.5, 2 successes: EMA = 0.5*1 + 0.5*(0.5*1 + 0.5*0.5) = 0.875
        assert 0.8 < p.success_probability < 0.9

    def test_stats(self):
        m = TimeSeriesPredictiveModel()
        m.update("find", 50.0, PhaseOutcome.SUCCESS)
        s = m.get_phase_stats("find")
        assert s["n_samples"] == 1


class TestEnsemblePredictiveModel:
    def test_empty_ensemble(self):
        m = EnsemblePredictiveModel()
        p = m.predict_phase("find", {})
        assert p.phase == "find"

    def test_combines_models(self):
        m = EnsemblePredictiveModel()
        m1 = MarkovPredictiveModel()
        m2 = TimeSeriesPredictiveModel()
        for _ in range(5):
            m1.update("find", 60.0, PhaseOutcome.SUCCESS)
            m2.update("find", 60.0, PhaseOutcome.SUCCESS)
        m.add_model(m1, weight=1.0)
        m.add_model(m2, weight=0.5)
        p = m.predict_phase("find", {"duration_sec": 60})
        assert p.success_probability > 0.5

    def test_propagates_updates(self):
        m = EnsemblePredictiveModel()
        sub = MarkovPredictiveModel()
        m.add_model(sub, weight=1.0)
        m.update("engage", 30.0, PhaseOutcome.SUCCESS)
        assert sub.get_phase_stats("engage")["n_samples"] == 1


class TestPredictiveKillChain:
    def test_cold_start_prediction(self):
        pkc = PredictiveKillChain()
        pred = pkc.predict_target("T1", "find")
        assert pred.target_id == "T1"
        assert len(pred.predictions) == 6
        assert all(phase in pred.predictions for phase in PHASE_ORDER)

    def test_chain_probability_increases_fewer_phases_remaining(self):
        pkc = PredictiveKillChain()
        for _ in range(20):
            for phase in PHASE_ORDER:
                pkc.record_outcome(phase, 60.0, PhaseOutcome.SUCCESS)
        early = pkc.predict_target("T1", "find")
        late = pkc.predict_target("T1", "assess")
        assert late.overall_success_probability >= early.overall_success_probability

    def test_record_outcome_history(self):
        pkc = PredictiveKillChain()
        pkc.record_outcome("find", 30.0, PhaseOutcome.SUCCESS)
        pkc.record_outcome("fix", 60.0, PhaseOutcome.TIMEOUT)
        h = pkc.get_history(limit=10)
        assert len(h) == 2
        assert h[0]["outcome"] == "success"
        assert h[1]["outcome"] == "timeout"

    def test_set_model(self):
        pkc = PredictiveKillChain()
        new_model = TimeSeriesPredictiveModel(alpha=0.1)
        pkc.set_model(new_model)
        assert pkc._model is new_model

    def test_stats(self):
        pkc = PredictiveKillChain()
        pkc.record_outcome("find", 30.0, PhaseOutcome.SUCCESS)
        s = pkc.stats()
        assert s["n_history"] == 1
        assert "phases" in s

    def test_unknown_phase_falls_back(self):
        pkc = PredictiveKillChain()
        pred = pkc.predict_target("T1", "unknown_phase")
        assert isinstance(pred, KillChainPrediction)

    def test_recommendations_no_duplicates(self):
        pkc = PredictiveKillChain()
        for _ in range(50):
            pkc.record_outcome("find", 120.0, PhaseOutcome.TIMEOUT)
        pred = pkc.predict_target("T1", "find")
        assert isinstance(pred.recommendations, list)
        assert len(pred.recommendations) == len(set(pred.recommendations))
