# ULTRONE Research-Grade Extensions — Progress

## Frontier Intelligence — *Complete*

### Status
Added a solver-agnostic Frontier Intelligence layer to improve reasoning,
self-correction, calibrated decision-making, and software engineering for
frontier benchmarks (GSM8K, MMLU, GPQA, HumanEval, MBPP, MATH, AIME,
SWE-bench). All tests use deterministic backend-agnostic test doubles.

### Files
- `frontier/reasoning/` — tree_of_thoughts, graph_of_thoughts,
  self_consistency, multi_agent_debate, constitutional_critique,
  beam_search_reasoner ✅
- `frontier/adaptation/` — critic_model, reflection_engine,
  self_correction_engine ✅
- `frontier/agents/` — planner, executor, verifier, tool_router ✅
- `frontier/decision/` — uncertainty, calibration, bayesian_decision ✅
- `coding_agent/` — full SWE stack (ast_analyzer, repository_indexer,
  symbol_search, static_analysis, test_runner, test_generator, bug_localizer,
  patch_validator) integrated into `CodingAgent` ✅
- `benchmarks/` — harness, runners, history, graph (extends base/registry) ✅
- `tests/test_frontier_reasoning.py` — 27 tests ✅
- `tests/test_coding_agent2.py` — 20 tests ✅
- `tests/test_benchmark_harness.py` — 20 tests ✅
- `docs/FRONTIER_INTELLIGENCE.md` — architecture documentation ✅

### Key Improvements
- **Search-based reasoning**: Tree of Thoughts, Graph of Thoughts, Beam Search
- **Consensus & debate**: Self-Consistency voting, Multi-Agent Debate
- **Self-correction**: Reflection Engine, Self-Correction Engine, Critic
- **Agent orchestration**: Planner, Executor, Verifier, Tool Router
- **Calibrated decisions**: Uncertainty estimation, confidence calibration,
  Bayesian decision layer with abstention
- **SWE automation**: AST analysis, repo indexing, symbol search, static
  analysis, dynamic test running, unit test generation, bug localization,
  patch validation
- **Benchmark harness**: solver-driven evaluation with append-only history
  (never overwrites prior runs) and improvement graphs

---

## Phase 1: Search & Planning — *Complete*

### Status
All 12 search/planning algorithms fully implemented with a common `Planner` interface.

### Files
- `brain/reasoning/search/__init__.py` — Module exports with lazy-loading
- `brain/reasoning/search/base.py` — Abstract `Planner` + data types
- `brain/reasoning/search/mcts.py` — Monte Carlo Tree Search ✅
- `brain/reasoning/search/htn.py` — Hierarchical Task Networks ✅
- `brain/reasoning/search/astar.py` — A*, D* Lite, LPA* ✅
- `brain/reasoning/search/mapf.py` — Multi-Agent Path Finding (CBS) ✅
- `brain/reasoning/search/beam_search.py` — Beam Search ✅
- `brain/reasoning/search/bidirectional.py` — Bidirectional Search ✅
- `brain/reasoning/search/pddl_interface.py` — STRIPS/PDDL planner ✅
- `brain/reasoning/search/anytime_planning.py` — Anytime planning wrapper ✅
- `brain/reasoning/search/receding_horizon.py` — Receding Horizon Control ✅
- `brain/reasoning/search/dynamic_programming.py` — DP-based planning ✅
- `tests/test_search_planning.py` — Unit & integration tests ✅

### Integration
- Lazy imports in `brain/reasoning/__init__.py` ✅
- `Planner` interface compatible with TacticalEngine ✅

---

## Phase 2: Reinforcement Learning — *Complete*

### Status
All 10 RL algorithms + adapter layer + algorithm registry implemented.

### Files
- `brain/learning/rl/__init__.py` — Module exports + registry ✅
- `brain/learning/rl/base.py` — BaseRLAlgorithm, RLTrainer, ExperienceBuffer ✅
- `brain/learning/rl/ppo.py` — Proximal Policy Optimization ✅
- `brain/learning/rl/sac.py` — Soft Actor-Critic ✅
- `brain/learning/rl/td3.py` — Twin Delayed DDPG ✅
- `brain/learning/rl/ddpg.py` — Deep Deterministic Policy Gradient ✅
- `brain/learning/rl/dqn.py` — DQN, Double DQN, Prioritized Replay ✅
- `brain/learning/rl/rainbow.py` — Rainbow DQN (C51, Noisy, Dueling) ✅
- `brain/learning/rl/marl.py` — Multi-Agent RL (Centralized Critic, Decentralized Actor) ✅
- `brain/learning/rl/self_play.py` — Self-play learning wrapper ✅
- `brain/learning/rl/curriculum.py` — Curriculum learning scheduler ✅
- `brain/learning/rl/adapter.py` — **NEW**: SB3Adapter, PPOAdapter, SACAdapter, TD3Adapter, DDPGAdapter, DQNAdapter, `create_rl_algorithm()`, `RL_REGISTRY` ✅

