# ⚡ ULTRONE - Self-Evolving Multi-Domain Battlefield AI

> **Next-generation hybrid intelligence system combining Generative LLM reasoning with Evolutionary swarm optimization across all warfighting domains**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](https://github.com/Mr-Nobody-Anonymous/ultrone)
[![Phase 8](https://img.shields.io/badge/Phase-8_•_Meta--Learning-red.svg)]()

---

## 🌟 What Makes ULTRONE Different?

Unlike traditional tactical systems, **ULTRONE thinks and evolves**. Every engagement feeds back into a collective intelligence mesh through a **closed-loop Meta-Learning Orchestration Layer**, allowing the system to adapt mid-battle and develop novel countermeasures autonomously.

```
🔥 INTELLIGENCE BECOMES STRENGTH — EVOLUTION BECOMES STRATEGY 🔥
```

### Core Innovation: Meta-Learning Orchestration Layer (Phase 8)

The Generative LLM subsystem and Evolutionary engine are now tied in a cybernetic feedback loop:

```
┌────────────────────────────────────────────────────────────────┐
│                    LLMCommander                                 │
│  optimize_evolution_parameters(league_stats, mc_results)        │
│       ↓ {sbx_eta_c, mutation_eta_m, uct_exploration_c}         │
├────────────────────────────────────────────────────────────────┤
│                   CoevolutionEngine                             │
│  apply_hyperparameter_payload(payload) → clamped + EMA-smoothed │
│  collect_telemetry_snapshot() → generation deltas, fuel, risk   │
│  stream_telemetry_to_kg(kg) → pushes to Knowledge Graph         │
├────────────────────────────────────────────────────────────────┤
│              MultiINTKnowledgeGraph (evolutionary_telemetry)     │
│  Evolutionary telemetry nodes (capped at 50 for flat memory)    │
│  EVOLUTION_TREND edges for cross-generational trend analysis    │
├────────────────────────────────────────────────────────────────┤
│              MonteCarloForklift (UCT with EMA-smoothed C)        │
│  Probabilistic COA evaluation with dynamic exploration constant │
└────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Capabilities Matrix

### ✅ Phase 7 (Completed) — AlphaStar League + CoT Reasoning

| Capability | Status | Description |
|-----------|--------|-------------|
| 🧬 AlphaStar League Training | ✅ | Main agent, main exploiters, league exploiters, past selves (5 checkpoint limit) |
| 🧬 SBX Crossover | ✅ | Simulated Binary Crossover for continuous parameters (eta_c tunable) |
| 🧬 Polynomial Mutation | ✅ | Fine-grained local search with self-adaptive mutation rate [0.01, 0.30] |
| 🧬 Self-Adaptive Mutation | ✅ | Tau-based log-normal update with verified safe bounds |
| 🧠 Chain-of-Thought Reasoning | ✅ | 4-step hidden deduction (Resource Constraints → Bottleneck → Deceit → Synthesis) |
| 🧠 Self-Correction Mechanism | ✅ | Critiques initial judgment against KG + MC evidence |
| 🎲 UCT Monte Carlo Forks | ✅ | 50 forks with UCT exploration (C = sqrt(2) default) |
| 🎲 Fork Configuration Diversity | ✅ | seed_offset, friction_bias, accuracy_noise, red_aggression |

### ✅ Phase 8 (Completed) — Meta-Learning Orchestration

| Capability | Status | Description |
|-----------|--------|-------------|
| 🔄 **Closed-Loop Meta-Learning** | ✅ | LLM → Coevolution → KG → LLM feedback cycle |
| 🔧 **Autonomous Hyperparameter Tuning** | ✅ | `optimize_evolution_parameters()` analyzes drift, win/loss, UCT convergence |
| 📊 **Evolutionary Telemetry Ingestion** | ✅ | `add_evolutionary_telemetry()` stores generational fitness, bottleneck risk |
| 🛡️ **Absolute Code Guardrails** | ✅ | SBX eta_c [5,30], Mutation eta_m [5,30], UCT C [0.5, 3.0], Mutation rate [0.01, 0.30] |
| 💨 **EMA Dampening** | ✅ | Exponential Moving Average (α=0.3) prevents parameter shock |
| 🧠 **LLM Non-Blocking Fallback** | ✅ | Returns safe defaults on parse/network failure |
| 🗄️ **Memory-Capped Telemetry** | ✅ | 50-generation window in KG (flat RAM profile) |

### ✅ Core Capabilities

| Capability | Status | Description |
|-----------|--------|-------------|
| 🧬 **Evolutionary Combat Engine** | ✅ | Tactical genomes mutate in real-time based on battlefield performance |
| 🧬 **Combinatorial COA Generation** | ✅ | `JAM + STRIKE → Cyber-Kinetic Sync` — automatic tactic synthesis |
| 🤖 **11 Specialized AI Perceptors** | ✅ | Each sensor type has its own AI expert with real signal processing |
| 🎲 **Predictive Kill-Chain Optimization** | ✅ | F2T2EA state machine + Monte Carlo probabilistic forecasting |
| 📱 **Battle-Damage Assessment** | ✅ | Supply node destruction tracking, effectiveness loss, fuel/ammo depletion |
| 🔄 **Multi-Agent Swarm Coordination** | ✅ | CommanderGenome → AssetMicroGenome hierarchical fleet control |
| 🌐 **Distributed Evolution** | ✅ | Cross-domain agent evolver with 5 domain specializations |
| 🔥 **Adversarial Coevolution** | ✅ | Blue vs Red force genomes co-evolve in closed-loop arms race |

---

## 🤖 Specialized AI Perceptors (11 Sensor Types)

Each sensor type has its own AI expert with real signal processing:

| Sensor | AI Specialist | Specialty | Signal Processing |
|--------|--------------|-----------|-------------------|
| 🛰️ Satellite | `SatelliteImageAI` | Formation/armor detection | Pattern template matching |
| 📡 Radar | `RadarAI` | Doppler/speed classification | FFT spectral analysis |
| 🛰️ GPS | `GPSAI` | Movement pattern analysis | Grid search detection |
| 🎙️ Voice | `VoiceAI` | Threat keyword detection | Whisper ASR + keyword density |
| 🔍 SIGINT | `SIGINTAI` | Signal pattern recognition | Burst detection + Shannon entropy |
| 💻 Cyber | `CyberFeedAI` | Attack/recon detection | Threat keyword classification |
| 🌊 Sonar | `SonarAI` | Underwater contacts | Signature classification |
| 👁️ Visual | `VisualAI` | Optical target ID | OWL-ViT zero-shot detection |
| 🔊 Acoustic | `AcousticAI` | Sound signatures | Spectral centroid + librosa |
| 🔥 Thermal | `ThermalAI` | Heat detection | Temperature anomaly analysis |
| 🧠 Multi-INT Fusion | `MultiSourceAnalyzer` | Cross-sensor correlation | Weighted evidence integration |

---

## 🧬 Evolutionary Genome Architecture

```
CommanderGenome (High-level strategy)
├── action_weights:      Dict[str, float]  (strike, jam, move, engage, locate, assess)
├── allocation_weights:  Dict[str, float]  (drones_recon, drones_strike, jammers_ew, ...)
├── synergy_map:         Dict[tuple, float] (action pair synergies)
├── phase_params:        Dict[str, PhaseParameters] (F2T2EA phase tuning)
├── resource_conservation: float
├── time_optimization:     float
├── mutation_rate:        float [0.01, 0.30] (self-adaptive)
└── spawn_asset_micro_genomes() → List[AssetMicroGenome]

AssetMicroGenome (Individual asset behavior)
├── heading, timing, aggressiveness
├── formation_spread, adaptation_rate
└── mutate() → AssetMicroGenome

RedForceGenome (Adversarial evolution)
├── evasion_tendency, burst_speed_factor, heading_change_angle
├── ecm_probability, ecm_noise_level
├── formation_density, dispersion_radius
└── mutate(), crossover() → RedForceGenome
```

---

## ⚡ Multi-Domain Control

| Domain | Asset Types | Capabilities |
|--------|-------------|--------------|
| ✈️ **AIR** | Drone swarms, fighter jets, missile defense | Aerial supremacy, recon, precision strikes |
| 🚁 **LAND** | Tank squadrons, mobile launchers, infantry | Ground assault, armor, artillery |
| 🚢 **SEA** | Submarines, destroyers, ASW warfare | Naval dominance, underwater warfare |
| 🛸 **SPACE** | Satellites, ICBM tracking, orbital sensors | Space domain awareness, orbital support |
| 💻 **CYBER** | Electronic attack, jamming, cyber ops | EW, SIGINT, cyber warfare |

---

## 📂 Architecture

```
ultrone/
├── brain/                          # 🧠 Central AI systems
│   ├── reasoning/                  # 🎯 Tactical decision engine
│   │   ├── coevolution_engine.py   #   AlphaStar League + SBX/Poly Mutation
│   │   ├── evolutionary_coagen.py  #   Genetic evolution of tactics
│   │   ├── monte_carlo_engine.py   #   UCT Monte Carlo forking (50 forks)
│   │   ├── kill_chain.py           #   F2T2EA state machine (FIND→ASSESS)
│   │   ├── secretary_council.py    #   Strategic LLM directive council
│   │   ├── swarm_genomes.py        #   CommanderGenome + AssetMicroGenome
│   │   └── red_force_genomes.py    #   Adversarial Red genome
│   ├── perception/                 # 👁️ Multi-sensor fusion
│   │   ├── specialized_analyzers.py #   11 AI experts per sensor type
│   │   ├── knowledge_graph.py      #   MultiINTKnowledge Graph (Phase 8 telemetry)
│   │   └── multi_source_analyzer.py#   Fusion layer
│   ├── learning/                   # 📚 Experience & adaptation
│   │   ├── llm_commander.py        #   LLM with CoT + Self-Correction (Phase 8 tuning)
│   │   ├── evolution_lab.py        #   Genome mutation engine
│   │   ├── agent_evolver.py        #   Cross-domain agent creation
│   │   └── performance_telemetry.py#   Training metrics
│   └── orchestrator.py             # 🔄 Master training loop with meta-learning
├── agents/                         # 🤖 Asset controllers (air, land, sea, space, cyber)
├── sim/                            # 🎮 Simulation environment
│   ├── battlefield_env.py          #   Battlefield with supply nodes, fuel, ammo
│   └── clock.py                    #   Simulation clock
├── generative/                     # 📝 Post-hoc analysis
│   ├── commander_briefing.py       #   Training summary reports
│   └── report_generator.py         #   Battle damage assessment
├── comms/                          # 📡 Messaging backbone
│   └── api_server.py               #   REST API (HITL + XAI)
├── config/                         # ⚙️ Configuration
│   └── settings.py                 #   Evolution/sensor parameters
└── viz/                            # 📊 Visualization
    └── telemetry_dashboard.py      #   Live training dashboard
```

---

## 🎮 Quick Start

```python
# Full autonomous training with meta-learning
python main.py

# Or use components directly:
from brain.learning.llm_commander import LLMCommander
from brain.reasoning.coevolution_engine import CoevolutionEngine
from brain.reasoning.swarm_genomes import CommanderGenome

# Initialize the coevolution engine
coev = CoevolutionEngine(sample_size=3, use_monte_carlo=True)

# Create a commander genome
blue = CommanderGenome(
    genome_id="BLUE-001",
    action_weights={"strike": 0.8, "jam": 0.4, "move": 0.3},
    mutation_rate=0.15,
)

# Initialize Blue and Red populations
coev.initialize_blue(blue)
coev.initialize_red(RedForceGenome(genome_id="RED-001"))

# Run one generation of evolution
new_blue = coev.evolve_blue_generation()

# LLM meta-analysis for hyperparameter tuning
llm = LLMCommander()
payload = llm.optimize_evolution_parameters(
    coev.get_stats(),
    {"uct_exploration_c_raw": 1.414}
)
print(payload)
# → {"sbx_eta_c": 18.5, "mutation_eta_m": 22.3, "uct_exploration_c": 1.8, ...}

# Apply with guardrails
applied = coev.apply_hyperparameter_payload(payload)
print(applied)
# → {"sbx_eta_c": 18.5, "mutation_eta_m": 22.0, ... "notifications": []}

# Stream telemetry to Knowledge Graph
from brain.perception.knowledge_graph import MultiINTKnowledgeGraph
kg = MultiINTKnowledgeGraph()
coev.stream_telemetry_to_kg(kg)
print(kg.get_evolutionary_telemetry(n_last=5))
# → [{"generation": 1, "avg_fitness": 0.5, "bottleneck_risk": 0.3, ...}]
```

---

## 🔬 Live Evolution Demo

When performance drops, ULTRONE adapts:

```
📊 Engagement Success Rate: 68% (↓ below threshold)
🧬 Adapting... Threat Pattern Changed Detected
🧪 Applying Genome Mutation: action_weights.jam *= 1.15
⚡ New COA Generated: "Cyber-Kinetic Sync" 
🎯 Combined Actions: JAM + STRIKE = Novelty 0.8
✅ Next Engagement: 89% Success Rate

🧠 Phase 8 Meta-Learning Cycle:
  → LLM analyzing league drift: eta_c=15.0 → 22.3 (↑ exploration)
  → EMA smoothing mutation transition: 0.15→0.18 (α=0.3)
  → Telemetry pushed to KG: gen=42, fitness_delta=+0.12
  → Guardrails verified: all params within safe envelope
```

---

## 🧪 Testing

```bash
# Run Phase 6 Palantir integration test suite (26 tests)
python test_phase6_palantir.py

# Run evolutionary coevolution stress test
python stress_test_red_queen.py

# Run evolutionary COA generator test
python test_evolutionary_coagen.py

# Test individual components
python -c "
from brain.perception.specialized_analyzers import SatelliteImageAI, VoiceAI
sat = SatelliteImageAI()
print(sat.analyze({'formation': 'tanks_3x3'}, {'signature': 'armor'}))
# → threat_indicator: 0.8, classification: 'armor'
"
```

---

## ⚙️ Configuration

Edit `config/settings.py`:

```python
# Evolution parameters
MUTATION_RATE = 0.15
MUTATION_MIN = 0.01
MUTATION_MAX = 0.30
SBX_ETA_C = 15.0           # Phase 8: dynamic via meta-learning
MUTATION_ETA_M = 15.0      # Phase 8: dynamic via meta-learning
UCT_EXPLORATION_C = 1.414  # Phase 8: dynamic via meta-learning

# League training
MAX_PAST_SELVES = 5
LEAGUE_EXPLOITERS = 3
MAIN_EXPLOITERS_PER_RED = 2

# Monte Carlo
NUM_FORKS = 50
FRICTION_LEVEL = 0.15

# Knowledge Graph
DECAY_STEPS = 5
MAX_TELEMETRY = 50  # Phase 8: memory cap
```

---

## 🧠 Meta-Learning Loop Detail

### Orchestrator Cycle (every 20 episodes)

1. **Collect Telemetry** → `CoevolutionEngine.collect_telemetry_snapshot()`
2. **Stream to KG** → `CoevolutionEngine.stream_telemetry_to_kg(kg)`
3. **LLM Analysis** → `LLMCommander.optimize_evolution_parameters(stats, mc)`
4. **Guardrail Enforcement** → `CoevolutionEngine.apply_hyperparameter_payload(payload)`
   - SBX eta_c clamped to [5.0, 30.0] + EMA dampened
   - Mutation eta_m clamped to [5.0, 30.0] + EMA dampened
   - UCT C clamped to [0.5, 3.0] + EMA dampened
5. **Secretary Council** → Strategic directive for fitness weight adjustment
6. **LLM Briefing** → Visual-grounding tactical analysis with CoT + self-correction

---

## 🚦 Development Roadmap

### ✅ Phase 7 — AlphaStar League + CoT (Complete)
- [x] Chain-of-Thought reasoning (4-step hidden deduction)
- [x] Self-correction mechanism (KG + MC cross-validation)
- [x] UCT Monte Carlo selection strategy
- [x] SBX crossover + Polynomial mutation
- [x] Self-adaptive mutation rate [0.01, 0.30]
- [x] AlphaStar league: main_agent, exploiters, past_selves

### ✅ Phase 8 — Meta-Learning Orchestration Layer (Complete)
- [x] Autonomous hyperparameter tuning (LLM → Evolutionary)
- [x] Evolutionary telemetry streaming to Knowledge Graph
- [x] Absolute code rigidity (guardrails, EMA dampening, zero-deepcopy)
- [x] 26/26 Phase 6 validation tests passing

### 🔮 Phase 9 — Distributed & Federated (Planned)
- [ ] Federated evolution across compute nodes
- [ ] Cross-instance genome migration
- [ ] Hierarchical meta-learning across battles
- [ ] Advanced battle-damage temporal modeling

---

## 📜 License

**MIT License** — Open source for defense innovation

## 🙏 Built With Inspiration From

- **ModelScope Ultron** — Collective intelligence mesh
- **AlphaStar** — League-based multi-agent reinforcement learning
- **OpenAI o1** — Chain-of-thought reasoning patterns
- **Palantir** — Multi-INT data fusion paradigms
- **A-Evolve** — Genetic algorithm concepts
- **Agent Zero** — Autonomous execution patterns

---

> **⚠️ FOR EDUCATIONAL AND SIMULATION PURPOSES ONLY**  
> This is a wargaming AI framework for research and development. Not for real-world weapons systems.

