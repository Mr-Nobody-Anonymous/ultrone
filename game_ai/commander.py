# Copyright (c) Ultrone Contributors. All rights reserved.
"""Utility-AI NPC squad commander with difficulty tiers.

Classic game-AI scoring, deliberately simple and legible:

- every alive unit is scored against three intents each tick:
  ``retreat`` (low HP), ``engage`` (enemy in range), ``advance``;
- the highest-scoring intent becomes that unit's order;
- difficulty scales reaction hesitation, aim error, aggression, and the
  retreat threshold -- NOT a smarter algorithm. Beating a harder tier means
  facing a sharper opponent, which is what players expect.

The commander never mutates the arena directly; it only emits
:class:`Order` objects that the :class:`game_ai.game.Game` adjudicates.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from game_ai.arena import Arena, Unit

Team = str  # "blue" | "red"


@dataclass(frozen=True)
class Difficulty:
    """Player-facing difficulty knob set."""

    name: str
    reaction_ticks: int      # ticks a unit may hesitate before engaging
    aim_error: float         # probability an attack misses outright
    aggression: float        # 0..1 willingness to push forward
    retreat_hp_fraction: float


EASY = Difficulty("easy", reaction_ticks=4, aim_error=0.40, aggression=0.35,
                  retreat_hp_fraction=0.55)
NORMAL = Difficulty("normal", reaction_ticks=2, aim_error=0.20, aggression=0.65,
                    retreat_hp_fraction=0.35)
HARD = Difficulty("hard", reaction_ticks=0, aim_error=0.07, aggression=0.90,
                  retreat_hp_fraction=0.20)


@dataclass(frozen=True)
class Order:
    """One adjudicated command for one unit this tick."""

    unit_id: str
    action: str                 # "attack" | "advance" | "retreat" | "hold"
    target_unit_id: Optional[str] = None
    move_to: Optional[tuple] = None


def _score_engage(unit: Unit, difficulty: Difficulty, rng: random.Random) -> float:
    base = 2.0 + difficulty.aggression
    return base + rng.uniform(0.0, 0.25)   # tiny noise breaks ties naturally


class UtilityAICommander:
    """Emits one :class:`Order` per alive friendly unit per decision tick."""

    def __init__(
        self, team: Team, difficulty: Difficulty, rng: Optional[random.Random] = None,
    ) -> None:
        assert team in ("blue", "red")
        self.team = team
        self.difficulty = difficulty
        self.rng = rng if rng is not None else random.Random()

    def decide(self, arena: Arena, tick: int) -> List[Order]:
        diff = self.difficulty
        orders: List[Order] = []
        for unit in arena.living(self.team):
            foe = arena.nearest_enemy(unit)

            # 1) Survival intent dominates when badly hurt.
            if unit.hp_fraction < diff.retreat_hp_fraction and foe is not None:
                away = (
                    unit.x + (unit.x - foe.x),
                    unit.y + (unit.y - foe.y),
                )
                orders.append(Order(
                    unit.unit_id, "retreat", move_to=_clamped(away, arena),
                ))
                continue

            if foe is None:
                orders.append(Order(unit.unit_id, "hold"))
                continue

            in_range = arena.distance(unit, foe) <= unit.range
            hesitating = (tick % max(1, diff.reaction_ticks + 1)) != 0

            # 2) Engage when effective; harder tiers hesitate less and miss less.
            if in_range and unit.ready_at <= tick and not hesitating:
                target = _pick_target(arena, unit, diff, rng=self.rng)
                orders.append(Order(unit.unit_id, "attack", target_unit_id=target.unit_id))
                continue

            # 3) Advance scaled by aggression (hold position when timid).
            if self.rng.random() < diff.aggression or in_range:
                if in_range:
                    # In range but on cooldown: close to mid-range pressure.
                    goal = ((unit.x + foe.x) / 2, (unit.y + foe.y) / 2)
                else:
                    goal = (foe.x, foe.y)
                orders.append(Order(
                    unit.unit_id, "advance", move_to=(goal[0], goal[1]),
                ))
            else:
                orders.append(Order(unit.unit_id, "hold"))
        return orders


def _pick_target(
    arena: Arena, unit: Unit, difficulty: Difficulty, rng: random.Random,
) -> Unit:
    """Focus-fire the weakest in-range foe; aggression widens the pool."""
    foes = arena.enemies_in_range(unit)
    if len(foes) <= 1:
        return foes[0]
    ranked = sorted(foes, key=lambda f: f.hp)
    pool = ranked[: max(1, int(round(len(ranked) * (0.5 + difficulty.aggression / 2))))]
    return pool[rng.randrange(len(pool))]


def _clamped(pt: tuple, arena: Arena) -> tuple:
    return (
        min(max(0.0, pt[0]), arena.size),
        min(max(0.0, pt[1]), arena.size),
    )