### Key Features Added
- Algorithm registry (`RL_REGISTRY`) for plugin-style instantiation
- Factory function `create_rl_algorithm()` for dynamic algorithm selection
- Stable-Baselines3 compatibility layer via adapters
- Configurable interchangeability via dependency injection

---

## Phase 3: Multi-Agent Coordination — *Complete*

### Status
All 12 coordination protocols implemented with a common `BaseCoordinator` interface.

### Files
- `brain/reasoning/coordination/__init__.py` — Module exports ✅
- `brain/reasoning/coordination/base.py` — BaseCoordinator, CoordinationConfig ✅
- `brain/reasoning/coordination/consensus.py` — Consensus Protocol ✅
- `brain/reasoning/coordination/task_allocation.py` — Task Allocation ✅
- `brain/reasoning/coordination/contract_net.py` — Contract Net Protocol ✅
- `brain/reasoning/coordination/coalition.py` — Coalition Formation ✅
- `brain/reasoning/coordination/blackboard.py` — Blackboard Architecture ✅
- `brain/reasoning/coordination/role_assignment.py` — Role Assignment ✅
- `brain/reasoning/coordination/formation_control.py` — Formation Control ✅
- `brain/reasoning/coordination/swarm_coordination.py` — Swarm Coordination ✅
- `brain/reasoning/coordination/team_reasoning.py` — **NEW**: Shared mental models for teams ✅
- `brain/reasoning/coordination/dynamic_leadership.py` — **NEW**: Dynamic leadership election ✅
- `brain/reasoning/coordination/emergent_behavior.py` — **NEW**: Emergent behavior analysis ✅

---

## Phase 4: Optimization — *Complete*

### Status
All 7 optimization engines implemented with a common `BaseOptimizer` interface.

### Files
- `brain/learning/optimization/__init__.py` — Module exports ✅
- `brain/learning/optimization/base.py` — BaseOptimizer, OptimizerConfig ✅
- `brain/learning/optimization/genetic_algorithm.py` — Genetic Algorithm ✅
- `brain/learning/optimization/cma_es.py` — CMA-ES ✅
- `brain/learning/optimization/differential_evolution.py` — Differential Evolution ✅
- `brain/learning/optimization/particle_swarm.py` — Particle Swarm ✅
- `brain/learning/optimization/simulated_annealing.py` — Simulated Annealing ✅
- `brain/learning/optimization/bayesian_optimization.py` — Bayesian Optimization ✅
- `brain/learning/optimization/ant_colony.py` — Ant Colony Optimization ✅

---

## Phase 5: Probabilistic Reasoning — *Complete*

### Status
All 8 probabilistic reasoning modules implemented with proper mathematical foundations.

### Files
- `brain/perception/probabilistic/__init__.py` — Module exports ✅
- `brain/perception/probabilistic/bayesian_network.py` — Bayesian Networks ✅
- `brain/perception/probabilistic/hidden_markov.py` — Hidden Markov Models ✅
- `brain/perception/probabilistic/kalman_filter.py` — KF, EKF, UKF ✅
- `brain/perception/probabilistic/particle_filter.py` — Particle Filter ✅
- `brain/perception/probabilistic/belief_propagation.py` — Belief Propagation ✅

### Key Improvements
- **EKF**: Full implementation with Jacobian-based linearisation, overridable `_state_transition()` and `_observation_model()` ✅
- **UKF**: Complete Unscented Transform with Cholesky sigma points, weighted reconstruction ✅

---

## Phase 6: Game Theory — *Complete*

### Status
All 7 game theory modules implemented.

### Files
- `brain/reasoning/game_theory/__init__.py` — Module exports ✅
- `brain/reasoning/game_theory/nash_equilibrium.py` — Nash Equilibrium ✅
- `brain/reasoning/game_theory/stackelberg.py` — Stackelberg Games ✅
- `brain/reasoning/game_theory/minimax.py` — Minimax with Alpha-Beta Pruning ✅
- `brain/reasoning/game_theory/cfr.py` — Counterfactual Regret Minimization ✅
- `brain/reasoning/game_theory/auction.py` — Auction Mechanisms ✅
- `brain/reasoning/game_theory/zero_sum.py` — **NEW**: Zero-sum game solvers ✅
- `brain/reasoning/game_theory/cooperative.py` — **NEW**: Cooperative game theory (Shapley value, etc.) ✅

