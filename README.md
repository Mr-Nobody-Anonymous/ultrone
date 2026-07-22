<div align="center">
  <img src="images.jfif" alt="ULTRONE Battlefield AI" width="600"/>
</div>

# ⚡ ULTRONE - Next-Gen Multi-Domain Battlefield AI

> **Self-evolving swarm intelligence controlling machines across all warfighting domains**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](https://github.com/Mr-Nobody-Anonymous/ultrone)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Coevolution](https://img.shields.io/badge/Coevolution-Red%20vs%20Blue-orange.svg)](https://github.com/Mr-Nobody-Anonymous/ultrone)

---

## 🌟 What Makes ULTRONE Different?

Unlike traditional tactical systems, **ULTRONE thinks and evolves**. Every engagement feeds back into a collective intelligence mesh, allowing the system to adapt mid-battle and develop novel countermeasures.

```
🔥 INTELLIGENCE BECOMES STRENGTH 🔥
```

---

## 🚀 Core Capabilities

### 🧬 **Evolutionary Combat Engine**
- Tactical genomes mutate in real-time based on battlefield performance
- Combinatorial COA generation: `JAM + STRIKE → Cyber-Kinetic Sync`
- Automatic adaptation when threat patterns change
- **Coevolution**: Red Force counter-evolves alongside Blue, creating an adversarial arms race

### 🤖 **Specialized AI Perceptors**
Each sensor type has its own AI expert:
| Sensor | AI Specialist | Specialty |
|--------|--------------|-----------|
| 🛰️ Satellite | `SatelliteImageAI` | Formation/armor detection |
| 📡 Radar | `RadarAI` | Doppler/speed classification |
| 🛰️ GPS | `GPSAI` | Movement pattern analysis |
| 🎙️ Voice | `VoiceAI` | Threat keyword detection |
| 🔍 SIGINT | `SIGINTAI` | Signal pattern recognition |
| 💻 Cyber | `CyberFeedAI` | Attack/recon detection |
| 🌊 Sonar | `SonarAI` | Underwater contacts |
| 👁️ Visual | `VisualAI` | Optical target ID |
| 🔊 Acoustic | `AcousticAI` | Sound signatures |
| 🔥 Thermal | `ThermalAI` | Heat detection |

### ⚡ **Multi-Domain Control**
- **AIR**: Drone swarms, fighter jets, missile defense
- **LAND**: Tank squadrons, mobile launchers, infantry
- **SEA**: Submarines, destroyers, ASW warfare
- **SPACE**: Satellites, ICBM tracking, orbital sensors
- **CYBER**: Electronic attack, jamming, cyber ops

### 🧠 **Strategic Planning & Doctrine**
- **Doctrine System**: 4 military doctrine presets (Aggressive, Defensive, Balanced, Asymmetric)
- **Operational Planner**: Mission decomposition from strategic objectives
- **Strategic Campaign Planner**: High-level objective management with priority queuing
- **Secretary Council**: AI-driven strategic directive deliberation every N episodes

### 🔫 **F2T2EA Kill Chain Management**
- Full **Find → Fix → Track → Target → Engage → Assess** state machine
- Phase timeout and success/failure tracking per target
- Concurrent multi-target engagement coordination

### 👻 **Ghost Wargaming**
- Generates adversarial scenarios targeting defensive weaknesses
- Mutated enemy forces based on difficulty scaling
- Fast-forward simulation to test evolved strategies

### 🎛️ **Human-in-the-Loop API**
- FastAPI server for live operational command
- **Override constraints**: Force novelty weights, blacklist actions mid-training
- **XAI Endpoints**: Get human-readable explanations of the best evolved genome
- REST endpoints: `GET /status`, `POST /override`, `POST /ask_reasoning`

### 📡 **Communications Layer**
- Async pub/sub message bus with priority queuing
- Message history for replay and acknowledgment
- AES-GCM encryption for secure battlefield comms
- Structured protocol with message types, priority levels, and targeting

---

## 📂 Architecture

```
ultrone/
├── brain/                          # 🧠 Central AI systems
│   ├── reasoning/                  # 🎯 Tactical decision engine
│   │   ├── course_of_action.py      # COA generation with combinatorial tactics
│   │   ├── evolutionary_coagen.py   # Genetic evolution of tactics
│   │   ├── tacitical_engine.py      # OODA loop execution
│   │   ├── coevolution_engine.py    # Red vs Blue adversarial coevolution
│   │   ├── kill_chain.py            # F2T2EA state machine
│   │   ├── composite_kill_chain.py  # Multi-target kill chain orchestration
│   │   ├── secretary_council.py     # AI strategic directive deliberation
│   │   ├── monte_carlo_engine.py    # Monte Carlo simulation planning
│   │   ├── resource_allocator.py    # Optimal asset allocation
│   │   ├── red_force_genomes.py     # Red Force genome definitions
│   │   └── swarm_genomes.py         # Swarm genome architectures
│   ├── perception/                 # 👁️ Multi-sensor fusion
│   │   ├── specialized_analyzers.py # 11 AI experts per sensor type
│   │   ├── multi_source_analyzer.py # Fusion layer
│   │   ├── sensor_fusion.py         # Combined sensor confidence
│   │   ├── situational_awareness.py # Battlefield state awareness
│   │   ├── knowledge_graph.py       # Entity relationship graph
│   │   └── threat_classifier.py     # Threat level classification
│   ├── learning/                   # 📚 Experience & adaptation
│   │   ├── evolution_lab.py         # Genome mutation engine
│   │   ├── genome.py                # Gene/Capsule data structures
│   │   ├── agent_evolver.py         # Domain-specialized sub-agent creation
│   │   ├── experience_memory.py     # Cross-session memory persistence
│   │   ├── pattern_recognizer.py    # Tactical pattern detection
│   │   ├── llm_commander.py         # Hybrid LLM-guided command
│   │   └── performance_telemetry.py # Fitness & performance tracking
│   └── strategy/                   # 🏛️ High-level planning
│       ├── doctrine.py              # Military doctrine presets (4 types)
│       ├── operational_planner.py   # Mission decomposition
│       └── strategic_planner.py     # Campaign objective management
├── agents/                         # 🤖 Asset controllers
│   ├── air/                         # Drones, fighters, missiles
│   │   ├── drone_agent.py
│   │   ├── fighter_agent.py
│   │   └── missile_agent.py
│   ├── land/                        # Tanks, infantry, mobile missiles
│   │   ├── tank_agent.py
│   │   ├── infantry_agent.py
│   │   └── mobile_missile_agent.py
│   ├── sea/                         # Vessels, submarines
│   │   └── vessel_agent.py
│   ├── space/                       # Satellite agents
│   │   └── space_agent.py
│   ├── cyber/                       # Cyber warfare agents
│   └── base_agent.py                # Abstract base agent
├── sim/                            # 🎮 Simulation environment
│   ├── battlefield_env.py           # 100x100 grid battlefield Gym env
│   ├── world_state.py               # Global battlefield state
│   ├── environment.py               # Environmental effects
│   └── clock.py                     # Simulation clock
├── comms/                          # 📡 Communications
│   ├── message_bus.py               # Async pub/sub with priority queue
│   ├── api_server.py                # FastAPI HITL + XAI server
│   ├── encryption.py                # AES-GCM message encryption
│   └── protocol.py                  # Message types, priorities, routing
├── generative/                     # 🎨 Content generation
│   ├── scenario_generator.py        # Ghost wargaming scenarios
│   ├── adversarial_emulator.py      # Adversarial force emulation
│   ├── commander_briefing.py        # Post-hoc tactical briefings
│   ├── report_generator.py          # After-action reports
│   └── tactical_synthesizer.py      # Novel tactic synthesis
├── config/                         # ⚙️ Configuration
│   ├── settings.py                  # Military simulation parameters
│   └── doctrine_presets.py          # 4 predefined doctrine profiles
├── memory/                         # 💾 Cross-session memory
│   └── best_genome.json             # Best evolved genome persistence
├── viz/                            # 📊 Visualization
│   └── telemetry_dashboard.py       # Live training telemetry plots
├── data/                           # 📁 Static data
│   ├── entities.py                  # Entity definitions
│   ├── feeds.py                     # Data feed definitions
│   └── terrain.py                   # Terrain data
└── utils/                          # 🛠️ Utilities
    ├── geo.py                       # Geospatial calculations
    ├── helpers.py                   # General helpers
    ├── logger.py                    # Logging configuration
    └── probability.py               # Probability distributions
```

---

## 🎮 Quick Start

```python
# Run the simulation
python main.py

# Or use the API directly
from brain.perception.specialized_analyzers import SatelliteImageAI, VoiceAI
from brain.reasoning.evolutionary_coagen import EvolutionaryCOAGenerator

# Analyze satellite imagery
sat_ai = SatelliteImageAI()
sat_ai.analyze({"formation": "tanks_3x3"}, {"signature": "armor"})
# → {"threat_indicator": 0.8, "classification": "armor"}

# Generate evolved tactics
evo = EvolutionaryCOAGenerator()
genome = evo.initialize_default_genome()
mutated = evo.mutate_genome(genome)
coa = evo.generate_evolved_coa({"domain": "cyber", "type": "threat"})
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
```

---

## ⚙️ Configuration

Edit `config/settings.py` or environment variables:
```python
# Evolution parameters
MUTATION_RATE = 0.15
FITNESS_THRESHOLD = 0.75
GENERATIONS = 50

# Sensor weights
SENSOR_CONFIDENCE = {
    "satellite": 0.95,
    "radar": 0.85,
    "voice": 0.90,
}
```

---

## 🧪 Testing

```bash
# Run all tests
python test_evolutionary_coagen.py

# Test specialized analyzers
python -c "
from brain.perception.specialized_analyzers import SatelliteImageAI, VoiceAI
sat = SatelliteImageAI()
print(sat.analyze({'formation': 'tanks'}, {}))
# → threat_indicator: 0.8, classification: 'armor'
"
```

---

## 🚦 Roadmap

- [x] ✅ Specialized AI perceptors (11 sensor types)
- [x] ✅ Evolutionary COA generation
- [x] ✅ Combinatorial tactic creation (JAM+STRIKE → Cyber-Kinetic Sync)
- [ ] 🔄 Multi-agent swarm coordination
- [ ] 🌐 Distributed evolution across nodes
- [ ] 📱 Battle-damage assessment
- [ ] 🎯 Predictive kill-chain optimization

---

## 📜 License

**MIT License** - Open source for defense innovation

## 🙏 Built With Inspiration From

- ModelScope Ultron - Collective intelligence mesh
- UltronAgent - Self-evolving agent patterns  
- A-Evolve - Genetic algorithm concepts
- Agent Zero - Autonomous execution

---

> **⚠️ FOR EDUCATIONAL AND SIMULATION PURPOSES ONLY**  
> This is a wargaming AI framework. Not for real-world weapons systems.