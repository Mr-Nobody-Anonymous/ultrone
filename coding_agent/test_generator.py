# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit Test Generator — generate unit tests from AST analysis.

Creates pytest-style unit test source for a function or class based on its
signature and a set of example inputs/expected outputs. Output is deterministic
and structured so the dynamic test runner can execute it.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .ast_analyzer import ASTAnalysis, FunctionInfo

logger = logging.getLogger("Ultrone.Coding.TestGenerator")


class UnitTestGenerator:
    """Generates unit test source code from code analysis."""

    def generate_for_function(
        self,
        analysis: ASTAnalysis,
        function_name: str,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate a pytest test module for a single function.

        Parameters
        ----------
        analysis
            The AST analysis of the containing file.
        function_name
            The function to generate tests for.
        examples
            Optional list of ``[{"args": [...], "expected": ...}]`` examples.

        Returns
        -------
        str
            Generated pytest source code.
        """
        fn = self._find_function(analysis, function_name)
        if fn is None:
            raise ValueError(f"Function '{function_name}' not found in analysis")

        examples = examples or [self._default_example(fn)]
        lines = [
            '"""Auto-generated unit tests."""',
            "import pytest",
            "",
            f"# Tests for {function_name}",
            "",
        ]
        for i, example in enumerate(examples):
            args_repr = ", ".join(repr(a) for a in example.get("args", []))
            expected_repr = repr(example.get("expected"))
            lines += [
                f"def test_{function_name}_{i}():",
                f"    result = {function_name}({args_repr})",
                f"    assert result == {expected_repr}",
                "",
            ]
        return "\n".join(lines)

    def generate_for_class(
        self,
        analysis: ASTAnalysis,
        class_name: str,
        examples: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> str:
        """Generate pytest tests for a class's methods.

        Parameters
        ----------
        analysis
            The AST analysis of the containing file.
        class_name
            The class to generate tests for.
        examples
            Optional mapping of method name to example list.

        Returns
        -------
        str
            Generated pytest source code.
        """
        cls = self._find_class(analysis, class_name)
        if cls is None:
            raise ValueError(f"Class '{class_name}' not found in analysis")

        examples = examples or {}
        lines = [
            '"""Auto-generated class tests."""',
            "import pytest",
            "",
            f"# Tests for {class_name}",
            "",
        ]
        for method in cls.methods:
            method_examples = examples.get(method, [self._default_method_example(method)])
            for i, example in enumerate(method_examples):
                args_repr = ", ".join(repr(a) for a in example.get("args", []))
                expected_repr = repr(example.get("expected"))
                lines += [
                    f"def test_{class_name}_{method}_{i}():",
                    f"    obj = {class_name}()",
                    f"    result = obj.{method}({args_repr})",
                    f"    assert result == {expected_repr}",
                    "",
                ]
        return "\n".join(lines)

    @staticmethod
    def _find_function(analysis: ASTAnalysis, name: str) -> Optional[FunctionInfo]:
        """Find a function by name in the analysis."""
        for fn in analysis.functions:
            if fn.name == name and not fn.is_method:
                return fn
        for fn in analysis.functions:
            if fn.name == name:
                return fn
        return None

    @staticmethod
    def _find_class(analysis: ASTAnalysis, name: str):
        """Find a class by name in the analysis."""
        for cls in analysis.classes:
            if cls.name == name:
                return cls
        return None

    @staticmethod
    def _default_example(fn: FunctionInfo) -> Dict[str, Any]:
        """Build a default (zero-arg) example based on the signature."""
        args = [] if not fn.args else [None] * len(fn.args)
        return {"args": args, "expected": None}

    @staticmethod
    def _default_method_example(method: str) -> Dict[str, Any]:
        """Build a default example for a method."""
        return {"args": [], "expected": None}

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {"type": "UnitTestGenerator"}