---

## Phase 7: Graph Intelligence — *Complete*

### Status
All 6 graph intelligence modules implemented.

### Files
- `brain/perception/graph_intelligence/__init__.py` — Module exports ✅
- `brain/perception/graph_intelligence/gnn.py` — Graph Neural Networks ✅
- `brain/perception/graph_intelligence/gat.py` — Graph Attention Networks ✅
- `brain/perception/graph_intelligence/knowledge_embeddings.py` — Knowledge Graph Embeddings ✅
- `brain/perception/graph_intelligence/community_detection.py` — Community Detection ✅
- `brain/perception/graph_intelligence/temporal_graph.py` — Temporal Graph Analysis ✅

---

## Phase 8: Prediction — *Not Implemented*

### Status
No files exist in `brain/learning/prediction/`. Requires:
- LSTM predictor
- Transformer predictor (GRU)
- Temporal Fusion Transformer
- Trajectory predictor
- Change-point detection

### Dependency
- Requires PyTorch or TensorFlow

---

## Phase 9: Explainable AI — *Complete*

### Status
All 6 XAI modules implemented.

### Files
- `brain/xai/__init__.py` — Module exports ✅
- `brain/xai/decision_trace.py` — Decision trace generation ✅
- `brain/xai/shap_explainer.py` — SHAP explanations ✅
- `brain/xai/lime_explainer.py` — LIME explanations ✅
- `brain/xai/counterfactual.py` — Counterfactual explanations ✅
- `brain/xai/confidence_calibration.py` — **NEW**: Confidence calibration ✅
- `brain/xai/reasoning_graph.py` — **NEW**: Reasoning graph visualization ✅

---

## Phase 10: Memory Systems — *Complete*

### Status
All 6 memory modules implemented.

### Files
- `brain/memory/__init__.py` — Module exports ✅
- `brain/memory/base.py` — BaseMemory, MemoryConfig, MemoryItem ✅
- `brain/memory/episodic_memory.py` — Episodic memory ✅
- `brain/memory/semantic_memory.py` — Semantic memory ✅
- `brain/memory/working_memory.py` — Working memory with decay ✅
- `brain/memory/associative_memory.py` — Associative pattern recall ✅
- `brain/memory/memory_consolidation.py` — Memory consolidation ✅

---

## Phase 11: World Modeling — *Implemented*

### Status
`sim/world_modeling/` contains terrain, weather, resource, supply/logistics,
event-scheduler, sensor-uncertainty, and stochastic-events models.

---

## Phase 12: AI Architectures — *Implemented*

### Status
`ai_architectures/` contains behavior-tree, GOAP, utility-AI, BDI, FSM,
hierarchical-state, blackboard, and reactive-planning patterns.

---

## Phase 13: Performance — *Implemented*

### Status
`sim/performance/` contains parallel, distributed, ray, gpu-accelerated, and
profiling tooling.

---

## Phase 14: Research Tooling — *Implemented*

### Status
`research/` contains experiment_manager, hyperparameter_optimizer,
scenario_benchmark, reproducibility/reproducer, statistical_evaluation,
ablation_framework, and automated_report.

---

## Summary

| Phase | Status | Modules | Notes |
|-------|--------|---------|-------|
| 1. Search & Planning | ✅ Complete | 12 | All algorithms with Planner interface |
| 2. Reinforcement Learning | ✅ Complete | 11 | + SB3 adapters + RL_REGISTRY |
| 3. Multi-Agent Coordination | ✅ Complete | 12 | + TeamReasoning, DynamicLeadership, EmergentBehavior |
| 4. Optimization | ✅ Complete | 7 | All engines with BaseOptimizer interface |
| 5. Probabilistic Reasoning | ✅ Complete | 8 | EKF/UKF full implementations |
| 6. Game Theory | ✅ Complete | 7 | + ZeroSum, Cooperative games |
| 7. Graph Intelligence | ✅ Complete | 6 | GNN, GAT, embeddings, community, temporal |
| 8. Prediction | ❌ Empty | — | Directory exists, no files |
| 9. Explainable AI | ✅ Complete | 6 | + ConfidenceCalibration, ReasoningGraph |
| 10. Memory Systems | ✅ Complete | 6 | Multi-tier architecture |
| 11. World Modeling | ✅ Complete | 7 | simulator/world_modeling (terrain, weather, resource, logistics, events, sensor uncertainty) |
| 12. AI Architectures | ✅ Complete | 10 | behavior trees, GOAP, utility AI, BDI, FSM, HSM, blackboard, reactive |
| 13. Performance | ✅ Complete | 5 | sim/performance tools (parallel, distributed, ray, gpu, profiling) |
| 14. Research Tooling | ✅ Complete | 8 | research/ tooling (experiments, HPO, scenarios, reproducibility, stats, ablation) |
| **Backend** | ✅ Complete | 10+ | API, DB, events, analytics, security, etc. |

