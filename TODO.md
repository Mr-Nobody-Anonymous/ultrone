# CI Fix Task — ULTRONE Research Platform

## Goal
Fix GitHub Actions CI failure: `ModuleNotFoundError: No module named 'numpy'` / `'torch'` during test collection.

## Root Cause
`requirements.txt` does not exist in the repo, so the CI workflow's conditional
`pip install -r requirements.txt` is silently skipped. The workflow only installs
`pytest`/`fastapi`/`pydantic`, which do not provide `numpy`/`torch` that the
test-suite imports at module load time.

## Steps
- [x] 1. Create `requirements.txt` with all runtime/test dependencies
- [x] 2. Update `.github/workflows/research-platform-ci.yml`:
       - Install `requirements.txt` unconditionally
       - Add pip dependency caching
       - Add `concurrency` guard to cancel stale runs
       - Consolidate redundant test runs / fix coverage collection path
- [x] 3. Update `infra/docker/Dockerfile.research`:
       - Remove `|| true` so dependency install failures are not silently swallowed
       - Install `requirements.txt` (now present) instead of hardcoded package list
- [x] 4. Validate: run tests locally (if environment allows) to confirm imports resolve
       → `307 passed` (pytest tests/ --tb=short -q) — full suite green

