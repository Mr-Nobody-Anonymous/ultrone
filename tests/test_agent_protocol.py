# Copyright (c) Ultrone Contributors. All rights reserved.
from packages.agents.protocol import (
    AgentMessage,
    ProtocolMessageType,
    ProtocolRouter,
)


def test_agent_message_serialization():
    msg = AgentMessage(
        sender="air-commander-01",
        recipient="uav-strike-04",
        message_type=ProtocolMessageType.REQUEST,
        payload={"target_coordinates": [32.1, 44.5], "altitude_m": 5000},
        capabilities_required=["reconnaissance", "laser_designation"],
        priority=2,
    )

    d = msg.to_dict()
    assert d["sender"] == "air-commander-01"
    assert d["recipient"] == "uav-strike-04"
    assert d["message_type"] == "REQUEST"
    assert d["payload"]["altitude_m"] == 5000

    reconstructed = AgentMessage.from_dict(d)
    assert reconstructed.sender == msg.sender
    assert reconstructed.message_type == ProtocolMessageType.REQUEST
    assert reconstructed.capabilities_required == msg.capabilities_required


def test_protocol_routing_and_inbox():
    router = ProtocolRouter()
    router.register_agent("agent-alpha")
    router.register_agent("agent-beta")

    msg = AgentMessage(
        sender="agent-alpha",
        recipient="agent-beta",
        payload={"status": "all systems nominal"},
    )
    router.send(msg)

    inbox = router.poll_inbox("agent-beta")
    assert len(inbox) == 1
    assert inbox[0].payload["status"] == "all systems nominal"

    # Subsequent poll is empty
    assert len(router.poll_inbox("agent-beta")) == 0
