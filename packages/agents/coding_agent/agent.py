"""Coding agent for software engineering tasks.

Extends the base coding agent with the full SWE automation stack:
AST analysis, repository indexing, symbol search, static analysis, dynamic
test running, unit test generation, bug localization, and patch validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .ast_analyzer import ASTAnalysis, ASTAnalyzer
from .repository_indexer import RepositoryIndex, RepositoryIndexer
from .symbol_search import SymbolSearcher, SymbolSearchResult
from .static_analysis import StaticAnalyzer, StaticIssue
from .test_runner import TestRunner, TestRun
from .test_generator import UnitTestGenerator
from .bug_localizer import BugLocalizer, BugLocalizationResult
from .patch_validator import PatchValidator, PatchValidationResult

logger = logging.getLogger("Ultrone.Coding.Agent")


@dataclass
class TaskResult:
    """The result of a coding task."""

    task: str = ""
    success: bool = False
    output: str = ""
    files_modified: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class CodingAgent:
    """Autonomous software engineering agent.

    Parameters
    ----------
    workspace : str
        The repository root directory to operate within.
    """

    def __init__(self, workspace: str = ".") -> None:
        self.workspace = workspace
        self._history: List[TaskResult] = []
        self.ast_analyzer = ASTAnalyzer()
        self.repository_indexer = RepositoryIndexer(self.ast_analyzer)
        self.symbol_searcher = SymbolSearcher()
        self.static_analyzer = StaticAnalyzer()
        self.test_runner = TestRunner()
        self.test_generator = UnitTestGenerator()
        self.bug_localizer = BugLocalizer(self.static_analyzer)
        self.patch_validator = PatchValidator(self.test_runner)
        self._repository_index: Optional[RepositoryIndex] = None

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def analyze_code(self, path: str) -> TaskResult:
        """Analyze a Python source file and return its AST structure."""
        try:
            analysis = self.ast_analyzer.analyze_file(self._resolve(path))
            summary = (
                f"Analyzed {path}: {len(analysis.functions)} functions, "
                f"{len(analysis.classes)} classes, {len(analysis.imports)} imports"
            )
            result = TaskResult(
                task=f"analyze:{path}",
                success=not analysis.errors,
                output=summary,
                errors=analysis.errors,
            )
        except Exception as exc:  # noqa: BLE001
            result = TaskResult(task=f"analyze:{path}", success=False, errors=[str(exc)])
        self._history.append(result)
        return result

    def analyze_string(self, code: str, source_path: str = "<string>") -> ASTAnalysis:
        """Analyze a string of Python source code."""
        return self.ast_analyzer.analyze_string(code, source_path)

    # ------------------------------------------------------------------
    # Code writing / patching
    # ------------------------------------------------------------------
    def write_code(self, path: str, content: str) -> TaskResult:
        """Write source code to a file."""
        try:
            full_path = self._resolve(path)
            with open(full_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            result = TaskResult(
                task=f"write:{path}",
                success=True,
                output=f"Wrote {len(content)} bytes to {path}",
                files_modified=[path],
            )
        except Exception as exc:  # noqa: BLE001
            result = TaskResult(task=f"write:{path}", success=False, errors=[str(exc)])
        self._history.append(result)
        return result

    # ------------------------------------------------------------------
    # Static analysis & searching
    # ------------------------------------------------------------------
    def run_static_analysis(self, path: str) -> List[StaticIssue]:
        """Run static analysis on a source file."""
        return self.static_analyzer.analyze_file(self._resolve(path))

    def index_repository(self, include: Optional[List[str]] = None) -> RepositoryIndex:
        """Build and cache a repository index."""
        self._repository_index = self.repository_indexer.index(self.workspace, include=include)
        return self._repository_index

    def search_symbols(self, query: str, limit: int = 50) -> SymbolSearchResult:
        """Search the repository index for a symbol."""
        if self._repository_index is None:
            self.index_repository()
        return self.symbol_searcher.search(self._repository_index, query, limit=limit)

    # ------------------------------------------------------------------
    # Testing
    # ------------------------------------------------------------------
    def run_tests(self, test_path: str = "tests/") -> TaskResult:
        """Run a test file or directory and return structured results."""
        try:
            run = self.test_runner.run_file(self._resolve(test_path))
            output = (
                f"Tests: {run.passed} passed, {run.failed} failed, "
                f"{run.errors} errors, {run.skipped} skipped "
                f"({run.duration_seconds:.2f}s)"
            )
            result = TaskResult(
                task="run_tests",
                success=run.success,
                output=output,
                errors=[] if run.success else ["One or more tests failed"],
            )
        except Exception as exc:  # noqa: BLE001
            result = TaskResult(task="run_tests", success=False, errors=[str(exc)])
        self._history.append(result)
        return result

    def run_test_file(self, path: str) -> TestRun:
        """Run a test file and return the raw TestRun."""
        return self.test_runner.run_file(self._resolve(path))

    # ------------------------------------------------------------------
    # Test generation
    # ------------------------------------------------------------------
    def generate_tests(
        self,
        path: str,
        function_name: str,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate unit tests for a function in a source file."""
        analysis = self.ast_analyzer.analyze_file(self._resolve(path))
        return self.test_generator.generate_for_function(analysis, function_name, examples)

    # ------------------------------------------------------------------
    # Bug localization & patching
    # ------------------------------------------------------------------
    def localize_bugs(
        self,
        run: TestRun,
        source_files: Optional[Dict[str, str]] = None,
    ) -> BugLocalizationResult:
        """Localize bugs from a failing test run."""
        return self.bug_localizer.localize(run, self._repository_index, source_files)

    def validate_patch(self, target: str, new_source: str, test_path: str) -> PatchValidationResult:
        """Validate a code patch against the test suite."""
        return self.patch_validator.validate_string(target, new_source, self._resolve(test_path))

    # ------------------------------------------------------------------
    # Refactoring
    # ------------------------------------------------------------------
    def refactor(self, path: str) -> TaskResult:
        """Analyze a file and report refactoring suggestions."""
        issues = self.static_analyzer.analyze_file(self._resolve(path))
        suggestions = [
            i.message for i in issues if i.severity in ("warning", "error")
        ]
        result = TaskResult(
            task=f"refactor:{path}",
            success=True,
            output=f"Refactoring suggestions for {path}: {len(suggestions)} found"
            if suggestions else f"No refactoring needed for {path}",
            files_modified=[path],
            errors=suggestions,
        )
        self._history.append(result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve(self, path: str) -> str:
        """Resolve a path against the workspace root."""
        import os
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace, path)

    @property
    def history(self) -> List[TaskResult]:
        """Return the task history."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the agent."""
        return {
            "type": "CodingAgent",
            "workspace": self.workspace,
            "tasks_completed": len(self._history),
            "success_rate": (
                sum(1 for t in self._history if t.success) / len(self._history)
                if self._history
                else 0.0
            ),
            "repository_indexed": self._repository_index is not None,
        }
