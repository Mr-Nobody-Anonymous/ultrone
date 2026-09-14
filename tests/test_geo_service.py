# Copyright (c) Ultrone Contributors. All rights reserved.
"""Tests for the ULTRONE geo service + API (Global Eye Phase 1)."""

import pytest
from fastapi.testclient import TestClient

from packages.geospatial.service import (
    GeoService,
    geo_to_grid,
    grid_to_geo,
    kind_for,
    parse_position,
)


class TestGeoMapping:
    def test_grid_geo_roundtrip(self):
        lat, lon = grid_to_geo(20, 50)
        x, y = geo_to_grid(lat, lon)
        assert abs(x - 20) < 1e-6
        assert abs(y - 50) < 1e-6

    def test_grid_geo_clamped(self):
        x, y = geo_to_grid(91.0, 181.0)
        assert 0.0 <= x <= 100.0
        assert 0.0 <= y <= 100.0


class TestParsing:
    def test_kind_for(self):
        assert kind_for("air_asset") == "air"
        assert kind_for("UAV") == "air"
        assert kind_for("vessel") == "sea"
        assert kind_for("satellite") == "space"
        assert kind_for("supply") == "facility"
        assert kind_for("armor") == "land"
        assert kind_for("something-weird") == "unknown"

    def test_parse_position_shapes(self):
        assert parse_position({"lat": 1.0, "lon": 2.0}) == (1.0, 2.0, 0.0)
        assert parse_position({"latitude": 1.0, "longitude": 2.0}) == (1.0, 2.0, 0.0)
        assert parse_position([2.0, 1.0]) == (1.0, 2.0, 0.0)
        assert parse_position([2.0, 1.0, 500.0]) == (1.0, 2.0, 500.0)
        assert parse_position({"x": 1}) is None
        assert parse_position(None) is None
        assert parse_position("nairobi") is None


def _fresh_service(seed_demo=True):
    from world_model import WorldModel

    return GeoService(world_model=WorldModel(), seed_demo=seed_demo)


class TestGeoService:
    def test_empty_world_without_seed(self):
        svc = _fresh_service(seed_demo=False)
        snap = svc.snapshot()
        assert snap["count"] == 0
        assert snap["entities"] == []

    def test_seed_demo_populates(self):
        svc = _fresh_service(seed_demo=True)
        snap = svc.snapshot()
        assert snap["count"] > 0
        kinds = {e["kind"] for e in snap["entities"]}
        assert {"air", "sea"} <= kinds
        assert all(-90 <= e["lat"] <= 90 for e in snap["entities"])
        assert all(-180 <= e["lon"] <= 180 for e in snap["entities"])

    def test_world_model_entity_flows_through(self):
        from world_model import Entity, WorldModel

        wm = WorldModel()
        e = Entity(entity_id="wm-1", type="air_asset")
        e.set("position", {"lat": 8.5, "lon": 39.2})
        e.set("team", "blue")
        wm.upsert(e)
        svc = GeoService(world_model=wm, seed_demo=False)
        snap = svc.snapshot()
        assert snap["count"] == 1
        ent = snap["entities"][0]
        assert ent["id"] == "wm-1"
        assert ent["kind"] == "air"
        assert ent["team"] == "blue"
        assert ent["source"] == "world_model"

    def test_sim_entities_mapped(self):
        svc = _fresh_service(seed_demo=False)
        svc.attach_sim()
        snap = svc.snapshot()
        ids = {e["id"] for e in snap["entities"]}
        assert "sim-red-force" in ids
        assert any(i.startswith("sim-blue-") for i in ids)
        assert all(e["source"] == "simulation" for e in snap["entities"])

    def test_tracks_accumulate(self):
        svc = _fresh_service(seed_demo=True)
        svc.snapshot()
        snap = svc.snapshot()
        assert snap["tracks"]
        for pts in snap["tracks"].values():
            assert len(pts) >= 2

    def test_tick_moves_demo_entities(self):
        svc = _fresh_service(seed_demo=True)
        svc.snapshot()
        before = {e["id"]: (e["lat"], e["lon"]) for e in svc.snapshot()["entities"]}
        import time

        svc.tick(now=time.time() + 60)
        after = {e["id"]: (e["lat"], e["lon"]) for e in svc.snapshot()["entities"]}
        moved = [eid for eid in before if before[eid] != after.get(eid)]
        assert moved, "seeded movers should drift kinematically"


class TestGeoApi:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("ULTRONE_GEO_SEED", "0")
        import packages.geospatial.api as geo_api

        geo_api._service = None
        from world_model import WorldModel

        from packages.geospatial.service import GeoService

        wm = WorldModel()
        geo_api._service = GeoService(world_model=wm, seed_demo=True)
        return TestClient(geo_api.create_geo_app())

    def test_health(self, client):
        r = client.get("/api/ultrone/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_entities(self, client):
        r = client.get("/api/ultrone/entities")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] > 0
        assert "theater" in body

    def test_tracks(self, client):
        r = client.get("/api/ultrone/tracks?history=5")
        assert r.status_code == 200
        assert r.json()["tracks"]

    def test_sim_lifecycle(self, client):
        assert client.post("/api/ultrone/sim/reset").status_code == 200
        r = client.post("/api/ultrone/sim/step", json={"steps": 2})
        assert r.status_code == 200
        assert r.json()["status"] == "stepped"

    def test_stream(self, client):
        with client.websocket_connect("/api/ultrone/stream?hz=5") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["count"] > 0
