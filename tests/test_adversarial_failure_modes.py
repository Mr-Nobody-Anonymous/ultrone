# Copyright (c) Ultrone Contributors. All rights reserved.
"""Adversarial / failure-mode tests (Sprint C).

Deterministic answers to: what happens when things go WRONG. Every test
pins an exact, reproducible outcome -- no flaky concurrency, no distributed
machinery. Known windows are pinned as documented fail-stop behavior.

Invariants asserted throughout:

- The audit hash chain stays verifiable (or raises TamperDetectedError).
- No decision ever executes twice.
- Rejected/overridden/failed decisions never reach the environment.
- Failures are loud (exceptions propagate), never silent.
"""

import json

import pytest

from core.pipeline import (
    DecisionPipeline,
    OverrideRejectedError,
    PendingDecisionError,
)
from ultrone_hitl.audit_store import (
    InMemoryAuditStore,
    JSONLAuditStore,
    TamperDetectedError,
)
from ultrone_hitl.decision_workflow import (
    InvalidTransitionError,
    Role,
)
from ultrone_hitl.pipeline_bridge import HITLBridge


TARGET = {"action": "move", "asset_type": "drones", "target": [50, 50]}


def _make_bridge():
    store = InMemoryAuditStore()
    return HITLBridge(store=store), store


def _gated_pipeline(bridge, seed=7, **kw):
    return DecisionPipeline(
        seed=seed, n_candidates=3,
        hitl_bridge=bridge,
        require_human_approval=True,
        scenario_id="adversarial",
        **kw,
    )


def _first_deferred(p, attempts=10):
    for _ in range(attempts):
        result = p.step()
        if result.info.get("deferred_decision"):
            return result.info["deferred_decision"]
    raise AssertionError("no deferrable decision found")


def _events_for(store, decision_id):
    return [e for e in store.replay() if e["decision_id"] == decision_id]

class TestDuplicateRequests:
    def test_duplicate_execution_request_refused(self):
        bridge, store = _make_bridge()
        p = _gated_pipeline(bridge, seed=3)
        p.reset_episode()
        did = _first_deferred(p)

        p.execute_approved(did, actor="bob")            # first: fine
        with pytest.raises(PendingDecisionError):       # bookkeeping gone
            p.execute_approved(did, actor="bob")
        with pytest.raises(Exception):                  # audit layer too
            bridge.record_execution(did, actor="alice")

        exec_events = [e for e in store.replay()
                       if e["decision_id"] == did and e["type"] == "execute"]
        assert len(exec_events) == 1                    # exactly once, ever
        assert store.verify() is True

    def test_duplicate_approval_refused(self):
        bridge, _ = _make_bridge()
        p = _gated_pipeline(bridge, seed=5)
        p.reset_episode()
        did = _first_deferred(p)

        bridge.approve(did, actor="bob")
        with pytest.raises(InvalidTransitionError):
            bridge.approve(did, actor="alice")
        assert bridge.state_of(did) == "APPROVED"


class TestRacingAttempts:
    """Sequential interleavings give deterministic race answers."""

    def test_two_approvers_exactly_one_wins(self):
        bridge, store = _make_bridge()
        p = _gated_pipeline(bridge, seed=7)
        p.reset_episode()
        did = _first_deferred(p)

        bridge.approve(did, actor="bob")
        with pytest.raises(InvalidTransitionError):     # loser refused
            bridge.approve(did, actor="alice")
        assert bridge.state_of(did) == "APPROVED"
        assert store.verify() is True

    def test_approve_vs_reject_single_winner(self):
        bridge, _ = _make_bridge()
        p = _gated_pipeline(bridge, seed=11)
        p.reset_episode()
        did = _first_deferred(p)

        bridge.reject(did, actor="alice", reason="first mover")
        with pytest.raises(InvalidTransitionError):
            bridge.approve(did, actor="bob")
        assert bridge.state_of(did) == "REJECTED"       # terminal sticks

    def test_concurrent_override_attempts_single_winner(self):
        bridge, store = _make_bridge()
        bridge.workflow.authorizer.register("sup1", Role.SUPERVISOR)
        p = _gated_pipeline(bridge, seed=13)
        p.reset_episode()
        parent = _first_deferred(p)

        child1 = p.override_pending(parent, "sup1", TARGET)
        with pytest.raises(PendingDecisionError):       # second racer loses
            p.override_pending(parent, "sup1", TARGET)
        with pytest.raises(InvalidTransitionError):     # workflow level too
            bridge.override(parent, "sup1", target=TARGET)
        assert bridge.state_of(parent) == "OVERRIDDEN"
        assert child1 in p._pending

