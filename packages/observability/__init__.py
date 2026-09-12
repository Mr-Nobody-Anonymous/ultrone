"""
ULTRONE Observability Package.

Provides unified observability across the platform:
- Structured logging
- Distributed tracing (OpenTelemetry)
- Metrics collection (Prometheus)
- Event streaming
- Visualization (existing viz/ module)
"""

from .structured_logging import StructuredFormatter, get_logger

__all__ = ["StructuredFormatter", "get_logger"]
