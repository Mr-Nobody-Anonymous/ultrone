# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Commander Briefing Generator - Post-hoc LLM observer.

Analyzes completed training episodes and writes tactical briefings
to memory/commander_log.txt. This is strictly a post-hoc observer;
it does NOT alter simulation step or fitness evaluation.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Generative.CommanderBriefing")

# Default output path
BRIEFING_LOG_PATH = Path(__file__).resolve().parent.parent / "memory" / "commander_log.txt"


class CommanderBriefingGenerator:
    """
    Generates post-hoc strategic briefings from training telemetry.
    
    Uses fast local inference when available; falls back to rule-based
    synthesis so it never impacts evolutionary speed.
    """
    
    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or BRIEFING_LOG_PATH
        self._ensure_log_dir()
        self._model = None
        self._use_llm = False
        self._init_llm()
    
    def _ensure_log_dir(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_llm(self) -> None:
        """Attempt to load a lightweight local LLM. Fall back if unavailable."""
        try:
            # Prefer transformers if torch is available
            import torch  # noqa: F401
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import threading
            
            model_name = "microsoft/Phi-3-mini-4k-instruct"
            
            def _load():
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
                    model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        trust_remote_code=True,
                        torch_dtype="auto",
                        device_map="cpu",
                    )
                    self._model = (tokenizer, model)
                    self._use_llm = True
                    logger.info("Commander briefing LLM loaded: %s", model_name)
                except Exception as e:
                    logger.warning("LLM load failed: %s", e)
                    self._use_llm = False
            
            threading.Thread(target=_load, daemon=True).start()
        except Exception:
            self._use_llm = False
            logger.info("Commander briefing using rule-based synthesis")
    
    def generate_briefing(self, episode: int, telemetry: Dict[str, Any]) -> str:
        """
        Generate a tactical briefing paragraph from recent telemetry.
        
        Args:
            episode: Current episode number
            telemetry: Dict with keys:
                success_rate, avg_reward, mutation_rate,
                best_novelty, red_survival_rate, generation
            
        Returns:
            Briefing string
        """
        if self._use_llm and self._model is not None:
            return self._llm_briefing(episode, telemetry)
        return self._rule_based_briefing(episode, telemetry)
    
    def _llm_briefing(self, episode: int, telemetry: Dict[str, Any]) -> str:
        """Generate briefing using local LLM."""
        tokenizer, model = self._model
        prompt = (
            "You are an AI general analyzing an adversarial training simulation. "
            "Write a concise, authoritative tactical briefing paragraph.\n\n"
            f"Episode {episode} summary:\n"
            f"- Blue success rate: {telemetry.get('success_rate', 0):.0%}\n"
            f"- Average reward: {telemetry.get('avg_reward', 0):.1f}\n"
            f"- Blue mutation rate: {telemetry.get('mutation_rate', 0):.4f}\n"
            f"- Red survival rate: {telemetry.get('red_survival_rate', 0):.0%}\n"
            f"- Generation: {telemetry.get('generation', 0)}\n\n"
            "Briefing:"
        )
        try:
            inputs = tokenizer(prompt, return_tensors="pt")
            output = model.generate(
                **inputs,
                max_new_tokens=120,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
            text = tokenizer.decode(output[0], skip_special_tokens=True)
            brief = text.split("Briefing:")[-1].strip()
            if brief:
                return brief
        except Exception as e:
            logger.debug("LLM briefing failed: %s", e)
        return self._rule_based_briefing(episode, telemetry)
    
    def _rule_based_briefing(self, episode: int, telemetry: Dict[str, Any]) -> str:
        """
        Rule-based tactical briefing synthesis.
        
        Produces a short strategic analysis paragraph from telemetry metrics.
        """
        success = telemetry.get("success_rate", 0)
        reward = telemetry.get("avg_reward", 0)
        mutation = telemetry.get("mutation_rate", 0)
        red_survival = telemetry.get("red_survival_rate", 0)
        generation = telemetry.get("generation", 0)
        
        # Blue performance assessment
        if success >= 0.8:
            blue_assessment = "Blue Force has achieved dominance through refined kill-chain execution"
        elif success >= 0.5:
            blue_assessment = "Blue is maintaining pressure but has not yet achieved decisive superiority"
        else:
            blue_assessment = "Blue is struggling to penetrate Red defenses and requires tactical innovation"
        
        # Red performance assessment
        if red_survival >= 0.8:
            red_assessment = "Red has preserved its force through effective ECM and dispersion"
        elif red_survival >= 0.5:
            Red_assessment = "Red is surviving but taking losses; evasion is partially effective"
        else:
            red_assessment = "Red is being destroyed before it can mount an effective defense"
        
        # Evolutionary state
        if mutation < 0.05:
            evo_state = "The genetic algorithm has converged and is exploiting a known solution"
        elif mutation < 0.12:
            evo_state = "Evolution is fine-tuning parameters in a stable regime"
        else:
            evo_state = "High mutation indicates active exploration of new tactical spaces"
        
        return (
            f"At episode {episode}, {blue_assessment.lower()}, "
            f"while {red_assessment.lower()}. "
            f"Evolution is at generation {generation}; {evo_state.lower()}. "
            f"Average reward is {reward:.1f} and Red survival stands at {red_survival:.0%}. "
            f"The swarm is adapting autonomously without human intervention."
        )
    
    def write_briefing(self, episode: int, telemetry: Dict[str, Any]) -> None:
        """
        Generate and append a briefing to the commander log.
        
        This is the main entry point for the orchestrator.
        """
        briefing = self.generate_briefing(episode, telemetry)
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[Episode {episode}] {briefing}\n\n")
            logger.info("Briefing written to %s", self.log_path)
        except Exception as e:
            logger.error("Failed to write briefing: %s", e)


def should_brief(episode: int, interval: int = 20) -> bool:
    """Return True if a briefing should be generated for this episode."""
    return episode > 0 and episode % interval == 0


def log_training_summary(path: Optional[Path] = None) -> None:
    """Log a startup banner to the commander log."""
    log_path = path or BRIEFING_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("ULTRONE COMMANDER LOG - Training Session\n")
        f.write("=" * 70 + "\n\n")