class TestCrashWindows:
    def test_crash_after_approval_before_execution(self):
        """Approval persists in the audit log; a crashed pipeline cannot
        silently lose or double-apply it."""
        bridge, store = _make_bridge()
        p = _gated_pipeline(bridge, seed=17)
        p.reset_episode()
        did = _first_deferred(p)
        bridge.approve(did, actor="bob")                # approved...
        # ...then the process dies: a fresh pipeline has no pending entry.
        revived = DecisionPipeline(
            seed=99, hitl_bridge=bridge, require_human_approval=True,
        )
        with pytest.raises(PendingDecisionError):
            revived.execute_approved(did, actor="alice")
        assert bridge.state_of(did) == "APPROVED"
        types = [e["type"] for e in _events_for(store, did)]
        assert "execute" not in types
        assert store.verify() is True

    def test_crash_after_execution_before_outcome_append(self):
        class OutcomeFailingStore(InMemoryAuditStore):
            def __init__(self):
                super().__init__()
                self.fail_next_outcome = True

            def append_event(self, event_type, decision_id, state, actor,
                             payload):
                if event_type == "outcome" and self.fail_next_outcome:
                    self.fail_next_outcome = False
                    raise OSError("simulated disk failure")
                return super().append_event(
                    event_type, decision_id, state, actor, payload,
                )

        store = OutcomeFailingStore()
        bridge = HITLBridge(store=store)
        p = _gated_pipeline(bridge, seed=19)
        p.reset_episode()
        did = _first_deferred(p)

        with pytest.raises(OSError):                    # crash mid-commit
            p.execute_approved(did, actor="bob")

        types = [e["type"] for e in _events_for(store, did)]
        assert types == ["submit", "approve", "execute"]
        assert store.verify() is True                   # chain intact

        bridge.record_outcome(did, {"reward": -1.0, "done": False})
        types = [e["type"] for e in _events_for(store, did)]
        assert types == ["submit", "approve", "execute", "outcome"]
        assert store.verify() is True


