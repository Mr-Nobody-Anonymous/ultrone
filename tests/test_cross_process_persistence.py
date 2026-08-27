# Copyright (c) Ultrone Contributors. All rights reserved.
"""Cross-process durability proofs for the long-term memory layer.

In-process ``save``/``load`` round-trips are necessary but *not*
sufficient for durable long-term memory: they can pass while state
actually lives in some process-global cache. The only honest proof is
two real OS processes::

    Process A: record experience, review + promote a config, persist
               ↓
           process exits (RAM gone)
               ↓
    Process B: fresh interpreter restores experience + brain state and
               verifies byte-level fidelity

These are the missing tests referenced by the module docs of
``brain.learning.experience_memory`` and ``adaptive.promotion``; they
use ``multiprocessing`` with the **spawn** start method (the strictest
mode: the child is a genuinely fresh Python interpreter with no shared
state), so a pass cannot be explained by hidden in-memory caches.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
import traceback
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SPAWN = multiprocessing.get_context("spawn")
_JOIN_TIMEOUT_S = 240


def _execute_worker(entry, payload: Dict[str, Any],
                    result_path: Path) -> None:
    """Child-side runner: execute ``entry``, report via result JSON.

    An exception inside a spawned child would otherwise surface only
    as a bare nonzero exitcode; wrapping keeps the traceback readable
    in the parent's assertion message.
    """
    try:
        out = entry(payload)
        out["ok"] = True
    except Exception:                                      # noqa: BLE001
        out = {"ok": False, "error": traceback.format_exc()}
    result_path.write_text(json.dumps(out), encoding="utf-8")


def _run_worker(target, payload: Dict[str, Any], result_path: Path) -> None:
    """Run module-level ``target`` in a spawned child; fail loudly."""
    proc = _SPAWN.Process(
        target=_execute_worker, args=(target, payload, result_path))
    proc.start()
    proc.join(timeout=_JOIN_TIMEOUT_S)
    if proc.is_alive():                                   # pragma: no cover
        proc.terminate()
        proc.join()
        raise AssertionError(
            f"worker {target.__name__} hung for "
            f"{_JOIN_TIMEOUT_S}s -- killed")
    assert proc.exitcode == 0, (
        f"worker {target.__name__} exited with {proc.exitcode}")


def _require_ok(result: Dict[str, Any]) -> None:
    assert result.get("ok"), "worker failed:\n" + result.get("error", "")


# --------------------------------------------------------------------- #
# Worker bodies                                                          #
# --------------------------------------------------------------------- #
def _experience_writer(payload: Dict[str, Any]) -> Dict[str, Any]:
    from brain.learning.experience_memory import (
        EngagementHistory, EngagementOutcome, ExperienceMemory)

    memory = ExperienceMemory(max_history=1000)
    for i, note in enumerate(("first mission", "second mission")):
        memory.record_engagement(EngagementHistory(
            engagement_id=f"xp-{i:03d}",
            attacker_id="agent:scout-01",
            target_id=f"target:{i}",
            domain="land",
            engagement_type="patrol",
            outcome=(EngagementOutcome.SUCCESSFUL if i == 0
                     else EngagementOutcome.PARTIAL),
            duration_ms=100.0 + i,
            kill_chain_phases=["move", "engage"],
            tactics_used=["waypoint_patrol", "suppress"],
            casualties=i,
            damage_dealt=12.5 * (i + 1),
            notes=note,
        ))
    memory.save(payload["experience"])
    return {
        "engagement_ids": [e.engagement_id for e in memory.engagements],
        "domains": sorted(memory.by_domain),
        "tactics": sorted(memory.by_tactic),
        "outcomes": memory.get_stats()["outcomes"],
        "damage": [e.damage_dealt for e in memory.engagements],
    }


def _experience_reader(payload: Dict[str, Any]) -> Dict[str, Any]:
    from brain.learning.experience_memory import (
        EngagementOutcome, ExperienceMemory)

    restored = ExperienceMemory.load(payload["experience"])
    return {
        "engagement_ids": [e.engagement_id for e in restored.engagements],
        "domains": sorted(restored.by_domain),
        "tactics": sorted(restored.by_tactic),
        "outcomes": restored.get_stats()["outcomes"],
        "damage": [e.damage_dealt for e in restored.engagements],
        "outcome_values": [e.outcome.value for e in restored.engagements],
        "is_enum": [isinstance(e.outcome, EngagementOutcome)
                    for e in restored.engagements],
    }


def _brain_writer(payload: Dict[str, Any]) -> Dict[str, Any]:
    from adaptive.evaluator import EvaluationResult
    from adaptive.optimizer import config_hash, default_patrol_registry
    from adaptive.promotion import BrainStore, PromotionGate

    baseline_config = default_patrol_registry().snapshot()
    candidate_config = {**baseline_config, "patrol.speed": 1.26}

    store = BrainStore(storage_dir=payload["brain_dir"])
    store.set_config("baseline", baseline_config)
    gate = PromotionGate()

    result = EvaluationResult(
        decision="promote",
        candidate_score=37.0,
        baseline_score=36.101538,
        margin_required=0.05,
        repeats=3,
        candidate_runs=[37.0] * 3,
        baseline_runs=[36.101538] * 3,
        reason="writer-process synthetic win",
    )
    record = gate.review(result, candidate_config,
                         config_hash(candidate_config))
    store.promote(candidate_config, record, gate)
    gate.save(payload["gate_history"])

    return {
        "promoted_config_hash": config_hash(candidate_config),
        "record_id": record.record_id,
        "candidate_config": candidate_config,
    }


def _brain_reader(payload: Dict[str, Any]) -> Dict[str, Any]:
    from adaptive.optimizer import config_hash
    from adaptive.promotion import BrainStore, PromotionGate

    store = BrainStore(storage_dir=payload["brain_dir"])
    store.load()
    gate = PromotionGate.load(payload["gate_history"])
    production = store.get_config("production")
    promotions = gate.promotions()
    return {
        "production_config": production,
        "production_config_hash": config_hash(production),
        "gate_decisions": [r.decision for r in gate.history],
        "promotion_hashes": [r.config_hash for r in promotions],
        "channel_hashes": store.summary(),
    }


# --------------------------------------------------------------------- #
# Tests                                                                  #
# --------------------------------------------------------------------- #
def test_experience_memory_survives_process_restart(tmp_path: Path):
    """Experience written by Process A is intact inside Process B."""
    experience_file = tmp_path / "experience.json"
    a_marker, b_marker = tmp_path / "a.json", tmp_path / "b.json"

    _run_worker(_experience_writer,
                {"experience": str(experience_file)}, a_marker)
    assert experience_file.exists(), (
        "Process A failed to persist experience to disk")

    _run_worker(_experience_reader,
                {"experience": str(experience_file)}, b_marker)

    a = json.loads(a_marker.read_text(encoding="utf-8"))
    b = json.loads(b_marker.read_text(encoding="utf-8"))
    _require_ok(a)
    _require_ok(b)

    # Process B sees every engagement Process A recorded, identically.
    assert b["engagement_ids"] == a["engagement_ids"] == \
        ["xp-000", "xp-001"]
    assert b["damage"] == a["damage"]
    assert b["domains"] == a["domains"] == ["land"]
    assert b["tactics"] == a["tactics"]

    # Secondary indexes rebuilt, enums deserialized, outcome counters
    # survived serialization.
    assert b["outcome_values"] == ["successful", "partial"]
    assert all(b["is_enum"]), "outcome enum type lost across restart"
    assert b["outcomes"]["successful"] == 1
    assert b["outcomes"]["partial"] == 1


def test_promoted_configuration_survives_process_restart(tmp_path: Path):
    """Production brain state + audit trail restore in a new process."""
    brain_dir = tmp_path / "brain"
    gate_file = tmp_path / "gate.json"
    a_marker, b_marker = tmp_path / "a.json", tmp_path / "b.json"

    _run_worker(_brain_writer,
                {"brain_dir": str(brain_dir),
                 "gate_history": str(gate_file)}, a_marker)
    persisted = brain_dir / "production.json"
    assert persisted.exists(), (
        "promotion in Process A did not reach durable storage")

    _run_worker(_brain_reader,
                {"brain_dir": str(brain_dir),
                 "gate_history": str(gate_file)}, b_marker)

    a = json.loads(a_marker.read_text(encoding="utf-8"))
    b = json.loads(b_marker.read_text(encoding="utf-8"))
    _require_ok(a)
    _require_ok(b)

    # THE durable-loop assertion: Process B's production brain carries
    # exactly the configuration Process A promoted, with the audit
    # trail proving it was reviewed rather than smuggled in.
    assert b["production_config_hash"] == a["promoted_config_hash"]
    assert b["production_config"]["patrol.speed"] == 1.26
    assert b["gate_decisions"] == ["promote"]
    assert b["promotion_hashes"] == [a["promoted_config_hash"]]
    assert b["channel_hashes"]["production"]["config_hash"] == \
        a["promoted_config_hash"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

