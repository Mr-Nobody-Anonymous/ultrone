# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE Research -- public, SIMULATION-ONLY multi-domain demo.

This is the Hugging Face Space entry point. It deliberately exposes a
narrow slice of ULTRONE:

    universal control  ->  structured commands  ->  simulated subsystems
    ->  unified platform state

Every machine here is synthetic (sandbox aircraft, vehicles, vessels,
spacecraft, robots, plants, network nodes). There is no connection to --
and no code path toward -- real machines, weapons, infrastructure, or
external networks. Import scoping is enforced by test
(``tests/test_deploy_demo.py``): this app may only touch the simulation
surface (sandbox/, data/, comms/, and the non-tactical agents packages).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from typing import Any, Dict, List

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from agents.commands import Command                                 # noqa: E402
from agents.platform_control import get_platform_state              # noqa: E402
from agents.subsystems.faults import FaultInjector                  # noqa: E402
from sandbox.ucl import SimulationLab                                # noqa: E402

#: Public demo platforms -- composed from the shared subsystem library.
#: Deliberately civilian/research surfaces only (no tactical modules).
SHOWCASE_PLATFORMS = {
    "delivery_truck": ("agents.civilian.subsystem_platforms",
                       "DeliveryTruckAgent"),
    "ground_robot": ("agents.robotics.ground_robot_agent",
                     "GroundRobotAgent"),
    "aerial_robot": ("agents.robotics.aerial_robot_agent",
                     "AerialRobotAgent"),
    "underwater_robot": ("agents.robotics.underwater_robot_agent",
                         "UnderwaterRobotAgent"),
    "industrial_robot": ("agents.robotics.industrial_robot_agent",
                         "IndustrialRobotAgent"),
    "power_grid": ("agents.infrastructure.power_agent", "PowerGridAgent"),
    "comms_backbone": ("agents.infrastructure.communications_agent",
                       "CommsInfrastructureAgent"),
    "industrial_plant": ("agents.infrastructure.industrial_agent",
                         "IndustrialPlantAgent"),
    "transit_segment": ("agents.infrastructure.transportation_agent",
                        "TransitNetworkAgent"),
}

#: Deterministic demo tasks for the UCL fleet tab (sandbox machines).
FLEET_TASK_PRESETS: Dict[str, Dict[str, Any]] = {
    "uav-1": {"type": "move", "to": [12.0, 8.0]},
    "ugv-1": {"type": "move", "to": [6.0, 6.0]},
    "rail-1": {"type": "move", "to": [10.0, 0.0]},
    "usv-1": {"type": "observe"},
    "sat-1": {"type": "observe"},
    "cyber-1": {"type": "observe"},
}


def _load_class(module_name: str, class_name: str):
    return getattr(importlib.import_module(module_name), class_name)


def _lab() -> SimulationLab:
    """Fresh deterministic fleet (cheap to construct, fully sandboxed)."""
    return SimulationLab(seed=7)


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of results/state into JSON-safe shapes."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return repr(value)


def _result_dict(result) -> Dict[str, Any]:
    return {"success": bool(result.success),
            "reason": result.reason,
            "value": _jsonable(getattr(result, "value", None))}


# --------------------------------------------------------------------- #
# Tab 1 -- UCL fleet                                                     #
# --------------------------------------------------------------------- #
def fleet_overview() -> List[Dict[str, Any]]:
    """Every sandboxed platform behind the universal control layer."""
    lab = _lab()
    rows = []
    for platform_id in sorted(lab.controllers):
        controller = lab.controllers[platform_id]
        from sandbox.ucl import Capability

        rows.append({
            "platform": platform_id,
            "domain": str(controller.domain),
            "kind": controller.machine.KIND,
            "capabilities": sorted(
                cap.value for cap in Capability
                if controller.supports(cap)),
        })
    return rows


def run_fleet_task(platform_id: str, task_json: str) -> Dict[str, Any]:
    """Execute one deterministic task through the single command path."""
    lab = _lab()
    if platform_id not in lab.controllers:
        return {"error": f"unknown platform '{platform_id}'"}
    try:
        task = json.loads(task_json) if task_json.strip() else {}
    except json.JSONDecodeError as exc:
        return {"error": f"invalid task JSON: {exc}"}
    controller = lab.controllers[platform_id]
    result = controller.execute_task(task)
    return {"task": task,
            "result": _jsonable(result),
            "state_after": _jsonable(controller.get_state())}


