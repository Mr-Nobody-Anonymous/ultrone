# Changelog

All notable changes to the **Ultrone** project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ultron/` compatibility package exposing the vendored Ultron collective-memory
  system (in `original_source/`) under its canonical import name `ultron.*`,
  so the merged Ultron tests, server, and clients resolve without duplicating code.
- Ultron integration entry points at the repository root: `ultrone.py`
  (evolution lab wiring), `ultron_client.py` and `memory_sync.py`
  (stdlib-only Ultron API clients), `server.py` / `server_state.py`
  (Ultron FastAPI server).
- Ultron skill packaging under `skills/ultron-1.0.0/` and persona/soul-preset
  data directories under `data/`.
- Adelise agent framework vendored under `adelise-agent-framework-main/` for
  reference and experimentation.

### Fixed

- **Global Eye console on GitHub Pages**: the deployed console never booted
  because every Cesium request 404'd. `vite-plugin-cesium` mirrors Vite's
  `base` into both `CESIUM_BASE_URL` and the build output directory, so the
  absolute `/ultrone/globe/` base copied the runtime to
  `dist/ultrone/globe/cesium/` while the document asked for
  `/ultrone/globe/cesium/…`. `apps/globe/vite.config.pages.js` now builds with
  a relative base (`./`), so the build works both from `dist/` locally and
  under the Pages subpath. Verified against a staged copy of the site: the
  Cesium runtime, widgets CSS, workers, snapshot and logo all load from
  `/ultrone/globe/`.
- **Deploy regression guard**: `apps/globe/scripts/qa-pages-assets.mjs`
  (run by `pages.yml` on the staged `site/globe` before upload, and locally via
  `npm run qa:pages-assets`) fails the deployment when a referenced asset is
  missing from the staged build, when a root-absolute reference escapes the
  deployed prefix, or when the Cesium runtime is copied below the site root
  again.
- The Global Eye logo asset is re-rooted at the Vite base (`src/logoGaze.js`),
  so the gaze animation loads its SVG under a subpath deployment instead of
  silently falling back to the static logo.
- Resolved the license contradiction: the repository uniformly uses the
  **MIT** license (README badge, `pyproject.toml`, deployment metadata).
  The stray Apache-2.0 `LICENSE` file that arrived with the Ultron merge was
  replaced with the MIT text.
- Replaced foreign-project documentation that had been flattened into the
  repository root and `docs/` (Bee/Adelise agent framework changelog,
  contributing guide, security policy, and module docs) with Ultrone-specific
  versions or relocations of the vendored copies.
- `scripts/` is no longer ignored by `.gitignore`; the analysis scripts
  referenced from the README (e.g. `scripts/run_bda_predictive_kc.py`) are
  now part of the repository.
- `ultrone.py` now imports the Ultron config and models through the
  `ultron` shim (`ultron.config`, `ultron.core.models`). The root-level
  `config.py` was permanently shadowed by the Ultrone `config/` package,
  making its `UltronConfig` import unreachable; the root `models.py` was a
  byte-identical duplicate of `ultron.core.models`.
- Guarded `ultrone.py`'s access to the optional `prediction_enabled` config
  flag (not defined by `UltronConfig`) and removed the non-existent
  `prediction_confidence` field from its `MemoryRecord` construction, so the
  self-evolution entry point runs end-to-end (`scripts/test_evolution.py`
  completes with live genome evolution cycles).
- Removed dead merge leftovers: root `config.py` (unreachable duplicate),
  root `models.py` (byte-identical duplicate of `ultron.core.models`),
  `README.md.bak`, and the unreferenced `Ultron.jpg`.
- Relocated the misnamed root file `inf` (a Loki Deployment Helm template)
  to `infra/helm/ultrone/templates/loki-deployment.yaml`, joining its
  sibling loki-configmap/service/statefulset templates.
- Renamed "ultron" to "ultrone" in the GitHub issue templates so they match
  the repository project.
- Pinned `starlette==0.36.3` compatibility: `fastapi 0.109.0` passes the
  removed `on_startup` kwarg to `Router.__init__`, which newer starlette
  versions reject; this unblocked `tests/api/test_repo_api.py` collection.
- Pinned `httpx<0.28` compatibility: starlette 0.36's `TestClient` passes
  the removed `app=` kwarg to `httpx.Client`, which httpx>=0.28 rejects;
  this unblocked the HITL and authentication API tests.
- Fixed an infinite loop in the MAPF planner
  (`brain/reasoning/search/mapf.py`): with wait moves legal, the `(x, y, t)`
  state space is unbounded, so when conflict-resolution bans walled an
  agent off from its goal the A* open set never emptied and the planner
  hung forever. The search is now bounded by a time horizon, the heap
  tie-breaker is deterministic (`itertools.count` instead of `id()`), and
  an agent's own goal cell can no longer be banned. The previously hanging
  `test_mapf_no_collisions_in_path` now passes.
- Fixed Windows-only test failures: `tests/core/test_logging.py` now closes
  removed log handlers so Windows can delete the temp log files, and
  `tests/services/test_allowlist_agents.py` asserts on path *names*
  instead of forward-slash suffixes that never match Windows backslash
  paths.
- Environment-dependent tests now skip gracefully instead of failing:
  `tests/test_server.py` (needs a dashscope embedding backend),
  `tests/utils/test_sanitizer.py` (needs presidio + spacy models),
  and the live ModelScope Hub integration tests
  (`tests/api/test_upload_download.py`, `test_watch_sync.py`,
  `test_client_integration.py`, which need `TOKEN`/`SERVER` credentials).
  `tests/services/test_memory_service.py` now injects a mock sanitizer so
  its unit tests no longer require presidio.
- Removed the pip-generated `build_artifacts/` directory (machine-specific
  build metadata) and updated `FOLDER_STRUCTURE_ANALYSIS.md` accordingly.

### Changed

- Python support aligned across documentation and packaging metadata:
  **Python 3.10+** (matches the `research-platform-ci.yml` test matrix of
  3.10 / 3.11 / 3.12).

## [3.0.0-EVO] - 2026-09-11

### Added

- Evolutionary self-improvement track: `evolution/` (genome, evolution lab,
  performance telemetry, agent evolver) and the `adaptive/` experimentation
  pipeline (evaluator, optimizer, parameter registry, promotion, skill library).
- Ultron collective-memory integration (Trajectory / Memory / Skill / Harness
  hubs) merged into the platform.

## [1.0.0] - 2026-08-05

### Added

- Initial public release of the Ultrone multi-domain battlefield AI research
  platform: 15-layer cognitive architecture, 7-tier memory system, safety
  gates, HITL audit chain, canonical benchmark suite, and the Gradio
  simulation-only public demo.
