# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Master Training Orchestrator - Multi-episode evolutionary training loop.

Ties the BattlefieldEnv and EvolutionaryCOAGenerator together for
autonomous, self-evolving AI across multiple sessions.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Ultrone.Brain.Orchestrator")

# Ensure project root is on sys.path for top-level imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Default paths
MEMORY_DIR = Path(__file__).parent.parent / "memory"
BEST_GENOME_PATH = MEMORY_DIR / "best_genome.json"


class Orchestrator:
    """
    Master training orchestrator for ULTRONE.
    
    Runs N episodes, evolves genomes via EvolutionaryCOAGenerator,
    persists the best genome, and adapts mutation rates dynamically.
    """

    def __init__(
        self,
        num_episodes: int = 100,
        max_steps_per_episode: int = 200,
        initial_mutation_rate: float = 0.15,
        success_rate_window: int = 10,
    ) -> None:
        self.num_episodes = num_episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.mutation_rate = initial_mutation_rate
        self.success_rate_window = success_rate_window
        
        # Lazy imports by file path to avoid broken package-level relative imports
        import importlib.util
        
        def _load_module_by_path(module_name: str, file_path: Path):
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            return mod
        
        base = PROJECT_ROOT
        env_mod = _load_module_by_path(
            "sim.battlefield_env",
            base / "sim" / "battlefield_env.py",
        )
        BattlefieldEnv = env_mod.BattlefieldEnv
        
        coa_mod = _load_module_by_path(
            "brain.reasoning.evolutionary_coagen",
            base / "brain" / "reasoning" / "evolutionary_coagen.py",
        )
        EvolutionaryCOAGenerator = coa_mod.EvolutionaryCOAGenerator
        EvolutionaryGenome = coa_mod.EvolutionaryGenome
        
        swarm_mod = _load_module_by_path(
            "brain.reasoning.swarm_genomes",
            base / "brain" / "reasoning" / "swarm_genomes.py",
        )
        CommanderGenome = swarm_mod.CommanderGenome
        AssetMicroGenome = swarm_mod.AssetMicroGenome
        
        coev_mod = _load_module_by_path(
            "brain.reasoning.coevolution_engine",
            base / "brain" / "reasoning" / "coevolution_engine.py",
        )
        CoevolutionEngine = coev_mod.CoevolutionEngine
        RedForceGenome = coev_mod.RedForceGenome
        
        self.BattlefieldEnv = BattlefieldEnv
        self.EvolutionaryCOAGenerator = EvolutionaryCOAGenerator
        self.EvolutionaryGenome = EvolutionaryGenome
        self.CommanderGenome = CommanderGenome
        self.AssetMicroGenome = AssetMicroGenome
        self.CoevolutionEngine = CoevolutionEngine
        self.RedForceGenome = RedForceGenome
        
        # Training state
        self.episode_rewards: List[float] = []
        self.episode_successes: List[bool] = []
        self.red_survival_rates: List[float] = []
        self.best_genome: Optional[EvolutionaryGenome] = None
        self.best_fitness: float = 0.0
        self.generation: int = 0
        self.current_mutation_rate = initial_mutation_rate
        self.use_coevolution = True
        
        # Ensure memory directory exists
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Post-hoc commander briefing generator
        self._briefing_generator = None

    def _load_elite_genome(self) -> Optional[EvolutionaryGenome]:
        """Load the best genome from persistent memory if it exists."""
        if not BEST_GENOME_PATH.exists():
            return None
        
        try:
            with open(BEST_GENOME_PATH, "r") as f:
                data = json.load(f)
            
            # Reconstruct EvolutionaryGenome from dict
            genome = self.EvolutionaryGenome(
                genome_id=data["genome_id"],
                generation=data.get("generation", 0),
                agent_id=data.get("agent_id", "elite"),
                action_weights=data.get("action_weights", {}),
                synergy_map={
                    tuple(k.split("|")): v 
                    for k, v in data.get("synergy_map", {}).items()
                },
                phase_params={
                    k: self._dict_to_phase_params(v) 
                    for k, v in data.get("phase_params", {}).items()
                },
                resource_conservation=data.get("resource_conservation", 0.7),
                time_optimization=data.get("time_optimization", 1.0),
                domain=data.get("domain", "all"),
                mutation_rate=data.get("mutation_rate", self.current_mutation_rate),
                fitness_score=data.get("fitness_score", 0.0),
            )
            logger.info(f"Elite genome loaded from {BEST_GENOME_PATH}")
            return genome
        except Exception as e:
            logger.warning(f"Failed to load elite genome: {e}")
            return None

    def _dict_to_phase_params(self, d: Dict) -> Any:
        """Convert dict to PhaseParameters dataclass."""
        from brain.reasoning.evolutionary_coagen import PhaseParameters
        return PhaseParameters(
            speed=d.get("speed", 1.0),
            confidence_threshold=d.get("confidence_threshold", 0.7),
            resource_efficiency=d.get("resource_efficiency", 0.8),
        )

    def _save_best_genome(self) -> None:
        """Save the best genome to persistent memory."""
        if not self.best_genome:
            return
        
        try:
            data = self.best_genome.to_dict()
            with open(BEST_GENOME_PATH, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Best genome saved to {BEST_GENOME_PATH}")
        except Exception as e:
            logger.error(f"Failed to save best genome: {e}")

    def _adapt_mutation_rate(self) -> None:
        """
        Dynamically adjust mutation rates for both Blue and Red based on recent performance.
        
        Blue rules:
        - If last 10 episodes have >80% success: DECREASE by 10% (exploit)
        - If last 10 episodes have <50% success: INCREASE by 20% (explore)
        
        Red rules:
        - If last 10 episodes have <50% Red survival: INCREASE by 20% (evade better)
        """
        window = self.success_rate_window
        if len(self.episode_successes) < window:
            return
        
        recent_success = self.episode_successes[-window:]
        success_rate = sum(recent_success) / len(recent_success)
        
        # Adaptive Blue mutation rate
        if success_rate > 0.8:
            self.current_mutation_rate *= 0.90
            logger.info(f"Blue mutation rate DECREASED to {self.current_mutation_rate:.4f} (exploiting)")
        elif success_rate < 0.5:
            self.current_mutation_rate *= 1.20
            logger.info(f"Blue mutation rate INCREASED to {self.current_mutation_rate:.4f} (exploring)")
        
        # Adaptive Red mutation rate based on survival
        if len(self.red_survival_rates) >= window:
            recent_survival = self.red_survival_rates[-window:]
            survival_rate = sum(recent_survival) / len(recent_survival)
            if survival_rate < 0.5:
                self.coevolution.red_mutation_rate *= 1.20
                logger.info(f"Red mutation rate INCREASED to {self.coevolution.red_mutation_rate:.4f} (evading better)")

    def _print_dashboard(self, episode: int) -> None:
        """Print clean dashboard every 10 episodes."""
        if episode % 10 != 0:
            return
        
        window = min(10, len(self.episode_rewards))
        recent_rewards = self.episode_rewards[-window:] if window > 0 else [0.0]
        avg_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
        
        window_s = min(10, len(self.episode_successes))
        recent_successes = self.episode_successes[-window_s:] if window_s > 0 else []
        success_rate = (sum(recent_successes) / len(recent_successes) * 100) if recent_successes else 0.0
        
        best_novelty = 0.0
        # Access best genome's fitness as proxy for novelty score
        if self.best_genome and hasattr(self.best_genome, 'fitness_score'):
            best_novelty = self.best_genome.fitness_score
        
        print("\n" + "=" * 70)
        print(f"ULTRONE TRAINING DASHBOARD - Episode {episode}/{self.num_episodes}")
        print("=" * 70)
        print(f"  Episode #          : {episode}")
        print(f"  Success Rate       : {success_rate:.1f}%")
        print(f"  Avg Reward         : {avg_reward:.1f}")
        print(f"  Mutation Rate      : {self.current_mutation_rate:.4f}")
        print(f"  Best Novelty Score : {best_novelty:.3f}")
        print(f"  Generation         : {self.generation}")
        print("=" * 70)
        
        # Compute red survival rate for this window
        window_survival = min(10, len(self.red_survival_rates))
        recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
        red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
        
        # Push telemetry to live visualization
        try:
            from viz.telemetry_dashboard import update_dashboard
            update_dashboard(
                episode=episode,
                success_rate=success_rate,
                mutation_rate=self.current_mutation_rate,
                avg_reward=avg_reward,
                novelty_score=best_novelty,
                red_survival_rate=red_survival_rate,
            )
        except Exception as e:
            logger.debug(f"Telemetry dashboard update skipped: {e}")

    def run(self) -> Dict[str, Any]:
        """
        Execute the master training loop.
        
        Returns:
            Training statistics summary
        """
        logger.info(f"Starting ULTRONE training: {self.num_episodes} episodes")
        
        # Try to load elite genome from memory
        elite = self._load_elite_genome()
        
        # Initialize environment and evolutionary engine
        env = self.BattlefieldEnv()
        
        # Initialize coevolution engine
        if self.use_coevolution and not hasattr(self, 'coevolution'):
            # Bootstrap populations from loaded elite or defaults
            blue_commander = None
            if hasattr(elite, 'spawn_asset_micro_genomes'):
                blue_commander = elite
            else:
                blue_commander = self.CommanderGenome(
                    genome_id=f"BLUE-{random.randint(10000, 99999)}",
                    action_weights={a: random.uniform(0.5, 1.0) for a in ["strike", "jam", "move", "engage", "locate", "assess"]},
                    synergy_map={(a, b): random.uniform(0.0, 1.0) for i, a in enumerate(["strike", "jam", "move", "engage", "locate", "assess"]) for b in ["strike", "jam", "move", "engage", "locate", "assess"][i+1:]},
                    mutation_rate=self.current_mutation_rate,
                )
            red_genome = self.RedForceGenome(genome_id=f"RED-{random.randint(10000, 99999)}")
            self.coevolution = self.CoevolutionEngine(sample_size=3)
            self.coevolution.initialize_blue(blue_commander)
            self.coevolution.initialize_red(red_genome)
        
        # Initialize post-hoc commander briefing generator
        if self._briefing_generator is None:
            try:
                from generative.commander_briefing import CommanderBriefingGenerator, log_training_summary
                self._briefing_generator = CommanderBriefingGenerator()
                log_training_summary()
            except Exception as e:
                logger.debug(f"Briefing generator unavailable: {e}")
        
        # Initialize hybrid LLM components
        self._llm_commander = None
        self._secretary_council = None
        self._current_directive = None
        try:
            from brain.learning.llm_commander import LLMCommander
            from brain.reasoning.secretary_council import SecretaryCouncil, analyze_red_behavior, analyze_blue_attrition
            self._llm_commander = LLMCommander()
            self._secretary_council = SecretaryCouncil()
            self._analyze_red_behavior = analyze_red_behavior
            self._analyze_blue_attrition = analyze_blue_attrition
        except Exception as e:
            logger.debug(f"Hybrid LLM components unavailable: {e}")
        
        # Initialize Operational API Server (HITL + XAI)
        self._intervention_manager = InterventionManager()
        self._api_server = None
        try:
            from comms.api_server import create_api_server
            self._api_server = create_api_server(self, self._intervention_manager)
            if self._api_server:
                self._api_server.start()
        except Exception as e:
            logger.debug(f"Operational API unavailable: {e}")
        
        # Track best across all episodes
        overall_best_fitness = self.best_fitness
        overall_best_genome = elite
        
        for episode in range(1, self.num_episodes + 1):
            # Reset environment
            obs = env.reset()
            
            # Check for human interventions before running this episode
            if hasattr(self, '_intervention_manager'):
                constraints = self._intervention_manager.get_constraints()
                if constraints:
                    logger.info(f"Applying {len(constraints)} intervention constraints")
                    # Force novelty weight override
                    if 'force_novelty_weight' in constraints:
                        if hasattr(self, '_secretary_council') and self._secretary_council:
                            from brain.reasoning.secretary_council import StrategicDirective
                            self._current_directive = StrategicDirective(
                                weights={
                                    'effectiveness_weight': 1.0 - constraints['force_novelty_weight'],
                                    'efficiency_weight': 0.0,
                                    'novelty_weight': constraints['force_novelty_weight'],
                                },
                                focus='human_override',
                                notes='Human forced novelty via API'
                            )
                    # Blacklist actions (e.g., blacklist STRIKE)
                    if 'blacklist_action' in constraints:
                        blacklisted = constraints['blacklist_action'].upper()
                        if blue_commander and hasattr(blue_commander, 'action_weights'):
                            # Zero out the blacklisted action weight
                            for action in list(blue_commander.action_weights.keys()):
                                if action.upper() == blacklisted:
                                    blue_commander.action_weights[action] = 0.0
            
            # Get current Blue and Red genomes
            blue_commander = self.coevolution.blue_active if self.use_coevolution else None
            red_genome = self.coevolution.red_active if self.use_coevolution else None
            
            # Initialize evolutionary engine for this episode
            coa_gen = self.EvolutionaryCOAGenerator()
            if blue_commander:
                coa_gen.active_genome = blue_commander
                coa_gen.population = [blue_commander]
                coa_gen._initialized = True
            elif elite:
                coa_gen.active_genome = elite
                coa_gen.population = [elite]
                coa_gen._initialized = True
            
            total_reward = 0.0
            success = False
            red_survived = True
            done = False
            step = 0
            
            # Episode loop
            while not done and step < self.max_steps_per_episode:
                step += 1
                
                # Generate Blue COA
                target_info = {
                    "domain": obs.get("red_force", {}).get("type", "unknown"),
                    "type": obs.get("red_force", {}).get("type", "unknown"),
                }
                context = {"observation": obs}
                coa = coa_gen.generate_evolved_coa(target_info, context)
                
                # Extract Blue action from COA phases
                blue_action = None
                swarm_coa = None
                if coa and coa.phases:
                    if hasattr(coa, 'swarm_fleet') and coa.swarm_fleet:
                        fleet = []
                        for micro in coa.swarm_fleet:
                            asset_action = {
                                "asset_type": micro.asset_type,
                                "action": "strike" if micro.aggressiveness > 0.6 else "move",
                                "target": (int(obs.get("red_force", {}).get("position", (50, 50))[0] + random.randint(-10, 10)),
                                           int(obs.get("red_force", {}).get("position", (50, 50))[1] + random.randint(-10, 10)))
                            }
                            fleet.append(asset_action)
                        swarm_coa = {
                            "type": "swarm",
                            "swarm_fleet": fleet,
                            "commander_genome": blue_commander.to_dict() if blue_commander else None,
                        }
                        blue_action = swarm_coa
                    else:
                        for phase in coa.phases:
                            if phase in ["strike", "jam", "move"]:
                                blue_action = {"action": phase, "asset_type": "missiles" if phase == "strike" else "jammers"}
                                if phase == "move":
                                    blue_action["target"] = (50, 50)
                                break
                
                # Generate Red action
                red_action = None
                if red_genome:
                    red_action = {
                        "evade": red_genome.should_evade(),
                        "ecm": red_genome.should_trigger_ecm(),
                        "ecm_noise": red_genome.ecm_noise_level,
                        "target": None,
                    }
                
                # Step environment with both Blue and Red actions
                try:
                    obs, reward, done, info = env.step(blue_action, red_action)
                    total_reward += reward
                    
                    # Check if target was destroyed (success)
                    if done and reward > 0:
                        success = True
                        red_survived = False
                
                except Exception as e:
                    logger.error(f"Error during environment step: {e}")
                    break
                
                # Evaluate fitness
                telemetry = {
                    "hits": 1 if success else 0,
                    "attempts": step,
                    "weapons_used": 1,
                    "weapons_allocated": 3,
                    "actions_used": coa.phases if coa else [],
                    "blue_on_blue": 1 if info.get("swarm_collisions", 0) > 0 else 0,
                    "collision_count": info.get("swarm_collisions", 0),
                    "red_survived": red_survived,
                    "ecm_active": info.get("ecm_active", False),
                }
                directive_weights = self._current_directive.weights if self._current_directive else None
                if blue_commander and self.use_coevolution:
                    self.coevolution.evaluate_blue_fitness(blue_commander, [red_genome], {red_genome.genome_id: telemetry}, directive=directive_weights)
                else:
                    fitness = coa_gen.evaluate_fitness(coa_gen.active_genome, telemetry)
                
                # Track best genome
                current_fitness = blue_commander.fitness_score if blue_commander else fitness
                if current_fitness > overall_best_fitness:
                    overall_best_fitness = current_fitness
                    overall_best_genome = blue_commander or coa_gen.active_genome
                    self.best_fitness = overall_best_fitness
                    self.best_genome = overall_best_genome
            
            # Record episode results
            self.episode_rewards.append(total_reward)
            self.episode_successes.append(success)
            self.red_survival_rates.append(1.0 if red_survived else 0.0)
            
            # Evolve generation
            if self.use_coevolution and blue_commander:
                new_blue = self.coevolution.evolve_blue_generation()
                new_red = self.coevolution.evolve_red_generation()
                if new_blue:
                    self.generation = new_blue.generation
                elite = new_blue or blue_commander
            else:
                self.generation = coa_gen.active_genome.generation if coa_gen.active_genome else self.generation
                elite = coa_gen.active_genome
            
            # Adapt mutation rate
            self._adapt_mutation_rate()
            
            # Print dashboard
            self._print_dashboard(episode)
            
            # Hybrid LLM guidance every 20 episodes
            if episode % 20 == 0:
                window_survival = min(10, len(self.red_survival_rates))
                recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
                red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
                
                window_rewards = min(10, len(self.episode_rewards))
                recent_rewards = self.episode_rewards[-window_rewards:] if window_rewards > 0 else [0.0]
                avg_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
                
                window_s = min(10, len(self.episode_successes))
                recent_successes = self.episode_successes[-window_s:] if window_s > 0 else []
                success_rate = (sum(recent_successes) / len(recent_successes)) if recent_successes else 0.0
                
                best_novelty = 0.0
                if self.best_genome and hasattr(self.best_genome, 'fitness_score'):
                    best_novelty = self.best_genome.fitness_score
                
                telemetry = {
                    "episode": episode,
                    "success_rate": success_rate,
                    "avg_reward": avg_reward,
                    "mutation_rate": self.current_mutation_rate,
                    "red_survival_rate": red_survival_rate / 100.0,
                    "generation": self.generation,
                    "best_novelty": best_novelty,
                }
                
                # LLM Commander visual-grounding brief
                if self._llm_commander is not None:
                    try:
                        ascii_map = env.render_ascii_map()
                        self._llm_commander.write_briefing(ascii_map, telemetry)
                    except Exception as e:
                        logger.debug(f"LLM commander brief failed: {e}")
                
                # Secretary Council strategic directive
                if self._secretary_council is not None:
                    try:
                        red_behavior = self._analyze_red_behavior(red_genome, self.red_survival_rates)
                        blue_attrition = self._analyze_blue_attrition(obs.get("blue_assets", {}))
                        directive = self._secretary_council.deliberate(telemetry, red_behavior, blue_attrition)
                        self._current_directive = directive
                        logger.info(f"Strategic directive: {directive.focus} - {directive.notes}")
                    except Exception as e:
                        logger.debug(f"Secretary council failed: {e}")
            
            # Post-hoc commander briefing every 20 episodes
            if self._briefing_generator is not None:
                from generative.commander_briefing import should_brief
                if should_brief(episode, interval=20):
                    window_survival = min(10, len(self.red_survival_rates))
                    recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
                    red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
                    
                    telemetry = {
                        "success_rate": (sum(self.episode_successes[-10:]) / len(self.episode_successes[-10:])) if len(self.episode_successes) >= 10 else (sum(self.episode_successes) / max(1, len(self.episode_successes))),
                        "avg_reward": avg_reward,
                        "mutation_rate": self.current_mutation_rate,
                        "red_survival_rate": red_survival_rate / 100.0,
                        "generation": self.generation,
                        "best_novelty": best_novelty,
                    }
                    self._briefing_generator.write_briefing(episode, telemetry)
        
        # Save best genome after all episodes
        if overall_best_genome:
            self.best_genome = overall_best_genome
            self.best_fitness = overall_best_fitness
            self._save_best_genome()
        
        # Final summary
        self._print_dashboard(self.num_episodes)
        
        summary = self.get_training_summary()
        logger.info(f"Training complete. Best fitness: {self.best_fitness:.3f}")
        return summary

    def get_training_summary(self) -> Dict[str, Any]:
        """Get training statistics summary."""
        if not self.episode_rewards:
            return {}
        
        total_episodes = len(self.episode_rewards)
        total_successes = sum(self.episode_successes)
        success_rate = total_successes / total_episodes if total_episodes > 0 else 0.0
        avg_reward = sum(self.episode_rewards) / total_episodes
        
        return {
            "total_episodes": total_episodes,
            "success_rate": success_rate,
            "avg_reward": avg_reward,
            "best_fitness": self.best_fitness,
            "final_mutation_rate": self.current_mutation_rate,
            "generation": self.generation,
        }


if __name__ == "__main__":
    orchestrator = Orchestrator(num_episodes=100)
    orchestrator.run()