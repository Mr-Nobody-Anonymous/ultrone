# Copyright (c) ModelScope Contributors. All rights reserved.
"""Enable ``python -m cli`` (from the repo root, once ``apps/`` is on path).

``python -m cli`` resolves this package via the ``apps/`` bucket; the
monorepo bootstrap below adds that bucket automatically when the CLI is
invoked as a plain script too.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
while not (_ROOT / "pyproject.toml").is_file() and _ROOT != _ROOT.parent:
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from _ultrone_paths import ensure_on_syspath  # type: ignore  # noqa: E402
    ensure_on_syspath(_ROOT)
except ImportError:
    pass

from . import main

if __name__ == "__main__":
    sys.exit(main())
