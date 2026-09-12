# ULTRONE Monorepo Reorganization — Architecture Decision Record

**Date:** 2026-09-12
**Status:** Implemented
**Scope:** Repository layout only. No file was deleted; every tracked file
was moved with `git mv`, so rename history is fully preserved.

---

## 1. Problem

Before this change the repository was an unstructured "algorithm zoo":

- 60+ top-level directories mixing product code, platform packages,
  research outputs, simulation, vendored third-party projects, and run
  artifacts.
- The vendored Ultron collective-memory system existed in *two* places
  (`original_source/` + a root-level compatibility `ultron/` shim pointing
  into it), next to conceptually overlapping root-level `api/`, `cli/`,
  `services/`, `dashboard/` — the classic "which copy does the runtime
  import?" hazard called out in `FOLDER_STRUCTURE_ANALYSIS.md`.
- `research_db/` (1187 files of experiment/paper records) sat at the repo
  root as if it were a platform package.
- Vendored `adelise-agent-framework-main` docs/examples were split across
  `adelise-agent-framework-main/`, `docs/framework/`, and `examples/`.
- Run artifacts (`memory/best_genome.json`, `memory/commander_log.txt`,
  `images.png`) mixed with source.

## 2. Decision

Reorganize every tracked item into semantic buckets. **All 3092 tracked
files were relocated via `git mv`; zero files were deleted.**

```text
apps/          product layer        (api, backend, cli, services, ultrone_hitl)
packages/      platform layer       (core, cognition, agents, knowledge,
                                     orchestration, runtime, safety,
                                     observability, transport)
research/      research layer       (benchmarks, research_db, research_division, *.py)
simulation/    simulation layer     (sim, *.py)
adapters/      integration ports    (llm, vision, vector_db, database, external)
data/          datasets + artifacts (memory/, terrain, entities, feeds)
infra/         deployment           (docker, helm, kubernetes, monitoring,
                                     nginx, deploy/hf_space)
vendor/        third-party          (original_source, ultron shim,
                                     adelise-agent-framework-main + docs + examples)
docs/          architecture docs, progress, plans, assets
tests/         unit, integration, smoke tests
scripts/       utility scripts
```

Legacy packages whose name equals the bucket name (`research`, `simulation`)
merged with the bucket root; their siblings moved inside alongside them.
`docs/framework/` and `examples/` belong to the vendored adelise framework
and were reunified under `vendor/adelise-agent-framework-main/`.

## 3. Import compatibility — the critical constraint

477 Python files import packages by their original top-level names
(`import brain`, `from cognitive import ...`, `from research_db.store
import ...`). Renaming imports across 3092 files in one pass would be
reckless. Instead, the import surface is kept **byte-identical** by making
the buckets resolvable:

1. **`_ultrone_paths.py`** (repo root) — central bootstrap. Lists every
   bucket and inserts it into `sys.path`. Entry points call
   `ensure_on_syspath()`:
   - `apps/api/main.py`
   - `apps/api/server.py`
   - `apps/api/ultrone.py`
   - `apps/cli/__main__.py`

2. **`pytest.ini`** — `pythonpath` lists every bucket, so all tests resolve
   moved packages unchanged.

3. **`pyproject.toml`** — `tool.setuptools.packages.find` lists every
   bucket `where`, so an editable install exposes all original names.

4. **CI workflows** — `PYTHONPATH` env set to every bucket:
   `canonical-benchmark.yml`, `research-platform-ci.yml`.

5. **`infra/docker/Dockerfile.research`** — in-container `PYTHONPATH` covers
   all buckets.

6. **Staging scripts that flatten buckets** — the HF Space deploy workflow
   copies `packages/agents/agents → stage/agents` etc., preserving the
   Space's flat-import contract (enforced by `tests/test_deploy_demo.py`,
   whose `APP_PATH` now points at `infra/deploy/hf_space/app.py`).

## 4. Path assumptions fixed

A few modules hard-coded repo-root-relative paths that broke after moving:

- `research/research_db/store.py` — `JSONResearchStore`,
  `SQLiteResearchStore` and the `ResearchDatabase` facade now default to the
  package directory (from `__file__`) instead of `"research_db"`.
- `research/benchmarks/canonical/research_sink.py` — `persist_run_metadata`
  defaults to the `research_db` package directory.

Explicit callers passing `base_dir` (tests use `tmp_path`) keep working.

## 5. New scaffolds (additive, nothing replaced)

- `packages/core/world_model/` — seed of the **one canonical world model**:
  `Entity` (stable `entity_id`, type, composable `Component`s with
  `confidence` + `Provenance`), `EntityUpdated` event payload, in-memory
  `WorldModel` store. Composes the existing SA/cognitive/sim world-state
  layers; it does not replace them.
- `adapters/` — `BaseAdapter` port plus placeholder seams for
  `llm/`, `vision/`, `vector_db/`, `database/`, `external/`. Each documents
  the platform module it should wrap (e.g. `orchestration/model_registry`,
  `core/llm_service`, `backend/vision`, `knowledge_engine/vector_memory`,
  `core/database`, `backend/integrations`).

## 6. Rollback

Single commit; `git revert <commit>` restores the previous layout. Because
everything moved with `git mv` in one transaction and no content changed,
revert is safe.

## 7. Follow-ups (out of scope here)

- Rename imports to bucket-qualified names gradually (or install all buckets
  as one editable package).
- Wire `adapters/` implementations to their platform modules.
- Grow `packages/core/world_model/` into the shared event-driven state layer
  (Postgres/Redis-backed, published over WebSocket).
- Consider Dockerfile files referenced by `infra/docker/docker-compose.yml`
  (`Dockerfile.api`, `Dockerfile.worker`) — they are not present in the
  repository; creating them is a follow-up, not a regression of this change.
