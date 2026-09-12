"""
Argus — Integration Base Classes
================================
Abstract integration protocol with typed configuration and result models.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class IntegrationConfig:
    """Base configuration for an integration."""

    name: str = ""
    endpoint: str = ""
    api_key: Optional[str] = None
    timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationResult:
    """Result of an integration operation."""

    integration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    integration: str = ""
    success: bool = False
    status_code: Optional[int] = None
    response: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self) -> "IntegrationResult":
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        return self


class Integration(ABC):
    """Abstract base class for all integrations."""

    name: str = "base"

    def __init__(self, config: Optional[IntegrationConfig] = None) -> None:
        self.config = config or IntegrationConfig()

    @abstractmethod
    def send(
        self,
        data: Dict[str, Any],
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Send data to the external service."""
        ...

    @abstractmethod
    def receive(
        self,
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Receive data from the external service."""
        ...

    def health_check(self) -> IntegrationResult:
        """Check if the integration is healthy."""
        return IntegrationResult(
            integration=self.name,
            success=True,
        ).complete()

    def close(self) -> None:
        """Release resources."""
        pass