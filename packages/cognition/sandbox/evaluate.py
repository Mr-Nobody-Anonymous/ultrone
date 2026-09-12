# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reproducible AGI-capability evaluation for the sandbox.

One call, :func:`run_capability_suite`, exercises every capability module
under one seed and returns a :class:`CapabilityReport` whose fingerprint is
stable across machines and runs. Reports are persisted through the EXISTING
``ultrone_hitl`` hash-chained audit store -- evaluation results inherit
tamper-evidence instead of inventing their own logging.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict

SANDBOX_EVAL_VERSION = "sandbox-eval-v2"


@dataclass(frozen=True)
class CapabilityReport:
    version: str
    seed: int
    sections: Dict[str, Any]
    fingerprint: str


# Shared fixture: three regimes with well-separated symbol signatures.
# Separation is deliberate: the benchmark scores belief maintenance and
# recovery speed, not the difficulty of nearly-indistinguishable regimes.
EMISSIONS = {
    "calm":  {"alpha": 0.85, "beta": 0.12, "gamma": 0.03},
    "storm": {"alpha": 0.05, "beta": 0.13, "gamma": 0.82},
    "drift": {"alpha": 0.22, "beta": 0.72, "gamma": 0.06},
}
SWITCHES = ((25, "storm"), (45, "drift"))


def _prediction_section(seed: int) -> Dict[str, Any]:
    from sandbox.prediction import (
        PredictionBenchmark, UniformAgent, make_bayesian, steady_records,
        summarize,
    )

    def run(factory):
        bench = PredictionBenchmark(
            factory, EMISSIONS, seed=seed, n_ticks=70,
            dropout_probability=0.15, switches=SWITCHES,
        )
        records = bench.run()
        summary = summarize(records, switch_ticks=[s for s, _ in SWITCHES])
        # Calibration/accuracy are scored on settled segments only: right
        # after a surprise even a good agent should be miscalibrated briefly.
        steady = steady_records(records, switch_ticks=[s for s, _ in SWITCHES])
        from sandbox.prediction import expected_calibration_error
        return {
            **summary,
            "steady_ece": round(expected_calibration_error(steady), 6),
            "steady_accuracy": round(
                sum(1 for r in steady if r.correct) / max(1, len(steady)), 6,
            ),
        }

    informed = run(make_bayesian(EMISSIONS))
    naive = run(lambda: UniformAgent(sorted(EMISSIONS)))
    novel = run(make_bayesian(EMISSIONS, exclude="drift"))  # never told about drift
    return {
        "bayesian": informed,
        "uniform_baseline": naive,
        "novel_regime_graceful": novel["brier_mean"] < 1.2,
        "beats_baseline": informed["brier_mean"] < naive["brier_mean"],
        "calibrated": informed["steady_ece"] < 0.20,
        "steady_accuracy_ok": informed["steady_accuracy"] > 0.80,
        "recovers_from_switches": all(
            informed[f"recovery_after_{s}"] is not None
            and informed[f"recovery_after_{s}"] <= 12
            for s, _ in SWITCHES
        ),
    }


def _planning_section() -> Dict[str, Any]:
    from sandbox.planning import backchain, build_example_domains

    domains = build_example_domains()
    plans = {
        name: backchain(reg, name, goal)
        for name, reg, goal in (
            ("kitchen", domains["kitchen"], "tea"),
            ("logistics", domains["logistics"], "box_delivered"),
        )
    }
    unsolvable = backchain(domains["kitchen"], "kitchen", "cold_fusion")
    return {
        "kitchen_plan": [s.name for s in plans["kitchen"]] if plans["kitchen"] else None,
        "logistics_plan": (
            [s.name for s in plans["logistics"]] if plans["logistics"] else None
        ),
        "both_domains_solved": all(p is not None for p in plans.values()),
        "impossible_task_rejected": unsolvable is None,
    }


def _tooluse_section() -> Dict[str, Any]:
    from sandbox.tooluse import build_demo_toolbox

    box = build_demo_toolbox()
    path = box.chain("text", "count")
    if path is None:
        return {"chain_found": False}
    value = box.execute("the quick brown fox and the dog", path)
    # BFS returns the shortest chain: tokenize -> count_tokens (7 raw
    # tokens). Longer filtering chains are reachable but not shortest.
    return {
        "chain_found": True,
        "chain": [t.name for t in path],
        "executed_value": value,
        "correct": value == 7,
    }


