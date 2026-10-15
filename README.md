<div align="center">

<img src="docs/assets/images.png" alt="ULTRONE Battlefield AI" width="320"/>

# ⚡ ULTRONE

### **Next-Gen Multi-Domain Battlefield AI**

> _Self-evolving swarm intelligence controlling machines across all warfighting domains._

<p>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License: MIT"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge" alt="Python 3.10+"/></a>
  <a href="https://github.com/Mr-Nobody-Anonymous/ultrone"><img src="https://img.shields.io/badge/AI-Powered-purple.svg?style=for-the-badge" alt="AI Powered"/></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/API-FastAPI-009688.svg?style=for-the-badge" alt="FastAPI"/></a>
  <a href="https://github.com/Mr-Nobody-Anonymous/ultrone"><img src="https://img.shields.io/badge/Coevolution-Red%20vs%20Blue-orange.svg?style=for-the-badge" alt="Coevolution"/></a>
</p>

<p>
  <a href="#-core-capabilities">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-roadmap">Roadmap</a> •
  <a href="#-artificial-intelligence-in-the-military">References</a>
</p>

</div>

---
## 🗂️ Repository Layout (monorepo)

ULTRONE is organized as a semantic monorepo. Packages keep their original
top-level import names (`import cognitive`, `import brain`, `import agents`,
...), but every package lives inside a bucket that states its role:

```text
ULTRONE/
│
├── apps/                     # Product layer — runnable applications
│   ├── api/                  # FastAPI service & REST routers (cockpit, defense, chat, neural)
│   ├── backend/              # Research platform REST surface (api/v1, exporters, vision)
│   ├── console/              # Interactive terminal / console utilities
│   ├── dashboard/            # Operations & monitoring dashboard application
│   ├── frontend/             # Next-gen React + Vite + Tailwind + Playwright UI cockpit
│   ├── globe/                # 3D geospatial / Cesium tactical visualization app
│   ├── simulator/            # Discrete-event tactical environment simulator
│   ├── ultrone/              # CLI entrypoint and orchestrator application
│   ├── cli/                  # Interactive CLI client
│   ├── services/             # Harness/memory/skill/trajectory services
│   └── ultrone_hitl/         # Human-in-the-loop decision workflows + audit store
│
├── packages/                 # Platform layer — modular domain building blocks
│   ├── core/                 # Core contracts, config, logging, defense ontology (5-Domain & Multi-INT MHT)
│   ├── runtime/              # DDIL CRDT World Mesh, Byzantine physical filter, event sourcing, OS kernel
│   ├── safety/               # Machine-checked ROE / LOAC verifier, HMAC EffectorLeases, HOTL veto
│   ├── cognition/            # Pareto kill-chain allocator, cognitive EW & anti-spoofing, AlphaWarfare MCTS
│   ├── geospatial/           # Coordinate transforms, spherical geometry, MGRS, terrain analysis
│   ├── investigation/        # Multi-modal intelligence investigation, timeline reconstruction
│   ├── research/             # Literature analysis, autonomous scientific hypothesis generation
│   ├── workflows/            # Orchestration DAGs, LangGraph pipelines, human-in-the-loop workflows
│   ├── adapters/             # Hardware, sensor, LLM, vision, and vector DB adapters
│   ├── simulation/           # Physics models, kinetic equations, radar cross-section profiles
│   ├── agents/               # Multi-agent orchestrators, plugin SDK, robotics controllers
│   ├── knowledge/            # Knowledge engine, learning platforms, memory clusters
│   ├── observability/        # Telemetry, OpenInference, Prometheus & Grafana metrics
│   └── transport/            # Comms, pub/sub bus, encrypted wire protocols
│
├── research/                 # Autonomous research platform, benchmarks, and databases
├── simulation/               # Digital twin simulation engines and fault injection
├── adapters/                 # Seams to external databases, vector stores, and models
├── infra/                    # Docker, Kubernetes, Helm, and deployment manifests
├── tests/                    # Defense superiority, cockpit API, conformance, and E2E suites
├── docs/                     # Specifications, architecture invariants, and deployment guides
└── vendor/                   # Third-party baseline and imported reference libraries
```

