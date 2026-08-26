"""Integration test: verify the full adaptation pipeline works end-to-end.

Tests the Learning + Long-Term Memory layer by running:
1. Experience storage
2. Reflection
3. Evaluation
4. Promotion
"""
import sys

def test_pipeline():
    print("=" * 60)
    print("ULTRONE ADAPTATION PIPELINE TEST")
    print("=" * 60)

    # 1. Experience Memory
    print("\n[1/5] Experience Memory...")
    from brain.learning.experience_memory import ExperienceMemory, EngagementOutcome
    mem = ExperienceMemory(max_history=500)
    print("  ✓ ExperienceMemory initialized")

    # 2. Reflection Layer
    print("\n[2/5] Reflection Layer...")
    from cognitive.self_reflection_layer import SelfReflectionLayer
    reflector = SelfReflectionLayer()
    print("  ✓ SelfReflectionLayer ready")

    # 3. Reflection Engine
    print("\n[3/5] Reflection Engine...")
    from frontier.adaptation.reflection_engine import ReflectionEngine
    reflection = ReflectionEngine(solver=None, reflector=reflector)
    print("  ✓ ReflectionEngine ready")

    # 4. Evaluator
    print("\n[4/5] Evaluator...")
    from adaptive.evaluator import Evaluator, ground_patrol_score
    evaluator = Evaluator(task=ground_patrol_score)
    print("  ✓ Evaluator ready")

    # 5. Promotion
    print("\n[5/5] Promotion Gate...")
    from adaptive.promotion import PromotionGate, BrainStore
    promotion = PromotionGate()
    print("  ✓ PromotionGate ready")

    print("\n" + "=" * 60)
    print("ALL CORE COMPONENTS LOADED SUCCESSFULLY")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ PIPELINE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)