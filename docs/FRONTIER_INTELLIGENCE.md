# ULTRONE Frontier Intelligence

**Version:** 1.0
**Status:** Production-Ready
**Purpose:** Make ULTRONE competitive on frontier benchmarks (GSM8K, MMLU, GPQA,
HumanEval, MBPP, SWE-bench, MATH, AIME) through architectural improvements to
reasoning, planning, memory, verification, and tool use — not benchmark hacks.

---

## 1. Overview

Frontier Intelligence is a modular layer that extends the existing ULTRONE
cognitive architecture with search-based and self-improving reasoning over
generated solutions. It combines:

- **Search-based reasoning** — Tree of Thoughts, Graph of Thoughts, Beam Search
- **Consensus & debate** — Self-Consistency voting, Multi-Agent Debate
- **Self-correction** — Reflection Engine, Self-Correction Engine, Critic Model
- **Agent orchestration** — Planner, Executor, Verifier, Tool Router
- **Calibrated decision-making** — Uncertainty estimation, confidence
  calibration, Bayesian decision layer
- **Software engineering** — full SWE stack (AST analysis, repo indexing, test
  generation, bug localization, patch validation)
- **Benchmark harness** — solver-driven evaluation with persistent history and
  improvement graphs

The design is deliberately solver-agnostic: any callable (a local model, an API
client, a heuristic) can be plugged in as the `solver`. All tests use
deterministic backend-agnostic test doubles.

---

## 2. Package Layout

```
frontier/
├── reasoning/
│   ├── base.py                 # Solution, Verification, ThoughtNode primitives
│   ├── tree_of_thoughts.py     # ToT search with evaluator-guided branching
│   ├── graph_of_thoughts.py    # GoT aggregation over a graph of thoughts
│   ├── self_consistency.py     # Majority/confidence-weighted voting
│   ├── multi_agent_debate.py   # Round-based agent debate
│   ├── constitutional_critique.py  # Constitution-constrained critique
│   └── beam_search_reasoner.py # Beam search over reasoning steps
├── adaptation/
│   ├── critic_model.py         # Evaluates candidate solutions
│   ├── reflection_engine.py    # Reflect → refine → re-solve loop
│   └── self_correction_engine.py  # Self-correct with verifier feedback
├── agents/
│   ├── planner.py              # Decomposes goals into plans
│   ├── executor.py             # Executes plans via tools
│   ├── verifier.py             # Checks plan/solution correctness
│   └── tool_router.py          # Routes intents to registered tools
└── decision/
    ├── uncertainty.py          # Ensemble/entropy/variance estimators
    ├── calibration.py          # ECE + temperature scaling
    └── bayesian_decision.py    # Bayesian decision layer with abstention
```

### Supporting software-engineering stack (`coding_agent/`)

```
coding_agent/
├── agent.py               # CodingAgent facade (full SWE workflow)
├── ast_analyzer.py        # Function/class/import extraction from Python AST
├── repository_indexer.py  # Builds a queryable repository index
├── symbol_search.py       # Symbol and definition lookup
├── static_analysis.py     # Undefined-name/bare-except/syntax checks
├── test_runner.py         # Dynamic execution of test functions/files
├── test_generator.py      # Unit test generation from AST + examples
├── bug_localizer.py       # Localizes bugs from failing test output
└── patch_validator.py     # Validates patches against the test suite
```

### Benchmark harness (`benchmarks/`)

```
benchmarks/
├── base.py       # Benchmark, BenchmarkConfig, BenchmarkResult (pre-existing)
├── registry.py   # BenchmarkRegistry (pre-existing)
├── harness.py    # BenchmarkHarness — solver-driven evaluation
├── runners.py    # gsm8k / mmlu / human_eval / mbpp problem factories
├── history.py    # BenchmarkHistory — append-only ledger (never overwrites)
└── graph.py      # BenchmarkGraph — improvement PNG generation
```

---

## 3. Reasoning Layer

### 3.1 Tree of Thoughts (`tree_of_thoughts.py`)

Explores multiple reasoning branches by repeatedly generating candidate thoughts
and using an evaluator to pick the most promising node. Supports BFS and DFS
search strategies with a configurable branching factor and depth limit.

### 3.2 Graph of Thoughts (`graph_of_thoughts.py`)

Treats generated thoughts as nodes in a graph, allowing aggregation and
merging of intermediate results. An aggregator combines node outputs into a
final answer.

### 3.3 Self-Consistency (`self_consistency.py`)

