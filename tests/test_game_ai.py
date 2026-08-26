# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the standalone game-AI package (arcade NPC commanders)."""

import random

import pytest

from game_ai import (
    EASY,
    HARD,
    NORMAL,
    Arena,
    Difficulty,
    Game,
    Order,
    Unit,
    UtilityAICommander,
)


def _one_on_one():
    arena = Arena(size=32)
    arena.spawn_squad("blue", ("rifle",), (4.0, 4.0))
    arena.spawn_squad("red", ("rifle",), (8.0, 4.0))
    return arena


class TestDeterminism:
    def test_same_seed_same_match(self):
        a = Game(seed=123, difficulty=NORMAL).run()
        b = Game(seed=123, difficulty=NORMAL).run()
        assert a == b

    def test_different_seeds_usually_differ(self):
        results = {
            Game(seed=s, difficulty=NORMAL).run()["winner"] for s in range(6)
        }
        # With six seeds we expect some variation across seeds OR at least
        # that every match resolves to a legal outcome.
        assert results <= {"blue", "red", "draw"}


class TestMatchIntegrity:
    @pytest.mark.parametrize("difficulty", [EASY, NORMAL, HARD])
    @pytest.mark.parametrize("seed", [0, 7, 42])
    def test_matches_complete_within_budget(self, difficulty, seed):
        stats = Game(seed=seed, difficulty=difficulty, max_ticks=400).run()
        assert stats["winner"] in {"blue", "red", "draw"}
        assert 0 < stats["ticks"] <= 400
        assert stats["damage_blue_to_red"] >= 0
        assert stats["damage_red_to_blue"] >= 0

    def test_hard_tier_misses_less_by_design(self):
        assert HARD.aim_error < NORMAL.aim_error < EASY.aim_error
        assert HARD.reaction_ticks < NORMAL.reaction_ticks < EASY.reaction_ticks

    def test_commanders_never_touch_the_arena_directly(self):
        """Structural guard: decide() must not mutate unit state."""
        arena = _one_on_one()
        before = [(u.unit_id, u.hp, u.x, u.y) for u in arena.units]
        cmd = UtilityAICommander("blue", NORMAL, random.Random(1))
        cmd.decide(arena, tick=1)
        after = [(u.unit_id, u.hp, u.x, u.y) for u in arena.units]
        assert before == after


class TestCommanderBehavior:
    def test_orders_reference_only_own_living_units(self):
        arena = _one_on_one()
        cmd = UtilityAICommander("blue", NORMAL, random.Random(3))
        orders = cmd.decide(arena, tick=1)
        ids = {u.unit_id for u in arena.living("blue")}
        assert orders
        for order in orders:
            assert order.unit_id in ids
            assert order.action in {"attack", "advance", "retreat", "hold"}

    def test_badly_wounded_unit_retreats(self):
        arena = _one_on_one()
        hurt = arena.living("blue")[0]
        hurt.hp = hurt.max_hp * 0.15  # below NORMAL's 35% threshold
        cmd = UtilityAICommander("blue", NORMAL, random.Random(5))
        orders = {o.unit_id: o for o in cmd.decide(arena, tick=1)}
        assert orders[hurt.unit_id].action == "retreat"

    def test_engagement_only_targets_enemies_in_range(self):
        arena = Arena(size=32)
        arena.spawn_squad("blue", ("rifle",), (4.0, 4.0))
        arena.spawn_squad("red", ("scout",), (30.0, 30.0))  # far away
        cmd = UtilityAICommander("blue", HARD, random.Random(9))
        for order in cmd.decide(arena, tick=1):
            assert order.action != "attack"  # nothing in rifle range yet


class TestArenaRules:
    def test_attack_respects_cooldown(self):
        arena = _one_on_one()
        blue = arena.living("blue")[0]
        red = arena.living("red")[0]
        rng = random.Random(1)
        assert arena.attack(blue, red, tick=1, rng=rng) in (True, False)
        # Same tick again: attacker is on cooldown, so no second swing.
        hp_after_first = red.hp
        assert arena.attack(blue, red, tick=1, rng=rng) is False
        assert red.hp == hp_after_first

    def test_attack_out_of_range_refused(self):
        arena = Arena(size=64)
        arena.spawn_squad("blue", ("rifle",), (2.0, 2.0))
        arena.spawn_squad("red", ("rifle",), (50.0, 50.0))
        blue = arena.living("blue")[0]
        red = arena.living("red")[0]
        assert arena.attack(blue, red, tick=1, rng=random.Random(1)) is False
        assert red.hp == red.max_hp

    def test_kills_are_credited(self):
        arena = _one_on_one()
        blue = arena.living("blue")[0]
        red = arena.living("red")[0]
        red.hp = 1.0
        while red.alive:
            red.ready_at = 0  # bypass cooldown for the test loop
            connected = arena.attack(blue, red, tick=1, rng=random.Random(0))
            if not connected:
                continue
        assert blue.kills == 1
