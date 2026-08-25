# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical end-to-end decision pipeline.

Wires the full chain using real ULTRONE components:

    BattlefieldEnv observation
        -> SensorSuite (noisy, lossy feeds - partial observability)
        -> SensorFusion (real brain/perception component)
        -> WorldEstimate (belief, never ground truth)
        -> EvolutionaryCOAGenerator (real brain/reasoning component)
        -> SafetyGate (independent constraint enforcement)
        -> env.step execution
        -> outcome + DecisionTrace
"""

from __future__ import annotations

import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.perception.sensor_fusion import SensorFusion  # noqa: E402
from brain.reasoning.course_of_action import CourseOfAction  # noqa: E402
from brain.reasoning.evolutionary_coagen import (  # noqa: E402
    EvolutionaryCOAGenerator,
)
from data.feeds import FeedType, RadarFeed, SigintFeed, VisualFeed  # noqa: E402
from sim.battlefield_env import BattlefieldEnv  # noqa: E402

from core.contracts import (  # noqa: E402
    ActionOrder,
    AssetSnapshot,
    DecisionTrace,
    Observation,
    SafetyVerdict,
    SensorRecord,
    StepResult,
    WorldEstimate,
    new_id,
)
from core.safety_gate import SafetyConfig, SafetyGate  # noqa: E402

logger = logging.getLogger("Ultrone.Core.Pipeline")


class PendingDecisionError(Exception):
    """A decision referenced for HITL resolution is not pending here."""


class OverrideRejectedError(Exception):
    """The independent SafetyGate refused a supervisor-proposed override."""

# COA phases that map to executable environment actions.
EXECUTABLE_PHASES = ("strike", "jam", "move", "resupply")

PHASE_TO_ASSET = {
    "strike": "missiles",
    "move": "drones",
    "jam": "jammers",
    "resupply": "missiles",
}


class SensorSuite:
    """Generates noisy, lossy sensor feeds from a raw observation.

    Models partial observability: gaussian position error per feed,
    per-feed confidence jitter, and random dropout. All randomness is
    drawn from the suite's own seeded RNG for reproducibility.
    """

    def __init__(
        self,
        rng: random.Random,
        position_noise_sigma: float = 2.0,
        confidence_jitter: float = 0.15,
        dropout_probability: float = 0.10,
    ) -> None:
        self.rng = rng
        self.position_noise_sigma = position_noise_sigma
        self.confidence_jitter = confidence_jitter
        self.dropout_probability = dropout_probability

    def generate(self, obs: Observation) -> List[SensorRecord]:
        truth = obs.true_red_position
        records: List[SensorRecord] = []
        if truth is None or obs.red_force.get("health", 0) <= 0:
            return records

        specs = [
            ("radar", FeedType.RADAR, 1.0),
            ("visual", FeedType.VISUAL, 0.8),
            ("sigint", FeedType.SIGINT, 0.6),
        ]
        for name, ftype, base_conf in specs:
            dropped = self.rng.random() < self.dropout_probability
            noisy_pos = (
                truth[0] + self.rng.gauss(0.0, self.position_noise_sigma),
                truth[1] + self.rng.gauss(0.0, self.position_noise_sigma),
                0.0,
            )
            confidence = max(
                0.05,
                min(1.0, base_conf + self.rng.uniform(
                    -self.confidence_jitter, self.confidence_jitter)),
            )
            records.append(SensorRecord(
                feed_id=new_id(f"FEED-{name.upper()}"),
                sensor_type=ftype.value,
                position=noisy_pos,
                confidence=round(confidence, 3),
                dropped=dropped,
            ))
        return records

    @staticmethod
    def to_feeds(records: List[SensorRecord]) -> List[Any]:
        """Convert received (non-dropped) records into typed sensor feeds."""
        feeds: List[Any] = []
        feed_classes = {"radar": RadarFeed, "visual": VisualFeed, "sigint": SigintFeed}
        for rec in records:
            if rec.dropped:
                continue
            cls = feed_classes.get(rec.sensor_type)
            if cls is not None:
                feeds.append(cls(
                    feed_id=rec.feed_id,
                    position=rec.position,
                    confidence=rec.confidence,
                ))
        return feeds


class DecisionPipeline:
    """One authoritative orchestration path from sensing to learning input."""

    def __init__(
        self,
        env: Optional[BattlefieldEnv] = None,
        coa_generator: Optional[EvolutionaryCOAGenerator] = None,
        safety_gate: Optional[SafetyGate] = None,
        seed: int = 42,
        n_candidates: int = 3,
        hitl_bridge: Optional[Any] = None,
        require_human_approval: bool = False,
        scenario_id: str = "",
        sensor_suite: Optional[SensorSuite] = None,
    ) -> None:
        self.env = env if env is not None else BattlefieldEnv()
        self.coa_generator = (
            coa_generator if coa_generator is not None else EvolutionaryCOAGenerator()
        )
        self.fusion = SensorFusion()
        self.safety_gate = safety_gate or SafetyGate(SafetyConfig())
        self.n_candidates = max(1, n_candidates)
        self.seed = seed
        self._rng = random.Random(seed)
        self.sensor_suite = sensor_suite if sensor_suite is not None else SensorSuite(self._rng)
        self.episode_id: str = new_id("EP")
        self.traces: List[DecisionTrace] = []
        self._obs: Dict[str, Any] = {}
        self._tick = 0
        # Sprint B-A: close the decision loop through the HITL/audit layer.
        # When a bridge is attached every finalized trace is automatically
        # persisted (exactly one proposal per decision). When human approval
        # is additionally required, execution of approved orders is deferred
        # until execute_approved() resolves them. With no bridge, behavior is
        # byte-for-byte the Phase 1 autonomous pipeline.
        self.hitl_bridge = hitl_bridge
        self.require_human_approval = require_human_approval
        self.scenario_id = scenario_id
        self._pending: Dict[str, Tuple[ActionOrder, SafetyVerdict]] = {}


    # ------------------------------------------------------------------ #
    # Episode control                                                     #
    # ------------------------------------------------------------------ #
    def reset_episode(self) -> Observation:
        """Reset the environment and start a fresh episode ID.

        Seeds the module-level RNGs used by BattlefieldEnv and the COA
        generator so that (seed + config) reproduces an entire episode.
        """
        random.seed(self.seed)
        np.random.seed(self.seed % (2 ** 32))
        self._obs = self.env.reset()
        self._tick = 0
        self.episode_id = new_id("EP")
        return Observation.from_env(self._obs, self._tick)

    # ------------------------------------------------------------------ #
    # Pipeline stages                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _asset_snapshot(obs: Observation, asset_type: str) -> AssetSnapshot:
        assets = obs.blue_assets.get(asset_type) or [{}]
        asset = assets[0]
        pos = asset.get("position")
        return AssetSnapshot(
            asset_type=asset_type,
            position=tuple(pos) if pos else None,
            fuel=float(asset.get("fuel", 1.0)),
            ammo=int(asset.get("ammo", 0)),
            range=float(asset.get("range", 9999.0)),
        )

    @staticmethod
    def _order_from_coa(coa: Any, estimate: WorldEstimate) -> Optional[ActionOrder]:
        """Translate a generated COA into an executable ActionOrder."""
        if not isinstance(coa, CourseOfAction):
            return None
        for phase in coa.phases:
            if phase in EXECUTABLE_PHASES:
                target = estimate.primary_target_position
                if target is None and phase == "move":
                    target = (50, 50)  # search center when nothing is tracked
                return ActionOrder(
                    action=phase,
                    asset_type=PHASE_TO_ASSET.get(phase, "drones"),
                    target=target,
                    source_coa_id=coa.coa_id,
                )
        return None

    def _fuse_world_estimate(
        self, records: List[SensorRecord]
    ) -> Tuple[WorldEstimate, Dict[str, Any]]:
        feeds = SensorSuite.to_feeds(records)
        fused = self.fusion.fuse_feeds(feeds)
        contacts = []
        primary_pos = None
        primary_conf = 0.0
        best = None
        for contact in fused:
            contacts.append({
                "contact_id": contact.contact_id,
                "confidence": round(contact.confidence, 3),
                "source_feeds": contact.source_feeds,
            })
            if contact.confidence > primary_conf:
                primary_conf = contact.confidence
                best = contact
        if best is not None:
            primary_pos = (best.position[0], best.position[1])
        estimate = WorldEstimate(
            contacts=contacts,
            primary_target_position=primary_pos,
            primary_target_confidence=primary_conf,
            n_feeds_generated=len(records),
            n_feeds_received=len(feeds),
        )
        perception_summary = {
            "feeds_generated": len(records),
            "feeds_received": len(feeds),
            "dropped": sum(1 for r in records if r.dropped),
            "fused_contacts": len(contacts),
        }
        return estimate, perception_summary

    # ------------------------------------------------------------------ #
    # One full decision cycle                                             #
    # ------------------------------------------------------------------ #
    def step(self) -> StepResult:
        """Run observe -> fuse -> plan -> gate -> execute -> trace once.

        With a HITL bridge attached and ``require_human_approval=True``,
        an approved order is NOT executed here: the decision enters PENDING
        and must be resolved via :meth:`execute_approved` /
        :meth:`reject_pending`.
        """
        from core.lifecycle import DecisionLifecycle

        lc = DecisionLifecycle()
        self._tick += 1
        obs = Observation.from_env(self._obs, self._tick)
        lc.advance("SENSE")
        trace = DecisionTrace(
            decision_id=new_id("DEC"),
            episode_id=self.episode_id,
            tick=self._tick,
            sensing={"observation": obs.to_dict()},
        )

        # 1-2. Sensing + perception (partial observability).
        records = self.sensor_suite.generate(obs)
        lc.advance("FUSE")
        estimate, perception_summary = self._fuse_world_estimate(records)
        lc.advance("ESTIMATE")
        trace.perception = perception_summary
        trace.world_state = estimate.to_dict()

        # 3. Planning - generate candidate COAs from belief, never truth.
        target_info = {
            "domain": obs.red_force.get("type", "unknown"),
            "type": obs.red_force.get("type", "unknown"),
        }
        context = {"world_estimate": estimate.to_dict()}
        candidates: List[Any] = []
        orders: List[Optional[ActionOrder]] = []
        for _ in range(self.n_candidates):
            coa = self.coa_generator.generate_evolved_coa(target_info, context)
            candidates.append(coa)
            orders.append(self._order_from_coa(coa, estimate))
        lc.advance("PLAN")
        trace.planning = {
            "n_candidates": len(candidates),
            "candidate_ids": [
                c.coa_id for c in candidates if isinstance(c, CourseOfAction)
            ],
            "proposed_orders": [o.to_env_action() if o else None for o in orders],
        }

        # 4. Safety gate - independent of the planner.
        selected: Optional[ActionOrder] = None
        verdict = SafetyVerdict(approved=False, reason="no executable order proposed")
        rejection_log: List[Dict[str, Any]] = []
        for order in orders:
            if order is None:
                continue
            snapshot = self._asset_snapshot(obs, order.asset_type)
            v = self.safety_gate.evaluate(order, estimate, snapshot)
            if v.approved:
                selected, verdict = order, v
                break
            rejection_log.append({"order": order.to_env_action(), "reason": v.reason})

        if selected is None and rejection_log:
            verdict = SafetyVerdict(
                approved=False,
                reason=f"all {len(rejection_log)} candidate orders rejected",
            )

        lc.advance("SAFETY_GATE")
        trace.safety = {
            "verdict": verdict.to_dict(),
            "rejections": rejection_log,
            "fallback_noop": selected is None,
        }

        # 5. Execution -- deferred when human approval is required for an
        # approved order. Rejected-by-safety orders always no-op regardless.
        deferred = (
            self.hitl_bridge is not None
            and self.require_human_approval
            and selected is not None
        )
        if deferred:
            lc.advance("PENDING")
            env_action = None
            reward, done, info = 0.0, False, {}
            self._pending[trace.decision_id] = (selected, verdict)
            trace.execution["awaiting_approval"] = True
        else:
            env_action = selected.to_env_action() if selected else None
            self._obs, reward, done, info = self.env.step(env_action)
        trace.execution["env_action"] = env_action

        # 6. Outcome + provenance seal.
        trace.outcome = {
            "reward": reward,
            "done": done,
            "roe_violation": info.get("roe_violation", False),
            "red_health": obs.red_force.get("health", 0),
        }
        if not deferred:
            lc.advance("EXECUTE")
            lc.advance("OUTCOME")
        trace.execution["lifecycle"] = lc.as_list()
        trace.finalize(selected)
        self.traces.append(trace)

        # Sprint B-A: automatically persist the canonical trace into the
        # HITL/audit layer (exactly one proposal per decision id). In
        # autonomous mode the execution/outcome are also audited.
        if self.hitl_bridge is not None:
            self.hitl_bridge.submit_trace(
                trace, scenario_id=self.scenario_id or "",
            )
            if not deferred:
                if selected is not None:
                    self.hitl_bridge.record_autonomous_execution(
                        trace.decision_id,
                    )
                    self.hitl_bridge.record_outcome(
                        trace.decision_id, dict(trace.outcome),
                    )
                else:
                    # Nothing executed; close the loop as an audited refusal.
                    self.hitl_bridge.record_refusal(
                        trace.decision_id, reason=str(verdict.reason),
                    )

        return StepResult(
            trace=trace, order=selected, verdict=verdict,
            reward=reward, done=done, info={
                **info,
                **({"deferred_decision": trace.decision_id} if deferred else {}),
            },
        )

    # ------------------------------------------------------------------ #
    # HITL resolution of deferred decisions                               #
    # ------------------------------------------------------------------ #
    def _trace_by_id(self, decision_id: str) -> DecisionTrace:
        for t in self.traces:
            if t.decision_id == decision_id:
                return t
        raise KeyError(decision_id)

    def execute_approved(self, decision_id: str, actor: str = "bob") -> StepResult:
        """Resolve a PENDING decision: HUMAN_DECISION -> EXECUTE -> OUTCOME."""
        if self.hitl_bridge is None:
            raise RuntimeError("execute_approved requires a HITL bridge")
        if decision_id not in self._pending:
            raise PendingDecisionError(
                f"decision {decision_id} is not pending in this pipeline"
            )
        from core.lifecycle import DecisionLifecycle, LifecycleState

        order, verdict = self._pending[decision_id]
        trace = self._trace_by_id(decision_id)
        lc = DecisionLifecycle(decision_id)
        # Replay the sealed prefix so every further transition is validated.
        lc._history = [LifecycleState(s) for s in trace.execution["lifecycle"]]
        lc.advance("HUMAN_DECISION")
        self.hitl_bridge.approve(decision_id, actor)
        lc.advance("EXECUTE")
        self.hitl_bridge.record_execution(decision_id, actor)
        env_action = order.to_env_action()
        self._obs, reward, done, info = self.env.step(env_action)
        lc.advance("OUTCOME")
        trace.execution["env_action"] = env_action
        trace.execution["awaiting_approval"] = False
        trace.execution["lifecycle"] = lc.as_list()
        outcome = {
            "reward": reward,
            "done": done,
            "roe_violation": info.get("roe_violation", False),
            "red_health": self._obs.get("red_force", {}).get("health", 0),
        }
        trace.outcome = outcome
        self.hitl_bridge.record_outcome(decision_id, dict(outcome))
        del self._pending[decision_id]
        return StepResult(
            trace=trace, order=order, verdict=verdict,
            reward=reward, done=done, info=info,
        )

    def override_pending(
        self,
        decision_id: str,
        actor: str,
        target_order: Dict[str, Any],
        note: str = "",
    ) -> str:
        """Supervisor override through the canonical machinery (Sprint C fix).

        The parent becomes terminal-OVERRIDDEN (validated against the
        allow-list; it can never execute afterwards). The HITL layer spawns
        and audits a child proposal; that child is materialized here as a
        first-class pipeline decision -- its trace is taken verbatim from
        the audit store's child proposal, so the pipeline and the audit log
        hold byte-identical content. Execution of the child then flows
        exclusively through :meth:`execute_approved`, the same path as any
        ordinary approved decision. Returns the child decision id.
        """
        if self.hitl_bridge is None:
            raise RuntimeError("override_pending requires a HITL bridge")
        if decision_id not in self._pending:
            raise PendingDecisionError(
                f"decision {decision_id} is not pending in this pipeline"
            )
        from core.lifecycle import DecisionLifecycle, LifecycleState

        # Sprint C: the independent SafetyGate re-certifies the SUPERVISOR's
        # order before anything is created. The gate -- not the proposer,
        # human or AI -- decides executability; an override can never relax
        # a constraint the planner itself was refused under.
        candidate = ActionOrder(
            action=str(target_order.get("action", "")),
            asset_type=str(target_order.get("asset_type", "drones")),
            target=(
                tuple(target_order["target"])
                if target_order.get("target") is not None
                else None
            ),
            source_coa_id=f"override-candidate-{decision_id}",
        )
        ws = self._trace_by_id(decision_id).world_state
        gate_estimate = WorldEstimate(
            contacts=list(ws.get("contacts") or []),
            primary_target_position=(
                tuple(ws["primary_target_position"])
                if ws.get("primary_target_position") else None
            ),
            primary_target_confidence=float(
                ws.get("primary_target_confidence", 0.0) or 0.0
            ),
            n_feeds_generated=int(ws.get("n_feeds_generated", 0) or 0),
            n_feeds_received=int(ws.get("n_feeds_received", 0) or 0),
        )
        gate_verdict = self.safety_gate.evaluate(
            candidate, gate_estimate, self._asset_snapshot(
                Observation.from_env(self._obs, self._tick),
                candidate.asset_type,
            ),
        )
        if not gate_verdict.approved:
            raise OverrideRejectedError(
                f"safety gate rejected supervisor override: {gate_verdict.reason}"
            )

        _, verdict = self._pending[decision_id]
        parent_trace = self._trace_by_id(decision_id)

        # Validate the lifecycle transition BEFORE touching any state.
        parent_lc = DecisionLifecycle(decision_id)
        parent_lc._history = [
            LifecycleState(s) for s in parent_trace.execution["lifecycle"]
        ]
        parent_lc.advance("HUMAN_DECISION")
        parent_lc.advance("OVERRIDDEN")  # terminal; REJECTED-style dead end

        # Audit-layer transition: parent OVERRIDDEN, audited child proposal.
        parent_view, child_view = self.hitl_bridge.override(
            decision_id, actor=actor, target=target_order, note=note,
        )

        # Seal the parent trace as terminal-OVERRIDDEN.
        parent_trace.execution["lifecycle"] = parent_lc.as_list()
        parent_trace.execution["awaiting_approval"] = False
        parent_trace.execution["superseded_by"] = child_view.decision_id
        del self._pending[decision_id]

        # Materialize the child from the AUDIT store's own proposal so the
        # pipeline-side trace matches the persisted record exactly.
        src = child_view.trace.to_dict()
        child_trace = DecisionTrace(
            decision_id=src["decision_id"],
            episode_id=src["episode_id"],
            tick=src["tick"],
            sensing=dict(src.get("sensing") or {}),
            perception=dict(src.get("perception") or {}),
            world_state=dict(src.get("world_state") or {}),
            planning=dict(src.get("planning") or {}),
            safety=dict(src.get("safety") or {}),
            execution=dict(src.get("execution") or {}),
            outcome=dict(src.get("outcome") or {}),
        )
        order = ActionOrder(
            action=str(target_order.get("action", "")),
            asset_type=str(target_order.get("asset_type", "drones")),
            target=(
                tuple(target_order["target"])
                if target_order.get("target") is not None
                else None
            ),
            source_coa_id=f"override-of-{decision_id}",
        )
        self.traces.append(child_trace)
        self._pending[child_view.decision_id] = (order, verdict)
        return child_view.decision_id

    def reject_pending(self, decision_id: str, actor: str, reason: str) -> DecisionTrace:
        """Terminal refusal: REJECTED decisions can never execute."""
        if self.hitl_bridge is None:
            raise RuntimeError("reject_pending requires a HITL bridge")
        if decision_id not in self._pending:
            raise PendingDecisionError(
                f"decision {decision_id} is not pending in this pipeline"
            )
        from core.lifecycle import DecisionLifecycle, LifecycleState

        trace = self._trace_by_id(decision_id)
        lc = DecisionLifecycle(decision_id)
        lc._history = [LifecycleState(s) for s in trace.execution["lifecycle"]]
        lc.advance("HUMAN_DECISION")
        lc.advance("REJECTED")  # terminal: no outgoing edge to EXECUTE exists
        self.hitl_bridge.reject(decision_id, actor, reason)
        trace.execution["lifecycle"] = lc.as_list()
        del self._pending[decision_id]
        return trace

    # ------------------------------------------------------------------ #
    # Full episodes                                                       #
    # ------------------------------------------------------------------ #
    def run_episode(self, max_steps: int = 200) -> Dict[str, Any]:
        """Run a complete episode; returns summary with all traces."""
        self.reset_episode()
        total_reward = 0.0
        steps = 0
        done = False
        while not done and steps < max_steps:
            result = self.step()
            total_reward += result.reward
            steps += 1
            done = result.done
        red_health = self._obs.get("red_force", {}).get("health", 0)
        return {
            "episode_id": self.episode_id,
            "steps": steps,
            "total_reward": total_reward,
            "success": done and red_health <= 0,
            "traces": [t.to_dict() for t in self.traces],
        }

