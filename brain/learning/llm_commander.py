# Copyright (c) Ultrone Contributors. All rights reserved.
"""
LLM Commander - Visual-Grounding tactical analysis.

Phase 7 Upgrade: Chain-of-Thought reasoning loop + Self-Correction.
  - _chain_of_thought(): Four-step hidden deduction (Resource Constraints,
    Bottleneck Vulnerabilities, Deceit Tactics, Synthesis)
  - _self_correct(): Critique initial suggestion against KG + MC, then
    adjust before finalizing the briefing payload.

Receives ASCII maps and telemetry from the battlefield and produces
tactical briefings. Strictly a post-hoc observer; does not alter
simulation step or evolutionary fitness.

Phase 6 Palantir-Style: Accepts knowledge graph summaries and Monte Carlo
probabilities for enhanced decision intelligence.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Learning.LLMCommander")

BRIEFING_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "commander_log.txt"


class LLMCommander:
    """
    LLM-based commander that analyzes battlefield state.
    
    Phase 7: Chain-of-Thought internal reasoning + self-correction.
    Phase 6: Palantir-style decision intelligence with KG + MC integration.
    """
    
    def __init__(self, log_path: Optional[Path] = None) -> None:
        self.log_path = log_path or BRIEFING_LOG_PATH
        self._model = None
        self._use_llm = False
        self._init_llm()
        
        # Phase 7: CoT state (ephemeral; reset per analyze call)
        self._cot_trace: List[str] = []
        self._initial_judgment: Optional[str] = None
        self._corrected_judgment: Optional[str] = None
    
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
    
    # ------------------------------------------------------------------
    # Public API (unchanged signature)
    # ------------------------------------------------------------------
    def analyze(self, ascii_map: str, telemetry: Dict[str, Any],
                kg_summary: Optional[str] = None,
                mc_probabilities: Optional[Dict[str, float]] = None) -> str:
        """
        Analyze battlefield and return tactical briefing.
        
        Phase 7: Internally runs CoT reasoning + self-correction before
        the final briefing is emitted.
        
        Args:
            ascii_map: ASCII map string from BattlefieldEnv.render_ascii_map()
            telemetry: Recent training telemetry
            kg_summary: Knowledge graph summary from MultiINTKnowledgeGraph.get_summary()
            mc_probabilities: Monte Carlo result dict from MonteCarloForklift
            
        Returns:
            Tactical briefing string (post-correction)
        """
        # Reset ephemeral CoT state
        self._cot_trace = []
        self._initial_judgment = None
        self._corrected_judgment = None
        
        if self._use_llm:
            try:
                return self._llm_analyze(ascii_map, telemetry, kg_summary, mc_probabilities)
            except Exception as e:
                logger.debug("LLM analysis failed: %s", e)
        return self._rule_based_analysis(ascii_map, telemetry, kg_summary, mc_probabilities)
    
    # ------------------------------------------------------------------
    # Phase 7: Chain-of-Thought Reasoning (4-step hidden deduction)
    # ------------------------------------------------------------------
    def _chain_of_thought(self, ascii_map: str, telemetry: Dict[str, Any],
                          kg_summary: Optional[str] = None,
                          mc_probabilities: Optional[Dict[str, float]] = None) -> str:
        """
        Internal multi-step reasoning pipeline.
        
        Step 1 — Resource Constraint Analysis
        Step 2 — Bottleneck Vulnerability Detection
        Step 3 — Deceit / Feint Tactic Detection
        Step 4 — Synthesis into a single judgment
        """
        lines: List[str] = []
        lines.append("=== CHAIN-OF-THOUGHT TRACE ===")
        
        # ---- Step 1: Resource Constraint Analysis ----
        lines.append("[Step 1] Resource Constraint Analysis")
        supply_count = _count_supply_nodes(ascii_map)
        fuel_estimate = _estimate_fuel_levels(ascii_map)
        red_ammo = telemetry.get("red_survival_rate", 0.5)
        
        # Blue supply health
        blue_resources_ok = supply_count.get("blue", 0) >= 1 and fuel_estimate.get("blue_avg", 1.0) > 0.3
        red_resources_ok = supply_count.get("red", 0) >= 1
        
        lines.append(f"  Blue supply nodes: {supply_count.get('blue', 0)} | "
                     f"Red supply nodes: {supply_count.get('red', 0)}")
        lines.append(f"  Blue avg fuel: {fuel_estimate.get('blue_avg', 0):.1%} | "
                     f"Red avg fuel: {fuel_estimate.get('red_avg', 0):.1%}")
        if not blue_resources_ok:
            lines.append("  ⚠ BLUE RESOURCE CONSTRAINT: Supply node deficit or fuel critically low.")
        if red_resources_ok:
            lines.append("  ⚠ RED HAS SUPPLY ADVANTAGE: Red supply nodes operational.")
        
        # ---- Step 2: Bottleneck Vulnerability Detection ----
        lines.append("")
        lines.append("[Step 2] Bottleneck & Vulnerability Analysis")
        chokepoints = _find_chokepoints(ascii_map)
        ecm_zones = ascii_map.count("E")
        
        if ecm_zones > 0:
            lines.append(f"  📡 ECM ZONES present: {ecm_zones} cells — sensor degradation risk.")
        
        if chokepoints:
            for cp in chokepoints[:3]:
                lines.append(f"  🔴 CHOKEPOINT at {cp}: high-density corridor — ambush risk.")
        else:
            lines.append("  No critical chokepoints detected (dispersed formation OK).")
        
        # Blue effectiveness trend
        success_rate = telemetry.get("success_rate", 0.5)
        if success_rate < 0.4:
            lines.append("  🔴 BLUE EFFECTIVENESS DROPPING: sustained low success rate indicates "
                         "systemic vulnerability.")
        elif success_rate < 0.7:
            lines.append("  🟡 MODERATE EFFECTIVENESS: Blue holds but not dominating.")
        else:
            lines.append("  🟢 HIGH EFFECTIVENESS: Blue kill-chain functioning.")
        
        # ---- Step 3: Deceit Tactic Detection ----
        lines.append("")
        lines.append("[Step 3] Deceit / Feint Tactic Detection")
        red_survival = telemetry.get("red_survival_rate", 0.5)
        mutation = telemetry.get("mutation_rate", 0.15)
        
        # Heuristic: high Red survival + high mutation = Red deploying deceptive strategy
        if red_survival > 0.7 and mutation > 0.2:
            lines.append("  ⚠ DECEIT PATTERN: Red survival is high (>70%) while Blue mutation "
                         "is elevated (>0.2). Red may be feinting or using sacrificial ECM decoys "
                         "to drain Blue ammunition.")
            deceit_flag = True
        elif red_survival > 0.6:
            lines.append("  🟡 POSSIBLE FEINT: Moderate-high Red survival suggests ECM/evasion "
                         "is effective, but no clear deception signature.")
            deceit_flag = False
        else:
            lines.append("  🟢 No deception pattern detected. Red is on the defensive.")
            deceit_flag = False
        
        # ---- Step 4: Synthesis ----
        lines.append("")
        lines.append("[Step 4] Multi-INT Synthesis")
        
        if not blue_resources_ok and success_rate < 0.4:
            judgment = (
                "CRITICAL: Blue is resource-constrained and losing. Immediate resupply "
                "or supply node defense required. Recommend shifting to electronic warfare "
                "to conserve munitions while re-establishing logistics."
            )
        elif deceit_flag:
            judgment = (
                "Red appears to be executing a feint/deception campaign. Blue should "
                "avoid committing reserves until deception is confirmed via SIGINT "
                "cross-correlation. Maintain ECM jamming to degrade Red comms."
            )
        elif success_rate > 0.8:
            judgment = (
                "Blue dominates the battlespace. Maintain pressure but monitor for "
                "Red adaptation. Recommend rotating asset positions to avoid pattern "
                "exploitation."
            )
        elif success_rate > 0.5:
            judgment = (
                "Blue holds a marginal advantage. Continue current strategy but prepare "
                "to counter Red ECM escalation. Recommend 60/40 split between continuation "
                "and resupply posture."
            )
        else:
            judgment = (
                "Blue is at a disadvantage. Recommend novel cross-domain tactics: "
                "increase drone reconnaissance to locate Red supply nodes, then "
                "coordinate precision strikes to sever logistics."
            )
        
        lines.append(f"  FINAL JUDGMENT: {judgment}")
        self._cot_trace = lines
        self._initial_judgment = judgment
        return judgment
    
    # ------------------------------------------------------------------
    # Phase 7: Self-Correction Mechanism
    # ------------------------------------------------------------------
    def _self_correct(self, judgment: str,
                      kg_summary: Optional[str] = None,
                      mc_probabilities: Optional[Dict[str, float]] = None) -> str:
        """
        Critique the initial judgment against KG and MC evidence.
        
        1. Check KG alignment: does the KG support the judgment's assumptions?
        2. Check MC alignment: does the MC forecast support the judgment's
           recommended action?
        3. If misalignment > threshold, produce a corrected judgment.
        """
        corrections: List[str] = []
        confidence_erosion = 0.0
        
        # 1. KG alignment
        if kg_summary:
            kg_lower = kg_summary.lower()
            # Check if KG mentions threat or supply issues
            has_threats = "high-threat" in kg_lower or "radar" in kg_lower or "sigint" in kg_lower
            has_supply = "supply" in kg_lower
            
            if "dominates" in judgment.lower() and has_threats:
                corrections.append(
                    "KG MISMATCH: Judgment says 'dominates' but KG reports active "
                    "high-threat entities. Overconfidence detected."
                )
                confidence_erosion += 0.25
            elif "dominates" not in judgment.lower() and not has_threats and not has_supply:
                corrections.append(
                    "KG MISMATCH: Judgment says Blue is disadvantaged but KG shows "
                    "no high-threat entities. Underconfidence detected."
                )
                confidence_erosion += 0.15
        
        # 2. MC alignment
        if mc_probabilities:
            mc_success = mc_probabilities.get("probability_of_success", 0.5)
            mc_cost = mc_probabilities.get("expected_resource_cost", 50.0)
            
            # If judgment says "continue pressure" but MC success < 30% → mismatch
            if "maintain pressure" in judgment.lower() and mc_success < 0.3:
                corrections.append(
                    f"MC MISMATCH: Judgment recommends 'maintain pressure' but MC forecasts "
                    f"only {mc_success:.0%} success. Recommend fallback to resupply."
                )
                confidence_erosion += 0.30
            elif "resupply" in judgment.lower() and mc_success > 0.7 and mc_cost < 30:
                corrections.append(
                    f"MC MISMATCH: Judgment recommends 'resupply' but MC forecasts "
                    f"{mc_success:.0%} success at low cost ({mc_cost:.0f}). "
                    "Recommend exploiting the favorable battle conditions."
                )
                confidence_erosion += 0.20
        
        # 3. Apply correction if confidence erosion is significant
        if confidence_erosion > 0.2 and corrections:
            # Build corrected judgment
            preamble = (
                "SELF-CORRECTION APPLIED: Initial assessment was revised after "
                "cross-referencing KG and MC evidence.\n"
            )
            correction_detail = "\n".join(f"  • {c}" for c in corrections[:3])
            
            if "dominates" in judgment.lower():
                corrected = (
                    "CORRECTED: Despite tactical advantages, Blue must verify full "
                    "battlespace awareness before committing to offensive. "
                    "Recommend cautious advance with ECM suppression."
                )
            elif "disadvantage" in judgment.lower() or "losing" in judgment.lower():
                corrected = (
                    "CORRECTED: The situation may be less dire than initial assessment. "
                    "Deploy recon drones to validate Red force disposition before "
                    "committing to defensive posture."
                )
            else:
                corrected = (
                    "CORRECTED: Adjusting strategic posture to align with KG and MC "
                    "evidence. Recommend balanced approach: continue operations but "
                    "maintain reserve for rapid resupply."
                )
            
            self._corrected_judgment = (
                f"{preamble}Initial: {judgment}\n"
                f"Corrections:\n{correction_detail}\n"
                f"{corrected}"
            )
            return self._corrected_judgment
        
        # No significant correction needed
        self._corrected_judgment = judgment
        return judgment
    
    # ------------------------------------------------------------------
    # LLM path (unchanged call signature)
    # ------------------------------------------------------------------
    def _llm_analyze(self, ascii_map: str, telemetry: Dict[str, Any],
                     kg_summary: Optional[str] = None,
                     mc_probabilities: Optional[Dict[str, float]] = None) -> str:
        """Analyze using Ollama llama3 with CoT + self-correction prompt."""
        
        # Phase 7: Run CoT reasoning to build internal trace
        cot_judgment = self._chain_of_thought(ascii_map, telemetry, kg_summary, mc_probabilities)
        cot_text = "\n".join(self._cot_trace)
        
        # Phase 7: Run self-correction
        corrected = self._self_correct(cot_judgment, kg_summary, mc_probabilities)
        
        kg_section = ""
        if kg_summary:
            kg_section = f"\nMulti-INT Knowledge Graph:\n{kg_summary}\n"
        
        mc_section = ""
        if mc_probabilities:
            mc_section = (
                f"\nMonte Carlo Forecast:\n"
                f"- Probability of Success: {mc_probabilities.get('probability_of_success', 0):.0%}\n"
                f"- Expected Casualties: {mc_probabilities.get('expected_casualties', 0):.2f}\n"
                f"- Expected Resource Cost: {mc_probabilities.get('expected_resource_cost', 0):.1f}\n"
            )
        
        prompt = (
            "You are a Palantir-style decision intelligence analyst with Chain-of-Thought reasoning.\n"
            "Below is your internal reasoning trace and a self-correction step.\n\n"
            f"### INTERNAL CoT TRACE ###\n{cot_text}\n\n"
            f"### SELF-CORRECTED JUDGMENT ###\n{corrected}\n\n"
            f"Current battlefield map:\n{ascii_map}\n\n"
            "Legend: R=Red Force, D=Drone, M=Missile, J=Jammer, S=Blue Supply, "
            "s=Red Supply, E=ECM zone, .=empty\n\n"
            "Current telemetry:\n"
            f"- Blue success rate: {telemetry.get('success_rate', 0):.0%}\n"
            f"- Avg reward: {telemetry.get('avg_reward', 0):.1f}\n"
            f"- Red survival: {telemetry.get('red_survival_rate', 0):.0%}\n"
            f"- Generation: {telemetry.get('generation', 0)}\n"
            f"{kg_section}"
            f"{mc_section}"
            "Provide a 2-3 sentence probabilistic assessment incorporating the reasoning above. "
            "Identify supply chain vulnerabilities, comms link criticalities, and recommend "
            "whether to continue, switch COA, or resupply."
        )
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "max_tokens": 150,
                },
                timeout=30,
            )
            data = response.json()
            text = data.get("response", "")
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug("Ollama request failed: %s", e)
        return self._rule_based_analysis(ascii_map, telemetry, kg_summary, mc_probabilities)
    
    # ------------------------------------------------------------------
    # Phase 7 Enhanced Rule-Based Analysis (with CoT + self-correction)
    # ------------------------------------------------------------------
    def _rule_based_analysis(self, ascii_map: str, telemetry: Dict[str, Any],
                             kg_summary: Optional[str] = None,
                             mc_probabilities: Optional[Dict[str, float]] = None) -> str:
        """
        Phase 7 Palantir-style tactical analysis with internal CoT reasoning
        and self-correction against KG + MC evidence.
        
        Produces a short strategic analysis paragraph with probabilistic forecasting.
        """
        # Phase 7: Run CoT reasoning (always — even in rule-based mode)
        judgment = self._chain_of_thought(ascii_map, telemetry, kg_summary, mc_probabilities)
        
        # Phase 7: Self-correction
        final_output = self._self_correct(judgment, kg_summary, mc_probabilities)
        
        # Build enriched briefing with CoT context
        success = telemetry.get("success_rate", 0)
        red_survival = telemetry.get("red_survival_rate", 0)
        generation = telemetry.get("generation", 0)
        
        # KG insight snippet
        kg_insight = ""
        if kg_summary:
            lines = kg_summary.split("\n")
            if lines:
                kg_insight = f" | INTEL: {lines[0]}"
        
        # MC insight snippet
        mc_insight = ""
        if mc_probabilities:
            prob = mc_probabilities.get("probability_of_success", 0)
            cost = mc_probabilities.get("expected_resource_cost", 0)
            casualties = mc_probabilities.get("expected_casualties", 0)
            mc_insight = f" | MC FORECAST: {prob:.0%} success, {cost:.0f} fuel cost, {casualties:.2f} casualties"
        
        return (
            f"Generation {generation}: {final_output}"
            f"{kg_insight}"
            f"{mc_insight}"
            f" | Red survival at {red_survival:.0%}. "
            f"Map shows R with S/s supply nodes."
        )
    
    # ------------------------------------------------------------------
    # ask_reasoning (unchanged — creates XAI from genome)
    # ------------------------------------------------------------------
    def ask_reasoning(self, genome: Any, telemetry: Optional[Dict[str, Any]] = None) -> str:
        """
        XAI: Produce a human-readable explanation of how the genome/swarm is adapting.
        
        Phase 7: Also includes CoT trace if available.
        """
        if not genome:
            return "No genome data available for reasoning."

        action_weights = getattr(genome, 'action_weights', {})
        fitness_score = getattr(genome, 'fitness_score', 0.0)
        mutation_rate = getattr(genome, 'mutation_rate', 0.15)
        generation = getattr(genome, 'generation', 0)
        genome_id = getattr(genome, 'genome_id', 'unknown')

        top_actions = sorted(action_weights.items(), key=lambda x: x[1], reverse=True)

        lines = []
        lines.append(f"🧬 GENETIC REASONING — Genome {genome_id} (Generation {generation})")
        lines.append(f"   Fitness Score : {fitness_score:.3f}")
        lines.append(f"   Mutation Rate : {mutation_rate:.4f}")
        lines.append("")

        if top_actions:
            lines.append("   Action Profile (top actions by weight):")
            for action, weight in top_actions[:5]:
                bar = "█" * int(weight * 20) + "░" * (20 - int(weight * 20))
                lines.append(f"     {action:>12s}: {weight:.3f} {bar}")
            lines.append("")

            dominant = top_actions[0][0] if top_actions else "unknown"
            dominant_weight = top_actions[0][1] if top_actions else 0.0

            if dominant == "strike" and dominant_weight < 0.3:
                lines.append("   🔄 STRATEGY SHIFT DETECTED: Strike capability is suppressed.")
                lines.append("      The swarm has shifted away from kinetic strikes toward")
                lines.append("      electronic warfare and maneuver.")
            elif dominant == "jam":
                lines.append("   📡 JAMMING-CENTRIC STRATEGY: The swarm prioritizes electronic warfare.")
                lines.append("      Jamming degrades Red sensors and creates windows for")
                lines.append("      coordinated drone infiltration.")
            elif dominant == "move":
                lines.append("   🏃 MANEUVER STRATEGY: The swarm prioritizes positional advantage.")
                lines.append("      Assets are repositioning to achieve optimal engagement geometry.")
            elif dominant == "strike" and dominant_weight > 0.7:
                lines.append("   💥 KINETIC-DOMINANT STRATEGY: The swarm favors direct firepower.")
                lines.append("      High strike weight suggests convergence on overwhelming kinetic force.")
            else:
                lines.append(f"   🎯 DOMINANT ACTION: '{dominant}' (weight: {dominant_weight:.3f})")
                lines.append("      The swarm is executing a diversified approach.")

            if len(top_actions) >= 2:
                a1, w1 = top_actions[0]
                a2, w2 = top_actions[1]
                if w2 > 0.3:
                    lines.append("")
                    lines.append(f"   🤝 SYNERGY NOTE: '{a1}' often combined with '{a2}'")
                    lines.append(f"      (combined weight: {w1 + w2:.3f}). Cross-domain coordination active.")
        else:
            lines.append("   No action weights recorded — genome is in early exploration phase.")

        if mutation_rate > 0.30:
            lines.append("")
            lines.append("   ⚠️ HIGH MUTATION: The genome is in an active exploratory panic.")
            lines.append("      Elevated mutation indicates searching broadly for viable alternatives.")
        elif mutation_rate > 0.20:
            lines.append("")
            lines.append("   ⚡ ELEVATED MUTATION: Moderate exploration above baseline.")
        elif mutation_rate < 0.12:
            lines.append("")
            lines.append("   ✅ STABLE MUTATION: The genome has converged on a reliable strategy.")

        fitness_history = getattr(genome, 'fitness_history', [])
        if len(fitness_history) >= 3:
            recent = fitness_history[-3:]
            trend = "rising 📈" if recent[-1] > recent[0] else "falling 📉" if recent[-1] < recent[0] else "stable ➡️"
            lines.append("")
            lines.append(f"   📊 FITNESS TREND (last 3): {trend}")
            lines.append(f"      Recent values: {[f'{f:.3f}' for f in recent]}")

        # Append CoT trace if available (Phase 7)
        if self._cot_trace:
            lines.append("")
            lines.append("--- Phase 7 CoT Reasoning Trace ---")
            for t in self._cot_trace:
                lines.append(f"  {t}")

        return "\n".join(lines)

    def write_briefing(self, ascii_map: str, telemetry: Dict[str, Any]) -> None:
        """Write tactical briefing to commander log."""
        briefing = self.analyze(ascii_map, telemetry)
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[Episode {telemetry.get('episode', '?')}] TACTICAL BRIEFING\n")
                f.write(f"Map:\n{ascii_map}\n")
                # Include CoT trace if generated
                if self._cot_trace:
                    f.write("CoT Trace:\n")
                    for t in self._cot_trace:
                        f.write(f"  {t}\n")
                f.write(f"Analysis: {briefing}\n\n")
            logger.info("Tactical briefing written to %s", self.log_path)
        except Exception as e:
            logger.error("Failed to write briefing: %s", e)


# =====================================================================
# Helper utilities for CoT analysis (stateless, pure functions)
# =====================================================================

def _count_supply_nodes(ascii_map: str) -> Dict[str, int]:
    """Count supply nodes by side from ASCII map."""
    blue = ascii_map.count("S")
    red = ascii_map.count("s")
    return {"blue": blue, "red": red}


def _estimate_fuel_levels(ascii_map: str) -> Dict[str, float]:
    """
    Rough estimate of fuel levels from map density.
    Returns normalized averages [0,1].
    """
    total_cells = max(1, len(ascii_map.replace("\n", "")))
    blue_density = ascii_map.count("D") + ascii_map.count("M") + ascii_map.count("J")
    red_density = ascii_map.count("R")
    return {
        "blue_avg": max(0.1, 1.0 - (blue_density / max(1, total_cells * 0.1))),
        "red_avg": max(0.1, 1.0 - (red_density / max(1, total_cells * 0.05))),
    }


def _find_chokepoints(ascii_map: str) -> List[Tuple[int, int]]:
    """
    Find candidate chokepoint positions where corridor density is high.
    Returns list of (row, col) tuples.
    """
    rows = ascii_map.strip().split("\n")
    chokepoints: List[Tuple[int, int]] = []
    for r in range(1, len(rows) - 1):
        for c in range(1, len(rows[r]) - 1):
            # Count non-empty neighbors in a 3x3 patch
            neighbors = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < len(rows) and 0 <= nc < len(rows[nr]):
                        ch = rows[nr][nc]
                        if ch not in (".", " "):
                            neighbors += 1
            if neighbors >= 5:  # dense cluster
                chokepoints.append((r, c))
    return chokepoints