# --------------------------------------------------------------------- #
# Tab 2 -- subsystem-composed platforms                                  #
# --------------------------------------------------------------------- #
def build_showcase_platform(kind: str):
    """Instantiate one public demo platform (fresh + deterministic)."""
    if kind not in SHOWCASE_PLATFORMS:
        raise KeyError(f"unknown showcase platform '{kind}'")
    module_name, class_name = SHOWCASE_PLATFORMS[kind]
    return _load_class(module_name, class_name)(unit_id=f"demo-{kind}")


def subsystem_catalog(kind: str) -> Dict[str, Any]:
    """Everything higher-level AI would ask before acting."""
    agent = build_showcase_platform(kind)
    catalog: Dict[str, Any] = {
        "platform": kind,
        "capabilities": agent.available_capabilities(),
        "subsystems": {},
    }
    for name in agent.subsystem_names():
        subsystem = agent.get_subsystem(name)
        catalog["subsystems"][name] = {
            "actions": subsystem.actions(),
            "status": _jsonable(subsystem.status()),
        }
    return catalog


def send_command(kind: str, subsystem: str, action: str,
                 parameters_json: str = "{}") -> Dict[str, Any]:
    """Issue ONE structured command through the ONE actuation path."""
    try:
        agent = build_showcase_platform(kind)
    except KeyError as exc:
        return {"error": str(exc)}
    try:
        parameters = json.loads(parameters_json) \
            if parameters_json.strip() else {}
    except json.JSONDecodeError as exc:
        return {"error": f"invalid parameter JSON: {exc}"}
    result = agent.execute(Command(subsystem=subsystem, action=action,
                                   parameters=parameters))
    return {"command": {"subsystem": subsystem, "action": action,
                        "parameters": parameters},
            "success": bool(result.success),
            "value": _jsonable(result.value),
            "reason": result.reason,
            "state_after": get_platform_state(agent)}


def set_estop(kind: str, engage: bool) -> Dict[str, Any]:
    """Toggle the platform interlock ON the single command path."""
    outcome: Dict[str, Any] = {}
    agent = build_showcase_platform(kind)
    if "safety" not in agent.subsystem_names():
        from agents.subsystems.safety import SafetyInterlockSubsystem

        agent.register_subsystem(SafetyInterlockSubsystem())
        outcome["note"] = "interlock composed onto platform for demo"
    verb = "engage_estop" if engage else "release_estop"
    outcome["interlock"] = _result_dict(agent.execute(Command("safety",
                                                              verb)))
    probe_subsystem = ("propulsion" if "propulsion"
                       in agent.subsystem_names() else "mobility")
    probe_action = ("set_throttle" if probe_subsystem == "propulsion"
                    else "drive")
    probe_param = ({"value": 0.5} if probe_subsystem == "propulsion"
                   else {"speed": 0.5})
    outcome["actuation_probe"] = _result_dict(
        agent.execute(Command(probe_subsystem, probe_action,
                              probe_param)))
    outcome["state_after"] = get_platform_state(agent)
    return outcome


# --------------------------------------------------------------------- #
# Tab 3 -- deterministic fault injection                                 #
# --------------------------------------------------------------------- #
FAULT_SCENARIOS = ("engine_failure", "sensor_blind",
                   "communication_blackout", "power_depletion",
                   "navigation_failure", "overheat", "degrade")

#: Each scenario needs a victim carrying the targeted subsystem.
SCENARIO_VICTIMS = {
    "engine_failure": "aerial_robot",       # carries propulsion
    "overheat": "industrial_plant",         # carries thermal
}


def run_fault_scenario(scenario: str) -> Dict[str, Any]:
    """Inject a deterministic fault; show it surface in unified state."""
    if scenario not in FAULT_SCENARIOS:
        return {"error": f"unknown scenario '{scenario}'"}
    agent = build_showcase_platform(
        SCENARIO_VICTIMS.get(scenario, "ground_robot"))
    injector = FaultInjector(agent.bus)
    before = get_platform_state(agent)
    getattr(injector, scenario)()
    for tick in range(3):
        agent.tick_platform(tick)
    after = get_platform_state(agent)
    probe = agent.execute(Command("mobility", "drive", {"speed": 1.0}))
    return {"scenario": scenario,
            "faults_after": after["active_faults"],
            "health_after": after["health"],
            "actuation_probe_refused": not probe.success}