Generates multiple independent solutions and votes on the final answer. Two
modes:

- **Majority voting** — most common answer wins.
- **Verifier-weighted** — weights each answer by verifier confidence.

### 3.4 Multi-Agent Debate (`multi_agent_debate.py`)

Runs `num_agents` agents for `num_rounds` rounds. Each agent critiques the
best proposal and proposes a refinement; the ensemble converges on a final
answer.

### 3.5 Constitutional Critique (`constitutional_critique.py`)

Applies a configurable set of constitution rules to critique candidate
solutions, returning a pass/fail verdict and a refined answer when the
candidate violates one or more rules.

### 3.6 Beam Search Reasoner (`beam_search_reasoner.py`)

Maintains a beam of partial reasoning states. A `step_generator` expands each
state and a scorer ranks expansions, keeping only the top-k by score.

---

## 4. Adaptation Layer

### 4.1 Reflection Engine (`reflection_engine.py`)

Loop of `solve → evaluate → reflect → refine`. If the verifier marks the
initial solution incorrect, the engine reflects on the failure and re-solves
for up to `max_reflections` passes.

### 4.2 Self-Correction Engine (`self_correction_engine.py`)

Similar in spirit but structured around verifier feedback: each attempt uses
the verifier's critique to produce a corrected attempt until success or
`max_attempts` is reached.

### 4.3 Critic Model (`critic_model.py`)

A lightweight module that scores candidate solutions. Supports a heuristic
scorer or an explicit `critic_fn`, and returns a normalized confidence score.

---

## 5. Agent Layer

- **Planner** — produces a structured plan (`Plan` with steps) from a goal,
  optionally with a heuristic scorer and a replan trigger.
- **Executor** — executes a plan step-by-step using a registry of tools,
  stopping early on tool failure.
- **Verifier** — checks plan feasibility and solution correctness via an
  oracle or a check function.
- **Tool Router** — routes an intent string to the most relevant registered
  tool by keyword overlap.

---

## 6. Decision Layer

### 6.1 Uncertainty Estimation (`uncertainty.py`)

Estimates uncertainty from a set of samples via ensemble disagreement,
entropy, and variance. Exposes a normalized `confidence()`.

### 6.2 Confidence Calibration (`calibration.py`)

Computes Expected Calibration Error (ECE) and fits a temperature-scaling
parameter to calibrate model confidence.

### 6.3 Bayesian Decision Layer (`bayesian_decision.py`)

Maintains a categorical prior over actions, updates a posterior from observed
likelihoods, and selects the action with the highest posterior probability.
Supports an `abstain_threshold` to decline low-confidence decisions.

---

## 7. Benchmark Harness

The harness evaluates an arbitrary `solver` callable against a list of
`BenchmarkProblem` objects and computes a per-problem accuracy.

```python
from benchmarks.harness import BenchmarkHarness, BenchmarkProblem
from benchmarks.history import BenchmarkHistory

solver = lambda prompt: "42"
harness = BenchmarkHarness(solver=solver)
problems = [BenchmarkProblem(prompt="What is the answer?", expected="42")]
run = harness.run("qa", problems)
print(run.accuracy)  # 1.0
```

History is **append-only**: every run is recorded with a timestamp, so previous
results are never overwritten. `BenchmarkGraph` renders an improvement chart
from the ledger.

---

## 8. Testing

Test suites (all backend-agnostic, no LLM required):

| File | Coverage |
|------|----------|
| `tests/test_frontier_reasoning.py` | ToT, GoT, self-consistency, debate, critique, beam search, reflection, self-correction, critic, planner/executor/verifier/router, uncertainty, calibration, bayesian decision |
| `tests/test_coding_agent2.py` | AST analyzer, repo indexer, symbol search, static analysis, test runner, test generator, bug localizer, patch validator, CodingAgent facade |
| `tests/test_benchmark_harness.py` | Harness, gsm8k/mmlu/human_eval/mbpp runners, history ledger, graph generation |

Run:

```bash
python -m pytest tests/test_frontier_reasoning.py \
  tests/test_coding_agent2.py tests/test_benchmark_harness.py -q
```

---

## 9. Integration

Frontier components are designed to plug into the existing ULTRONE cognitive
loop (`cognitive/`) and research platform (`research_division/`,
`self_improvement/`):

- The **verifier** can wrap the existing `QualityReviewer` agent.
- The **memory** modules can feed retrieved context into the solver.
- The **benchmark harness** can drive the `SelfImprovementLoop` validation
  phase with real solver scores instead of random improvements.
