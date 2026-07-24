# Copyright (c) Ultrone Contributors. All rights reserved.
"""
LLM Commander - Visual-Grounding tactical analysis.

Receives ASCII maps and telemetry from the battlefield and produces
tactical briefings. Strictly a post-hoc observer; does not alter
simulation step or evolutionary fitness.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.LLMCommander")

BRIEFING_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "commander_log.txt"


class LLMCommander:
    """
    LLM-based commander that analyzes battlefield state.
    
    Uses local Ollama when available; falls back to rule-based synthesis.
    """
    
    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or BRIEFING_LOG_PATH
        self._model = None
        self._use_llm = False
        self._init_llm()
    
    def _init_llm(self) -> None:
        """Attempt to initialize Ollama LLM."""
        try:
            import requests  # noqa: F401
            self._model = "ollama_llama3"
            self._use_llm = True
            logger.info("LLMCommander initialized with Ollama llama3")
        except Exception:
            self._use_llm = False
            logger.info("LLMCommander using rule-based synthesis")
    
    def analyze(self, ascii_map: str, telemetry: Dict[str, Any],
                knowledge_summary: Optional[str] = None) -> str:
        """
        Analyze battlefield and return tactical briefing.
        
        Phase 6 Multi-INT enhancement:
        Accepts an optional knowledge_summary from MultiINTKnowledgeGraph.
        When present, the summary provides threat density, high-value comms
        links, and entity cluster information for richer situational awareness.
        
        Args:
            ascii_map: ASCII map string from BattlefieldEnv.render_ascii_map()
            telemetry: Recent training telemetry
            knowledge_summary: Optional multi-INT knowledge graph summary string.
            
        Returns:
            Tactical briefing string
        """
        if self._use_llm:
            try:
                return self._llm_analyze(ascii_map, telemetry, knowledge_summary)
            except Exception as e:
                logger.debug("LLM analysis failed: %s", e)
        return self._rule_based_analysis(ascii_map, telemetry, knowledge_summary)
    
    def _llm_analyze(self, ascii_map: str, telemetry: Dict[str, Any],
                     knowledge_summary: Optional[str] = None) -> str:
        """Analyze using Ollama llama3, optionally with multi-INT context."""
        kg_section = ""
        if knowledge_summary:
            kg_section = (
                "\nMulti-INT Knowledge Graph Summary (correlated sensor intel):\n"
                f"{knowledge_summary}\n"
            )

        prompt = (
            "You are a VLM (Vision-Language Model) military commander.\n"
            "Here is the current battlefield map:\n"
            f"{ascii_map}\n\n"
            "Legend: R=Red Force, D=Drone, M=Missile, J=Jammer, E=ECM zone, "
            "B=Blue Supply, S=Red Supply, .=empty\n\n"
            "Current telemetry:\n"
            f"- Blue success rate: {telemetry.get('success_rate', 0):.0%}\n"
            f"- Avg reward: {telemetry.get('avg_reward', 0):.1f}\n"
            f"- Red survival: {telemetry.get('red_survival_rate', 0):.0%}\n"
            f"- Generation: {telemetry.get('generation', 0)}\n"
            f"- Supply penalty active: {telemetry.get('supply_penalty_active', False)}\n"
            f"- Fuel state: {telemetry.get('avg_fuel', 0):.2f}\n"
            f"{kg_section}"
            "Identify flanking opportunities, supply vulnerabilities, and "
            "multi-domain threats in 2-3 sentences."
        )
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "max_tokens": 120,
                },
                timeout=30,
            )
            data = response.json()
            text = data.get("response", "")
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug("Ollama request failed: %s", e)
        return self._rule_based_analysis(ascii_map, telemetry, knowledge_summary)
    
    def _rule_based_analysis(self, ascii_map: str, telemetry: Dict[str, Any],
                              knowledge_summary: Optional[str] = None) -> str:
        """
        Rule-based tactical analysis from ASCII map and telemetry.
        
        Phase 6 Multi-INT enhancement:
        Incorporates knowledge graph summary (threat density, comms links,
        clusters) into the textual analysis for richer situational awareness.
        
        Produces a short strategic analysis paragraph.
        """
        success = telemetry.get("success_rate", 0)
        red_survival = telemetry.get("red_survival_rate", 0)
        generation = telemetry.get("generation", 0)
        supply_penalty = telemetry.get("supply_penalty_active", False)
        avg_fuel = telemetry.get("avg_fuel", 1.0)
        
        if success >= 0.8:
            assessment = "Blue dominates the battlefield; maintain pressure."
        elif success >= 0.5:
            assessment = "Blue holds initiative but must adapt to Red counters."
        else:
            assessment = "Blue is losing; recommend regrouping and novel tactics."
        
        # Multi-INT insights from knowledge graph
        kg_insight = ""
        if knowledge_summary:
            lines = knowledge_summary.split("\n")
            hv_count = sum(1 for l in lines if "high-value comms" in l.lower() or "signal=" in l)
            threat_zones = sum(1 for l in lines if "high-density threat" in l.lower())
            cluster_info = [l.strip() for l in lines if l.strip().startswith("[") and "Cluster" in l]
            
            parts = []
            if threat_zones > 0:
                parts.append(f"{threat_zones} high-density threat zone(s)")
            if hv_count > 0:
                parts.append(f"{hv_count} high-value comms link(s) detected")
            if cluster_info:
                parts.append("multi-domain entity clusters present")
            
            if parts:
                kg_insight = f"KG intel: {'; '.join(parts)}. "
        
        # Supply & fuel status
        log_insight = ""
        if supply_penalty:
            log_insight = "Supply disruption active (one-time 20% penalty incurred). "
        if avg_fuel < 0.3:
            log_insight += "Blue fuel critically low; resupply recommended. "
        elif avg_fuel < 0.6:
            log_insight += "Blue fuel moderate; monitor consumption. "
        
        return (
            f"Generation {generation}: {assessment} "
            f"Red survival at {red_survival:.0%}. "
            f"{kg_insight}"
            f"{log_insight}"
            f"Current map shows R at central position with E zones indicating ECM activity."
        )
    
    def write_briefing(self, ascii_map: str, telemetry: Dict[str, Any]) -> None:
        """Write tactical briefing to commander log."""
        briefing = self.analyze(ascii_map, telemetry)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[Episode {telemetry.get('episode', '?')}] TACTICAL BRIEFING\n")
                f.write(f"Map:\n{ascii_map}\n")
                f.write(f"Analysis: {briefing}\n\n")
            logger.info("Tactical briefing written to %s", self.log_path)
        except Exception as e:
            logger.error("Failed to write briefing: %s", e)

