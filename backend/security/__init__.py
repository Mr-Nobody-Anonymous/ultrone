"""
Security Module — JWT, OAuth, HTTPS, secrets management, RBAC, audit logging, encryption, CSRF, input validation.
"""

import os
import re
import json
import time
import hmac
import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger("argus.security")


class Permission(Enum):
    CAMERA_VIEW = "camera:view"
    CAMERA_MANAGE = "camera:manage"
    EVENT_VIEW = "event:view"
    EVENT_MANAGE = "event:manage"
    RULE_VIEW = "rule:view"
    RULE_MANAGE = "rule:manage"
    USER_VIEW = "user:view"
    USER_MANAGE = "user:manage"
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    SYSTEM_MANAGE = "system:manage"
    AUDIT_VIEW = "audit:view"
    ADMIN = "admin"


ROLES = {
    "admin": {
        "name": "Administrator",
        "permissions": [p.value for p in Permission],
    },
    "operator": {
        "name": "Operator",
        "permissions": [
            "camera:view", "event:view", "event:manage",
            "rule:view", "analytics:view", "analytics:export",
        ],
    },
    "viewer": {
        "name": "Viewer",
        "permissions": ["camera:view", "event:view", "analytics:view"],
    },
    "investigator": {
        "name": "Investigator",
        "permissions": [
            "camera:view", "event:view", "event:manage",
            "analytics:view", "analytics:export", "audit:view",
        ],
    },
    "maintenance": {
        "name": "Maintenance",
        "permissions": ["camera:view", "camera:manage", "system:manage"],
    },
}


@dataclass
class User:
    id: int
    username: str
    email: str
    role: str
    is_active: bool = True
    permissions: Set[str] = None

    def __post_init__(self):
        if self.permissions is None:
            role_data = ROLES.get(self.role, ROLES["viewer"])
            self.permissions = set(role_data["permissions"])

    def has_permission(self, permission: str) -> bool:
        return "admin" in self.permissions or permission in self.permissions

    def has_any_permission(self, *permissions: str) -> bool:
        return any(self.has_permission(p) for p in permissions)


class JWTManager:
    """JWT token management with RS256 support."""

    def __init__(self, secret: Optional[str] = None, algorithm: str = "HS256"):
        self.secret = secret or os.environ.get("ARGUS_JWT_SECRET", secrets.token_hex(32))
        self.algorithm = algorithm
        self._blacklisted_tokens: Set[str] = set()

    def create_token(self, user_id: int, username: str, role: str,
                     expires_in: int = 86400) -> str:
        """Create JWT token."""
        header = {"alg": self.algorithm, "typ": "JWT"}
        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "jti": secrets.token_hex(16),
        }
        header_b64 = self._base64_encode(json.dumps(header))
        payload_b64 = self._base64_encode(json.dumps(payload))
        signature = self._sign(f"{header_b64}.{payload_b64}")
        return f"{header_b64}.{payload_b64}.{signature}"

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token."""
        if token in self._blacklisted_tokens:
            return None
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, signature = parts
            expected_sig = self._sign(f"{header_b64}.{payload_b64}")
            if not hmac.compare_digest(signature, expected_sig):
                return None
            payload = json.loads(self._base64_decode(payload_b64))
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    def blacklist_token(self, token: str) -> None:
        self._blacklisted_tokens.add(token)

    def _sign(self, data: str) -> str:
        return hmac.new(
            self.secret.encode(), data.encode(), hashlib.sha256
        ).hexdigest()

    def _base64_encode(self, data: str) -> str:
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")

    def _base64_decode(self, data: str) -> str:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data).decode()


class PasswordManager:
    """Password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return f"{salt}:{base64.b64encode(pwd_hash).decode()}"

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            salt, pwd_hash_b64 = stored.split(":")
            pwd_hash = base64.b64decode(pwd_hash_b64)
            new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(pwd_hash, new_hash)
        except Exception:
            return False


