# Copyright (c) Ultrone Contributors. All rights reserved.
"""Automatic Bug Localization — rank likely bug locations for failing tests.

Combines static analysis findings with failing-test tracebacks to rank the
most probable bug locations in a repository. Uses a simple scored heuristic:
- Static issues (undefined names, bare except, etc.) add weight.
- Functions referenced in the failing test traceback add weight.
- Files with more functions involved in the traceback rank higher.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .repository_indexer import RepositoryIndex
from .static_analysis import StaticAnalyzer, StaticIssue
from .test_runner import TestResult, TestRun

logger = logging.getLogger("Ultrone.Coding.BugLocalizer")


@dataclass
class BugLocation:
    """A ranked candidate bug location."""

    file_path: str
    score: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "score": self.score,
            "reasons": self.reasons,
        }


@dataclass
class BugLocalizationResult:
    """The ranked list of bug locations for a failing run."""

    run: TestRun
    locations: List[BugLocation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "locations": [l.to_dict() for l in self.locations],
        }


class BugLocalizer:
    """Localizes bugs by combining static analysis and test tracebacks.

    Parameters
    ----------
    static_analyzer : Optional[StaticAnalyzer]
        The static analyzer to use. Defaults to a fresh instance.
    """

    def __init__(self, static_analyzer: Optional[StaticAnalyzer] = None) -> None:
        self.static_analyzer = static_analyzer or StaticAnalyzer()
        self._history: List[BugLocalizationResult] = []

    def localize(
        self,
        run: TestRun,
        index: Optional[RepositoryIndex] = None,
        source_files: Optional[Dict[str, str]] = None,
    ) -> BugLocalizationResult:
        """Localize bugs for a failing test run.

        Parameters
        ----------
        run
            The failing (or partially failing) test run.
        index
            Optional repository index for symbol/file context.
        source_files
            Optional mapping of file path to source code for static analysis.

        Returns
        -------
        BugLocalizationResult
            Ranked candidate bug locations.
        """
        scores: Dict[str, float] = {}
        reasons: Dict[str, List[str]] = {}

        # 1. Traceback-based weights.
        for test in run.tests:
            if test.status in ("failed", "error") and test.message:
                for path in self._extract_files(test.message):
                    scores[path] = scores.get(path, 0.0) + 2.0
                    reasons.setdefault(path, []).append("Referenced in failing test traceback")

        # 2. Static analysis weights.
        if source_files:
            for path, code in source_files.items():
                issues = self.static_analyzer.analyze_string(code, path)
                severe = [
                    i for i in issues
                    if i.severity in ("error", "warning") and i.check in
                    ("undefined_name", "syntax", "bare_except")
                ]
                if severe:
                    scores[path] = scores.get(path, 0.0) + 1.0
                    reasons.setdefault(path, []).append(
                        f"{len(severe)} static issues: {severe[0].check}"
                    )

        # 3. Index-based: files with many symbols.
        if index is not None:
            for file_index in index.files:
                if file_index.symbols:
                    scores[file_index.path] = scores.get(file_index.path, 0.0) + 0.1 * min(
                        5, len(file_index.symbols)
                    )

        locations = sorted(
            (BugLocation(path, score, reasons.get(path, [])) for path, score in scores.items()),
            key=lambda loc: loc.score,
            reverse=True,
        )
        result = BugLocalizationResult(run=run, locations=locations)
        self._history.append(result)
        return result

    @staticmethod
    def _extract_files(traceback_message: str) -> List[str]:
        """Extract .py file paths referenced in a traceback message."""
        return list(set(re.findall(r'([\w./\\-]+\.py)', traceback_message)))

    def get_history(self) -> List[BugLocalizationResult]:
        """Return all localization results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {
            "localizations": len(self._history),
            "avg_locations": (
                sum(len(r.locations) for r in self._history) / len(self._history)
                if self._history
                else 0
            ),
        }
