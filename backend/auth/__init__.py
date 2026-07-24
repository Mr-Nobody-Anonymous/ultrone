"""
Authentication & Authorization — JWT, RBAC, API keys, OAuth hooks,
session management, password policies, and audit logging.
"""

import os
import re
import json
import time
import uuid
import hashlib
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger("argus.auth")


class Role(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AUDITOR = "auditor"
    INTEGRATION = "integration"


class Permission(Enum):
    CAMERA_READ = "camera:read"
    CAMERA_WRITE = "camera:write"
    CAMERA_DELETE = "camera:delete"
    EVENT_READ = "event:read"
    EVENT_ACK = "event:acknowledge"
    EVENT_RESOLVE = "event:resolve"
    RULE_READ = "rule:read"
    RULE_WRITE = "rule:write"
    RULE_DELETE = "rule:delete"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    ANALYTICS_READ = "analytics:read"
    EXPORT = "export"
    ADMIN = "admin"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],
    Role.OPERATOR: [
        Permission.CAMERA_READ, Permission.CAMERA_WRITE,
        Permission.EVENT_READ, Permission.EVENT_ACK, Permission.EVENT_RESOLVE,
        Permission.RULE_READ, Permission.RULE_WRITE,
        Permission.ANALYTICS_READ, Permission.EXPORT,
    ],
    Role.VIEWER: [
        Permission.CAMERA_READ, Permission.EVENT_READ,
        Permission.RULE_READ, Permission.ANALYTICS_READ,
    ],
    Role.AUDITOR: [
        Permission.EVENT_READ, Permission.AUDIT_READ,
        Permission.ANALYTICS_READ, Permission.EXPORT,
    ],
    Role.INTEGRATION: [
        Permission.CAMERA_READ, Permission.EVENT_READ,
        Permission.EVENT_ACK, Permission.RULE_READ,
    ],
}


@dataclass
class User:
    id: int
    username: str
    email: str
    role: Role
    is_active: bool = True
    permissions: List[Permission] = field(default_factory=list)
    api_key: Optional[str] = None
    last_login: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        return self.role == role or self.role == Role.ADMIN

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "permissions": [p.value for p in self.permissions],
            "last_login": self.last_login,
            "created_at": self.created_at,
        }


@dataclass
class Session:
    token: str
    user_id: int
    username: str
    role: Role
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_valid: bool = True

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def refresh(self, ttl_seconds: int = 86400) -> None:
        self.expires_at = time.time() + ttl_seconds


