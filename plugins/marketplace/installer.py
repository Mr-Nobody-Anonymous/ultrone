"""Plugin installer."""
from __future__ import annotations
import os
from typing import List, Optional

class PluginInstaller:
    def __init__(self, plugin_dir: str = "plugins") -> None:
        self.plugin_dir = plugin_dir
        self._installed: List[str] = []
    def install(self, name: str, source: str = "") -> bool:
        plugin_path = os.path.join(self.plugin_dir, name)
        os.makedirs(plugin_path, exist_ok=True)
        init_path = os.path.join(plugin_path, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write(f'"""Plugin {name}."""\n')
        self._installed.append(name)
        return True
    def uninstall(self, name: str) -> bool:
        if name in self._installed:
            self._installed.remove(name)
            return True
        return False
    def is_installed(self, name: str) -> bool:
        return name in self._installed
    @property
    def installed_plugins(self) -> List[str]:
        return list(self._installed)
