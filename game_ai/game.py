# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deterministic match loop: two AI-commanded squads, one winner.

Pacing guardrails keep matches watchable: a hard tick ceiling plus symmetric
squad composition. The loop is fully deterministic given (seed, difficulties).
"""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from game_ai.arena import Arena, TEAM_BLUE, TEAM_RED, _SQUAD_TEMPLATE
from game_ai.commander import Difficulty, NORMAL, UtilityAICommander


class Game:
    """One complete arcade skirmish between two utility-AI commanders."""

    def __init__(
        self,
        seed: int = 0,
        difficulty: Difficulty = NORMAL,
        blue_difficulty: Optional[Difficulty] = None,
        max_ticks: int = 400,
        size: float = 48.0,
    ) -> None:
        self.rng = random.Random(seed)
        self.arena = Arena(size=size)
        inset = size * 0.15
        self.arena.spawn_squad(TEAM_BLUE, _SQUAD_TEMPLATE, (inset, inset))
        self.arena.spawn_squad(
            TEAM_RED, _SQUAD_TEMPLATE, (size - inset, size - inset),
        )
        self.max_ticks = max_ticks
        self.tick = 0
        self.blue_commander = UtilityAICommander(
            TEAM_BLUE, blue_difficulty or difficulty, random.Random(seed ^ 0xA11CE),
        )
        self.red_commander = UtilityAICommander(
            TEAM_RED, difficulty, random.Random(seed ^ 0xB0B),
        )

    # -- simulation ---------------------------------------------------------- #
    def step(self) -> bool:
        """Advance one tick. Returns True while the match is still running."""
        if self.finished:
            return False
        self.tick += 1
        for commander in (self.blue_commander, self.red_commander):
            for order in commander.decide(self.arena, self.tick):
                self._adjudicate(order, commander.difficulty.aim_error)
        return not self.finished

    def _adjudicate(self, order, miss_chance: float) -> None:
        unit = next((u for u in self.arena.living()
                     if u.unit_id == order.unit_id), None)
        if unit is None:
            return
        if order.action == "attack":
            target = next(
                (u for u in self.arena.living()
                 if u.unit_id == order.target_unit_id), None,
            )
            if target is not None and target.team != unit.team:
                self.arena.attack(
                    unit, target, self.tick, self.rng,
                    miss_chance=miss_chance,
                )
        elif order.action in ("advance", "retreat") and order.move_to:
            self.arena.move_unit(unit, order.move_to[0], order.move_to[1])

    @property
    def finished(self) -> bool:
        return (
            not self.arena.living(TEAM_BLUE)
            or not self.arena.living(TEAM_RED)
            or self.tick >= self.max_ticks
        )

    def run(self) -> Dict[str, Any]:
        """Play to completion; returns a spectator-friendly stat line."""
        while self.step():
            pass
        blue, red = self.arena.living(TEAM_BLUE), self.arena.living(TEAM_RED)
        if blue and not red:
            winner = TEAM_BLUE
        elif red and not blue:
            winner = TEAM_RED
        else:
            winner = "draw"
        return {
            "winner": winner,
            "ticks": self.tick,
            "blue_survivors": len(blue),
            "red_survivors": len(red),
            "damage_blue_to_red": sum(u.damage_dealt for u in self.arena.units
                                      if u.team == TEAM_BLUE),
            "damage_red_to_blue": sum(u.damage_dealt for u in self.arena.units
                                      if u.team == TEAM_RED),
        }
