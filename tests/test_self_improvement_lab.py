# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the controlled self-improvement laboratory (Sprint E)."""

import random

import pytest

from self_improvement.lab.candidate_manager import (
    CandidateRegistry,
    EliteArchive,
    evaluate_promotion,
)
from self_improvement.lab.evaluator import (
    CAPABILITY_DIMENSIONS,
    CapabilitySnapshot,
    measure_genome,
)
from self_improvement.lab.evolutionary_search import run_lab
from self_improvement.lab.experiment_designer import (
    design_next_experiment,
    detect_weaknesses,
    run_experiment,
)
from self_improvement.lab.genome import (
    KNOB_BOUNDS,
    make_genome,
    mutate,
    seed_population,
)


def _snap(cid, caps=None, params=400_000_000, parent="", **overrides):
    base = {d: 0.5 for d in CAPABILITY_DIMENSIONS}
    if caps:
        base.update(caps)
    arch = {
        "parameter_count": int(params), "memory_capacity": 16,
        "planning_depth": 4, "tool_policy": "greedy", "noise_floor": 0.02,
        **overrides,
    }
    return CapabilitySnapshot(
        candidate_id=cid, parent_id=parent, generation=0,
        architecture=arch, capabilities=base,
        resource={"parameter_count": int(params),
                  "latency_ms_proxy": 10.0, "memory_units": 20.0},
        fingerprint=cid,
    )


@pytest.fixture(scope="module")
def measured_pair():
    weak = make_genome(200_000_000, 4, 2, "greedy", 0.08, generation=0)
    strong = make_genome(900_000_000, 48, 8, "deep", 0.01, generation=1,
                         parents=(weak.genome_id,))
    return measure_genome(weak), measure_genome(strong)


class TestEvaluator:
    def test_snapshot_reproducible(self):
        g = make_genome(500_000_000, 24, 5, "deep", 0.02)
        a, b = measure_genome(g), measure_genome(g)
        assert a.fingerprint == b.fingerprint
        assert a.capabilities == b.capabilities

    def test_all_thirteen_dimensions_measured(self, measured_pair):
        weak, _ = measured_pair
        assert set(weak.capabilities) == set(CAPABILITY_DIMENSIONS)
        assert "machine_control" in weak.capabilities
        assert weak.capabilities["machine_control"] > 0.5

    def test_knobs_have_real_consequences(self, measured_pair):
        weak, strong = measured_pair
        assert strong.capabilities["planning"] >= weak.capabilities["planning"]
        assert strong.capabilities["tool_use"] > weak.capabilities["tool_use"]
        assert strong.capabilities["memory"] > weak.capabilities["memory"]

    def test_planning_depth_monotone(self):
        shallow = measure_genome(make_genome(3e8, 32, 2, "deep", 0.02))
        deep = measure_genome(make_genome(3e8, 32, 7, "deep", 0.02))
        assert deep.capabilities["planning"] > shallow.capabilities["planning"]

    def test_efficiency_rewards_smaller_models(self):
        small = _snap("small", params=100_000_000)
        big = _snap("big", params=1_600_000_000)
        assert small.efficiency > big.efficiency


class TestPromotionGates:
    def test_strict_improvement_passes(self):
        parent = _snap("p")
        child = _snap("c", caps={d: 0.55 for d in CAPABILITY_DIMENSIONS})
        assert evaluate_promotion(parent, child).passed

    def test_regression_blocks_promotion(self):
        parent = _snap("p", caps={"memory": 0.9})
        child = _snap("c", caps={"memory": 0.5})
        gate = evaluate_promotion(parent, child)
        assert not gate.passed
        assert "memory" in gate.regressions

    def test_no_overall_improvement_blocks(self):
        parent = _snap("p")
        child = _snap("c")                       # identical index
        assert not evaluate_promotion(parent, child).passed

    def test_efficiency_collapse_blocks(self):
        parent = _snap("p", params=100_000_000)
        child = _snap("c", caps={d: 0.52 for d in CAPABILITY_DIMENSIONS},
                      params=1_600_000_000)
        assert not evaluate_promotion(parent, child).passed