def _world_model_section(seed: int) -> Dict[str, Any]:
    import random

    from sandbox.world_model import TransitionModel

    rng = random.Random(seed)
    model = TransitionModel()
    truth = {
        ("A", "go"): "B", ("B", "go"): "A",
        ("A", "stay"): "A", ("B", "stay"): "B",
    }
    states_actions = list(truth)
    for _ in range(40):
        sa = states_actions[rng.randrange(len(states_actions))]
        model.update(sa[0], sa[1], truth[sa])
    correct = all(
        max(model.predict(s, a), key=lambda k: model.predict(s, a)[k])
        == truth[(s, a)]
        for s, a in states_actions
    )
    cf = model.counterfactual("A", "go", "stay")
    return {
        "learned_transitions_correct": correct,
        "counterfactual_divergence_go_vs_stay": cf["divergence"],
        "counterfactual_distinguishes_actions": cf["divergence"] > 0.5,
        "surprise_on_novel_pair": model.surprise("Z", "go", "B"),
    }


def _critique_and_memory_section(seed: int) -> Dict[str, Any]:
    from sandbox.critique import OVERCONFIDENT, STUCK_LOOP, WRONG_TOP, SelfCritic
    from sandbox.memory import EpisodicMemory, GoalStack, GOAL_STALLED
    from sandbox.prediction import PredictionRecord

    records = [
        PredictionRecord(tick=t, true_state="X", observed="x",
                         top_hypothesis="Y", confidence=0.9,
                         correct=False, brier=1.2)
        for t in (1, 2, 3)
    ]
    critiques = SelfCritic().review_predictions(records)
    kinds = {c.kind for c in critiques}

    mem = EpisodicMemory()
    mem.remember("m1", "storm surge damaged pier seven",
                 tags=("hazard",), tick=1)
    mem.remember("m2", "routine inventory count completed",
                 tags=("admin",), tick=2)
    hits = mem.recall(keywords=("surge", "pier"), tick=3)

    goals = GoalStack()
    goals.push("g1", "repair pier", deadline_tick=5)
    stalled = goals.sweep(tick=6)

    return {
        "critique_kinds_detected": sorted(kinds),
        "wrong_top_found": WRONG_TOP in kinds,
        "overconfidence_found": OVERCONFIDENT in kinds,
        "stuck_loop_found": STUCK_LOOP in kinds,
        "memory_retrieves_relevant_episode": bool(hits) and hits[0].key == "m1",
        "goal_stall_detected": bool(stalled)
        and stalled[0].status == GOAL_STALLED,
    }


def _multimodal_section() -> Dict[str, Any]:
    from sandbox.perception import run_perception_suite

    result = run_perception_suite(seed=5, n_trials=400, modality_dropout=0.25)
    return {
        **result,
        "fuses_modalities": bool(result["beats_best_unimodal"]),
        "robust_to_dropout": bool(result["graceful_under_dropout"]),
    }


def _continual_section() -> Dict[str, Any]:
    from sandbox.continual import build_task_sequence, run_continual_sequence

    tasks = build_task_sequence(n_tasks=4, pairs_per_task=4)
    report = run_continual_sequence(tasks, n_train_reps=12,
                                    capacities=(None, 6))
    unbounded = report["learners"]["unbounded"]
    capped = report["learners"]["cap_6"]
    return {
        "learners": report["learners"],
        "acquires_each_task": bool(unbounded["learned_each_task"]),
        "no_forgetting_with_capacity": bool(unbounded["retained_everything"]),
        "benchmark_detects_forgetting": bool(report["benchmark_detects_forgetting"]),
        "capped_retention": capped["retention_after_all"],
    }


def _distribution_shift_section() -> Dict[str, Any]:
    from sandbox.robustness import run_shift_suite

    result = run_shift_suite(seed=3, n_ticks=60)
    return {
        "shifts": result["shifts"],
        "all_graceful": bool(result["all_graceful"]),
        "mild_shift_bounded": bool(result["mild_shift_bounded"]),
        "survives_novel_symbol": bool(result["survives_novel_symbol"]),
    }


def _experience_section() -> Dict[str, Any]:
    from sandbox.experience import run_learning_curve

    result = run_learning_curve(
        arm_probs=(0.2, 0.5, 0.8), seed=0, episodes=8, steps_per_episode=120,
    )
    return {
        "episode_mean_reward": result["episode_mean_reward"],
        "episode_regret": result["episode_regret"],
        "finds_best_arm": bool(result["finds_best_arm"]),
        "learns_from_experience": bool(result["learns_from_experience"]),
        "final_near_optimal": result["episode_mean_reward"][-1] >= 0.9 * 0.8,
    }


def _reasoning_section() -> Dict[str, Any]:
    from sandbox.reasoning import run_reasoning_suite

    result = run_reasoning_suite()
    return {
        **result,
        "cross_domain_reasoning_ok": bool(result["both_domains_solved"]),
    }


