# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.harness.checkpoint import CheckpointStore
from packages.agents.harness.three_agent import (
    DAGNode,
    F2T2EAPlanner,
    MissionDirective,
    ROEGrader,
    SwarmExecutionWorker,
    TaskDAG,
    ThreeAgentHarness,
)
from packages.agents.mcp import ActuatorMcpServer, McpClient, McpToolBridge, SensorMcpServer
from packages.agents.tools import ToolRuntime


def test_task_dag_dependency_resolution():
    dag = TaskDAG(name="test-dag")
    dag.add_node(DAGNode(node_id="n1", phase="FIND", description="Find", tool_name="tool_a", prerequisites=[]))
    dag.add_node(DAGNode(node_id="n2", phase="FIX", description="Fix", tool_name="tool_b", prerequisites=["n1"]))

    ready1 = dag.get_ready_nodes()
    assert len(ready1) == 1
    assert ready1[0].node_id == "n1"

    # Complete n1
    dag.mark_completed("n1", {"output": 123})
    ready2 = dag.get_ready_nodes()
    assert len(ready2) == 1
    assert ready2[0].node_id == "n2"


def test_task_dag_cycle_detection():
    dag = TaskDAG(name="cycle-dag")
    dag.add_node(DAGNode(node_id="a", phase="P1", description="A", tool_name="t", prerequisites=["b"]))
    with pytest.raises(ValueError, match="Cycle detected"):
        dag.add_node(DAGNode(node_id="b", phase="P2", description="B", tool_name="t", prerequisites=["a"]))


def test_end_to_end_three_agent_f2t2ea_mission(tmp_path):
    # 1. Setup MCP servers (Sensors + Actuators) and unified ToolRuntime
    sensor_server = SensorMcpServer()
    actuator_server = ActuatorMcpServer()

    client_sensor = McpClient(server=sensor_server)
    client_sensor.connect()

    client_actuator = McpClient(server=actuator_server)
    client_actuator.connect()

    bridge_sensor = McpToolBridge(client=client_sensor)
    bridge_sensor.sync_tools()

    bridge_actuator = McpToolBridge(client=client_actuator, registry=bridge_sensor.registry)
    bridge_actuator.sync_tools()

    tool_runtime = ToolRuntime(registry=bridge_sensor.registry)

    # 2. Setup Three-Agent Harness Components
    planner = F2T2EAPlanner()
    worker = SwarmExecutionWorker(tool_runtime=tool_runtime)
    grader = ROEGrader(min_pid_confidence=0.80)
    ckpt_store = CheckpointStore(storage_dir=str(tmp_path / "checkpoints"))

    harness = ThreeAgentHarness(
        planner=planner,
        worker=worker,
        grader=grader,
        checkpoint_store=ckpt_store,
    )

    # 3. Define Mission Directive
    directive = MissionDirective(
        mission_id="OPERATION-APEX-GUARDIAN",
        target_description="High-value mobile hostile surface radar",
        area_center_lat=34.0522,
        area_center_lon=-118.2437,
        rules_of_engagement=["Proportional kinetic response", "Zero collateral damage"],
        no_strike_entities=[],
        min_pid_confidence=0.85,
        designated_asset_id="UAV-ALFA-1",
    )

    # 4. Execute Full F2T2EA Mission
    report = harness.execute_mission(directive)

    assert report.success
    assert report.nodes_completed == 6
    assert report.nodes_failed == 0
    assert report.roe_clearance_issued is True
    assert len(report.checkpoints) == 6

    # Verify persistent checkpoints on disk
    saved_checkpoints = ckpt_store.list_checkpoints(f"{directive.mission_id}-stage-1-find")
    assert len(saved_checkpoints) >= 1