class TestCandidateRegistry:
    def test_append_only_no_overwrite(self):
        reg = CandidateRegistry()
        reg.register(_snap("A"))
        with pytest.raises(ValueError):
            reg.register(_snap("A"))

    def test_canonical_advances_only_through_gate(self):
        reg = CandidateRegistry()
        reg.register(_snap("A"))
        reg.promote("A")
        assert reg.canonical_id == "A"
        reg.register(_snap("B", caps={"memory": 0.1}, parent="A"))
        gate = reg.promote("B")
        assert not gate.passed
        assert reg.canonical_id == "A"           # unchanged
        assert reg.get("B").status == "experimental"

    def test_promotion_appends_audit_event(self):
        from ultrone_hitl.audit_store import InMemoryAuditStore

        store = InMemoryAuditStore()
        reg = CandidateRegistry()
        reg.register(_snap("A"))
        reg.promote("A", audit_store=store)
        events = [e for e in store.replay() if e["type"] == "lab-promotion"]
        assert len(events) == 1
        assert store.verify() is True

    def test_history_immutable_after_promotion(self):
        reg = CandidateRegistry()
        reg.register(_snap("A"))
        before = reg.get("A").snapshot.fingerprint
        reg.register(_snap("B", caps={d: 0.6 for d in CAPABILITY_DIMENSIONS},
                           parent="A"))
        reg.promote("B")
        assert reg.get("A").snapshot.fingerprint == before


class TestEliteArchive:
    def test_niche_leaders_only_change_when_beaten(self):
        archive = EliteArchive()
        s1 = _snap("s1", caps={"robustness": 0.9})
        assert "robustness" in archive.consider(s1)
        s2 = _snap("s2", caps={"robustness": 0.5})
        assert "robustness" not in archive.consider(s2)
        assert archive.leaders["robustness"].candidate_id == "s1"

    def test_distinct_tradeoff_niches_coexist(self):
        archive = EliteArchive()
        accurate = _snap("accurate",
                         caps={d: 0.6 for d in CAPABILITY_DIMENSIONS}
                         | {"adaptation": 0.3})
        adaptive = _snap("adaptive", caps={"adaptation": 0.95})
        archive.consider(accurate)
        archive.consider(adaptive)
        assert archive.leaders["overall"].candidate_id == "accurate"
        assert archive.leaders["adaptation"].candidate_id == "adaptive"


class TestGenomeMutation:
    def test_mutations_stay_within_bounds(self):
        rng = random.Random(0)
        g = make_genome(800_000_000, 32, 5, "deep", 0.02)
        for _ in range(60):
            m = mutate(g, rng, generation=1)
            for knob, (lo, hi) in KNOB_BOUNDS.items():
                v = m.knobs()[knob]
                assert lo <= v <= hi, knob

    def test_mutation_deterministic_given_seed(self):
        r1, r2 = random.Random(42), random.Random(42)
        g = make_genome(500_000_000, 24, 4, "greedy", 0.03)
        seq1 = [mutate(g, r1, 1).stable_hash() for _ in range(10)]
        seq2 = [mutate(g, r2, 1).stable_hash() for _ in range(10)]
        assert seq1 == seq2

    def test_founder_population_spreads_parameter_axis(self):
        pop = seed_population(random.Random(1), size=4)
        assert len({g.parameter_count for g in pop}) == 4