class TestAuditIntegrityUnderAttack:
    def _jsonl_with_events(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        store = JSONLAuditStore(path)
        bridge = HITLBridge(store=store)
        p = DecisionPipeline(seed=23, hitl_bridge=bridge)
        p.reset_episode()
        p.step()
        return path, store

    def test_tampered_record_detected(self, tmp_path):
        path, store = self._jsonl_with_events(tmp_path)
        lines = path.read_text(encoding="utf-8").splitlines()
        victim = json.loads(lines[0])
        victim["payload"]["scenario_id"] = "forged"   # rewrite history
        lines[0] = json.dumps(victim)
        path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

        reopened = JSONLAuditStore(path)
        with pytest.raises(TamperDetectedError):
            reopened.verify()
        with pytest.raises(TamperDetectedError):        # reads fail closed
            reopened.replay()

    def test_missing_middle_record_detected(self, tmp_path):
        path, store = self._jsonl_with_events(tmp_path)
        lines = path.read_text(encoding="utf-8").splitlines()
        del lines[1]                                    # swallow a record
        path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

        with pytest.raises(TamperDetectedError):
            JSONLAuditStore(path).verify()

    def test_missing_proposal_unknown_decision(self, tmp_path):
        path, store = self._jsonl_with_events(tmp_path)
        did = store.replay()[0]["decision_id"]
        lines = [l for l in path.read_text(encoding="utf-8").splitlines()
                 if json.loads(l)["decision_id"] != did]
        path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")

        fresh = HITLBridge(store=JSONLAuditStore(path))
        assert fresh.state_of(did) is None              # unknown, not trusted


class TestStalePipelineState:
    def test_externally_rejected_decision_cannot_execute(self):
        bridge, _ = _make_bridge()
        p = _gated_pipeline(bridge, seed=29)
        p.reset_episode()
        did = _first_deferred(p)

        # Someone rejects out-of-band while the pipeline still holds it.
        bridge.reject(did, actor="alice", reason="revoked elsewhere")
        obs_before = p._obs

        with pytest.raises(InvalidTransitionError):     # audit layer refuses
            p.execute_approved(did, actor="bob")
        # The environment was never touched for this decision.
        types = [e["type"] for e in bridge.replay()
                 if e["decision_id"] == did]
        assert "execute" not in types and "outcome" not in types
        assert p._obs == obs_before


class _ExplodingEnv:
    """Env whose first real action raises (hardware failure simulation)."""

    def __init__(self, base):
        self.base = base
        self.armed = True

    def reset(self, *a, **k):
        return self.base.reset(*a, **k)

    def step(self, action):
        if self.armed and action is not None:
            self.armed = False
            raise RuntimeError("actuator explosion")
        return self.base.step(action)


class TestEnvironmentFailure:
    def test_env_failure_is_fail_stop_no_double_execution(self):
        from sim.battlefield_env import BattlefieldEnv

        bridge, store = _make_bridge()
        p = DecisionPipeline(
            env=_ExplodingEnv(BattlefieldEnv()),
            seed=31, hitl_bridge=bridge,
            require_human_approval=True,
        )
        p.reset_episode()
        did = _first_deferred(p)

        with pytest.raises(RuntimeError):               # loud failure
            p.execute_approved(did, actor="bob")

        # Audit says EXECUTED but no outcome: the crash window is visible.
        types = [e["type"] for e in _events_for(store, did)]
        assert types == ["submit", "approve", "execute"]
        assert store.verify() is True

        # Fail-stop: retrying can never double-fire the actuator.
        with pytest.raises(InvalidTransitionError):
            p.execute_approved(did, actor="bob")


class TestMalformedAndMaliciousOverrides:
    def test_blacklisted_override_refused_before_any_audit_write(self):
        from core.safety_gate import SafetyConfig, SafetyGate

        bridge, store = _make_bridge()
        p = DecisionPipeline(
            seed=37, hitl_bridge=bridge,
            require_human_approval=True,
            safety_gate=SafetyGate(SafetyConfig(blacklisted_actions=["jam"])),
        )
        p.reset_episode()
        did = _first_deferred(p)
        events_before = len(store.replay())

        with pytest.raises(OverrideRejectedError):
            p.override_pending(
                did, "sup1",
                {"action": "jam", "asset_type": "jammers", "target": [50, 50]},
            )
        # Nothing was created or recorded: refusal happened pre-audit.
        assert len(store.replay()) == events_before
        assert bridge.state_of(did) == "PENDING"
        assert did in p._pending                        # still resolvable

    def test_malformed_override_refused(self):
        bridge, store = _make_bridge()
        bridge.workflow.authorizer.register("sup1", Role.SUPERVISOR)
        p = _gated_pipeline(bridge, seed=41)
        p.reset_episode()
        did = _first_deferred(p)

        for bad in (
            {},                                          # empty order
            {"action": "move", "asset_type": "drones"},  # no target
            {"action": "strike", "asset_type": "missiles", "target": None},
        ):
            with pytest.raises(OverrideRejectedError):
                p.override_pending(did, "sup1", bad)
        assert store.verify() is True

    def test_kinetic_override_without_confidence_refused(self):
        """A supervisor cannot override into a strike under low belief.

        Deterministic: take an ordinary pending decision, degrade its
        *recorded* world confidence (simulating a low-quality fuse), and
        verify the independent gate refuses the kinetic override against
        exactly that recorded belief.
        """
        bridge, store = _make_bridge()
        bridge.workflow.authorizer.register("sup1", Role.SUPERVISOR)
        p = _gated_pipeline(bridge, seed=43)
        p.reset_episode()
        did = _first_deferred(p)
        p._trace_by_id(did).world_state["primary_target_confidence"] = 0.10

        with pytest.raises(OverrideRejectedError):
            p.override_pending(
                did, "sup1",
                {"action": "strike", "asset_type": "missiles",
                 "target": [60, 60]},
            )


class TestSensorAndIOFailures:
    def test_total_comms_blacklist_degrades_to_audited_noop(self):
        import random as _random

        from core.pipeline import SensorSuite
        from sim.fault_injection import FaultSpec, FaultType, FaultySensorSuite

        bridge, store = _make_bridge()
        suite = FaultySensorSuite(
            SensorSuite(_random.Random(5)),
            (FaultSpec(FaultType.COMMS_LOSS, probability=1.0),),
            _random.Random(5),
        )
        p = _gated_pipeline(bridge, seed=47, sensor_suite=suite)
        p.reset_episode()
        for _ in range(4):
            result = p.step()                           # must never raise
            assert result.trace.safety["fallback_noop"]
            history = result.trace.execution["lifecycle"]
            assert validate_history_ok(history)
        assert store.verify() is True

    def test_audit_io_failure_is_loud_and_chain_safe(self, tmp_path):
        class IOFailingStore(JSONLAuditStore):
            def _persist(self, event):
                raise OSError("audit volume offline")

        bridge = HITLBridge(store=IOFailingStore(tmp_path / "x.jsonl"))
        p = DecisionPipeline(seed=53, hitl_bridge=bridge)   # autonomous mode
        p.reset_episode()
        with pytest.raises(OSError):                    # fail-stop, loud
            p.step()
        assert bridge.store._snapshot() == []           # nothing half-written


def validate_history_ok(history):
    from ultrone_hitl.pipeline_bridge import validate_lifecycle_history

    return validate_lifecycle_history(history)
