# ULTRONE Documentation

This repository is a multi-project monorepo. Documentation is organized by
project:

## Ultrone Core (battlefield AI research platform)

- [ARCHITECTURE.md](ARCHITECTURE.md) — unified master architecture, 14 buckets, 7 defense capabilities, and cockpit subsystem
- [ARCHITECTURE_INVARIANTS.md](ARCHITECTURE_INVARIANTS.md) — non-negotiable
  architectural rules (plane separation, safety-gate independence, canonical
  execution path)
- [FOLDER_STRUCTURE_ANALYSIS.md](FOLDER_STRUCTURE_ANALYSIS.md) — repository directory tree and monorepo structure
- [ULTRONE_MONOREPO_REORG.md](ULTRONE_MONOREPO_REORG.md) — monorepo reorganization architectural decision record (ADR)
- [DEPLOYMENT.md](DEPLOYMENT.md) — deployment guides, container builds, and Hugging Face space
- [COGNITIVE_ARCHITECTURE.md](COGNITIVE_ARCHITECTURE.md) — perception →
  cognition → decision → action loop
- [SITUATIONAL_AWARENESS.md](SITUATIONAL_AWARENESS.md) — multi-source sensor
  fusion and threat assessment
- [FRONTIER_INTELLIGENCE.md](FRONTIER_INTELLIGENCE.md) — frontier reasoning
  modules (coding agent, benchmark harness)
- [AUTONOMOUS_RESEARCH_ARCHITECTURE.md](AUTONOMOUS_RESEARCH_ARCHITECTURE.md) —
  autonomous research division design
- [RESEARCH_PLATFORM_ARCHITECTURE.md](RESEARCH_PLATFORM_ARCHITECTURE.md) —
  research platform layering
- [RESEARCH_DB_EVALUATION.md](RESEARCH_DB_EVALUATION.md) — research database
  evaluation methodology
- [REPO_AUDIT_AND_ROADMAP.md](REPO_AUDIT_AND_ROADMAP.md) — repository audit
  findings and roadmap
- [PROGRAMMING_LANGUAGE_POLICY.md](PROGRAMMING_LANGUAGE_POLICY.md) — Python /
  Rust / C++ language boundaries

## Ultron (collective-memory system, vendored)

Source lives in [`vendor/original_source/`](../vendor/original_source/) and is importable
as the `ultron` package via the [`vendor/ultron/`](../vendor/ultron/) shim.

- [docs/ultron/en/](ultron/en/) — English docs (API, Components, GetStarted,
  Showcase)
- [docs/ultron/zh/](ultron/zh/) — Chinese docs (中文文档)

The Ultron server (`server.py` at the repo root) requires an embedding
backend: `dashscope` (default), `openai` (OpenAI-compatible endpoint), or
`local` (sentence-transformers). Configure via `ULTRON_EMBEDDING_BACKEND` and
see `vendor/original_source/core/embeddings.py` for the full list of environment
variables.

## Adelise / bee-agent-framework (vendored)

Source lives in [`vendor/adelise-agent-framework-main/`](../vendor/adelise-agent-framework-main/).
See `vendor/adelise-agent-framework-main/README.md` for framework documentation and examples.
