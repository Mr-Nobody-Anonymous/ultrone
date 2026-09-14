# Ultrone — Repository Structure

This repository is a **multi-project monorepo**. It contains the Ultrone
battlefield-AI research platform plus two vendored projects that are
integrated into it.

## Projects in this monorepo

| Path | Project | Role |
|------|---------|------|
| `apps/`, `packages/`, `adapters/`, `simulation/`, `research/`, `tests/`, `scripts/`, `docs/`, `infra/` | **Ultrone** | Multi-domain battlefield AI research platform (the tracked core of this repo) |
| `vendor/original_source/`, `vendor/ultron/` | **Ultron** (ModelScope) | Collective-memory system for AI agents, vendored |
| `vendor/adelise-agent-framework-main/` | **Adelise / bee-agent-framework** | TypeScript agent framework, vendored for reference |

## Architecture

```
                 ┌─────────────────────────┐
                 │       ULTRONE UI         │
                 │   Operational Console    │
                 └────────────┬────────────┘
                              │
                       API / WebSocket
                              │
                 ┌────────────▼────────────┐
                 │    ULTRONE PLATFORM      │
                 │                         │
                 │  Orchestrator           │
                 │  World Model            │
                 │  Perception             │
                 │  Reasoning              │
                 │  Planning               │
                 │  Memory / Knowledge     │
                 │  Agent Runtime           │
                 └────────────┬────────────┘
                              │
            ┌─────────────────┼──────────────────┐
            │                 │                  │
       Simulation         Data/Events         AI Models
       & Digital Twin     Telemetry            Providers
```

## Top-level layout

