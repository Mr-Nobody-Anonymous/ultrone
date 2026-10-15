# ULTRONE Master Architecture Specification

## 1. Executive Overview

ULTRONE is an open, production-grade autonomous defense and multi-agent battlefield AI research platform. It unifies decentralized multi-domain command and control, resilient tactical edge networking, multi-objective sensor-to-effector kill chain allocation, formal rules-of-engagement verification, and real-time adversarial wargaming into a coherent, modular monorepo.

---

## 2. Monorepo Plane Topology & Code Layout

ULTRONE is organized as a semantic monorepo structured into 14 distinct functional buckets, guaranteeing clear domain boundaries while maintaining full backward-compatible Python import semantics via `_ultrone_paths.py`.

```
ultrone/
├── apps/                               # Operational Applications & User Surfaces (8 Apps)
│   ├── api/                            # FastAPI REST & WebSocket server (routers: cockpit, defense, chat, neural)
│   ├── backend/                        # Research platform REST API service (v1, vision, exporters)
│   ├── console/                        # Interactive operator REPL & terminal utilities
│   ├── dashboard/                      # Real-time metrics and operations dashboard
│   ├── frontend/                       # Tactical Autonomy Cockpit UI (React 18, Vite, Tailwind CSS, Playwright E2E)
│   ├── globe/                          # 3D geospatial / Cesium tactical visualization app
│   ├── simulator/                      # Discrete-event tactical environment simulator
│   └── ultrone/                        # CLI orchestrator & command-line interface
│
├── packages/                           # Modular Platform Packages (10 Core Packages)
│   ├── core/                           # Foundation contracts, config, logging, and 5-Domain Defense Ontology
│   ├── runtime/                        # Distributed State, DDIL CRDT World Mesh, Byzantine Filter, Event Sourcing
│   ├── safety/                         # Formal Machine-Checked ROE & LOAC Verifier, EffectorLease, HOTL Veto
│   ├── cognition/                      # Pareto Kill Chain Allocator, Cognitive EW, AlphaWarfare MCTS, Self-Improvement
│   ├── geospatial/                     # Coordinate transformations, spherical geometry, MGRS, terrain analysis
│   ├── investigation/                  # Multi-modal intelligence investigation & timeline reconstruction
│   ├── research/                       # Scientific literature analysis, hypothesis generation, and benchmarking
│   ├── workflows/                      # Orchestration DAGs, LangGraph stategraphs, and tactical execution plans
│   ├── adapters/                       # Integration seams (LLM, vision, vector DB, sensor hardware)
│   └── simulation/                     # Kinetic equations, physics models, radar cross-section profiles
│
├── infra/                              # Deployment & infrastructure manifests (Docker, Helm, Kubernetes, HF Space)
├── tests/                              # Comprehensive test suites (defense superiority, cockpit, conformance, evals)
├── docs/                               # Master architecture, invariants, deployment guides, and analysis
└── vendor/                             # Vendored libraries (original_source/, ultron/ shim, adelise/)
```

### Import Bootstrap Contract (`_ultrone_paths.py`)
All top-level entrypoints invoke `_ultrone_paths.ensure_on_syspath()`, which inspects repository root and systematically adds all 14 buckets to `sys.path`. This guarantees that legacy module import syntax (`from packages.core.ontology import ...` or `import brain`) resolves deterministically across development, CI workflows, and container runtimes without module collisions or stdlib shadowing.

---

## 3. Seven Defense Superiority Capabilities

ULTRONE is engineered to decisively leap beyond legacy defense AI platforms (Palantir Gotham/Foundry/AIP and Anduril Lattice OS/Menace) across seven key capabilities:

### Pillar 1: 5-Domain Defense Ontology & Multi-INT MHT
- **Location**: `packages/core/ontology/defense_ontology.py`
- **Key Types**: `WarfightingDomain`, `MultiHypothesisTracker`, `MultiIntTrack`, `TrackObservation`, `Affiliation`, `SensorModality`, `KinematicState`
- **Architecture**: Unifies five operational domains (`SPACE`, `AIR`, `LAND`, `MARITIME_SURFACE`/`MARITIME_SUBSURFACE`, `CYBER`/`ELECTROMAGNETIC_SPECTRUM`) across six sensor modalities (`RADAR`, `EO_IR`, `SIGINT`, `ACOUSTIC`, `CYBER_TELEMETRY`, `SATELLITE_IMAGERY`).
- **Mathematical Invariants**:
  - Gated track association using Mahalanobis Chi-Square spatial gating:
    $$d^2 = (\mathbf{z} - \hat{\mathbf{z}})^T \mathbf{S}^{-1} (\mathbf{z} - \hat{\mathbf{z}}) < \gamma$$
  - Multi-hypothesis track branching and Bayesian log-likelihood ratio scoring.
  - Spherical Haversine kinematics with antipodal cosine safety clamping avoiding math domain errors.
  - Track confirmation requiring $\ge 3$ corroborated hits and pruning handling zero-time initializations.

### Pillar 2: Decentralized Tactical World Mesh (DDIL CRDT)
- **Location**: `packages/runtime/crdt_mesh/` (`world_mesh.py`, `byzantine_filter.py`, `models.py`)
- **Key Types**: `DecentralizedWorldMesh`, `ByzantinePhysicalFilter`, `CRDTEntityState`, `SyncDelta`, `VectorClock`
- **Architecture**: Peer-to-peer conflict-free replicated data type (CRDT) engine operating over Disconnected, Disrupted, Intermittent, and Limited bandwidth (DDIL) tactical networks with zero cloud reachback.
- **Mathematical Invariants**:
  - Last-Write-Wins (LWW) element set reconciliation with SHA-256 state hash tie-breaking.
  - Causal Vector Clocks tracking partial-order event causality.
  - Byzantine Physical Filter rejecting impossible kinematic transitions: instantaneous teleportation ($v > 3000\text{ kts}$), zero-time multi-location ($dt = 0, dx > 0$), and coordinate domain bounds.
  - Full support for 180° antimeridian crossing and polar coordinate wraps.

### Pillar 3: Dynamic Multi-Objective Pareto Kill Chain Allocator
- **Location**: `packages/cognition/kill_chain/` (`allocator.py`, `models.py`)
- **Key Types**: `SensorToEffectorAllocator`, `EffectorAsset`, `EffectorType`, `KillChainStage`, `TargetTrack`
- **Architecture**: Real-time sensor-to-effector matching engine spanning the complete F2T2EA (Find, Fix, Track, Target, Engage, Assess) targeting cycle.
- **Mathematical Invariants**:
  - Multi-objective Pareto optimization scoring:
    $$\text{Score} = w_1 \cdot P_k + w_2 \cdot (1 - \text{TTI\_norm}) + w_3 \cdot (1 - \text{CDE}) + w_4 \cdot \text{CostEfficiency}$$
  - Soft-kill prioritization: Non-kinetic effectors (`SOFT_RF_JAMMER`, `SOFT_CYBER_PAYLOAD`) prioritized when collateral damage or cost asymmetry dictates.
  - Automatic fallback to soft-kill assets when kinetic options are denied by Rules of Engagement.
  - Weapon exhaustion enforcement capping simultaneous engagements at asset inventory capacity.

