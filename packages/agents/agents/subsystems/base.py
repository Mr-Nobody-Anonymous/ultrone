# Copyright (c) Ultrone Contributors. All rights reserved.
"""Subsystem base class: command handling, faults, telemetry."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, List

_HANDLERS_ATTR = "_command_handlers"


def command(action: str):
    """Register the decorated method as the handler for ``action``."""
    def decorator(fn: Callable) -> Callable:
        handlers = getattr(fn, _HANDLERS_ATTR, None)
        if handlers is None:
            def wrapper(self, *args: Any, **params: Any) -> Any:
                return fn(self, *args, **params)

            setattr(wrapper, _HANDLERS_ATTR, {action: fn.__name__})
            return wrapper
        handlers[action] = fn.__name__
        return fn
    return decorator


class Subsystem:
    """Base for every simulated machine subsystem.

    - declares accepted actions via the ``@command`` decorator;
    - ``handle(action, params)`` dispatches deterministically;
    - records faults and bounded telemetry history;
    - raises KeyError for unknown actions (the CommandBus converts this
      into a failed CommandResult).
    """

    name = "subsystem"

    def __init__(self, fault_log_size: int = 50) -> None:
        self.enabled = True
        self.faults: List[Dict[str, Any]] = []
        self.telemetry: deque = deque(maxlen=100)
        self._handlers: Dict[str, str] = {}
        # Scan the CLASS hierarchy (not instances) so @property attributes
        # are never evaluated during registration.
        for klass in reversed(type(self).__mro__):
            for attr_name, fn in list(vars(klass).items()):
                handlers = getattr(fn, _HANDLERS_ATTR, None)
                if handlers:
                    self._handlers.update(handlers)

    # -- dispatch ----------------------------------------------------------- #
    def actions(self) -> List[str]:
        return sorted(self._handlers)

    def handle(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.enabled:
            raise RuntimeError(f"{self.name} disabled")
        handler_name = self._handlers.get(action)
        if handler_name is None:
            raise KeyError(action)
        handler = getattr(self, handler_name)
        params = params or {}
        value = handler(**params)
        self.telemetry.append({"action": action,
                               "params": dict(params),
                               "value": value})
        return value

    # -- lifecycle ------------------------------------------------------------ #
    def tick(self, tick: int) -> None:   # pragma: no cover - optional hook
        pass

    def status(self) -> Dict[str, Any]:
        return {"subsystem": self.name, "enabled": self.enabled,
                "faults": len(self.faults)}

    def record_fault(self, reason: str) -> None:
        self.faults.append({"reason": reason})