### Next Priority
Phase 8 (Prediction) is the only remaining empty module; it should be implemented
or explicitly routed to `cognitive/prediction_layer` to remove the dead dir.

## Sprint A — HITL Decision Control & Audit Store (complete)

- `ultrone_hitl/` — clean, ULTRONE-owned HITL package (does **not** touch the
  vendored `backend/`).
- `ultrone_hitl/audit_store.py` — append-only, tamper-evident JSONL audit log
  (SHA-256 hash chain; unique decision IDs; timestamps; actor + transition
  records; replay/verify).
- `ultrone_hitl/decision_workflow.py` — server-side state machine
  (PENDING → APPROVED → EXECUTED; REJECTED / OVERRIDDEN terminal) with
  role-based authorization, operating on the canonical
  `core.contracts.DecisionTrace`.
- `ultrone_hitl/api.py` — FastAPI HITL endpoints: submit, approve, reject,
  override (spawns an audited child preserving the original proposal), execute,
  ask_reasoning, retrieve, list, audit replay.
- Tests: `tests/test_audit_store.py` + `tests/test_hitl_api.py` (31 new).

### Architecture Documentation
See `ARCHITECTURE_EXTENSION_PLAN.md` for the complete architecture overview and design decisions.

---

## Sprint B — Closed-Loop Learning Validation (complete)

Goal: stop *adding* modules and prove the existing Adaptive +
Learning/Memory layers form a genuinely **closed** loop that learns,
generalizes to unseen tasks, and survives process restarts.

### The cycle under test

```
Episode -> ExperienceMemory -> Reflection -> Candidate
   -> Evaluator (reproducibility + margin gates)
   -> PromotionGate (audited) -> BrainStore (production channel)
   -> next Episode (loads production config back through
      ParameterRegistry.apply()) -> ExperienceMemory -> ...
```

### Artifacts

- `tests/test_closed_loop_learning.py` — the 12-step integration loop:
  baseline episode -> experience -> reflection -> candidate ->
  multi-repeat evaluation -> gate review -> promotion -> persistence ->
  second episode -> second experience. Headline assertion is NOT
  `promotion.success` but::

      next_episode.configuration_hash == promoted.configuration_hash

  i.e. the promoted brain config demonstrably flows into the next
  cycle. (Required `ParameterRegistry.apply()` — added as the canonical
  bulk-load entry point used to rehydrate a registry from BrainStore.)

- `tests/test_cross_process_persistence.py` — durable long-term memory
  proof via `multiprocessing` spawn context: Process A records
  experiences and promotes a configuration, exits; Process B restores
  experience memory + BrainStore + PromotionGate audit trail in a fresh
  interpreter and verifies byte-level fidelity. This closes the
  requirement "ExperienceMemory persists across sessions" as *durable*
  long-term storage rather than episodic runtime memory.

- `benchmarks/learning_benchmark.py` (+ `tests/test_learning_benchmark.py`)
  — measurable learning benchmark over a family of seeded patrol
  scenarios (`adaptive.evaluator.PatrolScenario`, `scenario_from_seed`,
  `make_patrol_task`). Training and holdout seed sets are disjoint by
  construction; adaptation sees only training scenarios, so improvement
  on unseen scenarios evidences generalization rather than memorized
  tuning. Includes an advisory reflection rule fed from recorded
  experience (`reflect_on_experience`), evolutionary refinement
  (`AdaptiveOptimizer`) against the aggregate training objective, and
  regression-suite + reproducibility verdicts on every promotion.

### Sample benchmark output (default seeds, standalone run)

