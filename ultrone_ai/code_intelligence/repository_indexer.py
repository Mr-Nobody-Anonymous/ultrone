# Copyright (c) Ultrone Contributors. All rights reserved.
"""Repository Indexer — index source code repositories for search.

Scans a repository directory, indexes all source files, and builds
a searchable index of files, symbols, and code structure.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ast_analyzer import ASTAnalyzer

logger = logging.getLogger("Ultrone.AI.CodeIntelligence.Indexer")


@dataclass
class IndexConfig:
    """Configuration for repository indexing."""
    root_dir: str = "."
    include_extensions: List[str] = field(default_factory=lambda: [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs"])
    exclude_dirs: List[str] = field(default_factory=lambda: [
        ".git", "__pycache__", "node_modules", "venv", ".venv",
        "dist", "build", ".pytest_cache", ".mypy_cache",
    ])
    max_file_size: int = 1_000_000  # bytes
    follow_symlinks: bool = False


@dataclass
class FileEntry:
    """An indexed file in the repository."""
    path: str = ""
    filename: str = ""
    extension: str = ""
    size: int = 0
    line_count: int = 0
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    content_hash: str = ""
    last_modified: float = 0.0


class RepositoryIndexer:
    """Index source code repositories.

    Parameters
    ----------
    config : IndexConfig
        Configuration for indexing.
    """

    def __init__(self, config: Optional[IndexConfig] = None):
        self.config = config or IndexConfig()
        self._files: Dict[str, FileEntry] = {}
        self._symbol_to_files: Dict[str, List[str]] = {}
        self._analyzer = ASTAnalyzer()

    def index(self, root_dir: Optional[str] = None) -> Dict[str, Any]:
        """Index a repository directory.

        Parameters
        ----------
        root_dir : str, optional
            Root directory to index. Defaults to config.root_dir.

        Returns
        -------
        dict
            Indexing statistics.
        """
        root = Path(root_dir or self.config.root_dir)
        if not root.exists():
            return {"error": f"Directory not found: {root}", "files": 0}

        self._files = {}
        self._symbol_to_files = {}
        indexed = 0
        skipped = 0

        for file_path in root.rglob("*"):
            if file_path.is_dir():
                continue

            # Check exclusions
            rel_parts = file_path.relative_to(root).parts
            if any(part in self.config.exclude_dirs for part in rel_parts):
                continue

            # Check extension
            if file_path.suffix not in self.config.include_extensions:
                continue

            # Check size
            try:
                size = file_path.stat().st_size
                if size > self.config.max_file_size:
                    skipped += 1
                    continue
            except OSError:
                skipped += 1
                continue

            # Index the file
            entry = self._index_file(file_path, root)
            if entry:
                self._files[str(file_path)] = entry
                indexed += 1

        return {
            "files_indexed": indexed,
            "files_skipped": skipped,
            "total_files": len(self._files),
            "root": str(root),
        }

    def _index_file(self, file_path: Path, root: Path) -> Optional[FileEntry]:
        """Index a single file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        stat = file_path.stat()
        entry = FileEntry(
            path=str(file_path),
            filename=file_path.name,
            extension=file_path.suffix,
            size=stat.st_size,
            line_count=content.count("\n") + 1,
            last_modified=stat.st_mtime,
        )

        # Analyze Python files with AST
        if file_path.suffix == ".py":
            result = self._analyzer.analyze(content, str(file_path))
            entry.functions = [f["name"] for f in result["functions"]]
            entry.classes = [c["name"] for c in result["classes"]]
            entry.imports = [i["module"] for i in result["imports"] if i["module"]]

            # Index symbols
            for func_name in entry.functions:
                if func_name not in self._symbol_to_files:
                    self._symbol_to_files[func_name] = []
                self._symbol_to_files[func_name].append(str(file_path))

            for class_name in entry.classes:
                if class_name not in self._symbol_to_files:
                    self._symbol_to_files[class_name] = []
                self._symbol_to_files[class_name].append(str(file_path))

        # Simple hash for content
        import hashlib
        entry.content_hash = hashlib.md5(content.encode()).hexdigest()

        return entry

    def search_files(self, query: str) -> List[FileEntry]:
        """Search for files matching a query."""
        query_lower = query.lower()
        results = []
        for entry in self._files.values():
            if query_lower in entry.filename.lower() or query_lower in entry.path.lower():
                results.append(entry)
        return results

    def find_symbol(self, symbol: str) -> List[str]:
        """Find files containing a symbol."""
        return self._symbol_to_files.get(symbol, [])

    def get_file(self, path: str) -> Optional[FileEntry]:
        """Get a file entry by path."""
        return self._files.get(path)

    def get_all_files(self) -> List[FileEntry]:
        """Return all indexed files."""
        return list(self._files.values())

    def get_stats(self) -> Dict[str, Any]:
        """Return indexing statistics."""
        total_lines = sum(f.line_count for f in self._files.values())
        total_symbols = sum(len(v) for v in self._symbol_to_files.values())
        return {
            "files": len(self._files),
            "total_lines": total_lines,
            "total_symbols": total_symbols,
            "symbols": list(self._symbol_to_files.keys())[:100],
        }