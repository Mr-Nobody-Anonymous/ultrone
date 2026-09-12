# Copyright (c) Ultrone Contributors. All rights reserved.
"""Standalone game-AI package: NPC squad commanders for arcade wargames.

This package is *fully self-contained* -- it imports nothing from ``core``,
``brain``, ``sim``, or any other part of the research platform. It exists to
explore classic game-AI techniques (utility AI, behavior-style selectors,
difficulty scaling) for entertainment products: RTS-lite opponents, FPS bot
squad leaders, vehicle-combat skirmish AI.

Design goals (in priority order):

1. **Fun** -- readable matches, dramatic moments, comeback potential.
2. **Responsiveness** -- decisions within a frame budget on consumer hardware.
3. **Determinism** -- (seed, difficulty) reproduces a match exactly, for
   replay tools, CI smoke tests, and bug reports.
"""

from game_ai.arena import Arena, Unit
from game_ai.commander import (
    EASY,
    HARD,
    NORMAL,
    Difficulty,
    Order,
    UtilityAICommander,
)
from game_ai.game import Game

__all__ = [
    "Arena",
    "Unit",
    "Difficulty",
    "UtilityAICommander",
    "Order",
    "Game",
    "EASY",
    "NORMAL",
    "HARD",
]
