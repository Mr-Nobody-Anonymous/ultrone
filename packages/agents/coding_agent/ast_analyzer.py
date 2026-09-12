# Copyright (c) Ultrone Contributors. All rights reserved.
"""AST Code Analyzer — parse Python source into an abstract syntax tree (AST).

The AST analyzer extracts structural information (functions, classes, imports,
calls, assignments) needed for static analysis, symbol search, test generation,
and bug localization. It uses only the standard library ``ast`` module.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Coding.AST")


@dataclass
class FunctionInfo:
    """Metadata for a function or method definition."""

    name: str
    lineno: int
    end_lineno: int
    args: List[str]
    is_async: bool = False
    is_method: bool = False
    returns: Optional[str] = None
    decorators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "args": self.args,
            "is_async": self.is_async,
            "is_method": self.is_method,
            "returns": self.returns,
            "decorators": self.decorators,
        }


@dataclass
class ClassInfo:
    """Metadata for a class definition."""

    name: str
    lineno: int
    end_lineno: int
    bases: List[str]
    methods: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "bases": self.bases,
            "methods": self.methods,
        }


@dataclass
class CallSite:
    """A call expression found in the source."""

    name: str
    lineno: int
    args_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "lineno": self.lineno, "args_count": self.args_count}


@dataclass
class ASTAnalysis:
    """Full structural analysis of a source file."""

    source_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    calls: List[CallSite] = field(default_factory=list)
    assignments: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_path": self.source_path,
            "functions": [f.to_dict() for f in self.functions],
            "classes": [c.to_dict() for c in self.classes],
            "imports": self.imports,
            "calls": [c.to_dict() for c in self.calls],
            "assignments": self.assignments,
            "errors": self.errors,
        }


class ASTAnalyzer:
    """Parses and analyzes Python source code via the AST module."""

    def analyze_string(self, code: str, source_path: str = "<string>") -> ASTAnalysis:
        """Analyze a string of Python source code.

        Parameters
        ----------
        code
            The Python source code to analyze.
        source_path
            A label for the source (defaults to ``"<string>"``).

        Returns
        -------
        ASTAnalysis
            The structural analysis result.
        """
        analysis = ASTAnalysis(source_path=source_path)
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            analysis.errors.append(f"SyntaxError: {exc}")
            logger.warning("Syntax error in %s: %s", source_path, exc)
            return analysis

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis.functions.append(
                    FunctionInfo(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", node.lineno),
                        args=[a.arg for a in node.args.args],
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        returns=self._format_annotation(node.returns),
                        decorators=[self._format_decorator(d) for d in node.decorator_list],
                    )
                )
            elif isinstance(node, ast.ClassDef):
                analysis.classes.append(
                    ClassInfo(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=getattr(node, "end_lineno", node.lineno),
                        bases=[self._format_name(b) for b in node.bases],
                    )
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis.imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.Call):
                analysis.calls.append(
                    CallSite(
                        name=self._format_name(node.func),
                        lineno=node.lineno,
                        args_count=len(node.args),
                    )
                )
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    name = self._format_name(target)
                    if name:
                        analysis.assignments.append(name)

        # Populate class methods.
        for cls_node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for cls_info in analysis.classes:
                if cls_info.name == cls_node.name:
                    for child in cls_node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            cls_info.methods.append(child.name)
                            # Mark as method.
                            for fn in analysis.functions:
                                if fn.name == child.name and fn.lineno == child.lineno:
                                    fn.is_method = True
        return analysis

    def analyze_file(self, path: str) -> ASTAnalysis:
        """Analyze a Python source file on disk."""
        with open(path, "r", encoding="utf-8") as fh:
            code = fh.read()
        return self.analyze_string(code, source_path=path)

    @staticmethod
    def _format_annotation(node: Optional[ast.AST]) -> Optional[str]:
        """Format a type annotation node to a string."""
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _format_name(node: Optional[ast.AST]) -> str:
        """Format an AST name/attribute node to a dotted string."""
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _format_decorator(node: ast.AST) -> str:
        """Format a decorator node to a string."""
        try:
            return "@" + ast.unparse(node)
        except Exception:  # noqa: BLE001
            return ""