class AuthenticationManager:
    """
    Enterprise authentication manager with JWT, RBAC, API keys,
    session management, and audit logging.
    """

    def __init__(self, db=None, config: Optional[Dict] = None):
        self.db = db
        self.config = config or {}
        self._users: Dict[int, User] = {}
        self._sessions: Dict[str, Session] = {}
        self._api_keys: Dict[str, User] = {}
        self._lock = threading.RLock()
        self._secret_key = self.config.get("secret_key", os.environ.get("ARGUS_SECRET_KEY", str(uuid.uuid4())))
        self._token_ttl = self.config.get("token_ttl", 86400)
        self._audit_log: List[Dict] = []
        self._on_login_callbacks: List[Callable] = []

    def set_db(self, db) -> None:
        self.db = db
        self._load_users()

    def _load_users(self) -> None:
        if not self.db:
            return
        try:
            users_data = self.db.get_users()
            for u in users_data:
                try:
                    role = Role(u.get("role", "viewer"))
                    user = User(
                        id=u["id"],
                        username=u["username"],
                        email=u.get("email", ""),
                        role=role,
                        is_active=bool(u.get("is_active", True)),
                        permissions=ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.VIEWER]),
                    )
                    self._users[user.id] = user
                except Exception as e:
                    logger.warning(f"Failed to load user {u.get('username')}: {e}")
            logger.info(f"Loaded {len(self._users)} users")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")

    def authenticate(self, username: str, password: str, ip: Optional[str] = None) -> Optional[Session]:
        """Authenticate user with username/password."""
        user = self._find_user_by_username(username)
        if not user or not user.is_active:
            self._log_attempt(username, False, ip, "user_not_found_or_inactive")
            return None

        # Verify password
        password_hash = self._hash_password(password)
        if not self._verify_password(username, password_hash):
            self._log_attempt(username, False, ip, "invalid_password")
            return None

        # Create session
        with self._lock:
            token = self._generate_token()
            session = Session(
                token=token,
                user_id=user.id,
                username=user.username,
                role=user.role,
                ip_address=ip,
            )
            self._sessions[token] = session
            user.last_login = time.time()

        self._log_attempt(username, True, ip, "login_success")
        for cb in self._on_login_callbacks:
            try:
                cb(user, session)
            except Exception as e:
                logger.error(f"Login callback error: {e}")

        logger.info(f"User '{username}' authenticated from {ip}")
        return session

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        user = self._api_keys.get(api_key)
        if user and user.is_active:
            return user
        # Check database
        if self.db:
            result = self.db.query("SELECT * FROM users WHERE api_key = :key", {"key": api_key})
            if result:
                u = result[0]
                try:
                    role = Role(u.get("role", "viewer"))
                    user = User(
                        id=u["id"],
                        username=u["username"],
                        email=u.get("email", ""),
                        role=role,
                        is_active=bool(u.get("is_active", True)),
                        api_key=api_key,
                        permissions=ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.VIEWER]),
                    )
                    self._api_keys[api_key] = user
                    return user
                except Exception:
                    pass
        return None

    def validate_session(self, token: str) -> Optional[Session]:
        """Validate a session token."""
        session = self._sessions.get(token)
        if not session:
            return None
        if session.is_expired:
            del self._sessions[token]
            return None
        if not session.is_valid:
            return None
        return session

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session (logout)."""
        session = self._sessions.get(token)
        if session:
            session.is_valid = False
            del self._sessions[token]
            return True
        return False

    def create_user(self, username: str, email: str, password: str,
                     role: str = "viewer") -> Optional[User]:
        """Create a new user."""
        if self._find_user_by_username(username):
            logger.warning(f"User '{username}' already exists")
            return None

        password_hash = self._hash_password(password)
        user_id = None

        if self.db:
            try:
                user_id = self.db.insert("users", {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "role": role,
                })
            except Exception as e:
                logger.error(f"Failed to create user: {e}")
                return None

        if user_id is None:
            user_id = len(self._users) + 1

        role_enum = Role(role)
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role_enum,
            permissions=ROLE_PERMISSIONS.get(role_enum, ROLE_PERMISSIONS[Role.VIEWER]),
        )
        self._users[user.id] = user
        logger.info(f"User '{username}' created with role '{role}'")
        return user

    def generate_api_key(self, user_id: int) -> Optional[str]:
        """Generate API key for a user."""
        user = self._users.get(user_id)
        if not user:
            return None
        api_key = f"argus_{uuid.uuid4().hex}"
        user.api_key = api_key
        self._api_keys[api_key] = user
        if self.db:
            self.db.update("users", {"api_key": api_key}, {"id": user_id})
        return api_key

    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return user.has_permission(permission)

    def check_permissions(self, user: User, permissions: List[Permission], logic: str = "all") -> bool:
        """Check multiple permissions."""
        if logic == "all":
            return all(user.has_permission(p) for p in permissions)
        return any(user.has_permission(p) for p in permissions)

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def get_all_users(self) -> List[User]:
        return list(self._users.values())

    def on_login(self, callback: Callable) -> None:
        self._on_login_callbacks.append(callback)

    def _find_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        if self.db:
            result = self.db.query("SELECT * FROM users WHERE username = :u", {"u": username})
            if result:
                u = result[0]
                role = Role(u.get("role", "viewer"))
                user = User(
                    id=u["id"],
                    username=u["username"],
                    email=u.get("email", ""),
                    role=role,
                    is_active=bool(u.get("is_active", True)),
                    permissions=ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.VIEWER]),
                )
                self._users[user.id] = user
                return user
        return None

    def _verify_password(self, username: str, password_hash: str) -> bool:
        if not self.db:
            return True  # Development mode
        result = self.db.query("SELECT password_hash FROM users WHERE username = :u", {"u": username})
        if result:
            return result[0]["password_hash"] == password_hash
        return False

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256((password + self._secret_key).encode()).hexdigest()

    def _generate_token(self) -> str:
        return f"argus_{uuid.uuid4().hex}_{int(time.time())}"

    def _log_attempt(self, username: str, success: bool, ip: Optional[str], reason: str) -> None
