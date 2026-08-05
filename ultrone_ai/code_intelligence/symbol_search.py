# Copyright (c) Ultrone Contributors. All rights reserved.
"""Symbol Search — search for symbols across indexed repositories."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.CodeIntelligence.SymbolSearch")


@dataclass
class SymbolInfo:
    """Information about a symbol."""
    name: str = ""
    symbol_type: str = ""  # function, class, method, variable, constant
    file_path: str = ""
    line: int = 0
    signature: str = ""
    docstring: str = ""
    references: int = 0


class SymbolSearch:
    """Search for symbols in indexed code.

    Provides:
    - Exact symbol lookup
    - Fuzzy symbol search
    - Type-filtered search
    - Reference counting
    """

    def __init__(self) -> None:
        self._symbols: Dict[str, List[SymbolInfo]] = {}

    def index_symbol(self, symbol: SymbolInfo) -> None:
        """Index a symbol."""
        if symbol.name not in self._symbols:
            self._symbols[symbol.name] = []
        self._symbols[symbol.name].append(symbol)

    def index_symbols(self, symbols: List[SymbolInfo]) -> None:
        """Index multiple symbols."""
        for symbol in symbols:
            self.index_symbol(symbol)

    def search(self, query: str, symbol_type: Optional[str] = None) -> List[SymbolInfo]:
        """Search for symbols matching a query."""
        query_lower = query.lower()
        results = []

        for name, symbols in self._symbols.items():
            if query_lower in name.lower():
                for symbol in symbols:
                    if symbol_type and symbol.symbol_type != symbol_type:
                        continue
                    results.append(symbol)

        # Sort by relevance (exact matches first)
        results.sort(key=lambda s: (s.name.lower() != query_lower, -s.references))
        return results

    def exact_match(self, name: str) -> Optional[SymbolInfo]:
        """Find an exact symbol match."""
        symbols = self._symbols.get(name, [])
        return symbols[0] if symbols else None

    def find_by_type(self, symbol_type: str) -> List[SymbolInfo]:
        """Find all symbols of a given type."""
        results = []
        for symbols in self._symbols.values():
            for symbol in symbols:
                if symbol.symbol_type == symbol_type:
                    results.append(symbol)
        return results

    def get_references(self, name: str) -> int:
        """Get the number of references to a symbol."""
        symbols = self._symbols.get(name, [])
        return sum(s.references for s in symbols)

    def get_stats(self) -> Dict[str, Any]:
        """Return search statistics."""
        type_counts: Dict[str, int] = {}
        for symbols in self._symbols.values():
            for symbol in symbols:
                type_counts[symbol.symbol_type] = type_counts.get(symbol.symbol_type, 0) + 1
        return {
            "total_symbols": sum(len(v) for v in self._symbols.values()),
            "unique_names": len(self._symbols),
            "types": type_counts,
        }