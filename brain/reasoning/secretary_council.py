# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Secretary Council - WarAgent-inspired strategic LLM guidance.

Three secretaries analyze telemetry and produce a StrategicDirective
that dynamically alters evolutionary fitness weights for the next generation.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Reasoning.SecretaryCouncil")


class StrategicDirective:
    """Dynamic fitness weight adjustments produced by the council."""
    
    def __init__(self, weights: Dict[str, float], focus: str = "balanced", notes: str = "") -> None:
        self.weights = {
            "effectiveness_weight": weights.get("effectiveness_weight", 0.5),
            "efficiency_weight": weights.get("efficiency_weight", 0.3),
            "novelty_weight": weights.get("novelty_weight", 0.2),
        }
        self.focus = focus
        self.notes = notes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "weights": dict(self.weights),
            "focus": self.focus,
            "notes": self.notes,
        }


class SecretaryCouncil:
    """
    Council of 3 LLM secretaries that analyze telemetry and produce strategic directives.
    
    Secretaries:
    - OperationsSecretary: Analyzes overall telemetry and decides strategic focus
    - IntelSecretary: Analyzes Red Force behavior patterns
    - ResourceSecretary: Tracks Blue Force attrition
    
    Falls back to rule-based synthesis if Ollama/LLM unavailable.
    """
    
    def __init__(self) -> None:
        self._model = None
        self._use_llm = False
        self._init_llm()
        self._last_directive: Optional[StrategicDirective] = None
    
    def _init_llm(self) -> None:
        """Attempt to load Ollama llama3 model."""
        try:
            import requests  # noqa: F401
            self._model = "ollama_llama3"
            self._use_llm = True
            logger.info("Secretary Council initialized with Ollama llama3")
        except Exception:
            self._use_llm = False
            logger.info("Secretary Council using rule-based synthesis")
    
    def deliberate(self, telemetry: Dict[str, Any], red_behavior: Dict[str, Any], blue_attrition: Dict[str, Any]) -> StrategicDirective:
        """
        Convene the council and produce a strategic directive.
        
        Args:
            telemetry: Recent training telemetry
            red_behavior: Red Force behavior analysis
            blue_attrition: Blue Force attrition data
            
        Returns:
            StrategicDirective with adjusted fitness weights
        """
        if self._use_llm:
            try:
                return self._llm_deliberate(telemetry, red_behavior, blue_attrition)
            except Exception as e:
                logger.debug("LLM council failed: %s", e)
        
        return self._rule_based_directive(telemetry, red_behavior, blue_attrition)
    
    def _llm_deliberate(self, telemetry: Dict[str, Any], red_behavior: Dict[str, Any], blue_attrition: Dict[str, Any]) -> StrategicDirective:
        """Use Ollama llama3 to produce strategic directive."""
        prompt = self._build_prompt(telemetry, red_behavior, blue_attrition)
        
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "max_tokens": 200,
                },
                timeout=30,
            )
            data = response.json()
            text = data.get("response", "")
            return self._parse_directive(text)
        except Exception as e:
            logger.debug("Ollama request failed: %s", e)
            raise
    
    def _build_prompt(self, telemetry: Dict[str, Any], red_behavior: Dict[str, Any], blue_attrition: Dict[str, Any]) -> str:
        """Build deliberation prompt for the council."""
        return (
            "You are a military strategy council with 3 secretaries:\n"
            "1. Operations Secretary: Focus on overall mission effectiveness\n"
            "2. Intelligence Secretary: Focus on enemy behavior analysis\n"
            "3. Resource Secretary: Focus on force conservation\n\n"
            "Current situation:\n"
            f"- Blue success rate: {telemetry.get('success_rate', 0):.0%}\n"
            f"- Average reward: {telemetry.get('avg_reward', 0):.1f}\n"
            f"- Red survival rate: {telemetry.get('red_survival_rate', 0):.0%}\n"
            f"- Red ECM usage: {red_behavior.get('ecm_usage', 0):.0%}\n"
            f"- Red evasion: {red_behavior.get('evasion_usage', 0):.0%}\n"
            f"- Blue ammo remaining: {blue_attrition.get('ammo_remaining', 100):.0f}%\n"
            f"- Blue health remaining: {blue_attrition.get('health_remaining', 100):.0f}%\n\n"
            "Output JSON with keys: effectiveness_weight, efficiency_weight, novelty_weight, focus, notes\n"
            "Weights must sum to 1.0. Focus should be one of: balanced, effectiveness, efficiency, novelty, counter_ecm, counter_evade.\n"
            "JSON:"
        )
    
    def _parse_directive(self, text: str) -> StrategicDirective:
        """Parse LLM response into StrategicDirective."""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return StrategicDirective(
                    weights=data,
                    focus=data.get("focus", "balanced"),
                    notes=data.get("notes", ""),
                )
        except Exception:
            pass
        raise ValueError("Failed to parse directive")
    
    def _rule_based_directive(self, telemetry: Dict[str, Any], red_behavior: Dict[str, Any], blue_attrition: Dict[str, Any]) -> StrategicDirective:
        """
        Rule-based strategic directive synthesis.
        
        Produces fitness weight adjustments based on telemetry patterns.
        """
        success = telemetry.get("success_rate", 0)
        red_survival = telemetry.get("red_survival_rate", 0)
        ecm_usage = red_behavior.get("ecm_usage", 0)
        evasion_usage = red_behavior.get("evasion_usage", 0)
        ammo_remaining = blue_attrition.get("ammo_remaining", 100)
        
        # Default balanced weights
        weights = {
            "effectiveness_weight": 0.5,
            "efficiency_weight": 0.3,
            "novelty_weight": 0.2,
        }
        
        focus = "balanced"
        notes_parts = []
        
        # Counter high ECM
        if ecm_usage > 0.6:
            weights["novelty_weight"] = 0.4
            weights["effectiveness_weight"] = 0.35
            weights["efficiency_weight"] = 0.25
            focus = "counter_ecm"
            notes_parts.append("Red ECM dominance detected; reward sensor diversity and visual-centric COAs")
        
        # Counter high evasion
        elif evasion_usage > 0.6:
            weights["effectiveness_weight"] = 0.6
            weights["novelty_weight"] = 0.25
            weights["efficiency_weight"] = 0.15
            focus = "counter_evade"
            notes_parts.append("Red evasion dominance detected; reward hit probability and predictive targeting")
        
        # Ammo conservation
        if ammo_remaining < 30:
            weights["efficiency_weight"] = max(weights["efficiency_weight"], 0.5)
            focus = "efficiency"
            notes_parts.append("Low ammo; prioritize weapons conservation and precision strikes")
        
        # If Blue is failing hard, explore novelty
        if success < 0.3:
            weights["novelty_weight"] = max(weights["novelty_weight"], 0.5)
            focus = "novelty"
            notes_parts.append("Blue struggling; explore novel cross-domain tactics")
        
        notes = "; ".join(notes_parts) if notes_parts else "Maintaining current strategic balance"
        
        return StrategicDirective(weights=weights, focus=focus, notes=notes)
    
    def get_directive(self) -> Optional[StrategicDirective]:
        """Get the last issued directive."""
        return self._last_directive
    
    def set_directive(self, directive: StrategicDirective) -> None:
        """Set the current directive."""
        self._last_directive = directive


