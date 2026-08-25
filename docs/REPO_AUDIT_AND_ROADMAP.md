# ULTRONE — Module-by-Module Audit & P0/P1/P2 Roadmap

> **Status of this document:** current as of inspection of the working tree,
> not the README. Several findings in a prior external review are now stale;
> this audit corrects them against the actual code.

**Evidence base (verified in the tree):**
- `core/` (contracts, pipeline, safety_gate) — implemented, integration test
  `tests/test_core_pipeline.py` = **14 passed**.
- Unit counts are live counts of `.py` files/bytes per top-level directory.
- `PROJECT_PROGRESS.md` is **stale** (see §3 below).
- **Sprint A completed (post-audit):** backend identity decided (vendored
  "Argus" → **isolate**); clean `ultrone_hitl/` HITL API + tamper-evident
  audit store built; repo hygiene done; full test suite green.

---

## 1. Executive summary

The single biggest conclusion from the pasted review — *"no evidence of an
integrated end-to-end system"* — is **no longer true**. A canonical vertical
slice now exists and is tested:

```
BattlefieldEnv obs -> SensorSuite (noise/dropout)
  -> SensorFusion -> WorldEstimate (belief, not truth)
  -> EvolutionaryCOAGenerator -> SafetyGate (independent)
  -> env.step -> DecisionTrace (immutable provenance)
```

That is exactly the artifact the review said was missing (`core/pipeline.py`,
`core/contracts.py`, `core/safety_gate.py`), and `brain/orchestrator.py`
already calls the safety gate before execution (`Audit P0 fix` in its docstring).

So the review's **#1 issue is largely resolved**. The remaining critical gaps
are different, and one of them is a **new, important finding**:

> **`backend/` is not the ULTRONE backend the README describes.** It is the
> "Argus — Enterprise AI Video Analytics Platform" (`backend/__init__.py`),
> with `logger = "argus.api"`, `VideoPipeline`, `VisionEngine`. The `api/v1`
> endpoints return **seeded static data** and there is **no runnable FastAPI
> app entrypoint**, no HITL endpoints (`/override`, `/ask_reasoning` are
> absent). The README's backend claims are currently **not backed by the code**.

---

## 2. Module-by-module audit (what is real vs. scaffold/stale)

Legend: ✅ real & tested · 🟡 partial/thin · ❌ empty/scaffold · ⚠️ mismatch

| Module | Meas. | Verdict | Notes |
|---|---|---|---|
| `core/` | 4 py / 25 KB | ✅ **NEW, real** | Contracts + `DecisionPipeline` + `SafetyGate`; 14 tests pass. |
| `brain/` | 243 / 1.46 MB | ✅ real | Perception, sensor_fusion, reasoning (course_of_action, evolutionary_coagen), learning (rl, evolution), xai, memory, strategy — the substance of the system. |
| `cognitive/` | 24 / 295 KB | ✅ real | Multi-layer cognitive engine (planning, prediction, safety, perception layers). |
| `frontier/` | 39 / 277 KB | ✅ real | ToT/GoT/beam/self-consistency, reflection, agents, uncertainty/calibration. |
| `agents/` | 49 / 118 KB | ✅ real | air/land/sea/space/cyber multi-domain agents. |
| `sim/` | 20 / 82 KB | 🟡 real+thin | `battlefield_env`, `world_modeling/` (terrain, weather, logistics, sensor_uncertainty, stochastic_events), `performance/` (parallel, ray, gpu, profiler). Environment is 100x100; partial-observability only in `core.SensorSuite`. |
| `simulation/` | 4 / 3 KB | ⚠️ dup | Near-empty; overlaps `sim/`. |
| `comms/`, `knowledge_engine/`, `learning/`, `generative/` | ✅ | MessageBus, KG, continual learning, tact synth/adversarial emulator. |
| `backend/` | 43 / 230 KB | ⚠️ **mismatch** | "Argus" video platform; `api/v1` seeded; no FastAPI `app`; no HITL endpoints; no real auth/DB wiring to ULTRONE. |
| `research/` | 11 / 44 KB | ✅ real | experiment_manager, reproducer, reproducibility, scenario_benchmark, statistical_evaluation, ablation_framework, automated_report. |
| `research_division/`, `research_db/` | ✅ | experiment/paper/benchmark records; `research_db/` has untracked new records. |
| `benchmarks/` | 7 / 26 KB | 🟡 thin | harness/runners/history/graph exist; **not** wired to `core.Decision + Trace`; no fixed scenario suite. |
| `mlops/` | 9 / 27 KB | 🟡 thin | registry/deploy/monitor/drift/lineage present; **no approval gate** to learning loop. |
| `training_platform/` | 10 / 51 KB | 🟡 | datasets/distributed; **distributed = only `trainer.py`** (thin). |
| `frontend/` | React/Vite | ✅ | TacticalMapView, AgentInspector, AIReasoningPanel, DecisionTimeline, EventStream, KnowledgeGraph — good HITL foundation. |
| `infra/` | ✅ | 44 helm, 4 k8s, docker, monitoring — deployment exists. |
| `backend/` | — | ⚠️ (see above) | Argus mismatch; **do not extend before renaming**. |
| `memory/` (top) | 0 py | ⚠️ empty | real memory is in `brain/memory/`. |
| `brain/prediction/` | 0 | ⚠️ **empty** | the last truly empty research phase (Phase 8). |
| `robotics/` | 3 / 2 KB | 🟡 scaffold | |
| `plugins/`, `automl/`, `compiler/`, `hardware/`, `ultrone_os/`, `ultrone_bindings/`, `viz/` | 🟡 thin | scaffold/demo |
| `backend/` native: `go/`, `rust/`, `cpp/`, | 0 py | ⚠️ | bindings culture; not integrated. |
---

