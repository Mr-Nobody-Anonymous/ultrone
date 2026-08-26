# Copyright (c) Ultrone Contributors. All rights reserved.
"""Backend loader: compiled Rust core when available, Python otherwise.

Mirrors the ``ultrone_bindings`` policy -- graceful degradation so the
whole platform stays functional without a Rust toolchain.
"""

from __future__ import annotations

import importlib
from types import ModuleType

from ultrone_rt import kernels as _python_kernels

_RUST_MODULE = "ultrone_core"

_rust: ModuleType | None = None
try:                                   # pragma: no cover - needs toolchain
    _rust = importlib.import_module(_RUST_MODULE)
except ImportError:
    _rust = None


def backend_info() -> dict:
    return {
        "backend": "rust" if _rust is not None else "python",
        "rust_available": _rust is not None,
        "rust_module": _RUST_MODULE,
        "reference": "ultrone_rt.kernels",
    }


def get_kernels():
    """Return the active kernel module.

    When the ``ultrone_core`` extension has been built (``maturin
    develop`` inside ``rust/ultrone_core``), its Rust classes are
    returned; otherwise the pure-Python references are used. Both sides
    expose identical class/function names and deterministic results.
    """
    return _rust if _rust is not None else _python_kernels