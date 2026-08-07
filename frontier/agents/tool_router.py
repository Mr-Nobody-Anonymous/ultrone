# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tool Router — dispatches a request to the best available tool.

The tool router maintains a registry of tools and routes a request (described
by a goal and optional constraints) to the most appropriate tool. Routing can
be driven by:
- an explicit routing callable,
- a solver that picks the tool from a description, or
- an exact-match on tool names.

This enables capability-based tool use for agentic benchmarks (AgentBench,
Tau-Bench, WebArena, BFCL).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from frontier.reasoning.base import Solver

logger = logging.getLogger("Ultrone.Frontier.Agents.ToolRouter")


@dataclass
class Tool:
    """A registered tool with metadata."""

    name: str
    description: str
    fn: Callable[..., Any]
    category: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
        }


@dataclass
class RoutingResult:
    """The output of routing a request to a tool."""

    request: str
    tool: Optional[str]
    output: Any = None
    success: bool = False
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "tool": self.tool,
            "output": self.output,
            "success": self.success,
            "error": self.error,
        }


class ToolRouter:
    """Routes requests to the best available tool.

    Parameters
    ----------
    solver : Optional[Solver]
        A solver used to select a tool when no exact match or router callable
        applies.
    router_fn : Optional[Callable]
        An explicit callable ``(request, tools, context) -> tool_name``.
    """

    def __init__(
        self,
        solver: Optional[Solver] = None,
        router_fn: Optional[Callable[..., str]] = None,
    ) -> None:
        self.solver = solver
        self._router_fn = router_fn
        self._tools: Dict[str, Tool] = {}
        self._history: List[RoutingResult] = []

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        description: str,
        category: str = "general",
    ) -> None:
        """Register a tool."""
        self._tools[name] = Tool(name=name, description=description, fn=fn, category=category)

    def route(self, request: str, context: Optional[Dict[str, Any]] = None) -> RoutingResult:
        """Route ``request`` to a tool and execute it.

        Returns
        -------
        RoutingResult
            The routing outcome, including the tool output or error.
        """
        context = context or {}
        tool_name = self._select_tool(request, context)

        if tool_name is None or tool_name not in self._tools:
            result = RoutingResult(
                request=request, tool=tool_name, success=False,
                error=f"No suitable tool found for: {request}",
            )
            self._history.append(result)
            return result

        tool = self._tools[tool_name]
        try:
            output = tool.fn(**context.get("args", {}))
            result = RoutingResult(request=request, tool=tool_name, output=output, success=True)
        except Exception as exc:  # noqa: BLE001
            result = RoutingResult(
                request=request, tool=tool_name, success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        self._history.append(result)
        return result

    def _select_tool(self, request: str, context: Dict[str, Any]) -> Optional[str]:
        """Select the best tool name for the request."""
        if self._router_fn is not None:
            return self._router_fn(request, self._tools, context)

        # Exact-match on tool name mentioned in the request.
        for name in self._tools:
            if name.lower() in request.lower():
                return name

        # Solver-based selection.
        if self.solver is not None and self._tools:
            tool_descriptions = "\n".join(
                f"- {t.name}: {t.description}" for t in self._tools.values()
            )
            prompt = (
                f"Given the request: {request}\n\n"
                f"Available tools:\n{tool_descriptions}\n\n"
                f"Reply with the single most appropriate tool name, or 'none'."
            )
            choice = self.solver(prompt).strip().lower()
            for name in self._tools:
                if name.lower() in choice:
                    return name
            if "none" in choice:
                return None

        # Default to the first registered tool.
        return next(iter(self._tools), None)

    def get_tools(self) -> List[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_history(self) -> List[RoutingResult]:
        """Return all routing results."""
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        if not self._history:
            return {"routings": 0, "success_rate": 0.0, "tools": len(self._tools)}
        success = sum(1 for r in self._history if r.success)
        return {
            "routings": len(self._history),
            "success_rate": success / len(self._history),
            "tools": len(self._tools),
        }
