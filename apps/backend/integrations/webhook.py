"""
Argus — Webhook Integration
===========================
Sends event notifications to registered webhook URLs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

from .base import Integration, IntegrationConfig, IntegrationResult


class WebhookIntegration(Integration):
    """Webhook integration that POSTs events to registered URLs."""

    name = "webhook"

    def __init__(
        self,
        config: Optional[IntegrationConfig] = None,
        *,
        secret: Optional[str] = None,
        urls: Optional[List[str]] = None,
    ) -> None:
        super().__init__(config)
        self._secret = secret
        self._urls: List[str] = urls or []

    def register_url(self, url: str) -> None:
        """Register a webhook URL."""
        if url not in self._urls:
            self._urls.append(url)

    def unregister_url(self, url: str) -> None:
        """Unregister a webhook URL."""
        if url in self._urls:
            self._urls.remove(url)

    def send(
        self,
        data: Dict[str, Any],
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Send data to all registered webhook URLs."""
        import urllib.request

        targets = [endpoint] if endpoint else self._urls
        if not targets:
            return IntegrationResult(
                integration=self.name,
                success=False,
                error="No webhook URLs registered",
            ).complete()

        body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        # HMAC signature if secret is set.
        if self._secret:
            signature = hmac.new(
                self._secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        success_count = 0
        errors: List[str] = []

        for url in targets:
            for attempt in range(self.config.retry_count):
                try:
                    req = urllib.request.Request(
                        url, data=body, headers=headers, method="POST"
                    )
                    with urllib.request.urlopen(
                        req, timeout=self.config.timeout_seconds
                    ) as resp:
                        if 200 <= resp.status < 300:
                            success_count += 1
                            break
                except Exception as e:
                    if attempt == self.config.retry_count - 1:
                        errors.append(f"{url}: {e}")
                    time.sleep(self.config.retry_delay_seconds)

        return IntegrationResult(
            integration=self.name,
            success=success_count > 0,
            response={"delivered": success_count, "total": len(targets)},
            error="; ".join(errors) if errors else None,
        ).complete()

    def receive(
        self,
        *,
        endpoint: Optional[str] = None,
    ) -> IntegrationResult:
        """Webhooks are push-only; receive is not supported."""
        return IntegrationResult(
            integration=self.name,
            success=False,
            error="Webhook integration is push-only",
        ).complete()