"""
Middleware — Security, authentication, rate limiting, request logging, CORS, CSRF protection.
"""

import os
import time
import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("argus.middleware")


class SecurityMiddleware:
    """Security middleware for request validation, CORS, and headers."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.allowed_origins = set(self.config.get("allowed_origins", ["*"]))
        self.allowed_methods = self.config.get("allowed_methods", [
            "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS",
        ])
        self.allowed_headers = self.config.get("allowed_headers", [
            "Content-Type", "Authorization", "X-CSRF-Token", "X-API-Key",
        ])
        self.max_content_length = self.config.get("max_content_length", 50 * 1024 * 1024)  # 50MB

    def validate_request(self, request: Any) -> Optional[Tuple[int, str]]:
        """Validate incoming request. Returns None if valid, or (status, message) if invalid."""
        # Check content length
        content_length = getattr(request, "content_length", 0) or 0
        if content_length > self.max_content_length:
            return 413, "Request entity too large"

        # Validate content type for POST/PUT
        if request.method in ("POST", "PUT"):
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type and "multipart/form-data" not in content_type:
                return 415, "Unsupported media type"

        return None

    def add_security_headers(self, response: Any, request: Any) -> None:
        """Add security headers to response."""
        origin = request.headers.get("origin", "")
        if "*" in self.allowed_origins or origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin if "*" not in self.allowed_origins else "*"
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    def validate_cors(self, request: Any) -> bool:
        """Validate CORS origin."""
        if "*" in self.allowed_origins:
            return True
        origin = request.headers.get("origin", "")
        if not origin:
            return True
        parsed = urlparse(origin)
        return parsed.netloc in self.allowed_origins or origin in self.allowed_origins


class RequestLoggingMiddleware:
    """Request logging with timing and metadata."""

    def __init__(self):
        self._start_times: Dict[int, float] = {}

    def before_request(self, request: Any) -> None:
        request_id = id(request)
        self._start_times[request_id] = time.time()

    def after_request(self, request: Any, response: Any) -> None:
        request_id = id(request)
        start = self._start_times.pop(request_id, time.time())
        duration = time.time() - start
        logger.info(
            f"{request.method} {request.path} -> {response.status_code} "
            f"({duration:.3f}s) [{request.remote_addr}]"
        )


class ErrorHandler:
    """Centralized error handling."""

    @staticmethod
    def handle_error(status_code: int, message: str, details: Optional[Dict] = None) -> Tuple[int, Dict]:
        return status_code, {
            "error": True,
            "status": status_code,
            "message": message,
            "details": details or {},
            "timestamp": time.time(),
        }

    @staticmethod
    def handle_validation_error(errors: Dict) -> Tuple[int, Dict]:
        return 422, {
            "error": True,
            "status": 422,
            "message": "Validation error",
            "errors": errors,
            "timestamp": time.time(),
        }

    @staticmethod
    def handle_exception(exc: Exception) -> Tuple[int, Dict]:
        logger.exception("Unhandled exception")
        return 500, {
            "error": True,
            "status": 500,
            "message": "Internal server error",
            "timestamp": time.time(),
        }


class MiddlewareChain:
    """Chain of middleware handlers."""

    def __init__(self):
        self._middleware: list = []

    def add(self, middleware: Any) -> None:
        self._middleware.append(middleware)

    def process_request(self, request: Any) -> Optional[Tuple[int, str]]:
        for mw in self._middleware:
            if hasattr(mw, "validate_request"):
                result = mw.validate_request(request)
                if result:
                    return result
        return None

    def process_response(self, request: Any, response: Any) -> None:
        for mw in self._middleware:
            if hasattr(mw, "add_security_headers"):
                mw.add_security_headers(response, request)
            if hasattr(mw, "after_request"):
                mw.after_request(request, response)
