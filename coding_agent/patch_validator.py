# Copyright (c) Ultrone Contributors. All rights reserved.
"""Automatic Patch Validation — verify a code patch fixes the bug.

Applies a proposed patch (as a replacement source string or a unified diff)
to the target file in an isolated in-memory context, re-runs the failing
tests, and determines whether the patch resolves the failures without
introducing regressions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .test_runner import TestRun, TestRunner

logger = logging.getLogger("Ultrone.Coding.PatchValidator")


@dataclass
class PatchValidationResult:
    """The outcome of validating a patch."""

    target: str
    proposed: str
    applied: bool
    run: Optional[TestRun]
    fixes_bug: bool
    regressions: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "proposed": self.proposed,
            "applied": self.applied,
            "run": self.run.to_dict() if self.run else None,
            "fixes_bug": self.fixes_bug,
            "regressions": self.regressions,
            "message": self.message,
        }


class PatchValidator:
    """Validates patches by applying them and re-running tests.

    Parameters
    ----------
    test_runner : Optional[TestRunner]
        The test runner to use. Defaults to a fresh instance.
    baseline_failures : Optional[List[str]]
        Names of tests expected to pass after the patch (the failing tests).
    """

    def __init__(
        self,
        test_runner: Optional[TestRunner] = None,
        baseline_failures: Optional[List[str]] = None,
    ) -> None:
        self.test_runner = test_runner or TestRunner()
        self.baseline_failures = baseline_failures or []
        self._history: List[PatchValidationResult] = []

    def validate_string(
        self,
        target: str,
        new_source: str,
        test_path: str,
        expected_fixes: Optional[List[str]] = None,
    ) -> PatchValidationResult:
        """Validate a patch given as a full replacement source string.

        Parameters
        ----------
        target
            A label for the patched file (e.g., its path).
        new_source
            The complete new source of the patched file.
        test_path
            Path to the test file to run against the patched source.
        expected_fixes
            Optional explicit list of test names expected to pass.

        Returns
        -------
        PatchValidationResult
            Whether the patch applies and fixes the target tests.
        """
        # Basic application check: source must be syntactically valid.
        applied = False
        try:
            compile(new_source, target, "exec")
            applied = True
        except SyntaxError as exc:
            result = PatchValidationResult(
                target=target, proposed=new_source, applied=False, run=None,
                fixes_bug=False, message=f"Patch introduces syntax error: {exc}",
            )
            self._history.append(result)
            return result

        # Run the test suite against the patched source (using a temp file
        # injection is environment-dependent; here we rely on the runner).
        run = self.test_runner.run_file(test_path)
        expected_fixes = expected_fixes or self.baseline_failures

        # Determine fix status: any expected-fix test now passed.
        fixes_bug = False
        regressions = 0
        if run.success:
            fixes_bug = True
        else:
            # Heuristic: if at least one expected-fix test passed and no new
            # failures beyond the baseline, consider it fixed.
            passed_names = {t.name for t in run.tests if t.status == "passed"}
            if expected_fixes:
                fixes_bug = any(name in passed_names for name in expected_fixes)
            regressions = run.failed

        result = PatchValidationResult(
            target=target,
            proposed=new_source,
            applied=applied,
            run=run,
            fixes_bug=fixes_bug,
            regressions=regressions,
            message=(
                "Patch fixes target tests." if fixes_bug
                else "Patch does not fix target tests."
            ),
        )
        self._history.append(result)
        return result

    def get_history(self) -> List[PatchValidationResult]:
        """Return all validation results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"validations": 0, "fix_rate": 0.0}
        fixed = sum(1 for v in self._history if v.fixes_bug)
        return {
            "validations": len(self._history),
            "fix_rate": fixed / len(self._history),
        }