def _general_agent_section() -> Dict[str, Any]:
    from sandbox.agent import GeneralAgent
    from sandbox.prediction import PredictionRecord

    agent = GeneralAgent(seed=0)

    tool_result = agent.handle_tool_task(
        "T-tool", "the quick brown fox and the dog", needed_type="count",
    )
    # Learn a transition from experience, then exploit it.
    for _ in range(6):
        agent.handle_world_task(f"T-world-{_}", "dock", "ship_out", "harbor")
    prediction = agent.predict_transition("dock", "ship_out")

    critiques = agent.review_prediction_history([
        PredictionRecord(tick=1, true_state="X", observed="x",
                         top_hypothesis="Y", confidence=0.95,
                         correct=False, brier=1.3),
    ])
    recalled = agent.recall_about("surprise")
    return {
        "tool_task_success": bool(tool_result.success),
        "tool_value_correct": tool_result.detail.get("value") == 7,
        "learned_prediction_correct": prediction == "harbor",
        "goals_completed": agent.completed_goals == 7,
        "self_critique_recorded": critiques >= 1,
        "memory_populated": len(agent.memory) >= 7,
        "recall_finds_experience": any("surprise" in r for r in recalled),
    }


def _multiagent_section() -> Dict[str, Any]:
    from sandbox.multiagent import SandboxAgent, Task, cooperation_gain

    agents = [
        SandboxAgent("a1", frozenset({"lift", "carry"})),
        SandboxAgent("a2", frozenset({"carry"})),
        SandboxAgent("a3", frozenset({"lift"})),
    ]
    tasks = [
        Task(f"t{i}", "lift" if i % 2 == 0 else "carry", load=2 + (i % 3))
        for i in range(8)
    ]
    gain = cooperation_gain(tasks, agents)
    return {
        "cooperation_gain": gain,
        "coordination_helps": (
            gain["cooperative"]["imbalance_std"]
            <= gain["isolated"]["imbalance_std"]
        ),
    }


def run_capability_suite(seed: int = 0) -> CapabilityReport:
    sections: Dict[str, Any] = {
        "prediction": _prediction_section(seed),
        "planning_transfer": _planning_section(),
        "tool_use": _tooluse_section(),
        "world_model": _world_model_section(seed),
        "self_critique_memory": _critique_and_memory_section(seed),
        "multi_agent_cooperation": _multiagent_section(),
        # Sprint D completion: remaining capability areas.
        "multimodal_perception": _multimodal_section(),
        "continual_learning": _continual_section(),
        "distribution_shift": _distribution_shift_section(),
        "experience_learning": _experience_section(),
        "cross_domain_reasoning": _reasoning_section(),
        "general_agent_integration": _general_agent_section(),
    }
    payload = {"version": SANDBOX_EVAL_VERSION, "seed": seed, "sections": sections}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
    return CapabilityReport(
        version=SANDBOX_EVAL_VERSION, seed=seed, sections=sections,
        fingerprint=digest,
    )


def persist_report(report: CapabilityReport, store, actor: str = "bob") -> str:
    """Append the report to an existing AuditStore; returns event id."""
    return store.append_event(
        "eval-report",
        f"EVAL-{report.seed}",
        "COMPLETED",
        actor,
        {
            "version": report.version,
            "fingerprint": report.fingerprint,
            "sections": report.sections,
        },
    )


def all_checks_pass(report: CapabilityReport) -> bool:
    s = report.sections
    return bool(
        s["prediction"]["beats_baseline"]
        and s["prediction"]["calibrated"]
        and s["prediction"]["steady_accuracy_ok"]
        and s["prediction"]["recovers_from_switches"]
        and s["prediction"]["novel_regime_graceful"]
        and s["planning_transfer"]["both_domains_solved"]
        and s["planning_transfer"]["impossible_task_rejected"]
        and s["tool_use"]["chain_found"]
        and s["tool_use"]["correct"]
        and s["world_model"]["learned_transitions_correct"]
        and s["world_model"]["counterfactual_distinguishes_actions"]
        and s["self_critique_memory"]["wrong_top_found"]
        and s["self_critique_memory"]["memory_retrieves_relevant_episode"]
        and s["self_critique_memory"]["goal_stall_detected"]
        and s["multi_agent_cooperation"]["coordination_helps"]
        and s["multimodal_perception"]["fuses_modalities"]
        and s["multimodal_perception"]["robust_to_dropout"]
        and s["continual_learning"]["acquires_each_task"]
        and s["continual_learning"]["no_forgetting_with_capacity"]
        and s["continual_learning"]["benchmark_detects_forgetting"]
        and s["distribution_shift"]["all_graceful"]
        and s["distribution_shift"]["mild_shift_bounded"]
        and s["experience_learning"]["finds_best_arm"]
        and s["experience_learning"]["learns_from_experience"]
        and s["experience_learning"]["final_near_optimal"]
        and s["cross_domain_reasoning"]["cross_domain_reasoning_ok"]
        and s["general_agent_integration"]["tool_task_success"]
        and s["general_agent_integration"]["learned_prediction_correct"]
        and s["general_agent_integration"]["goals_completed"]
        and s["general_agent_integration"]["memory_populated"]
    )
