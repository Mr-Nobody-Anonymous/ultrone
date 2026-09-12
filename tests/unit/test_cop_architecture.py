# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for COP architecture: Ontology, Layers, and Investigations."""

import pytest
from packages.core.ontology import OntologyObject, OntologyLink, OntologyAction
from packages.geospatial.layers import LayerRegistry, LayerCategory, LayerType
from packages.investigation import Case, EvidenceItem


def test_ontology_object_and_links():
    """Verify ontology object creation and link construction."""
    obj = OntologyObject(object_id="asset_100", object_type="AirVehicle")
    obj.add_link("radar_200", "observed_by", confidence=0.95)
    assert len(obj.links) == 1
    assert obj.links[0].target_id == "radar_200"
    assert obj.links[0].relation_type == "observed_by"
    assert obj.links[0].confidence == 0.95


def test_ontology_action_execution():
    """Verify ontology action execution."""
    def sample_handler(p):
        return {"result": f"Tracked {p.get('target')}"}

    action = OntologyAction(
        action_id="track_target",
        name="Track Target",
        description="Initiate active tracking vector",
        target_object_types=["AirVehicle"],
        handler=sample_handler,
    )
    res = action.execute({"target": "asset_100"})
    assert res["result"] == "Tracked asset_100"


def test_geospatial_layer_registry():
    """Verify layer categorization and visibility toggling."""
    reg = LayerRegistry()
    layers = reg.list_all()
    assert len(layers) >= 10

    # Test toggling visibility
    radar_layer = reg.get_layer("env-radar-cones")
    assert radar_layer is not None
    assert radar_layer.category == LayerCategory.ENVIRONMENT

    reg.set_visibility("env-radar-cones", False)
    assert reg.get_layer("env-radar-cones").enabled is False


def test_investigation_case_dossier():
    """Verify investigation case and evidence reporting."""
    case = Case(case_id="INV-999", title="Sector Incursion")
    case.pin_entity("entity_001")
    case.add_evidence(EvidenceItem(
        title="Radar Spike",
        description="Bearing 045 degrees sudden altitude change",
        source_ref="entity_001",
    ))
    dossier = case.generate_dossier()
    assert "INVESTIGATION DOSSIER: INV-999" in dossier
    assert "entity_001" in dossier
    assert "Radar Spike" in dossier