## 3. The pasted review, re-scored against the current tree

| # | Review claim | Current truth |
|---|---|---|
| 1 | End-to-end pipeline missing | **Resolved.** `core/` pipeline + orchestrator gate + 14 tests. |
| 2 | Backend stubs | **Partly.** Code exists, but the package is the **Argus** video platform, not ULTRONE's; no real API/HITL/persisted wiring. |
| 3 | No benchmark authority | Open. Harness exists but not tied to `DecisionPipeline` + fixed scenarios. |
| 4 | Low sim realism | **Partly.** `core.SensorSuite` + `sim/world_modeling/*` added; no comms loss/GPS denial/actuator failure/adversarial deception. |
| 5 | Safety must be independent | **Resolved** (`SafetyGate` in `core`, wired pre-execution). Missing: human approval gate, risk estimator, audit persistence, emergency stop. |
| 6 | HITL workflow | **Open.** Endpoints (`/override`, `/ask_reasoning`) do **not** exist in backend. |
| 7 | Decision provenance | **Resolved** as a primitive (`DecisionTrace`, `new_id`, `to_dict`); not yet persisted. |
| 8 | Distributed execution | **Open.** `training_platform/distributed` = `trainer.py` only. |
| 9 | Model lifecycle gates | **Open.** mlops registry exists; no approval gate in the learn→deploy loop. |
| 10 | Reproducibility manifest | Partly. Seed supported in `Orchestrator` & `DecisionPipeline`; no full manifest. |
| 11 | Research vs prod boundary | **Improved** (`core/`); still many top-level dirs, `sim/` vs `simulation/`, `memory/` vs `brain/memory/`. |
| 12 | Behavior docs | **Open.** Only `core/__init__.py` docstring; no "add a sensor/planner/agent" guide. |
| 13 | Repo hygiene | Confirmed: 9 `example.com` links; committed `final_test_output.txt`, `full_test_output.txt`, `images.jfif`, dozens of `tests/ultrone/artifacts/*.bin`; untracked `research_db/*` + new `.bin`; `PROJECT_PROGRESS.md` stale. |

---

## 4. P0 — blocking (do first; correctness & credibility)

1. **Decide & document the backend story.** Either (a) rename/repurpose `backend/`
   to the ULTRONE control API, or (b) isolate it. As-is, the README backend
   claims are false and there is **no runnable app**. Largest identity defect.
2. **Add HITL authorization endpoints** (proposal queue, evidence, approve /
   reject / modify + reason, audit append). Frontend components already exist;
   the API layer does not. Minimum: expose each pipeline step + verdict as a
   pending item an operator approves before execution.
3. **Persist `DecisionTrace` to an append-only audit store** so provenance
   survives a process and can be replayed. Currently traces live in memory.
4. **Stop committing generated artifacts & stale docs.** Remove `images.jfif`,
   `final_test_output.txt`, `full_test_output.txt`, `tests/test_artifacts/*.bin`;
   add `research_db/` records + `.bin` to `.gitignore`; reconcile
   `PROJECT_PROGRESS.md` (prediction, world-modeling, research tooling status).
5. **Fix the 9 `www.example.com` source links** in the README (replace with real
   references or remove the placeholder `Source` lines).

## 5. P1 — high value (correctness of science & control)

1. **Tie the benchmark layer to the core pipeline**: a fixed scenario suite
   (`scenario_benchmark.py`) running `DecisionPipeline` over N seeds, emitting
   one canonical manifest (repo commit, scenario id, seed, model version, config
   hash, metrics, artifact paths). Make it the regression gate on every change.
2. **Persistence + real DB wiring.** Give ULTRONE a persistent store
   (experiments, models, audit traces, eval results) connected to `research_db`,
   rather than Argus-flavoured `backend/database`.
3. **Complete `brain/prediction`** (the remaining empty phase) or explicitly
   map it to `cognitive/prediction_layer`; document the choice. Don't leave a
   dead empty dir.
4. **Expand simulation realism** in `core.SensorSuite` beyond gaussian/dropout:
   comms loss, GPS denial, false positives/negatives, actuator failures. Add
   fault-injection cases to `test_core_pipeline.py`.
5. **Model lifecycle approval gates**: `ModelApprovalGate` blocks auto-deploy;
   require benchmark pass + checkpoints + human sign-off; wire into `mlops`.
6. **Independent risk estimator** layered on `SafetyGate` (quantify COA risk)
   ahead of any human gate.

## 6. P2 — consolidation & polish (after P0/P1)

7. **Consolidate the research/production boundary**: merge `sim/`+`simulation/`,
   `memory/`+`brain/memory/`, wire/drop `go/`/`rust/`/`cpp/`; reduce top-level
   dirs to `core / sim / research / platform / extensions`.
8. **Behavior docs**: `docs/INTEGRATION.md` — one end-to-end decision trace, plus
   "add a sensor / planner / agent" guides.
9. **Audit permissions + emergency stop** layered on `DecisionTrace` after P0.3.
10. **Distributed execution** (only `trainer.py` today) after single-node is solid.

---

## 7. Priority sequence (executable)

- **Sprint A (P0):** backend identity decision; HITL endpoints; audit-store
  persistence; repo hygiene sweep; fix README links & stale progress doc.
- **Sprint B (P1):** benchmark→pipeline manifest; prediction closure; sensor
  realism; model approval gate; risk estimator.
- **Sprint C (P2):** boundary consolidation; integration/contribution docs;
  audit permissions; distributed execution.

> **Guardrail:** evolution produces candidates; evaluation decides whether they
> graduate. Keep the safety gate and human gate independent of the proposing
> model.