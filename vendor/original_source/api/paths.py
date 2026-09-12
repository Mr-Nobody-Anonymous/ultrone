# Copyright (c) ModelScope Contributors. All rights reserved.
import os

# Monorepo note: this vendored tree lives under ``vendor/original_source/``.
# The dashboard and skills packages moved to ``apps/dashboard/`` and
# ``packages/agents/skills/`` respectively; resolve from this file's location
# (vendor/original_source/api -> 3 levels up = repo root).
_VENDORED_API_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_VENDORED_API_DIR, "..", "..", ".."))

_DASHBOARD_DIR = os.path.join(_REPO_ROOT, "apps", "dashboard")
DASHBOARD_DIR = os.path.normpath(_DASHBOARD_DIR)
DASHBOARD_DIST = os.path.join(DASHBOARD_DIR, "dist")
AGENT_SKILL_PACKAGE_DIR = os.path.normpath(
    os.path.join(_REPO_ROOT, "packages", "agents", "skills", "ultron-1.0.0")
)
SKILLS_ROOT = os.path.normpath(os.path.join(_REPO_ROOT, "packages", "agents", "skills"))
