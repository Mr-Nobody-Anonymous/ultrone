# Copyright (c) Ultrone Contributors. All rights reserved.
"""Symbol Search — find function/class/definition locations across a repo.

Queries the repository index to locate symbols (functions, classes, methods)
by name, returning the files and definitions that reference them. This powers
code navigation and bug localization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .repository_indexer import RepositoryIndex

logger = logging.getLogger("Ultrone.Coding.SymbolSearch")


@dataclass
class SymbolMatch:
    """A single symbol match with context."""

    symbol: str
    file_path: str
    kind: str  # "function" | "class" | "method" | "import"

    def to_dict(self) -> Dict[str, Any]:
        return {"symbol": self.symbol, "file_path": self.file_path, "kind": self.kind}


@dataclass
class SymbolSearchResult:
    """The result of a symbol search across the repository."""

    query: str
    matches: List[SymbolMatch] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "matches": [m.to_dict() for m in self.matches],
        }


class SymbolSearcher:
    """Searches a repository index for symbol definitions and references."""

    def search(self, index: RepositoryIndex, query: str, limit: int = 50) -> SymbolSearchResult:
        """Search for ``query`` across the repository index.

        Parameters
        ----------
        index
            The repository index to search.
        query
            The symbol name (or substring) to search for.
        limit
            Maximum number of matches to return.

        Returns
        -------
        SymbolSearchResult
            The matching symbols with file locations.
        """
        result = SymbolSearchResult(query=query)
        low = query.lower()
        count = 0

        for file_index in index.files:
            # Match functions.
            for fn in file_index.functions:
                if low in fn.lower():
                    result.matches.append(SymbolMatch(fn, file_index.path, "function"))
                    count += 1
            # Match classes.
            for cls in file_index.classes:
                if low in cls.lower():
                    result.matches.append(SymbolMatch(cls, file_index.path, "class"))
                    count += 1
            # Match methods (symbols with dots).
            for sym in file_index.symbols:
                if "." in sym and low in sym.lower():
                    result.matches.append(SymbolMatch(sym, file_index.path, "method"))
                    count += 1
            # Match imports.
            for imp in file_index.imports:
                if low in imp.lower():
                    result.matches.append(SymbolMatch(imp, file_index.path, "import"))
                    count += 1

            if count >= limit:
                break

        return result

    def find_definition(
        self, index: RepositoryIndex, symbol: str
    ) -> Optional[SymbolMatch]:
        """Find the primary definition of a symbol (function or class).

        Returns
        -------
        Optional[SymbolMatch]
            The definition match, or ``None`` if not found.
        """
        low = symbol.lower()
        for file_index in index.files:
            for fn in file_index.functions:
                if fn.lower() == low:
                    return SymbolMatch(fn, file_index.path, "function")
            for cls in file_index.classes:
                if cls.lower() == low:
                    return SymbolMatch(cls, file_index.path, "class")
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        return {"type": "SymbolSearcher"}
