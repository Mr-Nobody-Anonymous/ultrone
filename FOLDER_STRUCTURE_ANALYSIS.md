# Ultrone — Repository Structure

This repository is a **multi-project monorepo**. It contains the Ultrone
battlefield-AI research platform plus two vendored projects that are
integrated into it.

## Projects in this monorepo

| Path | Project | Role |
|------|---------|------|
| `brain/`, `agents/`, `sim/`, `cognitive/`, `frontier/`, `research*/`, `self_improvement/`, `knowledge_engine/`, `backend/`, `frontend/`, `comms/`, `config/`, `core/`, `utils/`, `data/`, `benchmarks/`, `tests/` (ULTRONE suites), … | **Ultrone** | Multi-domain battlefield AI research platform (the tracked core of this repo) |
| `original_source/`, `ultron/`, `api/`, `cli/`, `services/`, `dashboard/`, `skills/`, `examples/`, `evolution/`, `adaptive/`, `server.py`, `server_state.py`, `ultrone.py`, `ultron_client.py`, `memory_sync.py`, `tests/api|cli|core|services|utils` | **Ultron** (ModelScope) | Collective-memory system for AI agents (Trajectory / Memory / Skill / Harness hubs), merged in and wired to Ultrone's evolution track |
| `adelise-agent-framework-main/`, `docs/framework/` | **Adelise / bee-agent-framework** | TypeScript agent framework, vendored for reference |

## How the Ultron integration works

The Ultron sources live in `original_source/` (a complete, pristine copy of
the Ultron package). Ultron's modules import each other by the absolute
package name `ultron.*`. The `ultron/` directory at the repository root is a
small compatibility package that points `ultron.*` imports at
`original_source/` — no code is duplicated:

```python
import ultron                      # -> ultron/__init__.py (shim)
from ultron.api.sdk import Ultron  # -> original_source/api/sdk/ultron.py
```

The root-level `api/`, `cli/`, `services/`, `dashboard/` directories and the
Ultron files inside `core/` and `utils/` are the working copies of the same
sources (kept for direct editing); `original_source/` remains the canonical
import target.

## Root-level files

```
ultrone/
├── main.py                  # Battlefield simulation entry point
├── ultrone.py               # Ultrone agent class with integrated self-evolution
├── server.py                # Ultron FastAPI server entry point
├── server_state.py          # Ultron process-wide singletons
├── ultron_client.py         # Stdlib-only HTTP client for the Ultron API
├── memory_sync.py           # Stdlib-only memory-sync client
├── config.yaml              # Battlefield simulation YAML config
├── pyproject.toml           # Python packaging (setuptools)
├── requirements.txt         # Python dependencies
├── package.json             # Minimal Node deps for the frontend toolchain
├── LICENSE                  # MIT
├── README.md                # Main documentation
├── CHANGELOG.md             # Release changelog
├── ROADMAP.md               # Roadmap
├── CONTRIBUTING.md          # Contributing guide
├── SECURITY.md              # Security policy
├── CODE_OF_CONDUCT.md       # Code of conduct
├── CITATION.cff             # Citation metadata
├── DEPLOYMENT.md            # Deployment guide (CI + Hugging Face Space)
├── ARCHITECTURE_EXTENSION_PLAN.md, TODO.md, PROJECT_PROGRESS.md
└── ULTRONE_ARCHITECTURE_REVIEW.md     # Architecture review notes
```

## Documentation layout

```
docs/
├── ARCHITECTURE_INVARIANTS.md          # Ultrone safety/architecture rules
├── AUTONOMOUS_RESEARCH_ARCHITECTURE.md # Research-platform extension summary
├── COGNITIVE_ARCHITECTURE.md           # 15-layer cognitive architecture
├── FRONTIER_INTELLIGENCE.md            # Frontier intelligence modules
├── PROGRAMMING_LANGUAGE_POLICY.md      # Language policy
├── REPO_AUDIT_AND_ROADMAP.md           # Internal audit + sprint roadmap
├── RESEARCH_DB_EVALUATION.md          # Persistence backend evaluation
├── RESEARCH_PLATFORM_ARCHITECTURE.md   # Research platform architecture
├── SITUATIONAL_AWARENESS.md            # Situational awareness subsystem
├── framework/                          # Adelise agent framework docs (vendored)
└── ultron/                             # Ultron docsify site (en/ + zh/)
```

## Self-evolution infrastructure (`evolution/`)

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