### Pillar 4: Formal Machine-Checked Rules of Engagement (ROE) & LOAC Verifier
- **Location**: `packages/safety/roe/` (`rules_of_engagement.py`, `models.py`)
- **Key Types**: `RulesOfEngagementEngine`, `EffectorLease`, `EngagementRequest`, `EngagementVerdict`, `GeofencePolygon`
- **Architecture**: Temporal logic verification engine providing formal, machine-checked compliance with the Law of Armed Conflict (LOAC) and mission-specific Rules of Engagement.
- **Mathematical Invariants**:
  - LOAC Distinction Gate: Requires Positive Identification (PID) confidence $\ge \tau_{distinction}$ ($0.85$ for kinetic, $0.55$ for soft-kill).
  - LOAC Proportionality Gate: Requires Collateral Damage Estimate (CDE) $\le \tau_{proportionality}$.
  - 3D No-Strike List (NSL) Geofencing: Non-convex polygon ray-casting with vertical altitude envelopes.
  - Fratricide Protection: Strictly vetos engagements targeting `Affiliation.ASSUMED_FRIEND` or ghost tracks.
  - Time-bounded, cryptographically signed `EffectorLease` tokens (HMAC-SHA256) with millisecond TTL and Human-on-the-Loop (HOTL) instant revocation.

### Pillar 5: Cognitive Electronic Warfare (EW) & Multi-Layer Anti-Spoofing
- **Location**: `packages/cognition/electronic_warfare/` (`anti_spoofing.py`, `models.py`)
- **Key Types**: `CognitiveAntiSpoofEngine`, `GpsTelemetry`, `EmconState`, `SpoofVerdict`, `TrackConfidence`
- **Architecture**: Cognitive multi-spectral sensor fusion detecting GPS spoofing, signal replay, and adversarial deception decoys.
- **Mathematical Invariants**:
  - Kinematic GPS/INS cross-check detecting satellite dropouts, impossible velocity steps, and timestamp inversions ($dt < 0$).
  - Multi-spectral cross-correlation: Compares radar Radar Cross Section (RCS) against FLIR thermal temperature differentials ($\Delta T = T_{target} - T_{ambient}$) to reject passive corner reflectors and wind-drifting balloon decoys.
  - Autonomous EMCON scheduler managing emission postures (`EMCON_1_SILENT`, `EMCON_2_RESTRICTED`, `EMCON_3_TACTICAL`).

### Pillar 6: Predictive Adversarial Wargaming (AlphaWarfare MCTS)
- **Location**: `packages/cognition/adversarial_wargame/` (`predictive_wargame.py`, `models.py`)
- **Key Types**: `PredictiveWargameEngine`, `BattlefieldState`, `UnitState`, `TacticalActionType`
- **Architecture**: Real-time forward Monte Carlo Tree Search (MCTS) anticipating Red Force multi-ply counter-maneuvers.
- **Mathematical Invariants**:
  - Evaluates branching tactical Courses of Action (`DEFENSIVE_SCREEN`, `FEINT_DECEPTION`, `FLANKING_MANEUVER`, etc.).
  - Numerically stable bounded sigmoid payoff function avoiding arithmetic overflow on extreme values:
    $$S(\Delta) = \frac{1}{1 + e^{-\Delta / 1000}}$$
  - Computes predicted win-rate deltas and outputs prioritized Blue Force tactical recommendations.

### Pillar 7: Cockpit REST Defense API Subsystem
- **Location**: `apps/api/routers/cockpit.py`
- **Key Endpoints**:
  - `GET /api/cockpit/defense/cop` — Real-time Common Operational Picture tracks, domain distributions, and HVA threats.
  - `GET /api/cockpit/defense/mesh` — CRDT mesh node status, vector clocks, and quarantined entities.
  - `GET /api/cockpit/defense/kill-chain` — Active sensor-to-effector engagement plans and weapon inventory status.
  - `GET /api/cockpit/defense/roe` — Active effector leases, No-Strike List polygons, and LOAC audit logs.
  - `POST /api/cockpit/defense/roe/veto` — Operator Human-on-the-Loop instant lease revocation.
  - `GET /api/cockpit/defense/anti-spoofing` — GPS integrity telemetry, decoy detection flags, and EMCON status.
  - `GET /api/cockpit/defense/wargame` — AlphaWarfare MCTS tactical recommendations and predicted win-rate deltas.
  - `GET /api/cockpit/overview` — High-level operational readiness and defense posture summary.

