"""Plugin marketplace registry."""
from __future__ import annotations
from typing import Dict, List, Optional

class PluginMarketplace:
    def __init__(self) -> None:
        self._plugins: Dict[str, dict] = {}
    def publish(self, name: str, version: str, description: str = "") -> None:
        self._plugins[name] = {"version": version, "description": description, "downloads": 0}
    def search(self, query: str) -> List[dict]:
        query = query.lower()
        return [{"name": n, **info} for n, info in self._plugins.items() if query in n.lower() or query in info.get("description", "").lower()]
    def download(self, name: str) -> Optional[dict]:
        plugin = self._plugins.get(name)
        if plugin:
            plugin["downloads"] += 1
            return {"name": name, **plugin}
        return None
    @property
    def plugin_count(self) -> int:
        return len(self._plugins)
