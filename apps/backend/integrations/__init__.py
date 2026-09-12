"""
Argus — External Integrations
=============================
Integration adapters for external services: REST APIs, message queues,
object storage, and webhooks.
"""

from .base import Integration, IntegrationConfig, IntegrationResult
from .rest_client import RESTIntegration
from .webhook import WebhookIntegration

__all__ = [
    "Integration",
    "IntegrationConfig",
    "IntegrationResult",
    "RESTIntegration",
    "WebhookIntegration",
]