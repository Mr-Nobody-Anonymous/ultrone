# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the extended CodingAgent SWE stack.

Covers AST analysis, repository indexing, symbol search, static analysis,
dynamic test running, unit test generation, bug localization, and patch
validation.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from coding_agent.ast_analyzer import ASTAnalyzer
from coding_agent.repository_indexer import RepositoryIndexer
from coding_agent.symbol_search import SymbolSearcher
from coding_agent.static_analysis import StaticAnalyzer
from coding_agent.test_runner import TestRunner, TestRun, TestResult
from coding_agent.test_generator import UnitTestGenerator
from coding_agent.bug_localizer import BugLocalizer, BugLocalizationResult
from coding_agent.patch_validator import PatchValidator, PatchValidationResult
from coding_agent.agent import CodingAgent, TaskResult

SAMPLE_CODE = '''
"""A sample module for testing."""

import math


def add(a, b):
    """Return the sum of a and b."""
    return a + b


def square(n):
    return n * n


class Calculator:
    def __init__(self):
        self.value = 0

    def reset(self):
        self.value = 0

    def multiply(self, x, y):
        return x * y
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def temp_repo(tmp_path):
    """Create a temp repository with a source module and a test file."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "math_utils.py").write_text(SAMPLE_CODE, encoding="utf-8")

    test_file = tmp_path / "tests"
    test_file.mkdir()
    (test_file / "test_math.py").write_text(
        '''
from src.math_utils import add, square, Calculator

def test_add():
    assert add(1, 2) == 3

def test_square():
    assert square(3) == 9

def test_calculator():
    c = Calculator()
    c.multiply(2, 5)
    assert c.value == 0
''',
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# AST Analyzer
# ---------------------------------------------------------------------------
class TestASTAnalyzer:
    def test_analyze_string(self):
        analyzer = ASTAnalyzer()
        analysis = analyzer.analyze_string(SAMPLE_CODE, "sample.py")
        assert len(analysis.functions) == 3
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "Calculator"
        assert "add" in analysis.imports or "math" in [i for i in analysis.imports]

    def test_analyze_syntax_error(self):
        analyzer = ASTAnalyzer()
        analysis = analyzer.analyze_string("def broken(:\n", "bad.py")
        assert len(analysis.errors) >= 1

    def test_class_methods(self):
        analyzer = ASTAnalyzer()
        analysis = analyzer.analyze_string(SAMPLE_CODE, "sample.py")
        calc = analysis.classes[0]
        assert "reset" in calc.methods
        assert "multiply" in calc.methods


class TestRepositoryIndexer:
    def test_index_repo(self, temp_repo):
        indexer = RepositoryIndexer()
        index = indexer.index(str(temp_repo))
        assert len(index.files) >= 1
        assert any(f.path.endswith("math_utils.py") for f in index.files)

    def test_symbol_to_files(self, temp_repo):
        indexer = RepositoryIndexer()
        index = indexer.index(str(temp_repo))
        assert "add" in index.symbol_to_files


class TestSymbolSearcher:
    def test_search_function(self, temp_repo):
        indexer = RepositoryIndexer()
        index = indexer.index(str(temp_repo))
        searcher = SymbolSearcher()
        result = searcher.search(index, "add")
        assert len(result.matches) >= 1
        assert result.matches[0].kind == "function"

    def test_find_definition(self, temp_repo):
        indexer = RepositoryIndexer()
        index = indexer.index(str(temp_repo))
        searcher = SymbolSearcher()
        match = searcher.find_definition(index, "Calculator")
        assert match is not None
        assert match.kind == "class"


class TestStaticAnalyzer:
    def test_undefined_name(self):
        analyzer = StaticAnalyzer()
        issues = analyzer.analyze_string("def f():\n    return missing_var\n", "x.py")
        assert any(i.check == "undefined_name" for i in issues)

    def test_bare_except(self):
        analyzer = StaticAnalyzer()
        issues = analyzer.analyze_string("try:\n    pass\nexcept:\n    pass\n", "x.py")
        assert any(i.check == "bare_except" for i in issues)

    def test_syntax_error(self):
        analyzer = StaticAnalyzer()
        issues = analyzer.analyze_string("def f(:\n", "x.py")
        assert any(i.check == "syntax" for i in issues)


class TestTestRunner:
    def test_run_function_passes(self):
        runner = TestRunner()
        result = runner.run_function("def foo():\n    return 1\n", "foo")
        assert result.status == "passed"

    def test_run_function_error(self):
        runner = TestRunner()
        result = runner.run_function("def foo():\n    raise ValueError('boom')\n", "foo")
        assert result.status == "error"

    def test_run_function_missing(self):
        runner = TestRunner()
        result = runner.run_function("def foo():\n    return 1\n", "bar")
        assert result.status == "error"


class TestUnitTestGenerator:
    def test_generate_for_function(self):
        generator = UnitTestGenerator()
        analysis = ASTAnalyzer().analyze_string(SAMPLE_CODE, "sample.py")
        test_code = generator.generate_for_function(
            analysis, "add", examples=[{"args": [1, 2], "expected": 3}]
        )
        assert "def test_add_0" in test_code
        assert "add(1, 2)" in test_code

    def test_generate_for_class(self):
        generator = UnitTestGenerator()
        analysis = ASTAnalyzer().analyze_string(SAMPLE_CODE, "sample.py")
        test_code = generator.generate_for_class(analysis, "Calculator")
        assert "def test_Calculator_reset_0" in test_code


class TestBugLocalizer:
    def test_localize_from_traceback(self):
        run = TestRun(
            target="test_math.py",
            tests=[
                TestResult(
                    name="test_add",
                    status="failed",
                    message="at src/math_utils.py:5 in add, value 2 != 3",
                )
            ],
            failed=1,
            success=False,
        )
        localizer = BugLocalizer()
        result = localizer.localize(run)
        assert isinstance(result, BugLocalizationResult)
        assert len(result.locations) >= 1
        assert result.locations[0].file_path == "src/math_utils.py"


class TestPatchValidator:
    def test_syntax_error_patch_rejected(self):
        validator = PatchValidator()
        result = validator.validate_string("target.py", "def broken(:\n", "test_path.py")
        assert result.applied is False
        assert result.fixes_bug is False


# ---------------------------------------------------------------------------
# Integration: CodingAgent facade
# ---------------------------------------------------------------------------
class TestCodingAgentFacade:
    def test_analyze_code(self, temp_repo):
        agent = CodingAgent(workspace=str(temp_repo))
        result = agent.analyze_code("src/math_utils.py")
        assert isinstance(result, TaskResult)
        assert result.success is True
        assert "functions" in result.output

    def test_index_and_search(self, temp_repo):
        agent = CodingAgent(workspace=str(temp_repo))
        agent.index_repository()
        result = agent.search_symbols("add")
        assert len(result.matches) >= 1

    def test_generate_tests(self, temp_repo):
        agent = CodingAgent(workspace=str(temp_repo))
        test_code = agent.generate_tests(
            "src/math_utils.py", "add", examples=[{"args": [1, 2], "expected": 3}]
        )
        assert "test_add_0" in test_code

    def test_get_stats(self, temp_repo):
        agent = CodingAgent(workspace=str(temp_repo))
        stats = agent.get_stats()
        assert stats["type"] == "CodingAgent"
        assert stats["tasks_completed"] == 0
