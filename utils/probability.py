import random
from typing import Any, List, Tuple

def bayesian_update(prior: float, likelihood: float, evidence: float) -> float:
    """Bayesian probability update."""
    return (likelihood * prior) / evidence if evidence > 0 else prior

def confidence_decay(confidence: float, time_elapsed: float, decay_rate: float = 0.1) -> float:
    """Decay confidence over time."""
    return max(0.0, confidence - (decay_rate * time_elapsed))

def weighted_choice(choices: List[Tuple[Any, float]], total_weight: float = None) -> Any:
    """Select from weighted choices."""
    if not choices:
        return None
    total = total_weight or sum(w for _, w in choices)
    r = random.uniform(0, total)
    cumsum = 0
    for choice, weight in choices:
        cumsum += weight
        if r <= cumsum:
            return choice
    return choices[-1][0]