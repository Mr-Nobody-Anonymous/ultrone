# Copyright (c) Ultrone Contributors. All rights reserved.
"""Report Generator - auto-generates military reports in standard format."""

import logging
import random
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger("Ultrone.Generative.ReportGenerator")


@dataclass
class MilitaryReport:
    """Base military report structure."""
    report_id: str
    report_type: str
    timestamp: str
    content: str
    urgency: str
    
    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "type": self.report_type,
            "timestamp": self.timestamp,
            "urgency": self.urgency,
            "length": len(self.content),
        }


class ReportGenerator:
    """
    Auto-generates military reports: OPLANs, FRAGOs, SITREPs, AARs.
    """
    
    def __init__(self):
        self.reports: List[MilitaryReport] = []
        self._report_count = 0
    
    def generate_aar(
        self,
        battle_stats: Dict,
        evolution_stats: Dict,
        tactics_used: List[str],
    ) -> MilitaryReport:
        """Generate After Action Report."""
        self._report_count += 1
        
        lines = [
            "=" * 60,
            "AFTER ACTION REPORT (AAR)",
            "=" * 60,
            f"Report ID: AAR-{self._report_count:04d}",
            f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "--- EXECUTIVE SUMMARY ---",
            f"Total Engagements: {battle_stats.get('total_engagements', 0)}",
            f"Success Rate: {battle_stats.get('success_rate', 0):.1%}",
            f"Average Response Time: {battle_stats.get('avg_response_ms', 0):.0f}ms",
            "",
            "--- GENOME EVOLUTION ---",
            f"Evolution Cycles: {evolution_stats.get('evolution_count', 0)}",
            f"Final Generation: {evolution_stats.get('generation', 0)}",
            f"Best Fitness: {evolution_stats.get('best_fitness', 0):.3f}",
            "",
            "--- FAILED TACTICS IDENTIFIED ---",
        ]
        
        # Add failure analysis
        failure_patterns = evolution_stats.get("failure_analysis", {})
        if failure_patterns.get("common_failures"):
            for failure, count in failure_patterns.get("common_failures", {}).items():
                lines.append(f"  • {failure}: {count} occurrences")
        else:
            lines.append("  • No significant failures recorded")
        
        lines.extend([
            "",
            "--- RECOMMENDATIONS ---",
            "1. Continue monitoring cross-domain correlation",
            "2. Refine kill chain timing parameters",
            "3. Update threat matrix weights based on lessons learned",
            "=" * 60,
        ])
        
        report = MilitaryReport(
            report_id=f"AAR-{self._report_count:04d}",
            report_type="AAR",
            timestamp=datetime.utcnow().isoformat(),
            content="\n".join(lines),
            urgency="ROUTINE",
        )
        
        self.reports.append(report)
        return report
    
    def generate_sitrep(
        self,
        world_state,
        tactical_stats: Dict,
    ) -> MilitaryReport:
        """Generate Situation Report."""
        self._report_count += 1
        
        lines = [
            f"SITREP-{self._report_count:04d}",
            f"{datetime.utcnow().strftime('%H%MZ')}, ",
            f"Units Active: {len(world_state.units) if world_state else 0}, ",
            f"Contacts: {len(world_state.contacts) if world_state else 0}, ",
            f"Threats: {tactical_stats.get('threats', 0)}",
        ]
        
        return MilitaryReport(
            report_id=f"SITREP-{self._report_count:04d}",
            report_type="SITREP",
            timestamp=datetime.utcnow().isoformat(),
            content=" ".join(lines),
            urgency="IMMEDIATE",
        )
    
    def generate_oplan(
        self,
        objective: str,
        forces: List[str],
        timeline: int,
    ) -> MilitaryReport:
        """Generate Operations Plan."""
        self._report_count += 1
        
        lines = [
            "OPERATIONS ORDER (OPLAN)",
            f"Reference: OPLAN-{self._report_count:04d}",
            "",
            "1. MISSION",
            f"   {objective}",
            "",
            "2. EXECUTION",
            f"   Forces: {', '.join(forces[:5])}",
            f"   Timeline: {timeline} ticks",
            "",
            "3. SERVICE SUPPORT",
            "   Full autonomy mode - no logistics required",
        ]
        
        return MilitaryReport(
            report_id=f"OPLAN-{self._report_count:04d}",
            report_type="OPLAN",
            timestamp=datetime.utcnow().isoformat(),
            content="\n".join(lines),
            urgency="PRIORITY",
        )
    
    def get_stats(self) -> dict:
        return {
            "reports_generated": self._report_count,
            "report_types": {t: sum(1 for r in self.reports if r.report_type == t) for t in ["AAR", "SITREP", "OPLAN"]},
        }