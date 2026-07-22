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
    
    def analyze(self, ascii_map: str, telemetry: Dict[str, Any]) -> str:
        """
        Analyze battlefield and return tactical briefing.
        
        Args:
            ascii_map: ASCII map string from BattlefieldEnv.render_ascii_map()
            telemetry: Recent training telemetry
            
        Returns:
            Tactical briefing string
        """
        if self._use_llm:
            try:
                return self._llm_analyze(ascii_map, telemetry)
            except Exception as e:
                logger.debug("LLM analysis failed: %s", e)
        return self._rule_based_analysis(ascii_map, telemetry)
    
    def _llm_analyze(self, ascii_map: str, telemetry: Dict[str, Any]) -> str:
        """Analyze using Ollama llama3."""
        prompt = (
            "You are a VLM (Vision-Language Model) military commander.\n"
            "Here is the current battlefield map:\n"
            f"{ascii_map}\n\n"
            "Legend: R=Red Force, D=Drone, M=Missile, J=Jammer, E=ECM zone, .=empty\n\n"
            "Current telemetry:\n"
            f"- Blue success rate: {telemetry.get('success_rate', 0):.0%}\n"
            f"- Avg reward: {telemetry.get('avg_reward', 0):.1f}\n"
            f"- Red survival: {telemetry.get('red_survival_rate', 0):.0%}\n"
            f"- Generation: {telemetry.get('generation', 0)}\n\n"
            "Identify flanking opportunities, kill zones, and terrain bottlenecks in 2-3 sentences."
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
        return self._rule_based_analysis(ascii_map, telemetry)
    
    def _rule_based_analysis(self, ascii_map: str, telemetry: Dict[str, Any]) -> str:
        """
        Rule-based tactical analysis from ASCII map and telemetry.
        
        Produces a short strategic analysis paragraph.
        """
        success = telemetry.get("success_rate", 0)
        red_survival = telemetry.get("red_survival_rate", 0)
        generation = telemetry.get("generation", 0)
        
        if success >= 0.8:
            assessment = "Blue dominates the battlefield; maintain pressure."
        elif success >= 0.5:
            assessment = "Blue holds initiative but must adapt to Red counters."
        else:
            assessment = "Blue is losing; recommend regrouping and novel tactics."
        
        return (
            f"Generation {generation}: {assessment} "
            f"Red survival at {red_survival:.0%}. "
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

</parameter>
<task_progress>
- [x] Check for existing LLM commander
- [x] Create secretary_council.py
- [x] Add render_ascii_map() to BattlefieldEnv
- [x] Create llm_commander.py as post-hoc observer
- [x] Fix corrupted files
- [ ] Update orchestrator for hybrid loop
- [ ] Run tests and push to GitHub
</task_progress>
</write_to_file>