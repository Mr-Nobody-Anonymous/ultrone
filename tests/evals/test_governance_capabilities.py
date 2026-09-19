"""Tests for Capabilities Governance and L0-L6 maturity scale."""

from pathlib import Path
import pytest
from packages.runtime.governance.capabilities import CapabilityRegistry


def test_capability_registry_load():
    reg = CapabilityRegistry()
    assert len(reg.entries) >= 10

    # Test key capabilities exist and have valid maturity levels
    assert "battlefield_simulation" in reg.entries
    sim = reg.entries["battlefield_simulation"]
    assert sim.maturity_level == "L3"
    assert sim.simulation_only is True

    # Test robotics is constrained to L1 simulation scaffold
    robotics = reg.entries["robotics_actuation"]
    assert robotics.maturity_level == "L1"
    assert robotics.simulation_only is True

    # Test UDIS and MCP are L3
    assert reg.entries["udis_hardware_protocol"].maturity_level == "L3"
    assert reg.entries["mcp_2026_07_28"].maturity_level == "L3"


def test_capability_registry_generate_markdown():
    reg = CapabilityRegistry()
    table_md = reg.generate_markdown_table()
    assert "| Capability | Level | Status |" in table_md
    assert "Digital Battlefield Simulator" in table_md
    assert "ULTRONE Device Interface Standard" in table_md
    assert "Simulation Only" in table_md
