import math
from typing import Any

def haversine_distance(pos1: tuple, pos2: tuple) -> float:
    """Calculate distance in meters between two lat/lon positions."""
    R = 6371000
    lat1, lon1 = pos1[0], pos1[1]
    lat2, lon2 = pos2[0], pos2[1]
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def calculate_bearing(pos1: tuple, pos2: tuple) -> float:
    """Calculate bearing in degrees from pos1 to pos2."""
    lat1, lon1 = math.radians(pos1[0]), math.radians(pos1[1])
    lat2, lon2 = math.radians(pos2[0]), math.radians(pos2[1])
    dlon = math.radians(pos2[1] - pos1[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y))

def intercept_course(pursuer: tuple, target: tuple, target_velocity: tuple) -> tuple:
    """Calculate intercept course for pursuer to target."""
    px, py, pz = pursuer
    tx, ty, tz = target
    tvx, tvy, tvz = target_velocity
    dx, dy, dz = tx - px, ty - py, tz - pz
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    if dist == 0:
        return (0, 0, 0)
    return (dx/dist, dy/dist, dz/dist)

def line_of_sight(pos1: tuple, pos2: tuple, terrain_height: float = 0) -> bool:
    """Check if line of sight exists between positions."""
    dx, dy, dz = pos2[0] - pos1[0], pos2[1] - pos1[1], pos2[2] - pos1[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    height_diff = pos2[2] - pos1[2]
    return height_diff > terrain_height or dist < 1000