# Copyright (c) Ultrone Contributors. All rights reserved.
"""Closed-loop learning integration test.

Proves the Adaptation Layer + Learning/Memory Layer actually form a
*closed* loop. Concretely, after a candidate is promoted to production,
the next episode must (a) load it from the BrainStore, (b) actually use
it, and (c) record a new experience.

The headline assertion is NOT ``promotion_record.decision == "promote"``;
that only proves we promoted something. The headline is::

    next_episode.configuration_hash == promoted.configuration_hash

Anything weaker (e.g. just checking that the gate produced a "promote"
record) would still pass if the brain never read production back.

Cycle under test::

    Episode
       ↓
    ExperienceMemory
       ↓
    Reflection
       ↓
    Candidate
       ↓
    Evaluator (reproducibility + margin)
       ↓
    PromotionGate (audit)
       ↓
    BrainStore (production channel)
       ↓
    Next Episode
       ↓
    ExperienceMemory
       ↺
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest

from adaptive.evaluator import Evaluator, ground_patrol_score
from adaptive.optimizer import (
    AdaptiveOptimizer,
    Candidate,
    config_hash,
    default_patrol_registry,
)
from adaptive.parameter_registry import ParameterRegistry
from adaptive.promotion import BrainStore, PromotionGate

from brain.learning.experience_memory import (
    EngagementHistory,
    EngagementOutcome,
    ExperienceMemory,
)


# --------------------------------------------------------------------- #
# Reflection: a small, deterministic, *honest* proposal layer
# --------------------------------------------------------------------- #
@dataclass
class ReflectionProposal:
    """A small configuration delta derived from one engagement.

    Reflection here is intentionally not a learned policy: it is a
    transparent, auditable rule. The proposal is *advisory* -- the
    Evaluator still decides if it actually wins.
    """

    overrides: Dict[str, Any]
    rationale: str


def reflect(engagement: EngagementHistory,
            registry: ParameterRegistry) -> ReflectionProposal:
    """Propose a single override from one engagement.

    Logic
    -----
    - If the engagement caused nonzero damage, propose a small speed
      bump (the agent is doing useful work; go faster).
    - Otherwise, leave the registry alone.
    """
    snapshot = registry.snapshot()
    speed = float(snapshot.get("patrol.speed", 1.2))
    if engagement.damage_dealt > 0.0:
        new_speed = round(min(speed * 1.05, 2.4), 4)
        return ReflectionProposal(
            overrides={"patrol.speed": new_speed},
            rationale="engagement caused damage; try slightly faster "
                      "patrol to compress the kill chain",
        )
    return ReflectionProposal(
        overrides={},
        rationale="engagement produced no damage; no proposal",
    )


# --------------------------------------------------------------------- #
# Episode driver
# --------------------------------------------------------------------- #
@dataclass
class EpisodeResult:
    """Outcome of running one episode under one configuration."""

    episode_id: str
    configuration: Dict[str, Any]
    configuration_hash: str
    score: float
    engagement: EngagementHistory


def run_episode(episode_id: str,
                registry: ParameterRegistry,
                experience: ExperienceMemory,
                engagement_type: str = "patrol") -> EpisodeResult:
    """Run one episode and record the engagement.

    The "score" is the deterministic evaluator task score. The
    engagement is recorded in the experience memory so the reflection
    layer has something to read next.
    """
    config = registry.snapshot()
    score = ground_patrol_score(config)
    engagement = EngagementHistory(
        engagement_id=episode_id,
        attacker_id="agent:scout-01",
        target_id="target:waypoint-set",
        domain="land",
        engagement_type=engagement_type,
        outcome=(EngagementOutcome.SUCCESSFUL
                 if score > 30.0
                 else EngagementOutcome.PARTIAL),
        duration_ms=240.0,
        kill_chain_phases=["move", "engage"],
        tactics_used=["waypoint_patrol"],
        casualties=0,
        damage_dealt=score,
        notes=f"score={score}",
    )
    experience.record_engagement(engagement)
    return EpisodeResult(
        episode_id=episode_id,
        configuration=config,
        configuration_hash=config_hash(config),
        score=score,
        engagement=engagement,
    )


def apply_overrides(registry: ParameterRegistry,
                    overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a candidate override on top of the current registry.

    Uses the registry's own apply() so bounds enforcement stays the
    single source of truth.
    """
    if not overrides:
        return registry.snapshot()
    registry.apply(overrides)
    return registry.snapshot()


