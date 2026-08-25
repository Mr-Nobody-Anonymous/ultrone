# Copyright (c) Ultrone Contributors. All rights reserved.
"""Controlled simulation fault injection (Sprint B-C).

Deliberately kept at the *simulation/benchmark* level: faults are expressed
as deterministic, seeded wrappers around the existing ``SensorSuite`` and
``BattlefieldEnv`` interfaces, so the canonical ``DecisionPipeline``
requires no changes and no new algorithms are introduced.

Supported faults:

- SENSOR_DROPOUT       extra per-feed loss beyond the suite's baseline
- NOISY_OBSERVATION    biased gaussian corruption of one feed's position
                       (also used to model conflicting sensors)
- COMMS_LOSS           total blackout: every feed is dropped for a tick
- ACTUATOR_FAILURE     an approved order silently degrades to a no-op
- STALE_OBSERVATION    the pipeline acts on an aged observation snapshot
- RESOURCE_DEGRADATION fuel/ammo of blue assets shrink in the observation

All randomness is drawn from the injector's own seeded RNG, so
(seed + fault configuration) reproduces a fault schedule exactly.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


class FaultType(str, enum.Enum):
    SENSOR_DROPOUT = "sensor_dropout"
    NOISY_OBSERVATION = "noisy_observation"
    COMMS_LOSS = "comms_loss"
    ACTUATOR_FAILURE = "actuator_failure"
    STALE_OBSERVATION = "stale_observation"
    RESOURCE_DEGRADATION = "resource_degradation"


@dataclass(frozen=True)
class FaultSpec:
    """One controlled fault configuration.

    probability: per-tick chance the fault triggers (0.0 disables it).
    intensity:
        Fault magnitude. For NOISY_OBSERVATION this is the gaussian sigma
        added to the affected feed position; for RESOURCE_DEGRADATION it is
        the per-tick multiplicative factor applied to ammo/fuel (e.g. 0.9).
    feed_type / asset_type:
        Optional restriction of the fault to one sensor or asset type.
    """
    fault_type: FaultType
    probability: float = 0.0
    intensity: float = 0.0
    feed_type: str = ""
    asset_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fault_type": self.fault_type.value,
            "probability": self.probability,
            "intensity": self.intensity,
            "feed_type": self.feed_type,
            "asset_type": self.asset_type,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "FaultSpec":
        return FaultSpec(
            fault_type=FaultType(d["fault_type"]),
            probability=float(d.get("probability", 0.0)),
            intensity=float(d.get("intensity", 0.0)),
            feed_type=str(d.get("feed_type", "")),
            asset_type=str(d.get("asset_type", "")),
        )


class FaultySensorSuite:
    """Drop-in wrapper around :class:`core.pipeline.SensorSuite`.

    Exposes the same ``generate(obs)`` interface so it can be injected via
    ``DecisionPipeline(sensor_suite=...)``.
    """

    def __init__(
        self, base_suite: Any, specs: Tuple[FaultSpec, ...], rng: random.Random,
    ) -> None:
        self.base = base_suite
        self.specs = tuple(
            s for s in specs if s.fault_type in (
                FaultType.SENSOR_DROPOUT,
                FaultType.NOISY_OBSERVATION,
                FaultType.COMMS_LOSS,
            )
        )
        self.rng = rng

    def generate(self, obs):
        records = self.base.generate(obs)
        if not records:
            return records

        comms_down = any(
            s.fault_type is FaultType.COMMS_LOSS
            and self.rng.random() < s.probability
            for s in self.specs
        )
        if comms_down:
            for rec in records:
                rec.dropped = True
            return records

        out: List[Any] = []
        for rec in records:
            for spec in self.specs:
                if spec.fault_type is FaultType.SENSOR_DROPOUT:
                    if not rec.dropped and self.rng.random() < spec.probability:
                        rec.dropped = True
                elif spec.fault_type is FaultType.NOISY_OBSERVATION:
                    if spec.feed_type and rec.sensor_type != spec.feed_type:
                        continue
                    if not rec.dropped:
                        rec.position = (
                            rec.position[0] + self.rng.gauss(0.0, spec.intensity),
                            rec.position[1] + self.rng.gauss(0.0, spec.intensity),
                            rec.position[2],
                        )
                        rec.confidence = round(
                            max(0.05, min(1.0, rec.confidence - 0.1)), 3,
                        )
            out.append(rec)
        return out


class FaultyEnv:
    """Wraps a BattlefieldEnv with actuator/stale/resource fault behavior.

    Implements the ``reset()``/``step(action)`` interface consumed by
    ``DecisionPipeline``.
    """

    def __init__(
        self, base_env: Any, specs: Tuple[FaultSpec, ...], rng: random.Random,
    ) -> None:
        self.base = base_env
        self.specs = tuple(
            s for s in specs if s.fault_type in (
                FaultType.ACTUATOR_FAILURE,
                FaultType.STALE_OBSERVATION,
                FaultType.RESOURCE_DEGRADATION,
            )
        )
        self.rng = rng
        self._last_real_obs: Dict[str, Any] = {}
        self.stats: Dict[str, int] = {ft.value: 0 for ft in FaultType}

    # -- obs post-processing ----------------------------------------------- #
    def _degrade_resources(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        for spec in self.specs:
            if spec.fault_type is not FaultType.RESOURCE_DEGRADATION:
                continue
            factor = spec.intensity if spec.intensity > 0 else 0.95
            for _atype, assets in (obs.get("blue_assets") or {}).items():
                for asset in assets:
                    if "ammo" in asset:
                        asset["ammo"] = max(0, int(asset["ammo"] * factor))
                    if "fuel" in asset:
                        asset["fuel"] = round(
                            max(0.0, float(asset.get("fuel", 1.0)) * factor), 4,
                        )
        return obs

    def _maybe_stale(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        import copy

        stale_spec = next(
            (s for s in self.specs if s.fault_type is FaultType.STALE_OBSERVATION),
            None,
        )
        if stale_spec is None or self.rng.random() >= stale_spec.probability:
            self._last_real_obs = copy.deepcopy(obs)
            return obs
        if not self._last_real_obs:
            # Nothing cached yet: snapshot and continue with fresh data.
            self._last_real_obs = copy.deepcopy(obs)
            return obs
        self.stats[FaultType.STALE_OBSERVATION.value] += 1
        # Serve a copy so callers cannot mutate the cached snapshot.
        return copy.deepcopy(self._last_real_obs)

    def _post(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        import copy
        obs = copy.deepcopy(obs)
        obs = self._degrade_resources(obs)
        return self._maybe_stale(obs)

    # -- env interface ------------------------------------------------------ #
    def reset(self, *args, **kwargs):
        obs = self.base.reset(*args, **kwargs)
        return self._post(obs)

    def step(self, action):
        act_spec = next(
            (s for s in self.specs if s.fault_type is FaultType.ACTUATOR_FAILURE),
            None,
        )
        if action is not None and act_spec is not None \
                and self.rng.random() < act_spec.probability:
            blocked = (not act_spec.asset_type) or \
                action.get("asset_type") == act_spec.asset_type
            if blocked:
                self.stats[FaultType.ACTUATOR_FAILURE.value] += 1
                action = None  # actuator dead: order silently becomes a no-op
        obs, reward, done, info = self.base.step(action)
        return self._post(obs), reward, done, info