def analyze_red_behavior(red_genome: Any, red_survival_history: List[float]) -> Dict[str, Any]:
    """Analyze Red Force behavior patterns."""
    ecm_tendency = getattr(red_genome, 'ecm_probability', 0.2)
    evasion_tendency = getattr(red_genome, 'evasion_tendency', 0.5)
    
    recent_survival = red_survival_history[-10:] if len(red_survival_history) >= 10 else red_survival_history
    survival_rate = sum(recent_survival) / len(recent_survival) if recent_survival else 0.0
    
    return {
        "ecm_usage": ecm_tendency,
        "evasion_usage": evasion_tendency,
        "survival_rate": survival_rate,
    }


def analyze_blue_attrition(blue_assets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Analyze Blue Force attrition."""
    total_ammo = 0
    total_ammo_used = 0
    total_health = 0
    total_health_lost = 0
    
    for asset_type, assets in blue_assets.items():
        for asset in assets:
            total_ammo += asset.get("ammo", 0) + 1
            total_ammo_used += 1
            total_health += 100
            total_health_lost += max(0, 100 - asset.get("health", 100))
    
    ammo_remaining = (total_ammo - total_ammo_used) / max(1, total_ammo) * 100
    health_remaining = (total_health - total_health_lost) / max(1, total_health) * 100
    
    return {
        "ammo_remaining": max(0.0, min(100.0, ammo_remaining)),
        "health_remaining": max(0.0, min(100.0, health_remaining)),
    }