**Nothing was deleted in the reorganization** — every tracked file was moved
with `git mv`, so history is preserved. The duplicated `original_source/` +
root-level copies are now clearly vendored under `vendor/` with a single
import shim (`ultron` → `vendor/original_source`), eliminating the
"which copy does the runtime import?" problem.

**Imports keep working** thanks to `_ultrone_paths.py`: entry points call
`ensure_on_syspath()`, pytest and packaging list every bucket, and CI sets
`PYTHONPATH` to all buckets.

---

## 🌟 What Makes ULTRONE Different?

Unlike traditional tactical systems, **ULTRONE thinks and evolves**. Every engagement feeds back into a collective intelligence mesh, allowing the system to adapt mid-battle and develop novel countermeasures. The swarm acts as one mind — sharing perception, weighing consequences, and inventing new tactics on the fly.

```
╔══════════════════════════════════════════════════════════════════╗
║   🔥  INTELLIGENCE  BECOMES  STRENGTH  🔥                        ║
╚══════════════════════════════════════════════════════════════════╝
```

> _Decide faster. Adapt harder. Outlast everything._

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
- **AIR** — Drone swarms, fighter jets, missile defense
- **LAND** — Tank squadrons, mobile launchers, infantry
- **SEA** — Submarines, destroyers, ASW warfare
- **SPACE** — Satellites, ICBM tracking, orbital sensors
- **CYBER** — Electronic attack, jamming, cyber ops

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

### 💥 **Battle Damage Assessment & Predictive Kill-Chain**
- **BDA**: multi-sensor (visual/SAR/thermal/radar/SIGINT) damage fusion with severity + confidence scoring
- Re-engagement recommendations: `IMMEDIATE` / `SCHEDULED` / `HUNT` / `STAND_DOWN` / `UNCERTAIN`
- **Predictive Kill-Chain**: pluggable models (Markov transitions, EMA time series, ensemble) forecasting F2T2EA phase outcomes
- Bottleneck-phase detection, per-phase duration & success probability, automatic re-engagement
- Run: `python scripts/run_bda_predictive_kc.py`

### 🛡️ **Next-Gen Defense Superiority Architecture (Surpassing Palantir & Anduril)**
ULTRONE incorporates a production-grade defense superiority stack engineered to surpass legacy defense AI platforms (Palantir Gotham/Foundry/AIP and Anduril Lattice OS/Menace) across 7 core capabilities:

| Capability Pillar | Legacy Palantir (Gotham/AIP) | Legacy Anduril (Lattice OS) | ULTRONE Next-Gen Superiority | Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **1. Multi-Domain Defense Ontology** | Enterprise cloud ontology for analysts; high latency | Track-centric edge; lacks unified 5-domain ontology | Unified 5-domain ontology (Space, Air, Land, Maritime Surface/Subsurface, Cyber/EM Spectrum) with Multi-INT graph fusion & Multiple Hypothesis Tracking | [`packages/core/ontology/defense_ontology.py`](packages/core/ontology/defense_ontology.py) |
| **2. Decentralized Tactical World Mesh** | Cloud reachback required; degraded when severed | Mesh telemetry sharing; basic state sync | Fully decentralized, Byzantine-resilient CRDT World Mesh for DDIL edge nodes; zero cloud reliance; kinematic plausibility validation | [`packages/runtime/crdt_mesh/world_mesh.py`](packages/runtime/crdt_mesh/world_mesh.py) |
| **3. Sensor-to-Effector Kill Chain** | Manual workflow-assisted targeting in TOC | Point-defense kinetic interceptor allocation | Multi-objective Pareto optimization balancing Time-to-Intercept (TTI), $P_k$, Collateral Damage (CDE), and Cost Asymmetry; soft-kill prioritized | [`packages/cognition/kill_chain/allocator.py`](packages/cognition/kill_chain/allocator.py) |
| **4. Machine-Checked ROE & LOAC** | Post-hoc audit logs & policy prompts | Human-in-the-loop fire control button | Machine-checked temporal logic verifying Distinction (PID $\ge \tau$), Proportionality (CDE $\le \tau$), 3D polygon No-Strike geofences, and HOTL cryptographic effector leases | [`packages/safety/roe/rules_of_engagement.py`](packages/safety/roe/rules_of_engagement.py) |
| **5. Cognitive Electronic Warfare & Anti-Spoofing** | Passive intelligence feed ingestion | Sensor processing at edge | Cross-spectral radar RCS vs FLIR thermal decoy rejection, kinematic INS/GPS drift spoofing detection, and autonomous EMCON state machine | [`packages/cognition/electronic_warfare/anti_spoofing.py`](packages/cognition/electronic_warfare/anti_spoofing.py) |
| **6. Predictive Adversarial Wargaming** | Offline simulation & planning tools | Reactive interceptor vectoring | Real-time online Monte Carlo Tree Search (AlphaWarfare MCTS) anticipating multi-step adversary counter-moves with winning probability deltas | [`packages/cognition/adversarial_wargame/predictive_wargame.py`](packages/cognition/adversarial_wargame/predictive_wargame.py) |
| **7. Cockpit REST Defense API Subsystem** | Siloed analytics dashboards; high latency | Embedded vendor display; closed protocol | High-performance operational REST & WebSocket endpoints exposing real-time COP, CRDT mesh state, kill chain allocation, and ROE audits | [`apps/api/routers/cockpit.py`](apps/api/routers/cockpit.py) |

