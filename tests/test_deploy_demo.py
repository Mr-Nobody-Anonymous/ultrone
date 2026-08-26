# Copyright (c) Ultrone Contributors. All rights reserved.
"""Deployment guard tests for the public HF Space demo.

The public surface must stay exactly that -- a SIMULATION-ONLY research
demo. These tests enforce:

1. an import allowlist: the Space app can only touch stdlib plus the
   simulation packages (sandbox/, data/, comms/, non-tactical agents
   packages); tactical domain modules are unreachable;
2. only non-engaging (civilian/research) platforms are exposed;
3. the demo's core flows work headless (no gradio required).
"""

import ast
import importlib.util
import pathlib
import sys

import pytest

APP_PATH = pathlib.Path(__file__).resolve().parent.parent / \
    "deploy" / "hf_space" / "app.py"

ALLOWED_AGENT_MODULES = (
    "agents.base_agent",
    "agents.capabilities",
    "agents.commands",
    "agents.platform_agent",
    "agents.platform_control",
    "agents.registry",
    "agents.state",
    "agents.telemetry",
    "agents.config",
    "agents.subsystems",
    "agents.civilian",
    "agents.robotics",
    "agents.infrastructure",
)
FORBIDDEN_ROOTS = ("brain", "core", "sim", "simulation", "training_platform",
                   "game_ai", "frontier", "security", "self_improvement")

STDLIB_ALLOWED = {
    "__future__", "ast", "importlib", "json", "os", "pathlib", "sys",
    "typing",
}
ALLOWED_THIRD_PARTY = {"gradio"}


def _load_app():
    spec = importlib.util.spec_from_file_location("ultrone_space_app",
                                                  APP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("ultrone_space_app", module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def app():
    return _load_app()


class TestSimulationOnlyImportScoping:
    def _imports(self):
        tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append(node.module)
        return found

    def test_only_allowed_imports_present(self):
        violations = []
        for name in self._imports():
            root = name.split(".")[0]
            if root in STDLIB_ALLOWED or root in ALLOWED_THIRD_PARTY:
                continue
            if root in ("agents", "sandbox", "data", "comms"):
                if name.startswith(FORBIDDEN_ROOTS):
                    violations.append(name)
                if name.startswith("agents."):
                    if not any(name == prefix or name.startswith(prefix
                                                               + ".")
                               for prefix in ALLOWED_AGENT_MODULES):
                        violations.append(name)
                continue
            violations.append(name)
        assert violations == [], f"forbidden imports: {violations}"

    def test_no_tactical_domain_modules_reachable_from_app(self):
        forbidden = ("agents.air", "agents.land", "agents.sea",
                     "agents.space", "agents.cyber")
        offenders = [name for name in self._imports()
                     if name.startswith(forbidden)]
        assert offenders == []


class TestPublicDemoSurface:
    def test_fleet_overview_covers_all_domains(self, app):
        rows = app.fleet_overview()
        by_id = {row["platform"]: row for row in rows}
        assert {"uav-1", "rail-1", "usv-1", "sat-1",
                "cyber-1"} <= set(by_id)
        domains = {row["domain"] for row in rows}
        assert len(domains) >= 4

    def test_fleet_task_runs_deterministically(self, app):
        task = '{"type": "move", "to": [12.0, 8.0]}'
        first = app.run_fleet_task("uav-1", task)
        second = app.run_fleet_task("uav-1", task)
        assert "error" not in first
        assert first == second                      # deterministic

    def test_fleet_task_input_validation(self, app):
        assert "error" in app.run_fleet_task("ghost-1", "{}")
        assert "error" in app.run_fleet_task("uav-1", "{broken")

    def test_showcase_platforms_are_non_engaging(self, app):
        from agents.base_agent import AgentCapability

        assert len(app.SHOWCASE_PLATFORMS) >= 8
        for kind in app.SHOWCASE_PLATFORMS:
            agent = app.build_showcase_platform(kind)
            assert not agent.can_perform(AgentCapability.ENGAGE), kind
            assert set(agent.capabilities) == {
                AgentCapability.SENSE, AgentCapability.COMMUNICATE}
            assert len(agent.subsystem_names()) >= 4

    def test_unknown_showcase_kind_rejected(self, app):
        with pytest.raises(KeyError):
            app.build_showcase_platform("stealth_bomber")


class TestSubsystemDemoFlows:
    def test_catalog_lists_actions_and_capabilities(self, app):
        catalog = app.subsystem_catalog("ground_robot")
        assert "mobility" in catalog["subsystems"]
        assert {"drive", "set_mode", "stop"} <= set(
            catalog["subsystems"]["mobility"]["actions"])
        assert "task_execution" in catalog["capabilities"]["mission"]

    def test_send_command_happy_path(self, app):
        outcome = app.send_command("ground_robot", "mobility",
                                   "set_mode", '{"mode": "wheels"}')
        assert outcome["success"] is True
        assert "state_after" in outcome
        assert "subsystem_states" in outcome["state_after"]

    def test_send_command_failures_are_clean(self, app):
        bad_action = app.send_command("ground_robot", "mobility",
                                      "teleport", "{}")
        assert bad_action["success"] is False
        assert "unknown action" in bad_action["reason"]

        bad_json = app.send_command("ground_robot", "mobility",
                                    "drive", "{oops")
        assert "error" in bad_json

    def test_estop_blocks_then_releases(self, app):
        aerial = "aerial_robot"
        engaged = app.set_estop(aerial, True)
        probe = engaged["actuation_probe"]
        assert probe["success"] is False
        assert probe["reason"] == "e-stop engaged"

        released = app.set_estop(aerial, False)
        # Engine still off, so refusal reason differs from the gate.
        assert released["actuation_probe"]["reason"] != "e-stop engaged"

    def test_fault_scenarios_surface_in_state(self, app):
        for scenario in app.FAULT_SCENARIOS:
            report = app.run_fault_scenario(scenario)
            assert "error" not in report
            assert report["faults_after"], scenario
            if scenario == "engine_failure":
                # The injected failure must refuse actuation on the path.
                assert report["actuation_probe_refused"] is True

    def test_fault_scenario_input_validation(self, app):
        assert "error" in app.run_fault_scenario("warp_core_breach")
