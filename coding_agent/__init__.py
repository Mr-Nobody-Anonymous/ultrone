# Copyright (c) Ultrone Contributors. All rights reserved.
"""Coding Agent — Full SWE workflow automation.

Provides the autonomous software engineering stack: AST analysis, repository
indexing, symbol search, static analysis, dynamic test running, unit test
generation, bug localization, and patch validation.
"""

from .agent import CodingAgent, TaskResult
from .ast_analyzer import ASTAnalysis, ASTAnalyzer, FunctionInfo, ClassInfo
from .repository_indexer import RepositoryIndex, RepositoryIndexer, FileIndex
from .symbol_search import SymbolSearcher, SymbolSearchResult, SymbolMatch
from .static_analysis import StaticAnalyzer, StaticIssue
from .test_runner import TestRunner, TestRun, TestResult
from .test_generator import UnitTestGenerator
from .bug_localizer import BugLocalizer, BugLocation, BugLocalizationResult
from .patch_validator import PatchValidator, PatchValidationResult

__all__ = [
    "CodingAgent",
    "TaskResult",
    "ASTAnalysis",
    "ASTAnalyzer",
    "FunctionInfo",
    "ClassInfo",
    "RepositoryIndex",
    "RepositoryIndexer",
    "FileIndex",
    "SymbolSearcher",
    "SymbolSearchResult",
    "SymbolMatch",
    "StaticAnalyzer",
    "StaticIssue",
    "TestRunner",
    "TestRun",
    "TestResult",
    "UnitTestGenerator",
    "BugLocalizer",
    "BugLocation",
    "BugLocalizationResult",
    "PatchValidator",
    "PatchValidationResult",
]
