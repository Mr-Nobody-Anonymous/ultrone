# Ultrone Roadmap

This roadmap tracks the open engineering items for the Ultrone research
platform. It supersedes earlier notes and is kept in sync with
`docs/REPO_AUDIT_AND_ROADMAP.md` (the detailed audit) and the roadmap
section of `README.md`.

## Now

- [ ] **Real model adapter.** Replace the simulated `ModelAdapter` seam
  with a real neural backend while keeping the deterministic benchmark
  (`benchmarks/canonical/`) as the acceptance gate.
- [ ] **Out-of-sample validation.** Run the existing infrastructure on the
  frozen holdout and publish a reproducible result. The bar to clear is
  the repo's own deterministic out-of-sample signal: the
  `benchmarks/learning_benchmark.py` holdout (training and holdout seeds
  are disjoint by construction) and the `MEASURABLY BETTER` verdict from
  `benchmarks.self_training_benchmark` — not the simulated in-sample score.
- [ ] **Distributed evolution runs.** Parallelize `evolution/` evaluation
  across workers without breaking the single canonical execution path
  (`core/pipeline.py`).

## Next

- [ ] **Notebooks and walkthroughs.** Example notebooks for the cognitive
  loop, the HITL audit chain, and the Ultron memory integration.
- [ ] **Plugin marketplace.** Formalize the `plugin_sdk/` packaging story
  (discovery, versioning, signing) beyond the current hot-swap loader.
- [ ] **RL benchmark suite.** Extend `benchmarks/` with standard
  reinforcement-learning environments alongside the canonical suite.

## Later

- [ ] **Ultron server hardening.** Authentication and multi-tenant
  isolation for `server.py` beyond the current research-oriented setup.
- [ ] **Adelise framework evaluation.** Decide whether the vendored
  `adelise-agent-framework-main/` becomes an integration target or is
  dropped from the monorepo.

## Completed (high level)

- 15-layer cognitive architecture with a single canonical execution path.
- 7-tier memory system and tamper-evident HITL audit chain.
- Canonical benchmark suite with per-run research records
  (`research_db/`).
- Ultron collective-memory integration (Trajectory / Memory / Skill /
  Harness hubs) with a compatibility package (`ultron/`) and full test
  coverage.
- Simulation-only public demo on Hugging Face Spaces
  (`deploy/hf_space/`).
