"""Automatic hyperparameter tuning."""
from __future__ import annotations
from typing import Any, Dict, Optional

class AutoTuner:
    def __init__(self, method: str = "random") -> None:
        self.method = method
        self._trials: list = []
    def suggest(self, space: Dict[str, Any]) -> Dict[str, Any]:
        import random
        config = {}
        for key, spec in space.items():
            if isinstance(spec, list):
                config[key] = random.choice(spec)
            elif isinstance(spec, dict) and "range" in spec:
                lo, hi = spec["range"]
                config[key] = random.uniform(lo, hi) if spec.get("type") == "float" else random.randint(int(lo), int(hi))
            else:
                config[key] = spec
        self._trials.append(config)
        return config
    @property
    def trial_count(self) -> int:
        return len(self._trials)
