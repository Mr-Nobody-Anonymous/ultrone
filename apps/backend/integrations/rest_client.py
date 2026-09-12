"""
Argus — REST Integration
========================
REST API integration with retry, authentication, and typed responses.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from .base import Integration, IntegrationConfig, IntegrationResult


class RESTIntegration(Integration):
    """REST API integration using urllib."""

    name = "rest"

    def __init__(self, config: Optional[IntegrationConfig] = None) -> None:
        super().__init__(config)

    def send(
        self,
        data: Dict[str, Any],
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Send data via POST to the REST endpoint."""
        import urllib.request
        import urllib.error

        url = endpoint or self.config.endpoint
        if not url:
            return IntegrationResult(
                integration=self.name,
                success=False,
                error="No endpoint configured",
            ).complete()

        body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        headers.update(self.config.headers)

        for attempt in range(self.config.retry_count):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                    response_body = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(response_body)
                    except json.JSONDecodeError:
                        parsed = response_body
                    return IntegrationResult(
                        integration=self.name,
                        success=True,
                        status_code=resp.status,
                        response=parsed,
                    ).complete()
            except urllib.error.HTTPError as e:
                if attempt == self.config.retry_count - 1:
                    return IntegrationResult(
                        integration=self.name,
                        success=False,
                        status_code=e.code,
                        error=str(e),
                    ).complete()
                time.sleep(self.config.retry_delay_seconds)
            except Exception as e:
                if attempt == self.config.retry_count - 1:
                    return IntegrationResult(
                        integration=self.name,
                        success=False,
                        error=str(e),
                    ).complete()
                time.sleep(self.config.retry_delay_seconds)

        return IntegrationResult(
            integration=self.name,
            success=False,
            error="Max retries exceeded",
        ).complete()

    def receive(
        self,
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Receive data via GET from the REST endpoint."""
        import urllib.request
        import urllib.error

        url = endpoint or self.config.endpoint
        if not url:
            return IntegrationResult(
                integration=self.name,
                success=False,
                error="No endpoint configured",
            ).complete()

        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        headers.update(self.config.headers)

        for attempt in range(self.config.retry_count):
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                    response_body = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(response_body)
                    except json.JSONDecodeError:
                        parsed = response_body
                    return IntegrationResult(
                        integration=self.name,
                        success=True,
                        status_code=resp.status,
                        response=parsed,
                    ).complete()
            except Exception as e:
                if attempt == self.config.retry_count - 1:
                    return IntegrationResult(
                        integration=self.name,
                        success=False,
                        error=str(e),
                    ).complete()
                time.sleep(self.config.retry_delay_seconds)

        return IntegrationResult(
            integration=self.name,
            success=False,
            error="Max retries exceeded",
        ).complete()