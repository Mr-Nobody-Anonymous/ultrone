"""Neural Architecture Search."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Architecture:
    name: str = ""
    layers: List[Dict[str, Any]] = field(default_factory=list)
    params: int = 0
    score: float = 0.0

class NeuralArchitectureSearch:
    def __init__(self, search_space: Optional[Dict[str, Any]] = None) -> None:
        self.search_space = search_space or {"max_layers": 10, "hidden_range": (32, 512)}
        self._candidates: List[Architecture] = []
    def sample(self) -> Architecture:
        import random
        num_layers = random.randint(1, self.search_space["max_layers"])
        layers = [{"type": "linear", "size": random.randint(*self.search_space["hidden_range"])} for _ in range(num_layers)]
        arch = Architecture(name=f"arch_{len(self._candidates)}", layers=layers, params=sum(l["size"] for l in layers))
        self._candidates.append(arch)
        return arch
    def best(self) -> Optional[Architecture]:
        if not self._candidates:
            return None
        return max(self._candidates, key=lambda a: a.score)
    @property
    def candidate_count(self) -> int:
        return len(self._candidates)