class TestExperimentDesigner:
    def test_weakness_detected_and_ranked(self):
        snap = _snap("w", caps={"memory": 0.2, "planning": 0.7})
        weaknesses = detect_weaknesses(snap)
        assert weaknesses[0].dimension == "memory"
        assert all(w.gap >= 0 for w in weaknesses)

    def test_designer_targets_weakest_dimension(self):
        snap = _snap("w", caps={"tool_use": 0.3, "planning": 0.9})
        proposal = design_next_experiment(snap)
        assert proposal is not None
        assert proposal.target_dim == "tool_use"
        assert proposal.change == {"tool_policy": "deep"}

    def test_experiment_confirms_memory_hypothesis(self):
        g = make_genome(300_000_000, 4, 5, "deep", 0.02)
        snap = measure_genome(g)
        proposal = design_next_experiment(snap)
        assert proposal is not None
        evidence = run_experiment(proposal, g, seed=0)
        assert evidence.child_snapshot.candidate_id != g.genome_id
        if proposal.target_dim == "memory":
            assert evidence.confirmed
            assert evidence.delta > 0

    def test_baseline_regression_ranks_first(self):
        baseline = _snap("base", caps={"memory": 0.95})
        current = _snap("cur", caps={"memory": 0.55})
        weaknesses = detect_weaknesses(current, baseline=baseline)
        assert weaknesses[0].dimension == "memory"
        assert weaknesses[0].gap == pytest.approx(0.4)


class TestEvolutionLab:
    @pytest.fixture(scope="module")
    def lab(self):
        from ultrone_hitl.audit_store import InMemoryAuditStore

        store = InMemoryAuditStore()
        report = run_lab(seed=0, generations=2, pop_size=3,
                         audit_store=store)
        return report, store

    def test_timeline_covers_all_generations(self, lab):
        report, _ = lab
        assert len(report.timeline) == 3          # founders + 2 generations

    def test_at_least_one_promotion(self, lab):
        report, _ = lab
        assert len(report.promotions) >= 1

    def test_capability_index_never_degrades(self, lab):
        report, _ = lab
        indices = [t["capability_index"] for t in report.timeline]
        assert indices == sorted(indices)

    def test_archive_populated_per_niche(self, lab):
        report, _ = lab
        assert set(report.archive) == {
            "overall", "efficiency", "robustness", "planning", "adaptation",
        }

    def test_registry_grew_with_candidates(self, lab):
        report, _ = lab
        # 3 founders + up to 2 children/gen * 2 gens + confirmed experiments
        assert report.registry_size >= 5

    def test_lab_is_deterministic(self):
        a = run_lab(seed=11, generations=1, pop_size=2)
        b = run_lab(seed=11, generations=1, pop_size=2)
        assert ([t["candidate_id"] for t in a.timeline]
                == [t["candidate_id"] for t in b.timeline])
        assert a.archive == b.archive
        assert a.promotions == b.promotions

    def test_promotions_recorded_in_audit_chain(self, lab):
        report, store = lab
        events = [e for e in store.replay() if e["type"] == "lab-promotion"]
        assert len(events) == len(report.promotions)
        assert store.verify() is True

