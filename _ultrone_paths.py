# Copyright (c) Ultrone Contributors. All rights reserved.
"""Monorepo import-path bootstrap for ULTRONE.

After the repository reorganization every module KEEPS its top-level import
name (``import cognitive``, ``import brain``, ``import agents``, ...), but the
directories now live inside semantic buckets (``apps/``, ``packages/<area>/``,
``research/``, ``simulation/``, ``vendor/``).

This helper puts every bucket on ``sys.path`` so the original import names
keep resolving no matter which entry point the process starts from.

Usage (from any entry script / console):

    from _ultrone_paths import ensure_on_syspath
    ensure_on_syspath()          # repo root is auto-detected
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Bucket directories (relative to the repo root) that hold importable
#: top-level packages. Order matters for shadowing: apps first.
BUCKETS: tuple[str, ...] = (
    "apps",
    "packages/core",
    "packages/cognition",
    "packages/agents",
    "packages/knowledge",
    "packages/orchestration",
    "packages/runtime",
    "packages/safety",
    "packages/observability",
    "packages/transport",
    "research",
    "simulation",
    "vendor",
    "data",
)


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from *start* (default: this file) to the ULTRONE repo root."""
    node = Path(start or ROOT).resolve()
    if node.is_file():
        node = node.parent
    while True:
        if (node / "pyproject.toml").is_file():
            return node
        if node.parent == node:
            return ROOT
        node = node.parent


def ensure_on_syspath(root: Path | None = None) -> Path:
    """Insert every importable bucket (plus the repo root) into ``sys.path``.

    Returns the detected repo root.

    Ordering contract: after this call, ``sys.path`` starts with
    ``[repo_root, apps, packages/core, ..., data]`` — i.e. the FIRST bucket
    listed in :data:`BUCKETS` gets the HIGHEST priority, matching
    ``pytest.ini``'s ``pythonpath`` semantics (pytest inserts ini entries in
    reverse order for the same effect).

    This matters for the one cross-bucket name collision in the repo:
    ``packages/core/core/`` (package) vs ``simulation/core.py`` (module).
    ``packages/core`` must win so ``import core.contracts`` resolves to the
    package; ``simulation.core`` is always imported fully-qualified
    (``from simulation.core import ...``) and therefore still works.
    """
    repo_root = find_repo_root(root if root is not None and Path(root).is_dir() else None)
    entries = [repo_root] + [repo_root / b for b in BUCKETS]
    # Insert in reverse so the final sys.path order equals `entries`
    # (front-insertion puts the last-inserted entry first).
    for entry in reversed(entries):
        if not entry.is_dir():
            continue
        path = str(entry)
        if path not in sys.path:
            sys.path.insert(0, path)
    return repo_root


if __name__ == "__main__":
    root = ensure_on_syspath()
    print(f"ULTRONE repo root: {root}")
    for bucket in BUCKETS:
        if (root / bucket).is_dir():
            print(f"  on sys.path: {bucket}")