# Copyright (c) Ultrone Contributors. All rights reserved.
"""Distribution-shift robustness suite.

Agents are fitted on a base regime family, then evaluated in worlds whose
emission distributions have been deliberately shifted:

- ``mild``          -- small probability perturbations everywhere;
- ``novel_symbol``  -- a brand-new observation symbol appears;
- ``regime_merge``  -- two regimes' signatures converge toward each other.

For each shift we report the degradation index
``(brier_shifted - brier_base) / brier_base`` and whether degradation
stayed bounded (graceful) instead of diverging. This is the measurable
form of "robust against distribution shift".
"""

from __future__ import annotations

from typing import Any, Dict

BASE_EMISSIONS = {
    "calm":  {"alpha": 0.85, "beta": 0.12, "gamma": 0.03},
    "storm": {"alpha": 0.05, "beta": 0.13, "gamma": 0.82},
}


def _renormalize(rows: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    out = {}
    for regime, dist in rows.items():
        z = sum(dist.values()) or 1.0
        out[regime] = {s: round(p / z, 6) for s, p in sorted(dist.items())}
    return out


def shift(kind: str) -> Dict[str, Dict[str, float]]:
    if kind == "base":
        return {r: dict(d) for r, d in BASE_EMISSIONS.items()}
    if kind == "mild":
        rows = {
            r: {s: p * (1.06 if i % 2 == 0 else 0.94)
                for i, (s, p) in enumerate(sorted(d.items()))}
            for r, d in BASE_EMISSIONS.items()
        }
        return _renormalize(rows)
    if kind == "novel_symbol":
        rows = {
            r: {**d, "delta": 0.12} for r, d in BASE_EMISSIONS.items()
        }
        return _renormalize(rows)
    if kind == "regime_merge":
        merged = {
            s: round((BASE_EMISSIONS["calm"][s] + BASE_EMISSIONS["storm"][s]) / 2, 6)
            for s in sorted(BASE_EMISSIONS["calm"])
        }
        rows = {
            "calm": {**BASE_EMISSIONS["calm"],
                     "beta": min(0.5, BASE_EMISSIONS["calm"]["beta"] + 0.25)},
            "storm": dict(merged),
        }
        return _renormalize(rows)
    raise ValueError(f"unknown shift: {kind}")


def run_shift_suite(seed: int = 3, n_ticks: int = 60) -> Dict[str, Any]:
    from sandbox.prediction import PredictionBenchmark, make_bayesian

    factory = make_bayesian(BASE_EMISSIONS)  # agent only knows the BASE world

    def brier_on(world_rows: Dict[str, Dict[str, float]]) -> float:
        bench = PredictionBenchmark(factory, world_rows, seed=seed, n_ticks=n_ticks)
        return summarize_safe(bench.run())

    def summarize_safe(records) -> float:
        n = len(records) or 1
        return round(sum(r.brier for r in records) / n, 6)

    base_brier = brier_on(shift("base"))
    shifts: Dict[str, Any] = {}
    for kind in ("mild", "novel_symbol", "regime_merge"):
        shifted_brier = brier_on(shift(kind))
        degradation = round((shifted_brier - base_brier) / max(base_brier, 1e-9), 4)
        shifts[kind] = {
            "brier_base": base_brier,
            "brier_shifted": shifted_brier,
            "degradation_index": degradation,
            "graceful": shifted_brier < 1.2,
        }
    return {
        "shifts": shifts,
        "all_graceful": all(s["graceful"] for s in shifts.values()),
        "mild_shift_bounded": shifts["mild"]["degradation_index"] < 0.75,
        "survives_novel_symbol": shifts["novel_symbol"]["graceful"],
    }
