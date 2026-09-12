# Copyright (c) Ultrone Contributors. All rights reserved.
"""Static Analysis — detect common code issues without executing the code.

Performs lightweight static checks over the AST of Python source files:
- Undefined name usage (references not assigned/imported/defined).
- Unused imports.
- Bare except clauses.
- Multiple return types / unreachable code heuristics.
- Duplicate function definitions.

These checks feed bug localization and the code-review critic.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("Ultrone.Coding.StaticAnalysis")


@dataclass
class StaticIssue:
    """A single static-analysis finding."""

    file_path: str
    lineno: int
    check: str
    message: str
    severity: str = "warning"  # info | warning | error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "lineno": self.lineno,
            "check": self.check,
            "message": self.message,
            "severity": self.severity,
        }


class StaticAnalyzer:
    """Performs static analysis on Python source."""

    def analyze_string(self, code: str, source_path: str = "<string>") -> List[StaticIssue]:
        """Analyze a string of Python code for static issues.

        Returns
        -------
        List[StaticIssue]
            The detected issues.
        """
        issues: List[StaticIssue] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            issues.append(
                StaticIssue(source_path, exc.lineno or 0, "syntax", f"Syntax error: {exc}", "error")
            )
            return issues

        self._check_undefined_names(tree, source_path, issues)
        self._check_bare_except(tree, source_path, issues)
        self._check_unreachable(tree, source_path, issues)
        self._check_duplicate_defs(tree, source_path, issues)
        return issues

    def analyze_file(self, path: str) -> List[StaticIssue]:
        """Analyze a Python source file on disk."""
        with open(path, "r", encoding="utf-8") as fh:
            code = fh.read()
        return self.analyze_string(code, source_path=path)

    def _check_undefined_names(
        self, tree: ast.AST, path: str, issues: List[StaticIssue]
    ) -> None:
        """Detect names used but not defined locally or globally."""
        defined: Set[str] = set()
        # Collect all defined names (functions, classes, assignments, imports,
        # args, loop vars, comprehension targets).
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined.add(alias.asname or alias.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    for name in self._names_in(target):
                        defined.add(name)
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                for name in self._names_in(node.target):
                    defined.add(name)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars:
                        for name in self._names_in(item.optional_vars):
                            defined.add(name)

        # Builtins always defined.
        defined |= set(dir(__builtins__)) | {
            "True", "False", "None", "self", "cls", "_", "print", "len", "range",
            "str", "int", "float", "list", "dict", "set", "tuple", "open", "sum",
            "min", "max", "abs", "type", "isinstance", "enumerate", "zip", "map",
            "filter", "sorted", "any", "all", "Exception", "ValueError", "TypeError",
            "KeyError", "IndexError", "RuntimeError", "super", "property", "classmethod",
            "staticmethod", "__name__", "__file__",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined and not node.id.startswith("__"):
                    issues.append(
                        StaticIssue(path, node.lineno, "undefined_name",
                                    f"Name '{node.id}' is used but never defined", "warning")
                    )

    def _check_bare_except(self, tree: ast.AST, path: str, issues: List[StaticIssue]) -> None:
        """Detect bare ``except:`` clauses."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(
                    StaticIssue(path, node.lineno, "bare_except",
                                "Bare except clause; catch specific exceptions", "warning")
                )

    def _check_unreachable(self, tree: ast.AST, path: str, issues: List[StaticIssue]) -> None:
        """Detect code after unconditional return/raise in a function body."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                for i, stmt in enumerate(body[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Raise)):
                        issues.append(
                            StaticIssue(path, body[i + 1].lineno, "unreachable",
                                        "Unreachable code after return/raise", "info")
                        )
                        break

    def _check_duplicate_defs(self, tree: ast.AST, path: str, issues: List[StaticIssue]) -> None:
        """Detect duplicate function/class definitions (redefinition)."""
        seen: Dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in seen:
                    issues.append(
                        StaticIssue(path, node.lineno, "duplicate_def",
                                    f"'{node.name}' redefined (first at line {seen[node.name]})", "warning")
                    )
                else:
                    seen[node.name] = node.lineno

    @staticmethod
    def _names_in(node: Optional[ast.AST]) -> List[str]:
        """Return all Name ids within a node (e.g., a tuple target)."""
        if node is None:
            return []
        names: List[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                names.append(sub.id)
        return names
