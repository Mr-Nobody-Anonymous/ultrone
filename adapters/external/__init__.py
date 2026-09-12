# Copyright (c) Ultrone Contributors. All rights reserved.
"""External system adapters — port for third-party services.

Concrete wiring should wrap ``backend.integrations`` (REST client, webhook)
and ``comms`` (message bus, protocol, encryption). No vendor logic lives
here.
"""
from adapters.base import BaseAdapter, unavailable
from typing import Any, Dict

__all__ = ["ExternalAdapter"]


class ExternalAdapter(BaseAdapter):
    """Port every external-service implementation must satisfy."""

    name = "external"

    def connect(self) -> bool:  # pragma: no cover - placeholder
        return False

    def close(self) -> None:  # pragma: no cover - placeholder
        pass

    def health(self) -> Dict[str, Any]:  # pragma: no cover - placeholder
        return unavailable("no integration wired; see "
                           "backend/integrations and comms")
