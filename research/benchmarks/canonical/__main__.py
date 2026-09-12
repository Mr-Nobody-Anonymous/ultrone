"""CLI entry point so the regression gate can run as a module.

    python -m benchmarks.canonical [--update-baselines] [--output FILE]

Delegates to :func:`benchmarks.canonical.baselines.main`; exits non-zero on
any baseline/regression violation (the CI gate semantics).
"""

import sys

from benchmarks.canonical.baselines import main

if __name__ == "__main__":
    sys.exit(main())