---

## 📂 Architecture

```
ultrone/
├── apps/                               # Operational Applications & User Surfaces
│   ├── api/                            # FastAPI REST & WebSocket server (routers: cockpit, defense, chat, neural, tools)
│   ├── backend/                        # Research platform REST API service (v1, exporters, vision)
│   ├── console/                        # Interactive terminal utilities & operator REPL
│   ├── dashboard/                      # Real-time telemetry & metrics operations dashboard
│   ├── frontend/                       # Tactical Autonomy Cockpit (React 18, Vite, Tailwind CSS, Playwright E2E)
│   ├── globe/                          # 3D geospatial / Cesium tactical visualization app
│   ├── simulator/                      # Discrete-event tactical environment simulator
│   ├── ultrone/                        # CLI orchestrator & command-line interface
│   ├── cli/                            # Interactive CLI client
│   ├── services/                       # Background trajectory, harness & skill workers
│   └── ultrone_hitl/                   # Human-in-the-loop decision workflows & immutable audit store
│
├── packages/                           # Modular Platform Packages
│   ├── core/                           # Foundation contracts, config, logging, and 5-Domain Defense Ontology
│   │   ├── ontology/                   # 5-Domain Defense Ontology (Space, Air, Land, Sea, Cyber) & Multi-INT MHT
│   │   ├── config/                     # System configuration & doctrine settings (settings.py)
│   │   ├── core/                       # Core pipeline, safety gates, and interfaces
│   │   └── ultrone_types/              # Core type contracts (renamed to prevent stdlib shadowing)
│   ├── runtime/                        # Distributed State, Mesh & OS Kernel
│   │   ├── crdt_mesh/                  # Decentralized DDIL CRDT World Mesh & Byzantine Physical Filter
│   │   ├── event_sourcing/             # Immutable event store & deterministic replay engine
│   │   └── ultrone_os/                 # Autonomous OS kernel & process scheduler
│   ├── safety/                         # Safety, Formal Policy & Compliance
│   │   ├── roe/                        # Formal Machine-Checked ROE & LOAC Verifier, HMAC EffectorLease, HOTL Veto
│   │   └── security/                   # Sandbox execution, cryptographic permissions, secrets manager
│   ├── cognition/                      # Cognitive Architecture, Targeting & Adversarial AI
│   │   ├── kill_chain/                 # Pareto Sensor-to-Effector Allocator (TTI, Pk, CDE, Cost Asymmetry)
│   │   ├── electronic_warfare/         # Cognitive EW, cross-spectral decoy rejection, GPS anti-spoofing, EMCON
│   │   ├── adversarial_wargame/        # Real-time AlphaWarfare MCTS engine for multi-ply counter-move prediction
│   │   ├── brain/                      # Central tactical decision engine, reasoning, and multi-tier memory
│   │   ├── cognitive/                  # 15-Layer cognitive architecture & perception layers
│   │   └── self_improvement/           # Autonomous learning loops, neural LoRA trainers, and genome mutation
│   ├── geospatial/                     # Coordinate transformations, spherical geometry, MGRS, terrain analysis
│   ├── investigation/                  # Multi-modal intelligence investigation & timeline reconstruction
│   ├── research/                       # Scientific literature analysis, hypothesis generation, and benchmarking
│   ├── workflows/                      # Orchestration DAGs, LangGraph stategraphs, and tactical execution plans
│   ├── adapters/                       # Integration seams (LLM, vision, vector DB, sensor hardware)
│   ├── simulation/                     # Kinetic equations, physics models, radar cross-section profiles
│   ├── agents/                         # Autonomous tactical agents (air, land, maritime, space, cyber controllers)
│   ├── knowledge/                      # Knowledge engine, graph databases, and semantic search
│   ├── observability/                  # Telemetry, OpenInference, Prometheus & Grafana exporters
│   └── transport/                      # Pub/sub messaging bus, encrypted transport, and wire protocols
│
├── infra/                              # Deployment & infrastructure manifests (Docker, Helm, Kubernetes, HF Space)
├── tests/                              # Comprehensive test suites (defense superiority, cockpit, conformance, evals)
├── docs/                               # Master architecture, invariants, deployment guides, and analysis
└── vendor/                             # Vendored libraries (original_source/, ultron/ shim, adelise/)
```