# --------------------------------------------------------------------- #
# Research Analyst (self-analysis of evaluation history)                 #
# --------------------------------------------------------------------- #
class TestResearchAnalyst:
    def _snap(self, cid, caps, generation=0):
        from self_improvement.lab.evaluator import CapabilitySnapshot
        from tests.test_self_improvement_lab import CAPABILITY_DIMENSIONS

        full = {d: 0.5 for d in CAPABILITY_DIMENSIONS}
        full.update(caps)
        return CapabilitySnapshot(
            candidate_id=cid, parent_id="", generation=generation,
            architecture={}, capabilities=full,
            resource={"parameter_count": 400_000_000},
            fingerprint=cid,
        )

    def test_no_analysis_before_two_snapshots(self):
        from self_improvement.lab import ResearchAnalyst

        a = ResearchAnalyst()
        assert a.compare() is None
        assert a.observe(self._snap("A", {})).compare() is None

    def test_coupling_diagnosis_with_recommendation(self):
        from self_improvement.lab import ResearchAnalyst

        # reasoning up, memory down beyond tolerance -> coupling rule.
        before = self._snap("A", {"reasoning": 0.40, "memory": 0.60})
        after = self._snap("B", {"reasoning": 0.50, "memory": 0.50})
        report = ResearchAnalyst().observe(before).observe(after).compare()
        kinds = [d.kind for d in report.diagnoses]
        assert "coupling" in kinds
        coupling = next(d for d in report.diagnoses if d.kind == "coupling")
        assert coupling.dimensions == ("reasoning", "memory")
        assert report.recommended_change == {"memory_capacity": "+16"}
        assert "context consumption" in report.rationale
        assert "improved: reasoning" in report.headline
        assert "regressed: memory" in report.headline

    def test_plain_tradeoff_when_no_rule_matches(self):
        from self_improvement.lab import ResearchAnalyst

        before = self._snap("A", {"perception": 0.4, "language": 0.6})
        after = self._snap("B", {"perception": 0.55, "language": 0.5})
        report = ResearchAnalyst().observe(before).observe(after).compare()
        tradeoffs = [d for d in report.diagnoses if d.kind == "tradeoff"]
        assert tradeoffs and not report.recommended_change

    def test_plateau_detected_when_flat(self):
        from self_improvement.lab import ResearchAnalyst

        s1 = self._snap("A", {})
        s2 = self._snap("B", {}, generation=1)
        report = ResearchAnalyst().observe(s1).observe(s2).compare()
        assert any(d.kind == "plateau" for d in report.diagnoses)

    def test_analyst_is_immutable_on_observe(self):
        from self_improvement.lab import ResearchAnalyst

        a = ResearchAnalyst()
        b = a.observe(self._snap("A", {}))
        c = b.observe(self._snap("B", {}))
        assert len(a.history) == 0
        assert len(b.history) == 1
        assert len(c.history) == 2

    def test_analyze_history_convenience_wrapper(self):
        from self_improvement.lab import analyze_history

        h = [self._snap("A", {"planning": 0.3}),
             self._snap("B", {"planning": 0.6}, generation=1),
             self._snap("C", {"planning": 0.62}, generation=2)]
        report = analyze_history(h)
        assert report is not None
        assert report.to_candidate == "C"
        planning = next(d for d in report.deltas if d.dimension == "planning")
        assert abs(planning.delta - 0.02) < 1e-9


class TestCapabilityTrajectory:
    def test_plot_ready_series_shape(self):
        from self_improvement.lab import capability_trajectory
        from self_improvement.lab.evaluator import CapabilitySnapshot
        from tests.test_self_improvement_lab import CAPABILITY_DIMENSIONS

        snaps = []
        for i, cid in enumerate(["v18", "v29", "v37"]):
            caps = {d: 0.3 + 0.1 * i for d in CAPABILITY_DIMENSIONS}
            snaps.append(CapabilitySnapshot(
                candidate_id=cid, parent_id="", generation=i,
                architecture={}, capabilities=caps,
                resource={"parameter_count": 400_000_000},
                fingerprint=cid))
        traj = capability_trajectory(snaps)
        assert traj["candidates"] == ["v18", "v29", "v37"]
        assert len(traj["capability_index"]) == 3
        assert traj["capability_index"] == sorted(traj["capability_index"])
        assert set(traj["dimensions"]) == set(CAPABILITY_DIMENSIONS)
        assert all(len(v) == 3 for v in traj["dimensions"].values())

    def test_empty_history_is_clean(self):
        from self_improvement.lab import capability_trajectory

        assert capability_trajectory([])["candidates"] == []


class TestLabIntegration:
    def test_run_lab_reports_analyses_and_trajectory(self):
        from self_improvement.lab import run_lab

        report = run_lab(seed=11, generations=2, pop_size=4)
        assert isinstance(report.trajectory, dict)
        assert len(report.trajectory["candidates"]) >= 2
        assert all(a.headline for a in report.analyses)
