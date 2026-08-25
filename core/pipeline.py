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
        self.sensor_suite = SensorSuite(self._rng)
        self.episode_id: str = new_id("EP")
        self.traces: List[DecisionTrace] = []
        self._obs: Dict[str, Any] = {}
        self._tick = 0

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
        """Run observe -> fuse -> plan -> gate -> execute -> trace once."""
        self._tick += 1
        obs = Observation.from_env(self._obs, self._tick)
        trace = DecisionTrace(
            decision_id=new_id("DEC"),
            episode_id=self.episode_id,
            tick=self._tick,
            sensing={"observation": obs.to_dict()},
        )

        # 1-2. Sensing + perception (partial observability).
        records = self.sensor_suite.generate(obs)
        estimate, perception_summary = self._fuse_world_estimate(records)
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

        trace.safety = {
            "verdict": verdict.to_dict(),
            "rejections": rejection_log,
            "fallback_noop": selected is None,
        }

        # 5. Execution (no-op advance when nothing approved).
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
        trace.finalize(selected)
        self.traces.append(trace)

        return StepResult(
            trace=trace, order=selected, verdict=verdict,
            reward=reward, done=done, info=info,
        )

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