<details>
<summary>📖 <b>Full file-by-file architecture listing</b> (click to expand)</summary>

The complete per-file tree is maintained below and spans every module:

- `brain/reasoning/search/` — MCTS, HTN, A*, MAPF, PDDL and friends
- `brain/reasoning/game_theory/` — Nash, Stackelberg, CFR, Minimax, Auctions, Zero-Sum, Cooperative
- `brain/perception/probabilistic/` — Bayesian Networks, HMM, Kalman KF/EKF/UKF, Particle Filter
- `brain/learning/rl/` — PPO, SAC, TD3, DQN, Rainbow, MARL, QMIX, VDN…
- `brain/memory/` — Episodic, Semantic, Working, Associative, Consolidation
- `brain/xai/` — SHAP, LIME, Counterfactual, Confidence Calibration, Reasoning Graphs
- `ai_architectures/` — Behavior Trees, GOAP, Utility AI, BDI, FSM, Hierarchical FSM, Blackboard, Reactive Planning
- `sim/world_modeling/` + `sim/performance/` — Terrain, Weather, Resources, Logistics, Events / Parallel, Distributed, Ray, GPU, Profiler

</details>

---

## 🎮 Quick Start

```bash
# Clone and run the simulation
git clone https://github.com/Mr-Nobody-Anonymous/ultrone
cd ultrone
python main.py
```

```python
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

### 🧬 Neural Self-Improvement Milestone (new!)

ULTRONE can now answer *"did an actual neural model improve?"* — not just the simulated question. The `self_improvement/neural/` package plugs a model adapter, tokenizer pipeline, LoRA trainer, curated dataset split, and capability benchmark into the **same** orchestration / lineage / promotion-gate machinery — with zero changes to surrounding code:

```python
from self_improvement.neural import (
    NeuralAdapterConfig, DeterministicTestPipeline,
    ExternalCorpus, DatasetSplitter,
    LoRATrainer, NeuralLearnedWeights, NeuralCapabilityBenchmark,
)

config   = NeuralAdapterConfig(model_id="my-model")
base     = NeuralLearnedWeights(
    values={"reasoning": .5, "coding": .5, "retrieval": .5, "tool_use": .5},
    config_fingerprint=config.fingerprint(), base_model_hash="base")
split    = DatasetSplitter(train_ratio=.75, seed=42).split(
               ExternalCorpus(name="v1", kind="curated",
                              examples=my_examples).records())
candidate = LoRATrainer(rank=8, alpha=16., steps=5, seed=42).fit(
    base=base, examples=split.pair.train.load(),
    dataset_hash=split.pair.train.content_hash,
    config_fingerprint=config.fingerprint()).weights

report = NeuralCapabilityBenchmark(cycles=5, family_each=4,
                                   split_seed=42).run()