---

## 4. Autonomy Research Cockpit Subsystem

The Tactical Autonomy Cockpit (`apps/frontend/`) is a high-performance React 18 single-page application built with TypeScript, Vite, Tailwind CSS, Lucide icons, and MapLibre/Deck.gl/Three.js visualization components.

### Dual-Mode Architecture:
1. **Live Operational Mode**: Connects directly to the FastAPI REST and WebSocket services in `apps/api/`.
2. **Deterministic Test / Mock Mode (`ULTRONE_MOCK_BACKEND=1`)**: Vite dev-server middleware (`apps/frontend/e2e/mock-backend.ts`) provides full mock responses and fault-injection switches for headless, serial Playwright E2E browser testing without requiring the Python runtime.

### Test Harness Idempotency:
The scenario reset endpoint `/__test__/scenario` automatically resets `runtime.playing = false` and clears alert overrides, ensuring 100% idempotent, reproducible Playwright runs across all test suites.

---

## 5. Formal Safety Invariant Enclave

ULTRONE enforces a machine-checkable safety invariant registry spanning both core autonomy and defense operations:

| Invariant ID | Severity | Contract Name | Verification Mechanism |
| :--- | :--- | :--- | :--- |
| **`SAF-001`** | Critical | Causal Boundary Integrity | `CausalBoundaryValidator` rejects post-action outcome fields in pre-action contexts |
| **`SAF-002`** | Critical | Lease Expiration Gate | `CapabilityLease` verification prevents execution of expired tokens |
| **`SAF-003`** | High | Telemetry Freshness Horizon | `TelemetryStreamBuffer` blocks decisions when telemetry exceeds freshness threshold |
| **`SAF-004`** | Critical | Emergency Stop Terminal State | `DeviceStateMachine` guarantees emergency stop requires formal operator reset |
| **`SAF-005`** | Critical | Actuation Capability Binding | `PhysicalHardwareDriver` requires cryptographically verified actuation leases |
| **`DEF-001`** | Critical | LOAC Distinction | ROE engine strictly blocks kinetic weapons if PID confidence $< \tau_{kinetic}$ |
| **`DEF-002`** | Critical | LOAC Proportionality | ROE engine strictly vetos engagement if predicted CDE exceeds collateral threshold |
| **`DEF-003`** | Critical | No-Strike List Geofence | 3D polygonal ray-casting blocks strike assets within protected volumes |
| **`DEF-004`** | Critical | Fratricide Protection | Strict veto on friendly, neutral, or ghost-track targeting |
| **`DEF-005`** | High | Byzantine CRDT Plausibility | Physical filter quarantines non-physical teleportation or simultaneous multi-location |

---

## 6. Verification Pipeline & Acceptance Standards

Every change to the ULTRONE platform must satisfy the five-stage verification pipeline:

1. **Defense & Cockpit Tests**:
   ```bash
   python -m pytest tests/test_defense_superiority.py tests/test_cockpit_api.py -q
   ```
   *Standard: 45 passed (33 defense + 12 cockpit API), 0 failed.*

2. **Monorepo Architecture Invariant Validator**:
   ```bash
   python _validate_reorg.py
   ```
   *Standard: 58 imports OK, 14 buckets checked, 0 failures.*

3. **Frontend Static Typecheck**:
   ```bash
   cd apps/frontend && npm run typecheck
   ```
   *Standard: tsc --noEmit exits with code 0.*

4. **Playwright E2E Browser Test Suite**:
   ```bash
   cd apps/frontend && npx playwright test --workers=1
   ```
   *Standard: 25 passed in serial mode (1 worker).*

5. **Git Ancestry & Clean Tree Integrity**:
   ```bash
   git merge-base --is-ancestor 7036e8fd61e887243d38001086d5bd0568391033 main
   ```
   *Standard: Exit code 0, working tree clean, synced to origin/main.*
