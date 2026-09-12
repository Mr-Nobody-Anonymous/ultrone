# Copyright (c) Ultrone Contributors. All rights reserved.
"""Red-team perturbation and analyst-facing outcome prediction (Sprint B-B+).

Deliberately *not* a new algorithm: it reuses the canonical scenario suite
and runner, generating deterministic *variants* of existing scenarios
(perturbed seeds, sensing degradation, injected faults). A human analyst
consumes the aggregated output to understand how sensitive outcomes are to
degraded/adversarial conditions -- the tool predicts and summarizes; it
never decides.

Everything here is fully deterministic: (base scenario, variant index) maps
to exactly one variant configuration and therefore one outcome.

Exit-code contract (CLI):

- A variant that *crashes* (recorded ``failures``) is always fatal (exit 1).
- A *simulated* constraint violation induced by an injected fault (e.g. a
  stale-observation strike drawing a ROE penalty) is an expected analyst
  finding: it is reported loudly but exits 0, so automated consumers are
  not permanently red on deterministic fault behavior. Pass ``--strict``
  to treat such findings as fatal as well.
"""

from __future__ import annotations

import argparse
import json
import sys
import zlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from benchmarks.canonical.runner import content_fingerprint, run_scenario
from benchmarks.canonical.scenarios import SCENARIOS, ScenarioSpec
from sim.fault_injection import FaultSpec, FaultType

#: Bump when variant semantics change (invalidates prior analyses).
ADVERSARIAL_SUITE_VERSION = "canonical-adversarial-v1"

#: Fault menu cycled by variant index, so variants stay easy to reason about.
_INJECTED_FAULTS = (
    None,  # parameter-only perturbation
    FaultSpec(FaultType.SENSOR_DROPOUT, probability=0.25),
    FaultSpec(FaultType.NOISY_OBSERVATION, probability=0.6, intensity=6.0),
)


def variant_seed(spec: ScenarioSpec, index: int) -> int:
    """Deterministic per-(scenario, variant) seed."""
    return zlib.crc32(
        f"{ADVERSARIAL_SUITE_VERSION}:{spec.scenario_id}:{index}".encode(),
    ) % (2 ** 31)


def perturb(spec: ScenarioSpec, index: int) -> ScenarioSpec:
    """Return variant ``index`` of ``spec`` (deterministic, frozen dataclass)."""
    seed = variant_seed(spec, index)
    # Simple deterministic parameter wobble derived from the variant seed.
    dropout = min(0.9, max(0.0, spec.sensor_dropout + ((seed % 15) - 5) / 100.0))
    noise = round(spec.sensor_noise_sigma * (0.8 + (seed % 70) / 100.0), 3)
    jitter = round(max(0.05, spec.confidence_jitter - 0.02 + (seed % 5) / 100.0), 3)

    fault = _INJECTED_FAULTS[index % len(_INJECTED_FAULTS)]
    faults = spec.faults + ((fault,) if fault is not None else ())

    return ScenarioSpec(
        scenario_id=f"{spec.scenario_id}::rt{index}",
        description=(
            f"red-team variant {index} of '{spec.scenario_id}' "
            f"(perturbed sensing"
            f"{', injected ' + fault.fault_type.value if fault else ''})"
        ),
        seed=seed,
        n_steps=spec.n_steps,
        n_candidates=spec.n_candidates,
        sensor_dropout=dropout,
        sensor_noise_sigma=noise,
        confidence_jitter=jitter,
        min_engagement_confidence=spec.min_engagement_confidence,
        blacklisted_actions=spec.blacklisted_actions,
        faults=faults,
        human_policy=spec.human_policy,
    )


def red_team_suite(
    base_ids: Optional[List[str]] = None, variants_per: int = 2,
) -> List[ScenarioSpec]:
    """Build the red-team variant matrix over the (optionally subset) suite."""
    ids = base_ids or list(SCENARIOS.keys())
    specs: List[ScenarioSpec] = []
    for sid in ids:
        base = SCENARIOS[sid]
        specs.extend(perturb(base, i) for i in range(variants_per))
    return specs


