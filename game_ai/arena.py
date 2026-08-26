# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-contained arcade arena: units, movement, ranged attacks.

Pure game logic -- no research-platform imports, no networking, no
persistence. Coordinates are floats on a square field; combat is
range-based with per-unit cooldowns.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

TEAM_BLUE = "blue"
TEAM_RED = "red"

#: kind -> (max_hp, speed tiles/tick, range, damage, cooldown ticks)
UNIT_STATS: Dict[str, Tuple[int, float, float, int, int]] = {
    "scout":  (60,  2.6, 5.0, 8,  1),
    "rifle":  (100, 1.8, 7.0, 14, 2),
    "heavy":  (220, 1.0, 9.0, 30, 3),
}

_SQUAD_TEMPLATE = ("scout", "rifle", "rifle", "heavy")


@dataclass
class Unit:
    unit_id: str
    team: str
    kind: str
    hp: float
    x: float
    y: float
    ready_at: int = 0          # earliest tick this unit may act again
    kills: int = 0
    damage_dealt: int = 0

    @property
    def max_hp(self) -> int:
        return UNIT_STATS[self.kind][0]

    @property
    def speed(self) -> float:
        return UNIT_STATS[self.kind][1]

    @property
    def range(self) -> float:
        return UNIT_STATS[self.kind][2]

    @property
    def damage(self) -> int:
        return UNIT_STATS[self.kind][3]

    @property
    def cooldown(self) -> int:
        return UNIT_STATS[self.kind][4]

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def hp_fraction(self) -> float:
        return max(0.0, self.hp / self.max_hp)


class Arena:
    """A square battlefield holding both teams' units."""

    def __init__(self, size: float = 64.0) -> None:
        self.size = size
        self.units: List[Unit] = []
        self._next_id = 0

    # -- setup ------------------------------------------------------------- #
    def spawn_squad(self, team: str, kinds: tuple, origin: Tuple[float, float]) -> None:
        ox, oy = origin
        for i, kind in enumerate(kinds):
            self.units.append(Unit(
                unit_id=f"{team}-{self._next_id}",
                team=team, kind=kind,
                hp=float(UNIT_STATS[kind][0]),
                x=min(max(0.0, ox + (i % 2) * 2.0), self.size),
                y=min(max(0.0, oy + (i // 2) * 2.0), self.size),
            ))
            self._next_id += 1

    # -- queries ----------------------------------------------------------- #
    def living(self, team: Optional[str] = None) -> List[Unit]:
        return [u for u in self.units if u.alive and (team is None or u.team == team)]

    def enemies_in_range(self, unit: Unit) -> List[Unit]:
        return [
            e for e in self.living(None)
            if e.team != unit.team and self.distance(unit, e) <= unit.range
        ]

    def nearest_enemy(self, unit: Unit) -> Optional[Unit]:
        foes = [e for e in self.living(None) if e.team != unit.team]
        if not foes:
            return None
        return min(foes, key=lambda e: self.distance(unit, e))

    @staticmethod
    def distance(a: Unit, b: Unit) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    # -- actions ----------------------------------------------------------- #
    def move_unit(self, unit: Unit, tx: float, ty: float) -> None:
        """Move toward (tx, ty) at most ``unit.speed``; clamped to the field."""
        dist = math.hypot(tx - unit.x, ty - unit.y)
        step = min(unit.speed, dist)
        if dist > 1e-9:
            unit.x += (tx - unit.x) / dist * step
            unit.y += (ty - unit.y) / dist * step
        unit.x = min(max(0.0, unit.x), self.size)
        unit.y = min(max(0.0, unit.y), self.size)

    def attack(self, attacker: Unit, target: Unit, tick: int,
               rng: random.Random, miss_chance: float = 0.0) -> bool:
        """Resolve one attack. Returns True if it connected."""
        if not attacker.alive or not target.alive:
            return False
        if tick < attacker.ready_at:
            return False
        if self.distance(attacker, target) > attacker.range + 1e-9:
            return False
        attacker.ready_at = tick + attacker.cooldown
        if rng.random() < miss_chance:
            return False  # dramatic near-miss; nothing else happens
        dmg = attacker.damage
        target.hp = max(0.0, target.hp - dmg)
        attacker.damage_dealt += dmg
        if not target.alive:
            attacker.kills += 1
        return True
