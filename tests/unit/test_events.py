# Copyright (c) Ultrone Contributors. All rights reserved.
"""Unit tests for the canonical event system."""

import pytest
from packages.core.events import Event, EventType, EventBus


def test_event_serialization():
    evt = Event(
        type=EventType.ENTITY_UPDATED,
        entity_id="test_e1",
        source="radar_scanner",
        changes={"status": "active"},
        confidence=0.96,
        provenance=["radar_station_1"],
    )
    d = evt.to_dict()
    assert d["type"] == "ENTITY_UPDATED"
    assert d["entity_id"] == "test_e1"
    assert d["source"] == "radar_scanner"
    assert d["confidence"] == 0.96
    assert d["changes"]["status"] == "active"


def test_event_bus_publish_subscribe():
    bus = EventBus()
    received_events = []

    def subscriber(event: Event):
        received_events.append(event)

    bus.subscribe(EventType.SENSOR_READING, subscriber)

    evt1 = Event(type=EventType.SENSOR_READING, source="sensor_1")
    evt2 = Event(type=EventType.ENTITY_DESTROYED, source="sim")

    bus.publish(evt1)
    bus.publish(evt2)

    assert len(received_events) == 1
    assert received_events[0].source == "sensor_1"


def test_event_bus_subscribe_all():
    bus = EventBus()
    all_events = []

    bus.subscribe_all(lambda e: all_events.append(e))

    bus.publish(Event(type=EventType.DECISION_MADE, source="planner"))
    bus.publish(Event(type=EventType.ACTION_EXECUTED, source="executor"))

    assert len(all_events) == 2
