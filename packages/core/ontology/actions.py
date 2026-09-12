# Copyright (c) Ultrone Contributors. All rights reserved.
"""Ontology Action workflows executable on objects."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class OntologyAction:
    action_id: str
    name: str
    description: str
    target_object_types: List[str]
    handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.handler:
            return self.handler(params)
        return {
            "status": "executed",
            "action_id": self.action_id,
            "timestamp": time.time(),
            "params": params,
        }
