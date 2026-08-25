# Copyright (c) Ultrone Contributors. All rights reserved.
"""Baseline storage, regression detection, and the benchmark CLI.

The canonical suite fails (non-zero exit) whenever a known deterministic
baseline metric or content fingerprint is violated, or when latency
exceeds its ceiling -- making it usable as a CI regression gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmarks.canonical.runner import run_all
from benchmarks.canonical.scenarios import (
    REQUIRED_SCENARIO_IDS,
    SCENARIO_SUITE_VERSION,
)

#: Metrics compared exactly (deterministic given seed + config).
EXACT_METRICS = (
    "total_reward",
    "steps",
    "n_decisions",
    "safety_rejections",
    "human_rejections",
    "system_refusals",
    "overrides",
    "noop_steps",
    "roe_violations",
    "feeds_generated",
    "feeds_received",
    "candidates_evaluated",
)
#: Float metrics allowed a small tolerance instead of exact equality.
TOLERANT_METRICS = {"total_reward": 1e-6}
#: Hard ceilings; exceeding these fails CI even if decisions are unchanged.
LATENCY_CEILINGS_MS = {"mean_step_latency_ms": 5000.0}

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent / "baselines.json"


def load_baselines(path: Path = DEFAULT_BASELINE_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"scenario_suite_version": SCENARIO_SUITE_VERSION, "scenarios": {}}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_baselines(
    records: List[Dict[str, Any]], path: Path = DEFAULT_BASELINE_PATH,
) -> None:
    payload = {
        "scenario_suite_version": SCENARIO_SUITE_VERSION,
        "scenarios": {
            r["scenario_id"]: {
                "metrics": {
                    k: r["metrics"][k] for k in EXACT_METRICS if k in r["metrics"]
                },
                "fingerprint": r["fingerprint"],
            }
            for r in records
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def compare(
    records: List[Dict[str, Any]],
    baselines: Dict[str, Any],
) -> List[str]:
    """Return human-readable violations; empty list means green."""
    violations: List[str] = []
    base = baselines.get("scenarios", {})

    if baselines.get("scenario_suite_version") != SCENARIO_SUITE_VERSION:
        violations.append(
            f"suite version changed: baseline="
            f"{baselines.get('scenario_suite_version')} vs current="
            f"{SCENARIO_SUITE_VERSION} (regenerate baselines deliberately)"
        )

    missing = [sid for sid in REQUIRED_SCENARIO_IDS if sid not in base]
    if missing and base:
        violations.append(f"missing baselines for scenarios: {missing}")

    for record in records:
        sid = record["scenario_id"]
        entry = base.get(sid)

        # Invariant checks independent of any baseline file.
        if record.get("failures"):
            violations.append(f"{sid}: recorded failures {record['failures']}")
        if not record.get("audit_chain_verified", True):
            violations.append(f"{sid}: audit hash-chain verification FAILED")
        if sid == "deterministic_replay" and not record.get("replay_matches"):
            violations.append(
                f"{sid}: replay fingerprint mismatch "
                f"({record.get('fingerprint')} != {record.get('replay_fingerprint')})"
            )
        mean_latency = record["metrics"]["mean_step_latency_ms"]
        ceiling = LATENCY_CEILINGS_MS["mean_step_latency_ms"]
        if mean_latency > ceiling:
            violations.append(
                f"{sid}: mean_step_latency_ms {mean_latency} exceeds ceiling {ceiling}"
            )

        if entry is None:
            continue

        # Determinism / behavior regressions.
        if record["fingerprint"] != entry.get("fingerprint"):
            violations.append(
                f"{sid}: content fingerprint changed "
                f"(baseline {entry.get('fingerprint')} vs current "
                f"{record['fingerprint']})"
            )
        for key in EXACT_METRICS:
            if key not in entry["metrics"] or key not in record["metrics"]:
                continue
            expected, actual = entry["metrics"][key], record["metrics"][key]
            tol = TOLERANT_METRICS.get(key, 0)
            ok = (abs(expected - actual) <= tol
                  if isinstance(expected, (int, float))
                  and isinstance(actual, (int, float)) else expected == actual)
            if not ok:
                violations.append(
                    f"{sid}: metric '{key}' regressed "
                    f"(baseline {expected} vs current {actual})"
                )
    return violations


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.canonical",
        description=(
            "Run the canonical ULTRONE scenario suite and enforce baselines. "
            "Exits non-zero on any regression (CI gate)."
        ),
    )
    parser.add_argument(
        "--update-baselines", action="store_true",
        help="run the suite and overwrite baselines.json (deliberate change)",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="write full result records to this JSON file",
    )
    parser.add_argument(
        "--scenario", action="append", default=None,
        help="restrict to one scenario id (repeatable)",
    )
    args = parser.parse_args(argv)

    print(f"Running canonical ULTRONE benchmark suite ({SCENARIO_SUITE_VERSION}) ...")
    records = run_all(args.scenario)
    for r in records:
        m = r["metrics"]
        print(
            f"  [{r['scenario_id']}] reward={m['total_reward']} "
            f"safety_rej={m['safety_rejections']} human_rej={m['human_rejections']} "
            f"overrides={m['overrides']} noop={m['noop_steps']} "
            f"latency_ms={m['mean_step_latency_ms']}"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, default=str)
        print(f"Full results written to {args.output}")

    if args.update_baselines:
        save_baselines(records)
        print(f"Baselines updated at {DEFAULT_BASELINE_PATH}")
        return 0

    violations = compare(records, load_baselines())
    if violations:
        print("\nREGRESSION FAILURES:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("\nAll baseline checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
