# Copyright (c) Ultrone Contributors. All rights reserved.
"""Repository Indexer — build a searchable index of a code repository.

Walks a repository directory, analyzes each Python file with the AST analyzer,
and builds an in-memory + JSON-persisted index of files, functions, classes,
and imports. The index powers symbol search and repository-aware bug
localization.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ast_analyzer import ASTAnalysis, ASTAnalyzer

logger = logging.getLogger("Ultrone.Coding.RepositoryIndex")


@dataclass
class FileIndex:
    """Index entry for a single source file."""

    path: str
    symbols: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    line_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "symbols": self.symbols,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "line_count": self.line_count,
        }


@dataclass
class RepositoryIndex:
    """The full index of files and symbols in a repository."""

    root: str
    files: List[FileIndex] = field(default_factory=list)
    symbol_to_files: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "files": [f.to_dict() for f in self.files],
            "symbol_to_files": self.symbol_to_files,
            "errors": self.errors,
        }


class RepositoryIndexer:
    """Indexes a Python repository for symbol and static analysis."""

    def __init__(self, analyzer: Optional[ASTAnalyzer] = None) -> None:
        self.analyzer = analyzer or ASTAnalyzer()
        self._index: Optional[RepositoryIndex] = None

    def index(self, root: str, include: Optional[List[str]] = None) -> RepositoryIndex:
        """Build an index of the repository at ``root``.

        Parameters
        ----------
        root
            The repository root directory.
        include
            Optional list of subdirectory names to include (defaults to all).

        Returns
        -------
        RepositoryIndex
            The built index.
        """
        root_path = Path(root)
        index = RepositoryIndex(root=str(root_path))
        include = include or []

        for dirpath, dirnames, filenames in os.walk(root_path):
            # Filter directories if include list provided.
            if include:
                dirnames[:] = [d for d in dirnames if d in include]
            else:
                # Skip common non-source directories.
                dirnames[:] = [
                    d for d in dirnames
                    if d not in {".git", "__pycache__", "node_modules", ".venv", "venv"}
                ]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                file_path = Path(dirpath) / filename
                try:
                    analysis = self.analyzer.analyze_file(str(file_path))
                    file_index = self._to_file_index(str(file_path), analysis)
                    index.files.append(file_index)
                    for symbol in file_index.symbols:
                        index.symbol_to_files.setdefault(symbol, []).append(file_index.path)
                except Exception as exc:  # noqa: BLE001
                    index.errors.append(f"{file_path}: {exc}")
                    logger.warning("Failed to index %s: %s", file_path, exc)

        self._index = index
        return index

    @staticmethod
    def _to_file_index(path: str, analysis: ASTAnalysis) -> FileIndex:
        """Convert an AST analysis to a file index entry."""
        symbols = []
        for fn in analysis.functions:
            symbols.append(fn.name)
        for cls in analysis.classes:
            symbols.append(cls.name)
            for method in cls.methods:
                symbols.append(f"{cls.name}.{method}")
        return FileIndex(
            path=path,
            symbols=symbols,
            functions=[fn.name for fn in analysis.functions],
            classes=[cls.name for cls in analysis.classes],
            imports=analysis.imports,
            line_count=len(analysis.errors) if False else sum(
                (fn.end_lineno - fn.lineno + 1) for fn in analysis.functions
            ),
        )

    def save(self, path: str) -> None:
        """Persist the current index to a JSON file."""
        if self._index is None:
            raise ValueError("No index to save; call index() first.")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._index.to_dict(), fh, indent=2)

    def load(self, path: str) -> RepositoryIndex:
        """Load an index from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._index = self._from_dict(data)
        return self._index

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> RepositoryIndex:
        """Rebuild a RepositoryIndex from a dict."""
        index = RepositoryIndex(root=data["root"], errors=list(data.get("errors", [])))
        for fdict in data.get("files", []):
            index.files.append(FileIndex(**fdict))
        index.symbol_to_files = data.get("symbol_to_files", {})
        return index

    def get_index(self) -> Optional[RepositoryIndex]:
        """Return the current index."""
        return self._index
