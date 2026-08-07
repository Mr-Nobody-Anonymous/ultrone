# Copyright (c) Ultrone Contributors. All rights reserved.
"""Dynamic Test Runner — execute tests and collect results.

Runs pytest/unittest suites (or a single test function) in an isolated
process and captures pass/fail/error results, coverage of executed tests,
and duration. Output is structured for patch validation and bug localization.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Coding.TestRunner")


@dataclass
class TestResult:
    """The outcome of a single executed test."""

    name: str
    status: str  # passed | failed | error | skipped
    duration_ms: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


@dataclass
class TestRun:
    """The aggregate result of a test run."""

    target: str
    tests: List[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    success: bool = True
    output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "tests": [t.to_dict() for t in self.tests],
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "output": self.output,
        }


class TestRunner:
    """Runs tests and parses structured results."""

    def __init__(self, timeout_seconds: int = 120) -> None:
        self.timeout_seconds = timeout_seconds
        self._history: List[TestRun] = []

    def run_file(self, path: str) -> TestRun:
        """Run a test file (pytest or unittest compatible).

        Parameters
        ----------
        path
            Path to the test file.

        Returns
        -------
        TestRun
            Parsed test results.
        """
        start = time.time()
        cmd = [sys.executable, "-m", "pytest", path, "-q", "--no-header", "-p", "no:cacheprovider"]
        run = TestRun(target=path)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout_seconds,
                cwd=os.path.dirname(os.path.abspath(path)),
            )
            run.output = proc.stdout + proc.stderr
            run.duration_seconds = time.time() - start
            self._parse_pytest_output(run, proc.returncode)
        except subprocess.TimeoutExpired:
            run.output = "Test run timed out."
            run.success = False
            run.duration_seconds = time.time() - start
            logger.warning("Test run timed out for %s", path)
        except Exception as exc:  # noqa: BLE001
            run.output = f"Failed to run tests: {exc}"
            run.success = False
            run.duration_seconds = time.time() - start

        self._history.append(run)
        return run

    def run_function(self, code: str, fn_name: str) -> TestResult:
        """Execute a single function in an isolated namespace.

        Parameters
        ----------
        code
            The source code defining the function.
        fn_name
            The function name to invoke.

        Returns
        -------
        TestResult
            Pass/fail/error for the invocation.
        """
        start = time.time()
        namespace: Dict[str, Any] = {}
        try:
            exec(compile(code, "<function>", "exec"), namespace)  # noqa: S102
            fn = namespace.get(fn_name)
            if fn is None:
                return TestResult(fn_name, "error", 0.0, f"Function '{fn_name}' not found")
            fn()  # Call with no args; callers supply richer tests separately.
            return TestResult(fn_name, "passed", (time.time() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            return TestResult(fn_name, "error", (time.time() - start) * 1000, str(exc))

    def _parse_pytest_output(self, run: TestRun, returncode: int) -> None:
        """Parse pytest output into structured TestResult entries."""
        run.success = returncode == 0
        for line in run.output.splitlines():
            line = line.strip()
            if line.startswith("PASSED"):
                run.passed += 1
                run.tests.append(TestResult(line, "passed"))
            elif line.startswith("FAILED"):
                run.failed += 1
                run.tests.append(TestResult(line, "failed"))
            elif line.startswith("ERROR"):
                run.errors += 1
                run.tests.append(TestResult(line, "error"))
            elif line.startswith("SKIPPED"):
                run.skipped += 1
                run.tests.append(TestResult(line, "skipped"))
            elif "passed" in line and "failed" in line:
                # Summary line like "3 passed, 1 failed in 0.5s"
                self._parse_summary(run, line)

    def _parse_summary(self, run: TestRun, line: str) -> None:
        """Parse pytest summary counts."""
        import re
        for match in re.finditer(r"(\d+)\s+(passed|failed|error|skipped)", line):
            count = int(match.group(1))
            kind = match.group(2)
            if kind == "passed":
                run.passed = count
            elif kind == "failed":
                run.failed = count
            elif kind == "error":
                run.errors = count
            elif kind == "skipped":
                run.skipped = count

    def get_history(self) -> List[TestRun]:
        """Return all test runs."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"runs": 0, "pass_rate": 0.0}
        total = sum(r.passed + r.failed for r in self._history)
        passed = sum(r.passed for r in self._history)
        return {
            "runs": len(self._history),
            "pass_rate": (passed / total) if total else 0.0,
        }
