"""Hierarchical Finite State Machine architecture."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .fsm import FSM, FSMConfig, State, Transition

logger = logging.getLogger("Ultrone.AIArchitectures.HFSM")


@dataclass
class HFSMConfig(FSMConfig):
    """Configuration for Hierarchical FSM."""
    max_depth: int = 5


class HierarchicalFSM(FSM):
    """Hierarchical Finite State Machine.

    States can contain nested FSMs, enabling hierarchical
    decomposition of complex behaviors. Parent states
    can delegate to child FSMs for detailed control.
    """

    def __init__(self, config: Optional[HFSMConfig] = None):
        super().__init__(config or HFSMConfig())
        self._sub_fsms: Dict[str, FSM] = {}

    def add_sub_fsm(self, state_name: str, fsm: FSM) -> None:
        """Attach a sub-FSM to a state."""
        self._sub_fsms[state_name] = fsm

    def decide(self, state: Dict[str, Any]) -> str:
        parent_action = super().decide(state)

        # Check for sub-FSM in current state
        if self._current_state and self._current_state.name in self._sub_fsms:
            sub_fsm = self._sub_fsms[self._current_state.name]
            sub_action = sub_fsm.decide(state)
            self._last_action = f"{parent_action}.{sub_action}"
            return self._last_action

        return parent_action

    def reset(self) -> None:
        super().reset()
        for fsm in self._sub_fsms.values():
            fsm.reset()