```
ultrone/
│
├── apps/                      # Application layer
│   ├── api/                   # FastAPI public API
│   ├── backend/               # Backend services (auth, cache, events, workers, ...)
│   ├── cli/                   # CLI client
│   ├── console/               # ★ Operational Console (React/TypeScript/MapLibre/Deck.gl)
│   ├── dashboard/             # Monitoring dashboard
│   ├── frontend/              # Original web frontend (React/Vite)
│   ├── services/              # Background services (ingestion, training, harness, ...)
│   ├── simulator/             # Simulation UI/API
│   └── ultrone_hitl/          # Human-in-the-loop workflow
│
├── packages/                  # Core platform packages
│   ├── core/                  # Core domain types
│   │   ├── config/            # Doctrine presets, settings
│   │   ├── core/              # Pipeline, DB, storage, models, safety_gate, LLM service
│   │   ├── datasets/          # Dataset management (download, augment, validate, version)
│   │   ├── entities/          # ★ Canonical Entity type (entity_id, position, provenance, ...)
│   │   ├── events/            # ★ Canonical Event system (EventType, Event, EventBus)
│   │   ├── extension_log/     # Audit and extension stores
│   │   ├── ultrone_types/     # ★ Shared enums, type aliases, protocols
│   │   ├── utils/             # Utilities (geo, helpers, intent, LLM orchestrator, sanitizer, ...)
│   │   ├── world/             # ★ World module re-export (bridges world_model + entities + events)
│   │   └── world_model/       # World model implementation
│   │
│   ├── cognition/             # Cognitive architecture
│   │   ├── adaptive/          # Adaptive parameter optimization, promotion
│   │   ├── brain/             # Orchestrator + perception, reasoning, learning, memory, XAI
│   │   ├── cognitive/         # ★ 15-layer cognitive architecture (crown jewel)
│   │   ├── evolution/         # Genome evolution protocol
│   │   ├── frontier/          # Frontier reasoning, adaptation, agents, decision
│   │   ├── game_ai/           # Game AI arena, commander
│   │   ├── generative/        # Scenario/briefing generation
│   │   ├── sandbox/           # Evaluation sandbox, UCL, machines
│   │   ├── self_improvement/  # Self-improvement loop, neural, self-training
│   │   └── ultrone_ai/        # Code intelligence, reasoning
│   │
│   ├── agents/                # Agent runtime
│   │   ├── agents/            # Multi-domain agents (air, land, sea, space, cyber, ...)
│   │   ├── ai_architectures/  # BDI, behavior tree, FSM, GOAP, utility AI
│   │   ├── coding_agent/      # AST analysis, repository indexing, bug localization
│   │   ├── plugin_sdk/        # Plugin development SDK
│   │   ├── plugins/           # Installed plugins
│   │   ├── robotics/          # Robot interface/controller
│   │   └── skills/            # Agent skills
│   │
│   ├── orchestration/         # Model/tool/memory routing
│   │   └── orchestration/     # Router, task classifier, model/tool/memory/skill routers, traces
│   │
│   ├── knowledge/             # Knowledge & memory
│   │   ├── automl/            # AutoML experiments
│   │   ├── knowledge_engine/  # KG, RAG, ontology, memory_manager, vector_memory
│   │   ├── learning/          # Continual learning, feedback
│   │   ├── memory_cluster/    # Redis/DuckDB memory backends
│   │   ├── mlops/             # ML operations
│   │   └── training_platform/ # Training infrastructure
│   │
│   ├── simulation/            # ★ Simulation package (bridges root simulation/)
│   │   ├── entities/          # Simulated entity management
│   │   ├── environments/      # Environment definitions
│   │   ├── physics/           # Physics engine
│   │   ├── scenarios/         # Scenario configurations
│   │   ├── sensors/           # Sensor models
│   │   └── world/             # Simulation world state
│   │
│   ├── safety/                # Safety & security
│   │   ├── constraints/       # ★ Constraint definitions (geofence, authority, rate limits)
│   │   ├── policy/            # ★ Policy enforcement (escalation, autonomy bounds)
│   │   └── security/          # Security controls
│   │
│   ├── observability/         # Observability
│   │   ├── events/            # ★ Event bus observability layer
│   │   ├── logging/           # ★ Structured JSON logging
│   │   ├── metrics/           # ★ Prometheus-compatible metrics
│   │   ├── tracing/           # ★ OpenTelemetry distributed tracing
│   │   └── viz/               # Visualization
│   │
│   ├── runtime/               # OS-level runtime
│   │   ├── compiler/          # ULTRONE compiler
│   │   ├── cpp/               # C++ runtime
│   │   ├── go/                # Go runtime
│   │   ├── hardware/          # Hardware abstraction
│   │   ├── rust/              # Rust runtime
│   │   ├── runtime/           # Core runtime
│   │   ├── ultrone_bindings/  # Language bindings
│   │   ├── ultrone_os/        # ULTRONE OS (kernel, scheduler, service_registry)
│   │   └── ultrone_rt/        # ULTRONE real-time runtime
│   │
│   └── transport/             # Communication
│       └── comms/             # Communication protocols and message routing
│
├── adapters/                  # External integrations
│   ├── database/              # Database adapters
│   ├── external/              # External service adapters
│   ├── llm/                   # LLM provider adapters
│   ├── vector_db/             # Vector database adapters
│   └── vision/                # Vision model adapters
│
├── simulation/                # Root-level simulation engine
│   ├── core.py                # SimulationCore
│   ├── world.py               # SimulationWorld
│   ├── runner.py              # SimulationRunner
│   ├── physics.py             # PhysicsEngine
│   ├── digital_twin.py        # DigitalTwin
│   ├── comms_logistics.py     # Communications logistics
│   ├── environment_generator.py
│   └── sim/                   # Simulation sub-module
│
├── research/                  # Research platform
│   ├── benchmarks/            # Benchmark suites
│   ├── reports/               # Generated reports
│   ├── research_db/           # Research database
│   └── research_division/     # Research division modules
│
├── infra/                     # Infrastructure
│   ├── deploy/                # Deployment scripts
│   ├── docker/                # Docker configurations
│   ├── helm/                  # Helm charts
│   ├── kubernetes/            # Kubernetes manifests
│   ├── monitoring/            # Monitoring configs
│   ├── nginx/                 # Nginx configs
│   ├── observability/         # ★ Prometheus + Grafana + OTEL stack
│   ├── postgres/              # ★ PostgreSQL schema, migrations, init scripts
│   ├── redis/                 # ★ Redis configuration
│   └── security/              # ★ Auth/RBAC infrastructure
│
├── tests/                     # Test suites
│   ├── api/                   # API tests
│   ├── cli/                   # CLI tests
│   ├── core/                  # Core tests
│   ├── e2e/                   # ★ End-to-end tests
│   ├── integration/           # ★ Integration tests
│   ├── performance/           # ★ Performance/benchmark tests
│   ├── reproducibility/       # ★ Reproducibility tests
│   ├── services/              # Services tests
│   ├── unit/                  # ★ Unit tests
│   ├── utils/                 # Utility tests
│   └── test_*.py              # Existing flat test files (96+)
│
├── vendor/                    # Vendored third-party projects
│   ├── adelise-agent-framework-main/
│   ├── original_source/       # Ultron canonical source
│   └── ultron/                # Ultron compatibility shim
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE_EXTENSION_PLAN.md
│   ├── ARCHITECTURE_INVARIANTS.md
│   ├── AUTONOMOUS_RESEARCH_ARCHITECTURE.md
│   ├── COGNITIVE_ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   ├── FOLDER_STRUCTURE_ANALYSIS.md  ← this file
│   ├── FRONTIER_INTELLIGENCE.md
│   ├── PROGRAMMING_LANGUAGE_POLICY.md
│   ├── PROJECT_PROGRESS.md
│   ├── REPO_AUDIT_AND_ROADMAP.md
│   ├── RESEARCH_DB_EVALUATION.md
│   ├── RESEARCH_PLATFORM_ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── SITUATIONAL_AWARENESS.md
│   ├── TODO.md
│   ├── ULTRONE_ARCHITECTURE_REVIEW.md
│   ├── ULTRONE_MONOREPO_REORG.md
│   ├── assets/
│   └── ultron/                # Ultron docsify site
│
├── scripts/                   # Utility scripts
│   ├── validation/            # ★ Repository validation
│   ├── audit_warnings.py
│   ├── quick_test.py
│   ├── run_bda_predictive_kc.py
│   ├── run_neural_milestone.py
│   └── test_*.py              # Test/validation scripts
│
├── data/                      # Runtime data (gitignored)
├── checkpoints/               # Model checkpoints
├── datasets_cache/            # Cached datasets
├── exports/                   # Exported artifacts
│
├── __init__.py                # Root package init
├── config.yaml                # Simulation YAML config
├── pyproject.toml             # Python packaging
├── package.json               # Node.js (frontend toolchain)
├── docker-compose.yml         # ★ Development stack (postgres, redis, api)
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
├── LICENSE                    # MIT
├── README.md                  # Main documentation
├── CHANGELOG.md               # Release changelog
├── CONTRIBUTING.md            # Contributing guide
├── SECURITY.md                # Security policy
├── CODE_OF_CONDUCT.md         # Code of conduct
└── CITATION.cff               # Citation metadata
```

