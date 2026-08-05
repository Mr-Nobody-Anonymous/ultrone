# Copyright (c) Ultrone Contributors. All rights reserved.
"""AST Code Analyzer — parse and analyze source code structure.

Uses Python's built-in `ast` module to analyze Python source code,
extracting functions, classes, imports, and structural information.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.CodeIntelligence.AST")


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str = ""
    args: List[str] = field(default_factory=list)
    returns: str = ""
    decorators: List[str] = field(default_factory=list)
    docstring: str = ""
    line_start: int = 0
    line_end: int = 0
    complexity: int = 0
    is_async: bool = False
    is_method: bool = False
    calls: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str = ""
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: str = ""
    line_start: int = 0
    line_end: int = 0
    decorators: List[str] = field(default_factory=list)


@dataclass
class ImportInfo:
    """Information about an import."""
    module: str = ""
    names: List[str] = field(default_factory=list)
    alias: str = ""
    line: int = 0


class ASTAnalyzer:
    """Analyze Python source code using the AST module.

    Provides:
    - Function and class extraction
    - Import analysis
    - Cyclomatic complexity calculation
    - Function call graph
    - Docstring extraction
    """

    def __init__(self) -> None:
        self._functions: List[FunctionInfo] = []
        self._classes: List[ClassInfo] = []
        self._imports: List[ImportInfo] = []
        self._errors: List[str] = []

    def analyze(self, source: str, filename: str = "<string>") -> Dict[str, Any]:
        """Analyze Python source code.

        Parameters
        ----------
        source : str
            Python source code to analyze.
        filename : str
            Filename for error reporting.

        Returns
        -------
        dict
            Analysis results with functions, classes, imports, and metrics.
        """
        self._functions = []
        self._classes = []
        self._imports = []
        self._errors = []

        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as e:
            self._errors.append(f"Syntax error: {e}")
            return self._format_result()

        # Walk the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._functions.append(self._analyze_function(node, is_method=False))
            elif isinstance(node, ast.AsyncFunctionDef):
                func = self._analyze_function(node, is_method=False)
                func.is_async = True
                self._functions.append(func)
            elif isinstance(node, ast.ClassDef):
                self._classes.append(self._analyze_class(node))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._imports.append(ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        alias=alias.asname or "",
                        line=node.lineno,
                    ))
            elif isinstance(node, ast.ImportFrom):
                self._imports.append(ImportInfo(
                    module=node.module or "",
                    names=[alias.asname or alias.name for alias in node.names],
                    alias="",
                    line=node.lineno,
                ))

        return self._format_result()

    def _analyze_function(self, node: ast.FunctionDef, is_method: bool) -> FunctionInfo:
        """Analyze a function definition."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        returns = ""
        if node.returns:
            try:
                returns = ast.unparse(node.returns)
            except Exception:
                returns = "?"

        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("?")

        docstring = ast.get_docstring(node) or ""

        # Find function calls
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        return FunctionInfo(
            name=node.name,
            args=args,
            returns=returns,
            decorators=decorators,
            docstring=docstring,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            complexity=self._compute_complexity(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            calls=list(set(calls)),
        )

    def _analyze_class(self, node: ast.ClassDef) -> ClassInfo:
        """Analyze a class definition."""
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                bases.append("?")

        decorators = []
        for dec in node.decorator_list:
            try:
                decorators.append(ast.unparse(dec))
            except Exception:
                decorators.append("?")

        methods = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._analyze_function(child, is_method=True)
                methods.append(method)
                # Also add to global functions list
                self._functions.append(method)

        return ClassInfo(
            name=node.name,
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node) or "",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=decorators,
        )

    def _compute_complexity(self, node: ast.AST) -> int:
        """Compute cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        return complexity

    def _format_result(self) -> Dict[str, Any]:
        """Format the analysis results."""
        total_lines = 0
        complexities = []
        for func in self._functions:
            total_lines += func.line_end - func.line_start + 1
            complexities.append(func.complexity)

        return {
            "functions": [
                {
                    "name": f.name,
                    "args": f.args,
                    "returns": f.returns,
                    "decorators": f.decorators,
                    "docstring": f.docstring[:200],
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "complexity": f.complexity,
                    "is_async": f.is_async,
                    "is_method": f.is_method,
                    "calls": f.calls,
                }
                for f in self._functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "bases": c.bases,
                    "methods": [m.name for m in c.methods],
                    "docstring": c.docstring[:200],
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                }
                for c in self._classes
            ],
            "imports": [
                {
                    "module": i.module,
                    "names": i.names,
                    "line": i.line,
                }
                for i in self._imports
            ],
            "metrics": {
                "num_functions": len(self._functions),
                "num_classes": len(self._classes),
                "num_imports": len(self._imports),
                "total_function_lines": total_lines,
                "avg_complexity": (
                    sum(complexities) / len(complexities) if complexities else 0.0
                ),
                "max_complexity": max(complexities) if complexities else 0,
            },
            "errors": self._errors,
        }

    def get_functions(self) -> List[FunctionInfo]:
        """Return all functions found."""
        return self._functions

    def get_classes(self) -> List[ClassInfo]:
        """Return all classes found."""
        return self._classes

    def get_imports(self) -> List[ImportInfo]:
        """Return all imports found."""
        return self._imports

    def find_function(self, name: str) -> Optional[FunctionInfo]:
        """Find a function by name."""
        for func in self._functions:
            if func.name == name:
                return func
        return None

    def find_class(self, name: str) -> Optional[ClassInfo]:
        """Find a class by name."""
        for cls in self._classes:
            if cls.name == name:
                return cls
        return None