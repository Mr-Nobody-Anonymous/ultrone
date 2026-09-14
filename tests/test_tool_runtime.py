# Copyright (c) Ultrone Contributors. All rights reserved.
import pytest

from packages.agents.tools import (
    PermissionDeniedError,
    RiskLevel,
    ToolDefinition,
    ToolParameter,
    ToolPermissionChecker,
    ToolRegistry,
    ToolRuntime,
)


def test_tool_runtime_execution_success():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="add_numbers",
            description="Adds two integers",
            parameters=[
                ToolParameter(name="a", type="int", required=True),
                ToolParameter(name="b", type="int", required=True),
            ],
            risk_level=RiskLevel.LOW,
        ),
        lambda a, b: a + b,
    )

    runtime = ToolRuntime(registry=registry)
    res = runtime.execute("add_numbers", {"a": 10, "b": 25}, caller_agent_id="test-agent")

    assert res.success
    assert res.output == 35
    assert len(runtime.audit_logger.get_entries()) == 1


def test_tool_runtime_missing_param_validation():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="greet",
            description="Greets a person",
            parameters=[ToolParameter(name="name", required=True)],
        ),
        lambda name: f"Hello {name}",
    )

    runtime = ToolRuntime(registry=registry)
    res = runtime.execute("greet", {})  # Missing name parameter

    assert not res.success
    assert "Missing required parameter" in res.error


def test_tool_runtime_permission_and_human_approval():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="format_disk",
            description="Destructive drive wipe",
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
        ),
        lambda: "Formatted",
    )

    # Approver rejects
    rejecting_checker = ToolPermissionChecker(
        max_allowed_risk=RiskLevel.CRITICAL,
        human_approver=lambda tool, args: False,
    )
    runtime = ToolRuntime(registry=registry, permission_checker=rejecting_checker)

    res = runtime.execute("format_disk", {})
    assert not res.success
    assert "rejected" in res.error.lower()

    # Approver approves
    approving_checker = ToolPermissionChecker(
        max_allowed_risk=RiskLevel.CRITICAL,
        human_approver=lambda tool, args: True,
    )
    runtime_approved = ToolRuntime(registry=registry, permission_checker=approving_checker)
    res_ok = runtime_approved.execute("format_disk", {})
    assert res_ok.success
    assert res_ok.output == "Formatted"