★ = newly created during the monorepo reorganization

## How the Ultron integration works

The Ultron sources live in `vendor/original_source/` (a complete, pristine copy of
the Ultron package). Ultron's modules import each other by the absolute
package name `ultron.*`. The `vendor/ultron/` directory is a
small compatibility package that points `ultron.*` imports at
`original_source/` — no code is duplicated:

```python
import ultron                      # -> vendor/ultron/__init__.py (shim)
from ultron.api.sdk import Ultron  # -> vendor/original_source/api/sdk/ultron.py
```

## Canonical World Model

Everything talks to one world model through `packages/core/`:

```
                 WORLD MODEL
                     │
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   Entities        Events        State
       │             │             │
       ├─────────────┼─────────────┤
       │             │             │
   perception    simulation     external data
       │             │             │
       └─────────────┼─────────────┘
                     ↓
                  cognition
```

**Entity** (`packages/core/entities/`):
```python
Entity(entity_id="entity_001", type="air_asset", status=EntityStatus.ACTIVE,
       confidence=0.87, provenance=["sensor_fusion_v2", "radar-01"])
```

**Event** (`packages/core/events/`):
```python
Event(type=EventType.ENTITY_UPDATED, entity_id="entity_001",
      changes={"status": "active"}, confidence=0.91)
```

## Operational Console

The primary UI (`apps/console/`) follows the Palantir/Anduril operational model:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ULTRONE    WORKSPACE: ALPHA     ● SYSTEM OK     ● STREAMING     12:42:31    │
├───────┬──────────────────────────────────────────────────────────────┬───────┤
│       │                                                              │       │
│ Side  │                    WORLD VIEW                                │ Entity│
│ bar   │           map / 3D / graph / timeline                       │ Detail│
│       │                                                              │       │
│       ├──────────────────────────────────────────────────────────────┤       │
│       │  EVENT TIMELINE                                               │       │
├───────┴──────────────────────────────────────────────────────────────┴───────┤
│ CMD / SEARCH / ASK ULTRONE                                         ◉ ONLINE │
└──────────────────────────────────────────────────────────────────────────────┘
```

Tech stack: React + TypeScript + Vite + Zustand + TanStack Query + MapLibre + Deck.gl + Three.js

## Self-evolution infrastructure (`packages/cognition/evolution/`)

```
evolution/
├── genome.py               # Genome Evolution Protocol: Gene, Capsule, Genome, GenomeEngine
├── performance_telemetry.py # TelemetryEvent, TelemetryMetrics, PerformanceTelemetry
├── evolution_lab.py        # EvolutionConfig, EvolutionLab (telemetry -> genome -> evolve)
└── agent_evolver.py       # AgentPersonality, AgentEvolver (specialized sub-agents)
```

Flow: agent action → `PerformanceTelemetry` (fitness = success_rate × 0.7 +
time_score × 0.3) → `GenomeEngine` (mutate → crossover → select → deploy) →
updated `Genome` per sub-agent personality.

## CI / deployment

- `.github/workflows/research-platform-ci.yml` — pytest matrix on Python
  3.10 / 3.11 / 3.12.
- `.github/workflows/canonical-benchmark.yml` — canonical benchmark suite.
- `.github/workflows/deploy-hf-space.yml` — deploys the simulation-only
  Gradio demo to a Hugging Face Space.
