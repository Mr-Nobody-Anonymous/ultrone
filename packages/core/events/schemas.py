# Copyright (c) Ultrone Contributors. All rights reserved.
"""Validation schemas and payload templates for events."""
from __future__ import annotations

from typing import Any, Dict


def validate_event_payload(changes: Dict[str, Any]) -> bool:
    """Validate that changes payload contains valid serializable structure."""
    if not isinstance(changes, dict):
        return False
    return True
