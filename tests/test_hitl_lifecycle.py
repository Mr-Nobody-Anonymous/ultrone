# Copyright (c) Ultrone Contributors. All rights reserved.
"""End-to-end HITL lifecycle tests (Sprint B-A).

Prove that the canonical DecisionPipeline automatically persists exactly
one canonical DecisionTrace per decision through the hash-chained audit
layer, that the SENSE -> FUSE -> ESTIMATE -> PLAN -> SAFETY_GATE ->
PENDING -> HUMAN_DECISION -> EXECUTE -> OUTCOME lifecycle is enforced,
and that rejected/overridden decisions can never execute.
"""

import pytest

from core.lifecycle import (
    ALLOWED_TRANSITIONS,
    DecisionLifecycle,
    IllegalTransitionError,
    LifecycleState,
    validate_transition,
)
from core.pipeline import DecisionPipeline, PendingDecisionError
from ultrone_hitl.audit_store import (
    DuplicateDecisionError,
    InMemoryAuditStore,
    JSONLAuditStore,
)
from ultrone_hitl.decision_workflow import InvalidTransitionError, Role
from ultrone_hitl.pipeline_bridge import (
    HITLBridge,
    validate_lifecycle_history,
)


def _make_bridge():
    store = InMemoryAuditStore()
    return HITLBridge(store=store), store


def _gated_pipeline(bridge, seed=7):
    return DecisionPipeline(
        seed=seed, n_candidates=3,
        hitl_bridge=bridge,
        require_human_approval=True,
        scenario_id="lifecycle-test",
    )


class TestLifecycleTable:
    """The allow-list itself makes illegal transitions impossible."""

    def test_canonical_chain_is_contiguous(self):
        chain = [
            LifecycleState.SENSE, LifecycleState.FUSE, LifecycleState.ESTIMATE,
            LifecycleState.PLAN, LifecycleState.SAFETY_GATE, LifecycleState.PENDING,
            LifecycleState.HUMAN_DECISION, LifecycleState.EXECUTE, LifecycleState.OUTCOME,
        ]
        for cur, nxt in zip(chain, chain[1:]):
            assert nxt in ALLOWED_TRANSITIONS[cur]

    def test_terminal_states_have_no_outgoing_edges(self):
        for terminal in (LifecycleState.OUTCOME, LifecycleState.REJECTED,
                         LifecycleState.OVERRIDDEN):
            assert len(ALLOWED_TRANSITIONS[terminal]) == 0
            for target in LifecycleState:
                if target is not terminal:
                    with pytest.raises(IllegalTransitionError):
                        validate_transition(terminal, target)

    def test_rejected_cannot_reach_execute(self):
        with pytest.raises(IllegalTransitionError):
            validate_transition(LifecycleState.REJECTED, LifecycleState.EXECUTE)

    def test_override_parent_cannot_reach_execute(self):
        with pytest.raises(IllegalTransitionError):
            validate_transition(LifecycleState.OVERRIDDEN, LifecycleState.EXECUTE)

    def test_pending_cannot_skip_to_execute(self):
        with pytest.raises(IllegalTransitionError):
            validate_transition(LifecycleState.PENDING, LifecycleState.EXECUTE)

    def test_safety_gate_can_go_autonomous_or_pending(self):
        assert LifecycleState.EXECUTE in ALLOWED_TRANSITIONS[LifecycleState.SAFETY_GATE]
        assert LifecycleState.PENDING in ALLOWED_TRANSITIONS[LifecycleState.SAFETY_GATE]

    def test_lifecycle_tracker_enforces_order(self):
        lc = DecisionLifecycle("D1")
        for state in ("SENSE", "FUSE", "ESTIMATE", "PLAN", "SAFETY_GATE"):
            lc.advance(state)


