"""End-to-end smoke test: BDA + Predictive Kill-Chain.

Run:
    python scripts/run_bda_predictive_kc.py
"""
from __future__ import annotations

import json
import sys
import time

# Force UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Make project root importable
sys.path.insert(0, ".")

from brain.reasoning.battle_damage_assessment import (
    BattleDamageAssessment,
    BDAConfidence,
    BDASeverity,
    DamageAssessmentEngine,
    DamageIndicator,
    ReEngagementRecommendation,
)
from brain.reasoning.predictive_kill_chain import (
    EnsemblePredictiveModel,
    MarkovPredictiveModel,
    PhaseOutcome,
    PredictiveKillChain,
    TimeSeriesPredictiveModel,
)


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def demo_bda() -> DamageAssessmentEngine:
    section("BDA — battle damage assessment of three engagements")
    engine = DamageAssessmentEngine(bda_rigor=0.85)

    # 1) Heavily destroyed radar installation
    r1 = engine.assess("target_radar_01", "eng_001", {
        DamageIndicator.VISUAL: {"damage_score": 0.92,
                                  "structural": 0.95, "functional": 0.90, "mobility": 0.0},
        DamageIndicator.SAR_IMAGERY: {"damage_score": 0.88},
    })
    print(f"[destroyed] severity={r1.severity.value} damage={r1.damage_fraction:.0%} "
          f"confidence={r1.confidence.value} re-engage={r1.reengagement.value}")

    # 2) Lightly damaged vehicle, still mobile
    r2 = engine.assess("target_vehicle_02", "eng_002", {
        DamageIndicator.VISUAL: {"damage_score": 0.20,
                                  "structural": 0.25, "functional": 0.15, "mobility": 0.30},
    })
    print(f"[mobile]    severity={r2.severity.value} damage={r2.damage_fraction:.0%} "
          f"threatening={r2.still_threatening} re-engage={r2.reengagement.value}")

    # 3) Heavy structural damage, no intel on mobility
    r3 = engine.assess("target_bunker_03", "eng_003", {
        DamageIndicator.VISUAL: {"damage_score": 0.65,
                                  "structural": 0.85, "functional": 0.55},
        DamageIndicator.SIGINT: {"damage_score": 0.70},
        DamageIndicator.THERMAL: {"damage_score": 0.60},
    })
    print(f"[bunker]    severity={r3.severity.value} damage={r3.damage_fraction:.0%} "
          f"confidence={r3.confidence.value} re-engage={r3.reengagement.value}")

    print()
    print("Pending re-engagements:")
    for tid, plan in engine.get_all_pending_reengagements().items():
        print(f"  - {tid}: {plan['recommendation']} (damage~{plan['damage_fraction']:.0%})")

    print()
    print("Engine stats:", json.dumps(engine.stats(), indent=2, default=str))
    return engine


def demo_predictive_kc() -> PredictiveKillChain:
    section("Predictive Kill-Chain — training and forecasting")

    pkc = PredictiveKillChain()

    # Seed with 30 historical engagements
    print("Seeding 30 historical engagement traces...")
    for ep in range(30):
        for phase in ("find", "fix", "track", "target", "engage", "assess"):
            # Find is usually fast and successful; engage occasionally times out
            if phase == "engage" and ep % 7 == 0:
                pkc.record_outcome(phase, 95.0, PhaseOutcome.TIMEOUT)
            else:
                pkc.record_outcome(phase, 30.0, PhaseOutcome.SUCCESS)

    # Forecast
    pred = pkc.predict_target("target_vehicle_02", current_phase="find")
    print(f"\nForecast for target_vehicle_02 starting at 'find':")
    print(f"  Overall success probability: {pred.overall_success_probability:.0%}")
    print(f"  Predicted total duration:   {pred.predicted_total_duration_sec:.0f}s")
    print(f"  Predicted bottleneck:       {pred.predicted_bottleneck_phase}")
    print(f"  Recommendations:")
    for r in pred.recommendations:
        print(f"    - {r}")

    print("\nPer-phase predictions:")
    for phase, p in pred.predictions.items():
        print(f"  {phase:>7}: success={p.success_probability:.0%} "
              f"failure={p.failure_probability:.0%} "
              f"timeout={p.timeout_probability:.0%} "
              f"dur={p.predicted_duration_sec:.0f}s "
              f"most_likely={p.most_likely.value}")

    return pkc


def demo_combined(pkc: PredictiveKillChain, bda: DamageAssessmentEngine) -> None:
    section("Combined — predict, engage, assess, decide")

    # 1) Predict
    pred = pkc.predict_target("combined_target", current_phase="find")
    print(f"[predict]  P(success)={pred.overall_success_probability:.0%} bottleneck={pred.predicted_bottleneck_phase}")

    # 2) Engage (we fast-forward — record positive outcomes)
    for phase in ("find", "fix", "track", "target", "engage"):
        pkc.record_outcome(phase, 25.0, PhaseOutcome.SUCCESS)
    pkc.record_outcome("assess", 10.0, PhaseOutcome.SUCCESS)
    print("[engage]   engagement complete, BDA reading incoming...")

    # 3) BDA
    result = bda.assess("combined_target", "eng_combined", {
        DamageIndicator.VISUAL: {"damage_score": 0.55,
                                  "structural": 0.7, "functional": 0.45, "mobility": 0.5},
        DamageIndicator.SAR_IMAGERY: {"damage_score": 0.6},
    })
    print(f"[bda]      severity={result.severity.value} damage={result.damage_fraction:.0%} "
          f"re-engage={result.reengagement.value}")

    # 4) Decide
    if result.reengagement == ReEngagementRecommendation.STAND_DOWN:
        print("[decide]   target neutralised — stand down")
    elif result.reengagement == ReEngagementRecommendation.HUNT:
        print("[decide]   target mobile — hunt it down")
    elif result.reengagement in (
        ReEngagementRecommendation.IMMEDIATE, ReEngagementRecommendation.SCHEDULED
    ):
        print(f"[decide]   re-engage: {result.reengagement.value}")


def main() -> int:
    t0 = time.time()
    bda = demo_bda()
    pkc = demo_predictive_kc()
    demo_combined(pkc, bda)
    print()
    print(f"Done in {time.time() - t0:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
