"""ULTRONE Workflows - Operational Action registry and execution."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class WorkflowAction:
    """An operational action executable against entities or cases."""
    action_id: str
    display_name: str
    description: str
    required_permissions: List[str] = field(default_factory=list)
    requires_approval: bool = False
    parameter_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.handler:
            return self.handler(params)
        return {
            "status": "success",
            "action_id": self.action_id,
            "executed_at": time.time(),
            "params": params,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "display_name": self.display_name,
            "description": self.description,
            "required_permissions": self.required_permissions,
            "requires_approval": self.requires_approval,
            "parameter_schema": self.parameter_schema,
        }


class ActionRegistry:
    """Registry of all operational workflows and actions."""

    def __init__(self):
        self._actions: Dict[str, WorkflowAction] = {}
        self._register_default_actions()

    def register(self, action: WorkflowAction) -> None:
        self._actions[action.action_id] = action

    def get_action(self, action_id: str) -> Optional[WorkflowAction]:
        return self._actions.get(action_id)

    def list_actions(self) -> List[WorkflowAction]:
        return list(self._actions.values())

    def _register_default_actions(self) -> None:
        defaults = [
            WorkflowAction(
                action_id="compare_tracks",
                display_name="Compare Tracks",
                description="Cross-compare kinematic tracks of two or more entities.",
                parameter_schema={"entity_ids": {"type": "array", "required": True}},
            ),
            WorkflowAction(
                action_id="create_investigation",
                display_name="Create Investigation",
                description="Initiate an investigation case and pin selected entities.",
                parameter_schema={"title": {"type": "string", "required": True}},
            ),
            WorkflowAction(
                action_id="run_simulation_test",
                display_name="Run Simulation Test",
                description="Branch entity current state into synthetic sandbox.",
                parameter_schema={"scenario_id": {"type": "string", "required": True}},
            ),
            WorkflowAction(
                action_id="annotate",
                display_name="Annotate Contact",
                description="Attach an analytical note or tactical hypothesis.",
                parameter_schema={"note": {"type": "string", "required": True}},
            ),
            WorkflowAction(
                action_id="export_dossier",
                display_name="Export Operational Dossier",
                description="Compile complete markdown/HTML intelligence brief.",
            ),
            WorkflowAction(
                action_id="dispatch_sensor",
                display_name="Dispatch Sensor Tasking",
                description="Re-point or task an active sensor platform (Requires HITL Approval).",
                requires_approval=True,
                parameter_schema={"sensor_id": {"type": "string", "required": True}},
            ),
        ]
        for a in defaults:
            self.register(a)


__all__ = ["WorkflowAction", "ActionRegistry"]