```
Score
Baseline episode              33.80
Iteration 1                   34.45
Iteration 2                   34.45
Iteration 3                   34.45
Iteration 4                   34.47
Iteration 5                   34.48
Iteration 6                   34.48

Training scenarios   ↑ (33.80 -> 34.48)
Unseen scenarios     ↑ (34.28 -> 34.79)
Regression suite     PASS
Reproducibility      PASS
Promotion            promote (beats baseline by 0.671284)
Production hash      2b42d651c6f4e37f
```

Run it with:

```
python -m pytest tests/test_closed_loop_learning.py tests/test_cross_process_persistence.py tests/test_learning_benchmark.py -v
python -m benchmarks.learning_benchmark          # headline table
```

---

## Sprint C — Model + Tool Orchestration (complete)

Goal: a **routing layer**, not another giant agent class — ULTRONE now
selects among interchangeable models, tools, memory strategies, and
skills *per task*, and the existing adaptive machinery evolves the
routing policy itself through Evaluator gates into production.

### Architecture (orchestration/)

```
Task -> task_classifier -> RoutingPolicy (registry knobs) -> ranked candidates
   -> execute -> result_validator --accept--> StructuredResult
        |                                          |
     fallback chain                    trace + ExperienceMemory
```

- `task_classifier.py` — `TaskProfile` (difficulty, reasoning_depth,
  context_requirement, tool_requirement, latency_sensitivity,
  privacy) via transparent precedence rules; `synthetic_profile`
  builds deterministic benchmark families.
- `model_registry.py` / `tool_registry.py` / `memory_router.py` /
  `skill_router.py` — spec catalogs with measured tradeoffs
  (strengths per dimension, context window, credits, latency,
  reliability); no silent overwrites; selection rules are auditable.
- `context_builder.py`, `cost_policy.py`, `result_validator.py`,
  `fallback.py` — token-budgeted context planning; cost/latency
  accounting that bills retries in full; structured-result contract;
  ordered candidate chains.
- `router.py` — `RoutingPolicy` (economy/balanced/premium regimes
  driven by registry thresholds), `Orchestrator` execution loop with
  SLO-slack scoring, and the deterministic truth simulator seam for
  swapping real providers without touching callers.
- `traces.py` — every decision recorded as JSONL with
  `configuration_hash` of the policy snapshot => traces join to
  BrainStore promotions.

### The payoff: policy evolution

Every routing knob lives in `ParameterRegistry`
(`default_routing_registry`: regime thresholds, cost/latency/memory
weights, planning depth, iterations, budget cap, validator
intercept). `benchmarks/orchestration_benchmark.py` therefore points
the stock `AdaptiveOptimizer` at routing: disjoint train/holdout task
families, regression-aware objective (sacrificing a solved task costs
more than it can buy), regression suite gating promotion BEFORE
BrainStore writes.

```
Score
Baseline episode               4.89
Iteration 1                    5.01
Iteration 2                    5.22
Iteration 3                    5.24
Iteration 4                    5.65
Iteration 5                    5.65

Training scenarios   ↑ (4.89 -> 5.65)
Unseen scenarios     ↑ (2.14 -> 2.36)
Regression suite     PASS
Reproducibility      PASS
Promotion            promote (beats baseline by 0.759485)
Production hash      3723e0c130a746a7
```

Canonical route behavior (asserted by tests): simple -> cheap tier;
deep reasoning -> reasoner `[complexity]`; coding -> coder;
long-context -> longctx + tiered memory; private -> local tiers only;
validation failures walk the fallback chain and bill cumulatively;
impossible budgets stop runs with named failures.