print(report.simulated.measurably_better)  # surround improved?
print(report.neural.measurably_better)     # actual model improved?
```

> ⚠️ The benchmark **never merges** the simulated and neural verdicts — a simulated gain is evidence about the *surround*, not the underlying model.

Full walkthrough → [`packages/cognition/self_improvement/neural/README.md`](packages/cognition/self_improvement/neural/README.md)

---

## 🔬 Live Evolution Demo

When performance drops, ULTRONE adapts:

```
📊 Engagement Success Rate: 68% (↓ below threshold)
🧬 Adapting... Threat Pattern Change Detected
🧪 Applying Genome Mutation: action_weights.jam *= 1.15
⚡ New COA Generated: "Cyber-Kinetic Sync"
🎯 Combined Actions: JAM + STRIKE = Novelty 0.8
✅ Next Engagement: 89% Success Rate
```

---

## ⚙️ Configuration

Edit `packages/core/config/settings.py` (`MilitaryConfig`) or environment variables:

```python
@dataclass
class MilitaryConfig:
    # Evolution parameters
    evolution_enabled: bool = True
    evolution_interval_ticks: int = 10
    min_fitness_threshold: float = 0.75

    # Threat thresholds (per doctrine)
    threat_threshold_high: float = 0.8
    threat_threshold_medium: float = 0.5
    threat_threshold_low: float = 0.2

    # Sensor parameters
    radar_detection_range_km: float = 150.0
    visual_detection_range_km: float = 20.0
    sigint_detection_range_km: float = 300.0
```

---

## 🧪 Testing

```bash
# Run full defense superiority + Cockpit REST API test suites (45 passed)
python -m pytest tests/test_defense_superiority.py tests/test_cockpit_api.py -q

# Run monorepo reorganization and import validator (58 passed, 0 failures)
python _validate_reorg.py

# Run MCP wire conformance suite (30 tests)
pytest tests/conformance/mcp_2026_07_28_wire/ -q

# Just the neural milestone suite (63 tests)
pytest tests/test_neural_module.py -q

# Run frontend TypeScript typecheck (0 errors)
cd apps/frontend && npm run typecheck

# Run Playwright E2E Cockpit suite (25 passed, serial execution required)
cd apps/frontend && npx playwright test --workers=1
# Alternatively: npm run test:e2e