@dataclass(frozen=True)
class OutcomePrediction:
    """Analyst-facing aggregate over red-team variants of one base scenario."""

    base_scenario: str
    n_variants: int
    reward_mean: float
    reward_min: float
    reward_max: float
    noop_rate: float
    failure_rate: float
    constraint_violations: int
    worst_case_variant: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_scenario": self.base_scenario,
            "n_variants": self.n_variants,
            "predicted_reward_range": [self.reward_min, self.reward_max],
            "reward_mean": self.reward_mean,
            "noop_rate": self.noop_rate,
            "failure_rate": self.failure_rate,
            "constraint_violations": self.constraint_violations,
            "worst_case_variant": self.worst_case_variant,
        }


def predict_outcomes(records: List[Dict[str, Any]]) -> List[OutcomePrediction]:
    """Aggregate red-team records into per-base-scenario outcome predictions."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        base = rec["scenario_id"].split("::")[0]
        grouped.setdefault(base, []).append(rec)

    predictions: List[OutcomePrediction] = []
    for base, recs in sorted(grouped.items()):
        rewards = [float(r["metrics"]["total_reward"]) for r in recs]
        worst = min(recs, key=lambda r: r["metrics"]["total_reward"])
        n_steps = sum(int(r["metrics"]["steps"]) for r in recs) or 1
        predictions.append(OutcomePrediction(
            base_scenario=base,
            n_variants=len(recs),
            reward_mean=round(sum(rewards) / len(rewards), 4),
            reward_min=min(rewards),
            reward_max=max(rewards),
            noop_rate=round(
                sum(int(r["metrics"]["noop_steps"]) for r in recs) / n_steps, 4,
            ),
            failure_rate=round(
                sum(1 for r in recs if r["failures"]) / len(recs), 4,
            ),
            constraint_violations=sum(
                int(r.get("constraint_violations", 0)) for r in recs
            ),
            worst_case_variant=str(worst["scenario_id"]),
        ))
    return predictions


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.canonical.adversarial",
        description=(
            "Run the deterministic red-team variant suite and print "
            "analyst-facing outcome predictions. Variant crashes exit "
            "non-zero; simulated constraint violations are reported as "
            "findings (also fatal under --strict)."
        ),
    )
    parser.add_argument("--variants-per", type=int, default=2)
    parser.add_argument(
        "--strict", action="store_true",
        help="treat simulated constraint violations as fatal too",
    )
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args(argv)

    specs = red_team_suite(variants_per=args.variants_per)
    print(
        f"Running red-team suite ({ADVERSARIAL_SUITE_VERSION}): "
        f"{len(specs)} variants ..."
    )
    records = []
    for spec in specs:
        rec = run_scenario(spec)
        records.append(rec)
        m = rec["metrics"]
        print(
            f"  [{rec['scenario_id']}] reward={m['total_reward']} "
            f"noop={m['noop_steps']}/{m['steps']} "
            f"chain_ok={rec['audit_chain_verified']} "
            f"fingerprint={content_fingerprint(rec)[:12]}"
        )

    preds = [p.to_dict() for p in predict_outcomes(records)]
    payload = {
        "adversarial_suite_version": ADVERSARIAL_SUITE_VERSION,
        "predictions": preds,
    }
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nPredictions written to {args.output}")

    print("\nOutcome predictions (for human analysts):")
    for p in preds:
        print(
            f"  {p['base_scenario']}: expected reward in "
            f"[{p['predicted_reward_range'][0]}, {p['predicted_reward_range'][1]}] "
            f"(mean {p['reward_mean']}), worst case {p['worst_case_variant']}"
        )

    crashed = [p for p in preds if p["failure_rate"] > 0]
    if crashed:
        bases = [p["base_scenario"] for p in crashed]
        print(f"\nVARIANT FAILURES (crashes) in: {bases}")
        return 1

    violating = [p for p in preds if p["constraint_violations"] > 0]
    if violating:
        print("\nSimulated constraint violations (fault-induced findings):")
        for p in violating:
            print(
                f"  - {p['base_scenario']}: {p['constraint_violations']} ROE "
                f"violation(s), worst case {p['worst_case_variant']}"
            )
        if args.strict:
            print("--strict: treating simulated violations as fatal.")
            return 1
        print("(non-fatal analyst findings by default; re-run with --strict)")
        return 0

    print("\nAll red-team variants completed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