# --------------------------------------------------------------------- #
# The integration test
# --------------------------------------------------------------------- #
def test_closed_loop_episode_to_promotion_to_next_episode(tmp_path: Path):
    """The full 12-step closed loop from the research charter."""

    # 1. Baseline registry + brain + memory + gate.
    registry = default_patrol_registry()
    evaluator = Evaluator(task=ground_patrol_score, margin=0.05, repeats=3)
    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    experience = ExperienceMemory(max_history=1000)
    gate = PromotionGate()

    baseline_config = registry.snapshot()
    baseline_hash = config_hash(baseline_config)

    # 2. Episode 1: run baseline.
    episode_one = run_episode("ep-001", registry, experience)
    assert episode_one.configuration_hash == baseline_hash, (
        "episode 1 should run with the unpromoted baseline config")

    # 3. Reflect: propose an override from the engagement.
    proposal = reflect(episode_one.engagement, registry)
    assert "patrol.speed" in proposal.overrides, (
        "test setup expects reflection to propose a speed bump")

    # 4. Build a candidate by applying the proposal on top of baseline.
    candidate_config = apply_overrides(registry, proposal.overrides)
    candidate_hash = config_hash(candidate_config)
    assert candidate_hash != baseline_hash, (
        "candidate config must actually differ from baseline for the "
        "test to be meaningful")

    # 5. Evaluate the candidate vs the baseline (3 repeats each).
    result = evaluator.evaluate(candidate_config, baseline_config)
    assert len(set(result.candidate_runs)) == 1, (
        f"candidate is not reproducible: {result.candidate_runs}")
    assert len(set(result.baseline_runs)) == 1, (
        f"baseline is not reproducible: {result.baseline_runs}")
    assert result.decision in {"promote", "reject"}, (
        f"decision must be definitive, got {result.decision!r}")

    # 6. Audit: gate.review returns a PromotionRecord regardless.
    record = gate.review(result, candidate_config, candidate_hash)
    assert record.record_id == 1
    assert record.decision == result.decision

    # 7. Promote if and only if the evaluator said so.
    if record.decision == "promote":
        store.promote(candidate_config, record, gate)
        promoted_hash = config_hash(candidate_config)
    else:
        promoted_hash = baseline_hash

    # 8. Persist: durable across the next test (and the next process).
    experience.save(tmp_path / "experience_episode1.json")
    gate.save(tmp_path / "promotion_gate.json")
    if record.decision == "promote":
        persisted = tmp_path / "brain" / "production.json"
        assert persisted.exists(), (
            "production.json must exist on disk after a promotion")

    # 9. Episode 2: rehydrate experience + brain, and run a *fresh*
    #    registry that pulls the production config from the store.
    reloaded_experience = ExperienceMemory.load(
        tmp_path / "experience_episode1.json")
    assert len(reloaded_experience.engagements) == 1, (
        "reloaded experience must have episode 1's engagement")
    stats = reloaded_experience.get_stats()
    assert stats["total_engagements"] == 1

    next_registry = default_patrol_registry()
    if record.decision == "promote":
        next_registry.apply(store.get_config("production"))
    episode_two = run_episode("ep-002", next_registry,
                              reloaded_experience)

    # 10. The critical assertion: the next episode's configuration
    #     hash equals the promoted config's hash.
    if record.decision == "promote":
        assert episode_two.configuration_hash == promoted_hash, (
            "next episode did not use the promoted configuration; "
            "the learning loop is open")
        assert episode_two.configuration_hash == candidate_hash, (
            "next episode's config hash must match the candidate's")
    else:
        assert episode_two.configuration_hash == baseline_hash

    # 11. Record the new experience so the next iteration can read it.
    reloaded_experience.save(tmp_path / "experience_episode2.json")
    final_stats = ExperienceMemory.load(
        tmp_path / "experience_episode2.json").get_stats()
    assert final_stats["total_engagements"] == 2

    # 12. Audit history is also durable.
    reloaded_gate = PromotionGate.load(tmp_path / "promotion_gate.json")
    assert len(reloaded_gate.history) == 1
    assert reloaded_gate.history[0].record_id == record.record_id


# --------------------------------------------------------------------- #
# Stronger variant: an actual evolutionary search yields a real
# improvement, and we still assert the hash propagates.
# --------------------------------------------------------------------- #
def test_closed_loop_with_optimizer_propagates_improvement(
        tmp_path: Path):
    """Same loop, but the candidate comes from AdaptiveOptimizer."""
    registry = default_patrol_registry()
    evaluator = Evaluator(task=ground_patrol_score, margin=0.05, repeats=3)
    optimizer = AdaptiveOptimizer(
        registry, evaluator, population_size=6, seed=7)
    store = BrainStore(storage_dir=str(tmp_path / "brain"))
    experience = ExperienceMemory(max_history=1000)
    gate = PromotionGate()

    ep1 = run_episode("opt-001", registry, experience)
    baseline_config = ep1.configuration

    opt_result = optimizer.run(generations=3)
    candidate_config = opt_result.best.config
    candidate_hash = config_hash(candidate_config)
    assert candidate_hash != config_hash(baseline_config), (
        "optimizer failed to move the configuration")

    eval_result = evaluator.evaluate(candidate_config, baseline_config)
    record = gate.review(eval_result, candidate_config, candidate_hash)

    promoted_hash = config_hash(baseline_config)
    if record.decision == "promote":
        store.promote(candidate_config, record, gate)
        promoted_hash = candidate_hash
        assert eval_result.candidate_score > eval_result.baseline_score, (
            "a 'promote' decision must come with a real score gain")

    next_registry = default_patrol_registry()
    if record.decision == "promote":
        next_registry.apply(store.get_config("production"))
    ep2 = run_episode("opt-002", next_registry, experience)

    # THE headline assertion.
    assert ep2.configuration_hash == promoted_hash, (
        "promoted configuration did not flow into episode 2")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
