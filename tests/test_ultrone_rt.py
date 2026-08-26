# Copyright (c) Ultrone Contributors. All rights reserved.
"""Runtime kernel tests (pure-Python backend; Rust parity when built)."""

import math

import pytest

import ultrone_rt
from ultrone_rt.loader import backend_info, get_kernels


class TestBackendSelection:
    def test_backend_is_python_until_core_is_built(self):
        info = backend_info()
        assert info["backend"] == "python" or info["backend"] == "rust"
        assert info["rust_available"] is False  # no toolchain on CI/dev box

    def test_loader_returns_working_module(self):
        kernels = get_kernels()
        assert hasattr(kernels, "WorldState")
        assert hasattr(kernels, "batch_sphere_eval")


class TestWorldStateAndSimulator:
    def test_spawn_duplicate_rejected(self):
        world = ultrone_rt.WorldState()
        world.spawn("e1", 1.0, 2.0)
        with pytest.raises(ValueError):
            world.spawn("e1", 3.0, 4.0)

    def test_fixed_step_integration(self):
        world = ultrone_rt.WorldState()
        world.spawn("mover", x=0.0, y=0.0, vx=1.0, vy=-2.0)
        simulator = ultrone_rt.Simulator(world, dt=0.5)
        assert simulator.run(10) == 10
        state = world.get("mover")
        assert state["x"] == pytest.approx(5.0)
        assert state["y"] == pytest.approx(-10.0)

    def test_snapshot_restore_roundtrip(self):
        world = ultrone_rt.WorldState()
        world.spawn("a", 1.0, 1.0, vx=0.5)
        snapshot = world.snapshot()
        for _ in range(3):                    # three ticks of dt=1
            world.step(1.0)
        assert world.tick() == 3
        assert world.get("a")["x"] == pytest.approx(2.5)
        world.restore(snapshot)
        assert world.tick() == snapshot["tick"]
        assert world.get("a")["x"] == 1.0


class TestSpatialIndex:
    def test_radius_query_nearest_first(self):
        index = ultrone_rt.SpatialIndex(cell_size=1.0)
        index.insert("far", 10.0, 10.0)
        index.insert("near", 0.5, 0.5)
        index.insert("mid", 1.5, 1.0)
        hits = index.query_radius(0.0, 0.0, 2.0)
        assert hits[0] == "near"
        assert set(hits) == {"near", "mid"}
        assert "far" not in hits

    def test_empty_result_outside_range(self):
        index = ultrone_rt.SpatialIndex()
        index.insert("p", 50.0, 50.0)
        assert index.query_radius(0.0, 0.0, 1.0) == []


class TestTickScheduler:
    def test_fifo_order_by_tick_then_id(self):
        scheduler = ultrone_rt.TickScheduler()
        scheduler.schedule(5, "b")
        scheduler.schedule(5, "a")
        scheduler.schedule(2, "early")
        due = scheduler.pop_due(5)
        assert [task for task, _ in due] == ["early", "a", "b"]
        assert scheduler.pending() == 0

    def test_future_tasks_stay_queued(self):
        scheduler = ultrone_rt.TickScheduler()
        scheduler.schedule(9, "later")
        assert scheduler.pop_due(5) == []
        assert scheduler.pending() == 1

    def test_cancel_removes_task(self):
        scheduler = ultrone_rt.TickScheduler()
        scheduler.schedule(3, "gone")
        assert scheduler.cancel("gone") is True
        assert scheduler.cancel("gone") is False
        assert scheduler.pop_due(10) == []

    def test_duplicate_task_id_rejected(self):
        scheduler = ultrone_rt.TickScheduler()
        scheduler.schedule(1, "dup")
        with pytest.raises(ValueError):
            scheduler.schedule(2, "dup")


class TestCommandRouter:
    def test_known_route_accepted_and_logged(self):
        router = ultrone_rt.CommandRouter()
        router.register("propulsion", "set_throttle")
        result = router.route("propulsion", "set_throttle")
        assert result["ok"] is True
        tail = router.log_tail(1)
        assert tail[0]["accepted"] is True
        assert tail[0]["target"] == "propulsion"

    def test_unknown_route_fails_cleanly(self):
        router = ultrone_rt.CommandRouter()
        router.register("navigation", "set_heading")
        result = router.route("warp", "engage")
        assert result["ok"] is False

    def test_duplicate_route_registration_rejected(self):
        router = ultrone_rt.CommandRouter()
        router.register("power", "recharge")
        with pytest.raises(ValueError):
            router.register("power", "recharge")


class TestMemoryIndex:
    def test_index_search_remove(self):
        index = ultrone_rt.MemoryIndex()
        index.index_document("d1", "Patrol pace matters")
        index.index_document("d2", "Speed costs energy")
        assert index.search("speed") == ["d2"]
        assert index.search("patrol") == ["d1"]
        assert index.remove_document("d1") is True
        assert index.search("patrol") == []
        assert index.stats()["documents"] == 1

    def test_duplicate_document_rejected(self):
        index = ultrone_rt.MemoryIndex()
        index.index_document("x", "hello")
        with pytest.raises(ValueError):
            index.index_document("x", "again")


class TestTensorOpsAndBatchEval:
    def test_softmax_sums_to_one_and_is_shift_invariant(self):
        scores = [1000.0, 1001.0, 1002.0]
        probs = get_kernels().softmax(scores)
        assert sum(probs) == pytest.approx(1.0)
        shifted = get_kernels().softmax([v - 1000.0 for v in scores])
        assert probs == pytest.approx(shifted)

    def test_dot_and_cosine(self):
        k = get_kernels()
        assert k.dot_product([1, 2, 3], [4, 5, 6]) == 32
        assert k.cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
        assert k.cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_top_k_stable_on_ties(self):
        assert get_kernels().top_k_indices([5.0, 7.0, 7.0, 1.0], 2) == \
            [1, 2]

    def test_batch_sphere_eval_matches_manual(self):
        population = [[1.0, 2.0], [0.0, 0.0], [3.0]]
        expected = [5.0, 0.0, 9.0]
        result = get_kernels().batch_sphere_eval(population)
        assert result == pytest.approx(expected)