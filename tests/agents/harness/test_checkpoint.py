# Copyright (c) Ultrone Contributors. All rights reserved.
import tempfile
from pathlib import Path

from packages.agents.harness.checkpoint import CheckpointStore
from packages.agents.harness.schemas import CheckpointData


def test_in_memory_checkpoint_save_and_load():
    store = CheckpointStore()
    cp = CheckpointData(
        task_id="task-123",
        goal={"description": "Test in-memory checkpoint"},
        current_phase="EXECUTING",
        completed_steps=[{"step": 1, "action": "init"}],
    )
    store.save(cp)

    loaded = store.load_latest("task-123")
    assert loaded is not None
    assert loaded.task_id == "task-123"
    assert loaded.current_phase == "EXECUTING"
    assert len(loaded.completed_steps) == 1


def test_disk_atomic_checkpoint_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CheckpointStore(storage_dir=tmpdir)
        cp1 = CheckpointData(
            task_id="task-disk-1",
            goal={"description": "Disk task"},
            current_phase="PLANNING",
            working_state={"step": 1},
        )
        store.save(cp1)

        cp2 = CheckpointData(
            task_id="task-disk-1",
            goal={"description": "Disk task"},
            current_phase="EXECUTING",
            working_state={"step": 2},
        )
        store.save(cp2)

        latest = store.load_latest("task-disk-1")
        assert latest is not None
        assert latest.current_phase == "EXECUTING"
        assert latest.working_state["step"] == 2

        all_cps = store.list_checkpoints("task-disk-1")
        assert len(all_cps) == 2
