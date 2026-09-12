"""
Self-Evolution Test Script
Verifies the full evolution cycle integration.
"""
import logging
import sys
import os

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# Suppress INFO logs for cleaner output
logging.getLogger("Ultrone").setLevel(logging.WARNING)
logging.getLogger("Ultrone.Evolution.Lab").setLevel(logging.WARNING)
logging.getLogger("Ultrone.Evolution.Genome").setLevel(logging.WARNING)

from ultrone import Ultrone

print("\n" + "="*60)
print("🧬 ULTRONE SELF-EVOLUTION TEST")
print("="*60)

# 1. Initialize
u = Ultrone()
print("\n✅ Ultrone initialized with Self-Evolution")
print(f"   Generation: {u.get_stats()['evolution']['generation']}")
print(f"   Capsules: {u.get_stats()['evolution']['active_capsules']}")
print(f"   Genes: {u.get_stats()['evolution']['active_genes']}")

# 2. Simulate learning cycles with varied success/failure
print("\n📊 Running 20 action learning cycles...\n")
for i in range(20):
    domain = ["air", "land", "cyber", "sea", "space"][i % 5]
    success = (i % 3) != 0  # ~33% failure rate — triggers evolution
    latency = 100 + (i * 30)
    
    result = u.learn({
        "success": success,
        "latency_ms": latency,
        "domain": domain,
        "action": "intercept" if domain == "air" else "engage",
    })
    
    status = "✓" if success else "✗"
    gen = result["generation"]
    evo = "🧬" if result["evolved"] else "  "
    fit = result["fitness"]
    print(f"   {i+1:2d}. [{status}] {domain:6s} | fit={fit:.3f} | gen={gen} {evo}")

# 3. Test manual evolution
print("\n🔬 Triggering manual evolution cycle...")
evo_result = u.evolve()
print(f"   Evolved: {evo_result['evolved']}")
print(f"   Generation: {evo_result['generation']}")
print(f"   Best Fitness: {evo_result['best_fitness']:.3f}")

# 4. Test think with evolved parameters
print("\n🧠 Testing evolved think()...")
params = u.get_genome_parameters()
print(f"   Evolved genome parameters: {len(params)} genes active")
for name, value in list(params.items())[:3]:
    print(f"     {name} = {value:.4f}")

result = u.think("We have a critical system error that keeps recurring")
print(f"   Prediction confidence: {result.get('confidence', 0):.3f}")
print(f"   Genome generation: {result['genome_generation']}")

# 5. Test agent evolver
print("\n🤖 Testing Agent Evolver (sub-agent creation)...")
from evolution import AgentEvolver
evolver = AgentEvolver(u.evolution_lab)

air_agent = evolver.create_agent("SkyGuardian", "air", "Air defense specialist")
cyber_agent = evolver.create_agent("CyberSentinel", "cyber", "Cyber warfare specialist")

for agent_name in ["SkyGuardian", "CyberSentinel"]:
    for j in range(5):
        evolver.record_task_result(agent_name, j % 2 == 0, 150 + j*20)

print(evolver.get_agent_report())

# 6. Final summary
print("\n" + u.get_evolution_summary())
print("\n" + "="*60)
print("✅ SELF-EVOLUTION TEST COMPLETE")
print("="*60)