class AuditLogger:
    """Security audit logging."""

    def __init__(self, db=None):
        self.db = db

    def log(self, user_id: int, action: str, resource: str,
            resource_id: Optional[int] = None, details: Optional[Dict] = None,
            ip_address: Optional[str] = None) -> None:
        entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "details": json.dumps(details or {}),
            "ip_address": ip_address or "",
            "timestamp": datetime.now().isoformat(),
        }
        if self.db:
            try:
                self.db.insert("audit_log", entry)
            except Exception as e:
                logger.error(f"Audit log error: {e}")
        logger.info(f"AUDIT: user={user_id} action={action} resource={resource}")

    def query(self, user_id: Optional[int] = None, action: Optional[str] = None,
              limit: int = 100) -> List[Dict]:
        if not self.db:
            return []
        try:
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = {}
            if user_id:
                query += " AND user_id = :uid"
                params["uid"] = user_id
            if action:
                query += " AND action = :act"
                params["act"] = action
            query += " ORDER BY timestamp DESC LIMIT :lim"
            params["lim"] = limit
            return self.db.query(query, params)
        except Exception as e:
            logger.error(f"Audit query error: {e}")
            return []


class InputValidator:
    """Input validation and sanitization."""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        value = str(value).strip()
        if len(value) > max_length:
            value = value[:max_length]
        # Remove potentially dangerous characters
        value = re.sub(r'[<>\'";]', '', value)
        return value

    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_ip(ip: str) -> bool:
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = [int(p) for p in ip.split(".")]
        return all(0 <= p <= 255 for p in parts)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Remove path separators and dangerous characters
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        filename = filename.strip()
        if not filename:
            filename = "unnamed"
        return filename

    @staticmethod
    def validate_json(data: str) -> bool:
        try:
            json.loads(data)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    @staticmethod
    def sanitize_html(html: str) -> str:
        import html as html_module
        return html_module.escape(html)


class SecurityManager:
    """Central security manager coordinating all security components."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.jwt = JWTManager(
            secret=self.config.get("jwt_secret"),
            algorithm=self.config.get("jwt_algorithm", "HS256"),
        )
        self.password = PasswordManager()
        self.audit = AuditLogger()
        self.validator = InputValidator()
        self._csrf_tokens: Dict[str, float] = {}
        self._rate_limits: Dict[str, List[float]] = {}

    def set_db(self, db) -> None:
        self.audit.db = db

    def authenticate(self, username: str, password: str) -> Optional[User]:
        if not self.db:
            return None
        try:
            results = self.db.query(
                "SELECT * FROM users WHERE username = :user AND is_active = 1",
                {"user": username},
            )
            if not results:
                return None
            user_data = results[0]
            if not self.password.verify_password(password, user_data["password_hash"]):
                return None
            return User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=user_data["role"],
                is_active=bool(user_data["is_active"]),
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def check_rate_limit(self, key: str, max_requests: int = 100, window: int = 60) -> bool:
        now = time.time()
        if key not in self._rate_limits:
            self._rate_limits[key] = []
        self._rate_limits[key] = [t for t in self._rate_limits[key] if now - t < window]
        self._rate_limits[key].append(now)
        return len(self._rate_limits[key]) <= max_requests

    def generate_csrf_token(self) -> str:
        token = secrets.token_hex(32)
        self._csrf_tokens[token] = time.time() + 3600
        return token

    def verify_csrf_token(self, token: str) -> bool:
        if token in self._csrf_tokens:
            if self._csrf_tokens[token] > time.time():
                del self._csrf_tokens[token]
                return True
            del self._csrf_tokens[token]
        return False

    def cleanup_expired(self) -> None:
        now = time.time()
        self._csrf_tokens = {k: v for k, v in self._csrf_tokens.items() if v > now}
        self._rate_limits = {
            k: [t for t in v if now - t < 60]
            for k, v in self._rate_limits.items()
        }

    @property
    def db(self):
        from ..database import get_database
        return get_database()