# Test specialized analyzers
python -c "from brain.perception.specialized_analyzers import SatelliteImageAI; sat = SatelliteImageAI(); print(sat.analyze({'formation': 'tanks'}, {}))"
# → threat_indicator: 0.8, classification: 'armor'
```

---

## 🚦 Capability Maturity Matrix (L0–L6)

To maintain scientific rigor and epistemic integrity, ULTRONE replaces binary checkmarks with an explicit **L0–L6 maturity classification** governed by machine-readable [`capabilities.yaml`](capabilities.yaml) and tracked in [`VALIDATION_STATUS.md`](VALIDATION_STATUS.md):

- **`L0` (Planned)**: Architecture/specification stage.
- **`L1` (Scaffold)**: Interfaces and abstract classes exist; hardware actuation strictly disabled.
- **`L2` (Unit-Tested)**: Modular unit test coverage without full integration.
- **`L3` (Integrated)**: Multi-component end-to-end integration verified (e.g. MCP + CBF + SITL).
- **`L4` (Benchmarked)**: Statistical evaluation over $N$ seeds with confidence intervals.
- **`L5` (Reproducible)**: Evaluated on held-out datasets with frozen lockfiles.
- **`L6` (Externally Validated)**: Validated against third-party agent harnesses (e.g. UK AISI Inspect).

| Capability | Level | Status | Unit Tests | Integration | Benchmarked | Safety Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| **Multi-Domain Defense Ontology** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Tactical World Mesh (CRDT)** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Pareto Kill Chain Allocator** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Formal ROE & LOAC Verifier** | `L3` | integrated | Yes | Yes | Yes | Simulation Only |
| **Cognitive Electronic Warfare** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Adversarial Wargame (MCTS)** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Digital Battlefield Simulator** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **F2T2EA Dynamic Kill-Chain State Machine** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Control Barrier Function (CBF) & ROE Grader** | `L3` | integrated | Yes | Yes | Yes | Simulation Only |
| **Model Context Protocol (MCP 2026-07-28)** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **UDIS (MHS-Inspired Device Protocol)** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Event-Sourced Provenance & Deterministic Replay** | `L3` | integrated | Yes | Yes | No | Simulation Only |
| **Multi-Sensor Perception & Fusion** | `L2` | unit_tested | Yes | No | No | Simulation Only |
| **Real-Time Genome Evolution** | `L2` | unit_tested | Yes | No | No | Simulation Only |
| **Autonomous Research & Self-Improvement Loop** | `L2` | experimental | Yes | No | No | Simulation Only |
| **Neural Model Self-Improvement Adapter** | `L1` | scaffold | No | No | No | Simulation Only |
| **Physical Robotics Actuation** | `L1` | simulation_scaffold | Yes | No | No | Simulation Only |

> [!NOTE]
> UDIS is an **MHS-inspired device abstraction layer** extending the Anthropic Model Hardware Standard research preview with ULTRONE-specific safety bounds, capability leases, 10-state FSM guards, and compiled deterministic procedures. Direct physical hardware actuation remains prohibited in favor of digital-twin and simulation drivers. Detailed empirical validation progress is maintained in [`VALIDATION_STATUS.md`](VALIDATION_STATUS.md).

### Upcoming Milestones
- [ ] 🔌 Swap `MockNeuralAdapter` for a real open-weight model adapter (HF local or hosted inference) behind the same `ModelAdapter` seam
- [ ] 🌐 Distributed evolution across nodes
- [ ] 📓 Tutorial notebooks in `/notebooks/`
- [ ] 🔌 Plugin marketplace for community algorithms
- [ ] 🧪 Benchmark suite against standard RL environments and UK AISI Inspect harness integration

---

## 📜 License

**MIT License** — Open source for defense innovation.

## 🙏 Built With Inspiration From

| Project | What ULTRONE borrowed |
|---------|----------------------|
| [ModelScope Ultron](https://github.com/modelscope/modelscope-agent) | Collective intelligence mesh |
| [UltronAgent](https://github.com/Cassian-Vale/Ultra-Agent-Flow) | Self-evolving agent patterns |
| [A-Evolve](https://github.com/A-EVO-Lab/a-evolve) | Genetic algorithm concepts |
| [Agent Zero](https://github.com/frdel/agent-zero) | Autonomous execution |

---

## 📚 Artificial Intelligence in the Military

> A curated reference collection on AI/LLM applications in military and national security contexts.
> Originally compiled by **Dr. Tristan Behrens** — *Military AI* — [LinkedIn](https://www.linkedin.com/in/dr-tristan-behrens-734967a2/)

---

### 🔬 Science

#### 2024.07.03 — [On Large Language Models in National Security Applications](https://arxiv.org/abs/2407.03453)
📄 *W. N. Caballero & P. R. Jenkins — arXiv:2407.03453*

Examines the integration of LLMs like GPT-4 into national security operations, highlighting both opportunities and challenges. LLMs offer substantial benefits for national security organizations, including automating information processing, enhancing data analysis, and improving decision-making efficiency. When coupled with decision-theoretic principles and Bayesian reasoning, these models can facilitate the transition from data to actionable decisions with reduced manpower requirements.

The US Department of Defense is already implementing LLMs in various applications, such as the USAF's use for wargaming and automatic summarization of intelligence reports. However, significant risks accompany these benefits — hallucinations, data privacy concerns, and vulnerability to adversarial attacks are critical challenges, particularly in high-stakes environments where information accuracy is crucial. Recent developments such as China's reported use of LLMs for military purposes (2024 DoD China Report) underscore the geopolitical stakes involved.

#### 2024.02.01 — [COA-GPT: Generative Pre-trained Transformers for Accelerated Course of Action Development in Military Operations](https://arxiv.org/abs/2402.01786)
📄 *V. G. Goecks & N. Waytowich — arXiv:2402.01786 · [IEEE ICMCIS 2024](https://ieeexplore.ieee.org/document/10540749) · [Project videos](https://sites.google.com/view/coa-gpt)*

Introduces **COA-GPT**, an algorithm using LLMs to generate military Courses of Action rapidly and efficiently, incorporating military doctrine and expertise through in-context learning. Commanders input mission information (text and image formats) and receive strategically aligned action plans within seconds, with real-time refinement based on feedback. Evaluated in a militarized version of StarCraft II against reinforcement-learning baselines, COA-GPT generated more strategically sound plans more quickly than alternatives.

#### 2024.10.26 — [Fine-Tuning and Evaluating Open-Source Large Language Models for the Army Domain](https://arxiv.org/abs/2410.20297)
📄 *D. C. Ruiz & J. Sell — arXiv:2410.20297 · featured on [Hugging Face Daily Papers](https://huggingface.co/papers?q=battlefield+applications)*

Explores **TRACLM**, a family of open-source LLMs fine-tuned specifically for US Army applications — addressing the challenge of adapting general-purpose models with Army-specific terminology, doctrine, and operational data. Evaluated on intelligence analysis, report generation, and operational planning tasks, TRACLM demonstrated improved performance over unmodified models in domain-specific language understanding, with particular promise for resource-constrained environments. This work directly informs ULTRONE's LoRA fine-tuning strategy in [`packages/cognition/self_improvement/neural/`](packages/cognition/self_improvement/neural/README.md).

#### 2024.01.29 — [Escalation Risks from Language Models in Military and Diplomatic Decision-Making](https://arxiv.org/abs/2401.03408)
📄 *J.-P. Rivera, G. Mukobi, A. Reuel, M. Lamparth, C. Smith & J. Schneider — arXiv:2401.03408 · published at [FAccT 2024](https://facctconference.org/static/papers24/facct24-57.pdf) ([Stanford HAI policy brief](https://hai.stanford.edu/policy/policy-brief-escalation-risks-llms-military-and-diplomatic-contexts)) · press coverage: [Vice](https://www.vice.com/en/article/ai-launches-nukes-in-worrying-war-simulation-i-just-want-to-have-peace-in-the-world/) · [The Register](https://www.theregister.com/software/2024/02/06/boffins_find_ai_models_tend_to_escalate_conflicts/) · [TechStrongAI](https://techstrong.ai/articles/research-shows-risk-in-using-llms-for-military-decision-making/)*

Investigates the risks of deploying LLMs in military and diplomatic decision-making, focusing on their potential to escalate conflicts unintentionally. Through wargaming simulations with five off-the-shelf LLMs (GPT-4, GPT-3.5, Claude 2, Llama-2-Chat, GPT-4-Base) each controlling autonomous nation agents, most models exhibited bellicose tendencies — recommending aggressive actions over diplomatic ones, developing arms-race dynamics, and in rare cases deploying nuclear weapons ("We have it! Let's use it!"). The authors attribute this to training-data bias and lack of nuanced intent understanding, warning that over-reliance could lead to miscalculation in nuclear or cyber warfare contexts. **This paper motivates ULTRONE's hard separation between simulated and neural capability claims.**

---

### 📰 Media

#### 2025.07.10 — [Department of the Air Force Launches NIPRGPT](https://www.afrc.af.mil/News/Article-Display/Article/3802898/department-of-the-air-force-launches-niprgpt/)
📰 Official DAF announcement · coverage: [Breaking Defense](https://breakingdefense.com/2024/06/department-of-the-air-force-announces-new-generative-ai-program-niprgpt/) · [DefenseScoop — 5-month review](https://defensescoop.com/2024/11/07/air-force-niprgpt-experimental-chatbot-how-things-are-going/) · [Meritalk](https://www.meritalk.com/articles/air-force-launches-new-experimental-genai-chatbot/)

The Department of the Air Force launched **NIPRGPT**, an experimental AI chatbot allowing personnel to use Generative AI on the Non-classified Internet Protocol Router Network. This CAC-enabled tool lets Airmen, Guardians, civilians, and contractors draft correspondence, background papers, and code at no additional cost to units — an "experimental bridge" while commercial tools navigate security parameters. DAF CIO Venice Goodwine emphasized it's time to give personnel tools to develop AI skills; acting chief data & AI officer Chandra Donelson noted that *"technology is learned by doing."* Built on AFRL's Dark Saber software platform in Rome, NY.

#### 2025.03.06 — Revealed: Israeli Military Creating ChatGPT-like Tool Using Palestinian Surveillance Data
📰 *The Guardian* · see also [MIT Technology Review's summary](https://www.technologyreview.com/2025/03/11/1112983/agi-is-suddenly-a-dinner-table-topic/) and [The Guardian's follow-up Unit 8200 investigation](https://www.theguardian.com/world/2025/sep/25/microsoft-blocks-israels-use-of-its-technology-in-mass-surveillance-of-palestinians)

The Guardian revealed that Israel's military intelligence agency, Unit 8200, is developing a ChatGPT-like AI tool trained on approximately **100 billion words** of intercepted Palestinian communications to understand colloquial Arabic dialects rather than formal written Arabic. Development accelerated after October 2023, benefiting from reservists with AI expertise from major tech companies. Human rights organizations warn these systems can amplify biases and produce errors with severe consequences — raising important questions about surveillance ethics and consequential-error risk in military AI applications.

#### 2024.11.04 — [Meta AI is Ready for War](https://www.theverge.com/2024/11/4/24287951/meta-ai-llama-war-us-government-national-security)
📰 *The Verge* (by Emma Roth) · official Meta announcement: [Open Source AI Can Help America Lead in AI and Strengthen Global Security](https://about.fb.com/news/2024/11/open-source-ai-america-global-security/) · coverage: [TechCrunch](https://techcrunch.com/2024/11/04/meta-says-its-making-its-llama-models-available-for-us-national-security-applications/)

Meta announced it would allow US government agencies and military contractors to use its open-source Llama model for national security applications, reversing its acceptable-use restriction against using Llama 3 for "military, warfare, nuclear industries or applications, espionage." Partners include Amazon, Microsoft, IBM, Lockheed Martin, Oracle, and others. Oracle uses Llama to help aircraft technicians synthesize repair documents; Lockheed Martin uses it for code generation and data analysis. This followed reports that Chinese researchers used Meta's earlier Llama 2 to build a defense chatbot ([Reuters via TechCrunch](https://techcrunch.com/2024/11/01/chinese-military-researchers-used-metas-ai-to-develop-a-defense-chatbot/)). Meta framed the shift as being *"in both America and the wider democratic world's interest."*

#### 2024.11.05 — [Scale AI Unveils 'Defense Llama' Large Language Model for National Security Users](https://scale.com/blog/defense-llama)
📰 Official Scale AI announcement · coverage: [ExecutiveBiz](https://www.executivebiz.com/articles/scale-ai-meta-defense-llama-large-language-model)

Scale AI introduced **Defense Llama** — a specialized LLM built on Meta's Llama 3 and fine-tuned with Scale's Data Engine for national security missions like planning military or intelligence operations and assessing adversary vulnerabilities. Available exclusively in controlled US government environments within [Scale Donovan](https://scale.com/donovan), it was trained on military doctrine, international humanitarian law, and DoD-aligned policy data, with responses adhering to ODNI style guidelines. A critical reference point for ULTRONE's own fine-tune-on-domain-data approach.

#### 2024.02.20 — Pentagon Explores Military Uses of Emerging AI Technologies
📰 *The Washington Post* (paywalled) · related public reporting: [OECD.AI incident record](https://oecd.ai/en/incidents/2024-11-04-19e5)

The Washington Post reported that the Pentagon is actively exploring LLMs for military applications, including intelligence summarization and training simulations. At a 2024 conference, defense officials discussed integrating models from OpenAI and Anthropic to enhance operational efficiency — specific use cases included automating analysis of intercepted communications and generating realistic wargaming scenarios — while raising concerns about hallucination susceptibility in critical missions.

---

### ⚠️ Disclaimer

The information presented here offers a neutral representation of artificial intelligence applications in military contexts based on publicly available sources. This document does not advocate for or against the use of AI in military operations, nor does it endorse specific AI military technologies, policies, or strategies of any nation.

The summaries are intended solely for informational and educational purposes. Readers should note that military applications of AI raise complex questions regarding international humanitarian law, ethics, accountability, privacy rights, and potential risks — different stakeholders hold varying perspectives on these issues. This document does not represent the official position of any government, military organization, or technology company mentioned. Developments evolve rapidly and information may change as technologies and policies advance.

---

## 🚀 Deployment (free)

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**: GitHub Actions runs the test suite and benchmarks; a slim **simulation-only** Hugging Face Space demo (`infra/deploy/hf_space/`) syncs automatically on push. Setup steps, verified ZeroGPU quotas, and the public-safety scoping are documented there.

## 🧠 Neural Milestone Docs

Deep dive into the simulated-vs-neural capability split, LoRA trainer contract, dataset splitting and benchmark design → [`packages/cognition/self_improvement/neural/README.md`](packages/cognition/self_improvement/neural/README.md).

---

<div align="center">

###  ULTRONE — _Decide faster. Adapt harder. Outlast everything._ 

</div>
