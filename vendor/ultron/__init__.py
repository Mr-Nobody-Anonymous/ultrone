# Copyright (c) Ultrone Contributors. All rights reserved.
"""Compatibility shim: expose the vendored Ultron memory system as ``ultron``.

The Ultron collective-memory project (ModelScope) is vendored under
``original_source/``. Its modules import each other via the absolute package
name ``ultron.*`` (e.g. ``from ultron.core.models import MemoryRecord``).
This package makes that resolve without duplicating any code:

    import ultron                      -> original_source/__init__.py
    from ultron.api.sdk import Ultron  -> original_source/api/sdk/ultron.py

It works by pointing this package's ``__path__`` at ``original_source/`` and
executing the vendored ``__init__.py`` in this namespace, so every
``ultron.<submodule>`` import resolves inside the vendored tree.
"""

from __future__ import annotations

from pathlib import Path

_DEST = Path(__file__).resolve().parent.parent / "original_source"

if not (_DEST / "__init__.py").is_file():
    raise ImportError(
        "ultron alias target 'original_source/' not found; "
        "the vendored Ultron sources are missing"
    )

# Route ultron.<submodule> imports into the vendored tree.
__path__ = [str(_DEST)]

# Adopt the vendored package's public API (Ultron, configs, models, ...).
_vendored_init = _DEST / "__init__.py"
exec(
    compile(_vendored_init.read_text(encoding="utf-8"), str(_vendored_init), "exec"),
    globals(),
)