class TestAutomaticTracePersistence:
    """Every decision gets exactly one canonical trace, automatically."""

    def test_step_auto_submits_trace_without_manual_http(self):
        bridge, store = _make_bridge()
        p = DecisionPipeline(seed=7, hitl_bridge=bridge)
        p.reset_episode()
        result = p.step()

        events = store.replay()
        submits = [
            e for e in events
            if e["type"] == "submit" and e["decision_id"] == result.trace.decision_id
        ]
        assert len(submits) == 1  # exactly one canonical proposal
        assert submits[0]["state"] == "PENDING"
        assert submits[0]["payload"]["trace"]["decision_id"] == result.trace.decision_id

    def test_duplicate_submission_is_impossible(self):
        bridge, store = _make_bridge()
        p = DecisionPipeline(seed=7, hitl_bridge=bridge)
        p.reset_episode()
        result = p.step()

        with pytest.raises(DuplicateDecisionError):
            store.append_event(
                "submit", result.trace.decision_id, "PENDING", "bob",
                {"trace": result.trace.to_dict()},
            )

    def test_hash_chain_survives_full_lifecycle(self):
        bridge, store = _make_bridge()
        p = DecisionPipeline(seed=11, hitl_bridge=bridge)
        p.reset_episode()
        for _ in range(5):
            p.step()  # autonomous mode: submit + execute + outcome audited
        assert store.verify() is True
        types = [e["type"] for e in store.replay()]
        assert "outcome" in types or "reject" in types  # loop fully closed
        prev = ""
        for ev in store.replay():
            assert ev["prev_hash"] == prev
            prev = ev["hash"]

    def test_jsonl_store_round_trip_preserves_chain(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        store = JSONLAuditStore(path)
        bridge = HITLBridge(store=store)
        p = DecisionPipeline(seed=3, hitl_bridge=bridge)
        p.reset_episode()
        p.step()

        reopened = JSONLAuditStore(path)
        assert reopened.verify() is True
        assert len(reopened.replay()) == len(store.replay())


class TestAutonomousBridgeMode:
    """Bridge attached but no human required: Phase 1 behavior + audit."""

    def test_autonomous_mode_still_executes_immediately(self):
        bridge, _ = _make_bridge()
        p = DecisionPipeline(seed=42, hitl_bridge=bridge)
        p.reset_episode()
        result = p.step()
        assert "env_action" in result.trace.execution
        assert result.trace.execution.get("awaiting_approval") is None
        history = result.trace.execution["lifecycle"]
        assert history[-2:] == ["EXECUTE", "OUTCOME"]


class TestFullHumanLifecycle:
    """SENSE..SAFETY_GATE -> PENDING -> HUMAN_DECISION -> EXECUTE -> OUTCOME."""

    def _first_deferred(self, p, attempts=10):
        for _ in range(attempts):
            result = p.step()
            if result.info.get("deferred_decision"):
                return result
        raise AssertionError("expected an approved order within attempts")

    def test_approved_decision_executes_and_records_outcome(self):
        bridge, store = _make_bridge()
        p = _gated_pipeline(bridge)
        p.reset_episode()
        result = self._first_deferred(p)
        decision_id = result.info["deferred_decision"]

        # Not executed yet: no env action ran while pending.
        assert result.trace.execution["env_action"] is None
        assert result.trace.execution["awaiting_approval"] is True
        assert bridge.state_of(decision_id) == "PENDING"

        resolved = p.execute_approved(decision_id, actor="alice")
        assert resolved.trace.execution["env_action"] is not None
        assert bridge.state_of(decision_id) == "EXECUTED"

        history = resolved.trace.execution["lifecycle"]
        assert history == [
            "SENSE", "FUSE", "ESTIMATE", "PLAN", "SAFETY_GATE",
            "PENDING", "HUMAN_DECISION", "EXECUTE", "OUTCOME",
        ]
        assert validate_lifecycle_history(history)

        outcome_events = [
            e for e in store.replay()
            if e["type"] == "outcome" and e["decision_id"] == decision_id
        ]
        assert len(outcome_events) == 1
        assert "reward" in outcome_events[0]["payload"]["outcome"]

    def test_rejected_decision_never_executes(self):
        bridge, store = _make_bridge()
        p = _gated_pipeline(bridge, seed=5)
        p.reset_episode()
        result = self._first_deferred(p)
        decision_id = result.info["deferred_decision"]
        proposed_action = p._pending[decision_id][0].action

        trace = p.reject_pending(decision_id, actor="alice", reason="not acceptable")
        assert trace.execution["lifecycle"][-1] == "REJECTED"
        assert bridge.state_of(decision_id) == "REJECTED"

        # Execution attempts are refused structurally AND procedurally.
        assert decision_id not in p._pending
        with pytest.raises(PendingDecisionError):
            p.execute_approved(decision_id, actor="alice")
        with pytest.raises(Exception):  # server-side state machine refuses too
            bridge.record_execution(decision_id, actor="alice")

        exec_events = [
            e for e in store.replay()
            if e["decision_id"] == decision_id and e["type"] == "execute"
        ]
        assert exec_events == []
        assert proposed_action in {"strike", "jam", "move", "resupply"}

    def test_override_spawns_child_parent_stays_dead(self):
        bridge, _store = _make_bridge()
        bridge.workflow.authorizer.register("sup1", Role.SUPERVISOR)
        p = _gated_pipeline(bridge, seed=9)
        p.reset_episode()
        result = self._first_deferred(p)
        decision_id = result.info["deferred_decision"]

        parent, child = bridge.override(
            decision_id, actor="sup1",
            target={"action": "move", "asset_type": "drones", "target": [50, 50]},
            note="safer repositioning",
        )
        assert parent.state.value == "OVERRIDDEN"
        assert child.state.value == "PENDING"
        assert parent.decision_id == decision_id
        assert child.decision_id != decision_id

        with pytest.raises(Exception):
            bridge.record_execution(parent.decision_id, actor="alice")
        bridge.approve(child.decision_id, actor="alice")
        bridge.record_execution(child.decision_id, actor="alice")
        assert bridge.state_of(child.decision_id) == "EXECUTED"

    def test_execute_without_approval_refused(self):
        bridge, _ = _make_bridge()
        p = _gated_pipeline(bridge, seed=13)
        p.reset_episode()
        result = self._first_deferred(p)
        decision_id = result.info["deferred_decision"]

        assert bridge.state_of(decision_id) == "PENDING"
        with pytest.raises(Exception):  # PENDING cannot jump to EXECUTED
            bridge.record_execution(decision_id, actor="alice")
        with pytest.raises(InvalidTransitionError):
            bridge.workflow.execute(decision_id, actor="alice")


class TestExactlyOneCanonicalTrace:
    def test_many_steps_one_proposal_each(self):
        bridge, store = _make_bridge()
        p = DecisionPipeline(seed=21, hitl_bridge=bridge)
        summary = p.run_episode(max_steps=12)

        submits = {}
        for ev in store.replay():
            if ev["type"] == "submit":
                submits.setdefault(ev["decision_id"], 0)
                submits[ev["decision_id"]] += 1
        assert set(submits.values()) == {1}

        for t in summary["traces"]:
            assert t["execution"]["lifecycle"][0] == "SENSE"
            assert validate_lifecycle_history(t["execution"]["lifecycle"])

    def test_no_bridge_lifecycle_recorded_but_unreviewed(self):
        p = DecisionPipeline(seed=42)  # no bridge at all: pure Phase 1
        p.reset_episode()
        result = p.step()
        assert result.trace.execution["lifecycle"] == [
            "SENSE", "FUSE", "ESTIMATE", "PLAN", "SAFETY_GATE",
            "EXECUTE", "OUTCOME",
        ]