Loop closure (Sprint B's headline property, orchestration edition):
a fresh Orchestrator rebuilt from the BrainStore production channel
routes under the promoted policy -- proven via trace provenance

    fresh_trace.configuration_hash == promoted.configuration_hash

rather than by trusting stored JSON
(`test_promoted_policy_drives_the_next_run`).

Run it with:

```
python -m pytest tests/test_orchestration_components.py \
                 tests/test_router_integration.py \
                 tests/test_orchestration_benchmark.py -v
python -m benchmarks.orchestration_benchmark    # headline table
```

---

## Sprint D — Self-Training Substrate *(learning support + controlled loop)*

Goal: give ULTRONE a real **learning substrate** that can turn its own
experiences into training signal and a **controlled self-improvement
cycle** -- while resisting the trap of calling parameter/route
optimization "training." Per the architecture charter, the substrate is
a *capability learner* (not a pretrained foundation model): a
serialized ``LearnedWeights`` model that the Orchestrator executes
through an adapter seam, so a real neural backend can be swapped in
without touching any gate.

### Architecture (self_improvement/self_training/)

```
GENERATE -> EXECUTE -> EVALUATE -> SELECT -> TRAIN
  -> VALIDATE (regression families) -> COMPARE -> PROMOTE
```

- `task_generator.py` / `curriculum_manager.py` — 5-rung curriculum
  ladder; a level graduates only when mean utility saturates
  (streak-based), so the system practices before advancing.
- `experience_selector.py` — three-way bucket (good/bad/uncertain);
  only *good* experiences become training data, so bad examples can
  never teach bad behavior; a weakness profile targets practice.
- `dataset_builder.py` — experience -> SFT-shaped JSONL with dedup and
  a **supervisor ceiling** target (so the learner moves, not just
  converges to its own self-reported quality), plus a continuous
  70/20/10 historical/recent/weakness mixture to resist forgetting.
- `trainer.py` — prior-shrunk statistical capability learner;
  `LearnedWeights` is the serialized model, `make_executor` bridges it
  into the Orchestrator seam (real training slots in behind the same
  ``to_config``/``from_config`` contract).
- `regression.py` + `promotion.py` — five gated families (normal,
  unseen, difficult, fault_recovery, adversarial); promotion reuses
  the existing `Evaluator` -> `PromotionGate` -> `BrainStore` pipeline
  and refuses a candidate that breaks any family (honest 'reject'
  recorded, never 'promote').
- `checkpoint.py` / `scheduler.py` — lineage-tracked models
  (model/dataset/config hashes, seed, parent) with a separate
  production channel, and a gate deciding *when* a cycle is worthwhile.
- `controller.py` — the closed loop; production model is only ever
  READ as baseline; candidates are trained in the sandbox workdir and
  reach production only through the gates.

### Proof (tests/test_self_training.py, 24 tests)

Cycle one from a starter model is a genuine promotion: dataset built,
candidate differs from baseline, regression passes, production updated
(baseline 3.516 -> candidate 3.570 on the holdout objective). Later
cycles keep climbing capability while the promotion gate honestly
refuses the plateau (no measurable holdout gain). Cross-process
reproducibility holds: two independent runs produce the identical
production model hash.

Run it with:

```
python -m pytest tests/test_self_training.py -v
```

---

## Sprint E — Capability Evaluation & the "measurably better?" harness

Goal: turn the Phase-4 question into an exact, re-runnable measurement --
**does the loop-produced model measurably beat the model it started
with?** -- without faking a neural training pass.

### Additions

- `self_improvement/self_training/evaluation.py` — multidimensional
  model report `CapabilityMetrics` covering **reasoning, planning,
  memory, tool use, generalization, robustness, simulation
  performance, regression risk, latency, and resource cost**, computed
  deterministically by running the candidate's executor over the same
  gated families as promotion. `compare_capabilities` applies the
  verdict:
  ```
  promotable = overall  AND no critical regression
               AND holdout improvement AND reproducibility
  ```
- `benchmarks/self_training_benchmark.py` — runs the self-training
  loop from a starter, then reports baseline-vs-final capability
  deltas, the regression verdict, and `MEASURABLY BETTER` /
  `not measurably better`, with JSON persistence. Deterministic:
  identical final hash every run. Standalone:
  `python -m benchmarks.self_training_benchmark`.
- `tests/test_self_training_benchmark.py` — 5 tests (determinism,
  all-dimension report, better/worse verdicts, benchmark + persistence).

### Measured result (default run)

```
Capability benchmark    MEASURABLY BETTER
Baseline model          a0ba2825cc2d9ffb
Final model             51e47cec943aec81
Regression suite        PASS
Promoted during loop      yes
Plateau honestly refused  yes

generalization       3.7353 -> 3.7799   (+0.0445, the transfer gain)
reasoning            0.2896 -> 0.2984   (+0.0088)
robustness          -1.0000 -> -1.0000   (+0.0000 -- NOT faked)
```

The cell-verify signal: the harness is honest on the underside too --
the adversarial/robustness dimension shows no improvement because none
was achieved; only measured gains count.

**Milestone boundary stays intact:** this is a *measurement harness*,
not a training run. The same harness is the benchmark you'll point at
a real neural/hosted backend once it is substituted behind the
executor seam -- the verdict criteria, lineage, and gating already
operate on any model exposing ``LearnedWeights``.

Run it with:

```
python -m pytest tests/test_self_training_benchmark.py -v
python -m benchmarks.self_training_benchmark    # headline table
```





