"""Behavior Tree architecture."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import AIArchitecture, AIArchitectureConfig

logger = logging.getLogger("Ultrone.AIArchitectures.BT")

# Status codes
BT_SUCCESS = 1
BT_FAILURE = 2
BT_RUNNING = 3

Status = int


class BTNode:
    """Base class for behavior tree nodes."""

    def tick(self, state: Dict[str, Any]) -> Status:
        """Execute this node. Returns SUCCESS, FAILURE, or RUNNING."""
        return BT_SUCCESS


class Action(BTNode):
    """Leaf node that performs an action."""

    def __init__(self, name: str, action_fn: Optional[Callable] = None):
        self.name = name
        self.action_fn = action_fn

    def tick(self, state: Dict[str, Any]) -> Status:
        if self.action_fn:
            return self.action_fn(state)
        logger.debug("Action: %s", self.name)
        return BT_SUCCESS


class Condition(BTNode):
    """Leaf node that checks a condition."""

    def __init__(self, name: str, condition_fn: Callable[[Dict[str, Any]], bool]):
        self.name = name
        self.condition_fn = condition_fn

    def tick(self, state: Dict[str, Any]) -> Status:
        return BT_SUCCESS if self.condition_fn(state) else BT_FAILURE


class Sequence(BTNode):
    """Composite node that runs children in sequence.

    Succeeds only if all children succeed. Fails on first failure.
    """

    def __init__(self, children: Optional[List[BTNode]] = None):
        self.children = children or []

    def tick(self, state: Dict[str, Any]) -> Status:
        for child in self.children:
            status = child.tick(state)
            if status == BT_FAILURE:
                return BT_FAILURE
            if status == BT_RUNNING:
                return BT_RUNNING
        return BT_SUCCESS


class Selector(BTNode):
    """Composite node that runs children in order.

    Succeeds on first child success. Fails if all children fail.
    """

    def __init__(self, children: Optional[List[BTNode]] = None):
        self.children = children or []

    def tick(self, state: Dict[str, Any]) -> Status:
        for child in self.children:
            status = child.tick(state)
            if status == BT_SUCCESS:
                return BT_SUCCESS
            if status == BT_RUNNING:
                return BT_RUNNING
        return BT_FAILURE


class Decorator(BTNode):
    """Node that wraps a single child with custom logic."""

    def __init__(self, child: BTNode):
        self.child = child


class InvertDecorator(Decorator):
    """Inverts the child's result."""

    def tick(self, state: Dict[str, Any]) -> Status:
        status = self.child.tick(state)
        if status == BT_SUCCESS:
            return BT_FAILURE
        if status == BT_FAILURE:
            return BT_SUCCESS
        return BT_RUNNING


@dataclass
class BTConfig(AIArchitectureConfig):
    """Configuration for Behavior Tree."""
    tick_rate: float = 10.0  # ticks per second


class BehaviorTree(AIArchitecture):
    """Behavior Tree for modular agent control.

    Supports composite nodes (Sequence, Selector), decorators,
    action leaves, and condition leaves.
    """

    def __init__(self, config: Optional[BTConfig] = None):
        super().__init__(config or BTConfig())
        self._root: Optional[BTNode] = None

    def set_root(self, root: BTNode) -> None:
        self._root = root

    def decide(self, state: Dict[str, Any]) -> str:
        if self._root is None:
            return "idle"
        status = self._root.tick(state)
        self._last_action = f"bt_status_{status}"
        return f"status_{status}"

    def reset(self) -> None:
        pass
