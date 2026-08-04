"""Code execution sandbox."""
from __future__ import annotations
from typing import Any, Dict, Optional

class Sandbox:
    def __init__(self, timeout: float = 30.0, max_memory: int = 256*1024*1024) -> None:
        self.timeout = timeout
        self.max_memory = max_memory
        self._violations: list = []
    def execute(self, code: str, globals_dict: Optional[Dict] = None) -> Any:
        safe_globals = {"__builtins__": {}}
        if globals_dict:
            safe_globals.update(globals_dict)
        try:
            exec(code, safe_globals)
            return safe_globals.get("__result__")
        except Exception as e:
            self._violations.append(str(e))
            return None
    @property
    def violations(self) -> list:
        return list(self._violations)
