# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for the canonical world model and entity component model."""

import pytest
from packages.core.world_model import WorldModel, Entity, Component, Provenance, EntityUpdated


def test_entity_creation_and_components():
    entity = Entity(entity_id="test_entity_01", type="air_asset")
    assert entity.entity_id == "test_entity_01"
    assert entity.type == "air_asset"
    assert entity.status == "active"

    prov = Provenance(source="radar_01", transformation="fusion", model="ekf_v1")
    entity.set("position", {"lat": 34.05, "lng": -118.25}, confidence=0.92, provenance=[prov])

    pos = entity.get("position")
    assert pos["lat"] == 34.05
    assert entity.components["position"].confidence == 0.92
    assert len(entity.components["position"].provenance) == 1
    assert entity.components["position"].provenance[0].source == "radar_01"


def test_world_model_upsert_and_get():
    wm = WorldModel()
    entity = Entity(entity_id="e_001", type="ground_unit")
    entity.set("speed", 45, confidence=0.88)

    wm.upsert(entity)
    retrieved = wm.get("e_001")
    assert retrieved is not None
    assert retrieved.entity_id == "e_001"
    assert retrieved.get("speed") == 45


def test_world_model_apply_update():
    wm = WorldModel()
    entity = Entity(entity_id="e_002", type="recon_drone")
    wm.upsert(entity)

    update = EntityUpdated(
        entity_id="e_002",
        changes={"status": "engaged", "fuel": 0.65},
        confidence=0.95,
    )
    wm.apply(update)

    updated_entity = wm.get("e_002")
    assert updated_entity.status == "engaged"
    assert updated_entity.get("fuel") == 0.65


def test_world_model_snapshot():
    wm = WorldModel()
    e1 = Entity(entity_id="e1", type="target")
    e2 = Entity(entity_id="e2", type="sensor")
    wm.upsert(e1)
    wm.upsert(e2)

    snapshot = wm.snapshot()
    assert len(snapshot) == 2
    ids = {item["entity_id"] for item in snapshot}
    assert ids == {"e1", "e2"}