# --------------------------------------------------------------------- #
# Gradio UI (guarded: core logic above works headless without gradio)    #
# --------------------------------------------------------------------- #
try:
    import gradio as gr
except ImportError:                                   # pragma: no cover
    gr = None

SIMULATION_NOTICE = (
    "## ULTRONE Research \u2014 **simulation only**\n"
    "Every aircraft, vehicle, vessel, spacecraft, robot, plant, and "
    "network node in this demo is a deterministic sandbox simulation. "
    "**No connection to real machines, weapons, infrastructure, or "
    "external systems exists or is possible from this app.**"
)


def build_demo():
    """Assemble the Gradio UI (requires ``gradio`` to be installed)."""
    if gr is None:
        raise RuntimeError(
            "gradio is not installed -- the pure-logic demo API still "
            "works headless; install requirements.txt for the UI")
    platform_choice = gr.Dropdown(sorted(SHOWCASE_PLATFORMS),
                                  value="ground_robot", label="Platform")

    with gr.Blocks(title="ULTRONE Research") as demo:
        gr.Markdown(SIMULATION_NOTICE)

        with gr.Tab("Universal fleet"):
            gr.Markdown(
                "One control interface over every simulated machine, in "
                "every domain. Tasks run deterministically through the "
                "UCL.")
            fleet_btn = gr.Button("List platforms")
            fleet_table = gr.JSON(label="Platforms")
            fleet_btn.click(fleet_overview, None, fleet_table)
            with gr.Row():
                fleet_id = gr.Dropdown(
                    sorted(FLEET_TASK_PRESETS), value="uav-1",
                    label="Platform")
                fleet_task = gr.Textbox(label="Task (JSON)",
                                        lines=2)
                fleet_run = gr.Button("Execute task")
            fleet_out = gr.JSON(label="Result + state after")
            fleet_run.click(run_fleet_task,
                            [fleet_id, fleet_task], fleet_out)

        with gr.Tab("Subsystem platforms"):
            gr.Markdown(
                "Platforms composed from subsystems and driven by "
                "structured commands: `Command(subsystem, action, "
                "parameters)` -> CommandBus -> unified state.")
            with gr.Row():
                kind = platform_choice
                catalog_btn = gr.Button("Inspect")
            catalog = gr.JSON(label="Subsystems / actions / capabilities")
            catalog_btn.click(subsystem_catalog, kind, catalog)
            with gr.Row():
                sub = gr.Textbox(label="Subsystem", value="propulsion")
                act = gr.Textbox(label="Action", value="start_engine")
                params = gr.Textbox(label="Parameters (JSON)",
                                    value="{}")
                send = gr.Button("Send command")
            command_out = gr.JSON(label="CommandResult + state after")
            send.click(send_command, [kind, sub, act, params],
                       command_out)
            with gr.Row():
                estop_on = gr.Button("Engage e-stop")
                estop_off = gr.Button("Release e-stop")
            estop_out = gr.JSON(label="Interlock + probe result")
            estop_on.click(lambda k: set_estop(k, True), kind, estop_out)
            estop_off.click(lambda k: set_estop(k, False), kind,
                            estop_out)

        with gr.Tab("Fault injection"):
            gr.Markdown(
                "Research-grade simulation must test failures. Each "
                "scenario injects a deterministic fault and shows it "
                "surface in the unified state.")
            scenario = gr.Dropdown(list(FAULT_SCENARIOS),
                                   value="engine_failure",
                                   label="Scenario")
            fault_btn = gr.Button("Inject")
            fault_out = gr.JSON(label="Fault report")
            fault_btn.click(run_fault_scenario, scenario, fault_out)

        gr.Markdown(
            "*Deterministic everywhere: identical inputs reproduce "
            "identical runs, so every number you see is reproducible.*")
    return demo


if __name__ == "__main__":
    build_demo().launch(server_name="0.0.0.0",
                        server_port=int(os.environ.get("PORT", 7860)))