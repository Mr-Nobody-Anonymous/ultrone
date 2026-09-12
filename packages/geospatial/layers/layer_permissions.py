# Copyright (c) Ultrone Contributors. All rights reserved.
"""Role-based access control (RBAC) permissions for geospatial layers."""
from __future__ import annotations

from typing import Dict, List, Set


class LayerPermissions:
    """Manages role-based visibility permissions for sensitive layers."""

    def __init__(self) -> None:
        self._role_permissions: Dict[str, Set[str]] = {
            "viewer": {"base_map", "objects"},
            "operator": {"base_map", "objects", "environment", "analytics"},
            "admin": {"base_map", "objects", "environment", "analytics", "classified"},
        }

    def can_access_category(self, role: str, category: str) -> bool:
        allowed = self._role_permissions.get(role, self._role_permissions["viewer"])
        return category in allowed
