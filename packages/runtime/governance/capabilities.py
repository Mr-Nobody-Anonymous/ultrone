"""Capability Governance: Parses and generates machine-readable maturity reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class CapabilityEntry:
    key: str
    name: str
    maturity_level: str  # L0 to L6
    status: str
    unit_tests: bool
    integration_tests: bool
    benchmarked: bool
    reproducible: bool
    simulation_only: bool
    description: str


class CapabilityRegistry:
    """Loads and validates capability profiles against the L0-L6 maturity scale."""

    LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6"]

    def __init__(self, config_path: Optional[Path | str] = None):
        self.config_path = Path(config_path or Path(__file__).parents[3] / "capabilities.yaml")
        self.entries: Dict[str, CapabilityEntry] = {}
        self.version: str = "unknown"
        if self.config_path.exists():
            self.load()

    def load(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.version = str(data.get("version", "1.0"))
        caps = data.get("capabilities", {})
        for k, v in caps.items():
            self.entries[k] = CapabilityEntry(
                key=k,
                name=v.get("name", k),
                maturity_level=v.get("maturity_level", "L0"),
                status=v.get("status", "planned"),
                unit_tests=bool(v.get("unit_tests", False)),
                integration_tests=bool(v.get("integration_tests", False)),
                benchmarked=bool(v.get("benchmarked", False)),
                reproducible=bool(v.get("reproducible", False)),
                simulation_only=bool(v.get("simulation_only", True)),
                description=v.get("description", ""),
            )

    def generate_markdown_table(self) -> str:
        """Generates GitHub-flavored markdown table representing active maturity matrix."""
        headers = ["Capability", "Level", "Status", "Unit Tests", "Integration", "Benchmarked", "Safety Boundary"]
        lines = [
            f"| {' | '.join(headers)} |",
            f"| {' | '.join(['---'] * len(headers))} |",
        ]
        for cap in self.entries.values():
            unit_str = "Yes" if cap.unit_tests else "No"
            integ_str = "Yes" if cap.integration_tests else "No"
            bench_str = "Yes" if cap.benchmarked else "No"
            safety_str = "Simulation Only" if cap.simulation_only else "Physical Authorized"
            row = [
                f"**{cap.name}**",
                f"`{cap.maturity_level}`",
                cap.status,
                unit_str,
                integ_str,
                bench_str,
                safety_str,
            ]
            lines.append(f"| {' | '.join(row)} |")
        return "\n".join(lines)

    @staticmethod
    def calculate_achievable_level(entry: CapabilityEntry) -> str:
        """Mechanically calculates the highest achievable maturity level supported by evidence."""
        if entry.status == "planned":
            return "L0"
        if not entry.unit_tests:
            return "L1"
        if not entry.integration_tests:
            return "L2"
        if not entry.benchmarked:
            return "L3"
        if not entry.reproducible:
            return "L4"
        return "L5"

    def verify_evidence(self) -> Dict[str, Dict[str, Any]]:
        """Verifies whether declared levels match mechanically achievable levels."""
        report = {}
        for k, entry in self.entries.items():
            achievable = self.calculate_achievable_level(entry)
            declared_num = int(entry.maturity_level[1:]) if entry.maturity_level.startswith("L") else 0
            achievable_num = int(achievable[1:])
            is_valid = declared_num <= achievable_num
            report[k] = {
                "name": entry.name,
                "declared_level": entry.maturity_level,
                "achievable_level": achievable,
                "is_valid": is_valid,
            }
        return report
