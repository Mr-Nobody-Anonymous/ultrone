"""Permission management."""
from __future__ import annotations
from typing import Dict, List, Set

class PermissionManager:
    def __init__(self) -> None:
        self._roles: Dict[str, Set[str]] = {}
    def grant(self, role: str, permission: str) -> None:
        self._roles.setdefault(role, set()).add(permission)
    def revoke(self, role: str, permission: str) -> bool:
        perms = self._roles.get(role, set())
        return perms.discard(permission) is None or permission in perms
    def check(self, role: str, permission: str) -> bool:
        return permission in self._roles.get(role, set())
    def roles(self) -> List[str]:
        return list(self._roles.keys())
