# Copyright (c) Ultrone Contributors. All rights reserved.
"""Canonical authentication boundary for ULTRONE HITL (Sprint C).

Deliberately small: an identity abstraction, an error hierarchy, one
provider interface, and the development/test provider backed by the
existing in-process actor->role registry. No OAuth/OIDC/JWT -- the point
is that a production provider can replace :class:`DevelopmentAuthenticator`
without touching ``DecisionWorkflow``, ``AuditStore``, or
``DecisionPipeline``.

Rules enforced here and by consumers:

- Authorization consumes an authenticated :class:`Principal`, never a
  caller-supplied actor string or role field.
- Unknown/unauthenticated credentials fail closed
  (:class:`UnauthenticatedError`, also a legacy-compatible
  ``UnauthorizedActionError``).
- Audit events record the authenticated subject and effective role.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ultrone_hitl.decision_workflow import Role, UnauthorizedActionError


@dataclass(frozen=True)
class Principal:
    """An authenticated identity. Immutable by construction.

    ``subject`` is the stable identifier written into audit records;
    ``role`` is the effective role resolved by the provider -- never by
    anything client-supplied.
    """

    subject: str
    role: Role
    display_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "role": self.role.value if isinstance(self.role, Role) else str(self.role),
            "display_name": self.display_name,
        }


class AuthenticationError(Exception):
    """Base error for the authentication boundary."""


class UnauthenticatedError(AuthenticationError, UnauthorizedActionError):
    """Credential is unknown or unauthenticated. Fail-closed.

    Also subclasses the legacy ``UnauthorizedActionError`` so existing
    callers/tests that expect a 403-style authorization failure keep
    working unchanged.
    """

    def __init__(self, credential: Any) -> None:
        super().__init__(
            f"unauthenticated principal: {credential!r}",
            "<unauthenticated>",
        )
        self.credential = credential


class Authenticator(ABC):
    """Provider interface: credential -> authenticated Principal.

    Implementations MUST fail closed: raise (subclasses of)
    :class:`AuthenticationError` rather than returning a principal for
    anything they cannot verify.
    """

    @abstractmethod
    def authenticate(self, credential: Any) -> Principal:
        """Verify ``credential`` and return its Principal."""


class DevelopmentAuthenticator(Authenticator):
    """Development/test provider over the in-process actor->role registry.

    This is the existing ``Authorizer`` mapping re-expressed as an
    ``Authenticator`` so every current test stays deterministic. A real
    deployment replaces this class -- nothing else changes.
    """

    def __init__(self, authorizer: Any) -> None:
        self._authorizer = authorizer

    def authenticate(self, credential: Any) -> Principal:
        role = self._authorizer.role_of(credential) if hasattr(
            self._authorizer, "role_of"
        ) else None
        if role is None:
            raise UnauthenticatedError(credential)
        return Principal(
            subject=str(credential),
            role=role,
            display_name=f"dev:{credential}",
        )


def principal_payload(principal: Optional[Principal]) -> Optional[Dict[str, Any]]:
    """Audit-record projection of an authenticated principal."""
    return principal.to_dict() if principal is not None else None
