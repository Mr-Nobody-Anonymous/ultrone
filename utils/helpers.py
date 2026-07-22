import math
from typing import Tuple

def format_position(pos: Tuple[float, float, float]) -> str:
    """Format position as X,Y,Z string."""
    return f"({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})"

def calculate_speed(velocity: Tuple[float, float, float]) -> float:
    """Calculate speed from velocity vector."""
    return math.sqrt(sum(v*v for v in velocity))

def estimate_time_to_target(distance: float, speed: float) -> float:
    """Estimate time to target in seconds."""
    return distance / speed if speed > 0 else float('inf')