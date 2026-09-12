"""Quick verification that the evolution module works."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test 1: import evolution module
from evolution import EvolutionLab, GenomeEngine, PerformanceTelemetry, Genome, Gene, Capsule
print("✅ evolution module imports OK")

# Test 2: create and initialize evolution lab
lab = EvolutionLab()
lab.initialize("test-agent")
print(f"✅ EvolutionLab initialized: gen={lab.genome_engine.generation}")

# Test 3: check genome structure
g = lab.genome_engine.active_genome
print(f"✅ Genome: {len(g.capsules)} capsules, {len(g.get_all_genes())} genes")

# Test 4: simulate actions to trigger evolution
for i in range(12):
    success = i % 3 != 0
    result = lab.log_action("test_action", "air", success, 100 + i*20)
print(f"✅ {lab.action_count} actions logged, {lab.evolution_count} evolutions triggered")

# Test 5: check stats
stats = lab.get_stats()
print(f"✅ Stats: gen={stats['genome_engine']['generation']}, pop={stats['genome_engine']['population_size']}")

# Test 6: agent evolver
from evolution import AgentEvolver
evolver = AgentEvolver(lab)
agent = evolver.create_agent("TestAgent", "cyber", "Test sub-agent")
print(f"✅ AgentEvolver: created '{agent.name}' with {len(agent.genome.get_all_genes())} genes")

# Test 7: summary
print()
print(lab.get_evolution_summary())
print("\n🧬 All evolution systems verified successfully!")