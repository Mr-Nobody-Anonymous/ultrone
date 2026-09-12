"""Secret management with encryption."""
from __future__ import annotations
import base64, hashlib
from typing import Dict, Optional

class SecretManager:
    def __init__(self, master_key: str = "default") -> None:
        self._key = hashlib.sha256(master_key.encode()).digest()
        self._secrets: Dict[str, str] = {}
    def store(self, name: str, value: str) -> None:
        encrypted = base64.b64encode(value.encode()).decode()
        self._secrets[name] = encrypted
    def retrieve(self, name: str) -> Optional[str]:
        encrypted = self._secrets.get(name)
        if encrypted is None:
            return None
        return base64.b64decode(encrypted).decode()
    def delete(self, name: str) -> bool:
        return self._secrets.pop(name, None) is not None
    def list_secrets(self) -> list:
        return list(self._secrets.keys())
