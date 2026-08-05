# ULTRONE Frontier Intelligence — Implementation TODO

## Objective
Transform ULTRONE into a state-of-the-art autonomous AI system competitive on
frontier benchmarks (GSM8K, MATH, MMLU, GPQA, HumanEval, MBPP, SWE-bench, etc.)
through architectural improvements — not benchmark hacks.

---

## Phase 1 — Frontier Reasoning Strategies ✅ IN PROGRESS
- [ ] `frontier/reasoning/base.py` — Solver/Verifier protocols, ReasoningStrategy base
- [ ] `frontier/reasoning/tree_of_thoughts.py` — ToT (BFS/DFS over thoughts)
- [ ] `frontier/reasoning/graph_of_thoughts.py` — GoT (DAG memories, aggregation)
- [ ] `frontier/reasoning/self_consistency.py` — N-sample majority / weighted voting
- [ ] `frontier/reasoning/multi_agent_debate.py` — multi-solver debate convergence
- [ ] `frontier/reasoning/constitutional_critique.py` — generate → critique → revise
- [ ] `frontier/reasoning/beam_search_reasoner.py` — beam search over reasoning steps
- [ ] `frontier/reasoning/__init__.py` — public API exports

## Phase 2 — Reflection & Self-Correction
- [ ] `frontier/adaptation/reflection_engine.py`
- [ ] `frontier/adaptation/self_correction_engine.py`
- [ ] `frontier/adaptation/critic_model.py`

## Phase 3 — Agent Orchestration
- [ ] `frontier/agents/planner.py`
- [ ] `frontier/agents/executor.py`
- [ ] `frontier/agents/verifier.py`
- [ ] `frontier/agents/tool_router.py`

## Phase 4 — Bayesian Decision & Uncertainty
- [ ] `frontier/decision/bayesian_decision.py`
- [ ] `frontier/decision/uncertainty.py`
- [ ] `frontier/decision/calibration.py`

## Phase 5 — Software Engineering Stack (extend coding_agent)
- [ ] `coding_agent/ast_analyzer.py`
- [ ] `coding_agent/repository_indexer.py`
- [ ] `coding_agent/symbol_search.py`
- [ ] `coding_agent/static_analysis.py`
- [ ] `coding_agent/test_runner.py`
- [ ] `coding_agent/test_generator.py`
- [ ] `coding_agent/bug_localizer.py`
- [ ] `coding_agent/patch_validator.py`
- [ ] Integrate into `coding_agent/agent.py`

## Phase 6 — Benchmark Harness (extend benchmarks)
- [ ] `benchmarks/harness.py`
- [ ] `benchmarks/runners.py`
- [ ] `benchmarks/history.py`
- [ ] `benchmarks/graph.py`

## Phase 7 — Tests & Docs
- [ ] `tests/test_frontier_reasoning.py`
- [ ] `tests/test_coding_agent2.py`
- [ ] `tests/test_benchmark_harness.py`
- [ ] `docs/FRONTIER_INTELLIGENCE.md`
- [ ] Update `README.md`, `PROJECT_PROGRESS.md`

## Final
- [ ] Run new test suites
- [ ] Run full test suite
- [ ] Update progress docs
