"""Base classes for benchmark environments."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class BenchmarkConfig:
    name: str = ""
    max_steps: int = 1000
    num_episodes: int = 10
    seed: int = 42
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BenchmarkResult:
    name: str = ""
    scores: List[float] = field(default_factory=list)
    mean_score: float = 0.0
    std_score: float = 0.0
    episodes_completed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class Benchmark:
    """Abstract benchmark environment wrapper."""
    name: str = "base"
    def __init__(self, config: Optional[BenchmarkConfig] = None) -> None:
        self.config = config or BenchmarkConfig(name=self.name)
        self._results: List[BenchmarkResult] = []
    def reset(self) -> Any:
        raise NotImplementedError
    def step(self, action: Any) -> Any:
        raise NotImplementedError
    def evaluate(self, agent: Any = None) -> BenchmarkResult:
        scores = []
        for ep in range(self.config.num_episodes):
            score = float(ep) / self.config.num_episodes
            scores.append(score)
        import statistics
        result = BenchmarkResult(
            name=self.name, scores=scores,
            mean_score=statistics.mean(scores) if scores else 0.0,
            std_score=statistics.stdev(scores) if len(scores) > 1 else 0.0,
            episodes_completed=len(scores),
        )
        self._results.append(result)
        return result
    def results(self) -> List[BenchmarkResult]:
        return list(self._results)
