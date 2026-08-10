# Copyright (c) Ultrone Contributors. All rights reserved.
"""Code intelligence for software engineering benchmarks.

Implements:
- AST Code Analyzer
- Repository Indexer
- Symbol Search
- Static Analysis
- Code Metrics
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ASTAnalyzer", "FunctionInfo", "ClassInfo", "ImportInfo",
    "RepositoryIndexer", "IndexConfig", "FileEntry",
    "SymbolSearch", "SymbolInfo",
    "StaticAnalyzer", "AnalysisIssue",
]


def __getattr__(name: str) -> Any:
    if name in {"ASTAnalyzer", "FunctionInfo", "ClassInfo", "ImportInfo"}:
        from .ast_analyzer import ASTAnalyzer, FunctionInfo, ClassInfo, ImportInfo
        mapping = {"ASTAnalyzer": ASTAnalyzer, "FunctionInfo": FunctionInfo, "ClassInfo": ClassInfo, "ImportInfo": ImportInfo}
        return mapping[name]
    if name in {"RepositoryIndexer", "IndexConfig", "FileEntry"}:
        from .repository_indexer import RepositoryIndexer, IndexConfig, FileEntry
        mapping = {"RepositoryIndexer": RepositoryIndexer, "IndexConfig": IndexConfig, "FileEntry": FileEntry}
        return mapping[name]
    if name in {"SymbolSearch", "SymbolInfo"}:
        from .symbol_search import SymbolSearch, SymbolInfo
        mapping = {"SymbolSearch": SymbolSearch, "SymbolInfo": SymbolInfo}
        return mapping[name]
    if name in {"StaticAnalyzer", "AnalysisIssue"}:
        try:
            from .static_analyzer import StaticAnalyzer, AnalysisIssue
        except ModuleNotFoundError:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
        mapping = {"StaticAnalyzer": StaticAnalyzer, "AnalysisIssue": AnalysisIssue}
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")