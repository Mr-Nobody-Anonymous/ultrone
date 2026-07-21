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
        
        self.BattlefieldEnv = BattlefieldEnv
        self.EvolutionaryCOAGenerator = EvolutionaryCOAGenerator
        self.EvolutionaryGenome = EvolutionaryGenome
        
        # Training state
        self.episode_rewards: List[float] = []
        self.episode_successes: List[bool] = []
        self.best_genome: Optional[EvolutionaryGenome] = None
        self.best_fitness: float = 0.0
        self.generation: int = 0
        self.current_mutation_rate = initial_mutation_rate
        
        # Ensure memory directory exists
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

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
        Dynamically adjust mutation rate based on recent success rate.
        
        - If last 10 episodes have >80% success: DECREASE by 10% (exploit)
        - If last 10 episodes have <40% success: INCREASE by 20% (explore)
        """
        window = self.success_rate_window
        if len(self.episode_successes) < window:
            return
        
        recent = self.episode_successes[-window:]
        success_rate = sum(recent) / len(recent)
        
        if success_rate > 0.8:
            self.current_mutation_rate *= 0.90
            logger.info(f"Mutation rate DECREASED to {self.current_mutation_rate:.4f} (exploiting)")
        elif success_rate < 0.4:
            self.current_mutation_rate *= 1.20
            logger.info(f"Mutation rate INCREASED to {self.current_mutation_rate:.4f} (exploring)")

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
        
        # Push telemetry to live visualization
        try:
            from viz.telemetry_dashboard import update_dashboard
            update_dashboard(
                episode=episode,
                success_rate=success_rate,
                mutation_rate=self.current_mutation_rate,
                avg_reward=avg_reward,
                novelty_score=best_novelty,
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
        
        # Track best across all episodes
        overall_best_fitness = self.best_fitness
        overall_best_genome = elite
        
        for episode in range(1, self.num_episodes + 1):
            # Reset environment
            obs = env.reset()
            
            # Initialize evolutionary engine for this episode
            coa_gen = self.EvolutionaryCOAGenerator()
            
            # If we have an elite genome, use it as the starting point
            if elite:
                coa_gen.active_genome = elite
                coa_gen.population = [elite]
                coa_gen._initialized = True
            
            total_reward = 0.0
            success = False
            done = False
            step = 0
            
            # Episode loop
            while not done and step < self.max_steps_per_episode:
                step += 1
                
                # Generate COA using evolutionary engine
                target_info = {
                    "domain": obs.get("red_force", {}).get("type", "unknown"),
                    "type": obs.get("red_force", {}).get("type", "unknown"),
                }
                context = {"observation": obs}
                
                coa = coa_gen.generate_evolved_coa(target_info, context)
                
                # Extract action from COA phases
                action = None
                if coa and coa.phases:
                    for phase in coa.phases:
                        if phase in ["strike", "jam", "move"]:
                            action = {"action": phase, "asset_type": "missiles" if phase == "strike" else "jammers"}
                            if phase == "move":
                                action["target"] = (50, 50)
                            break
                
                # Step environment
                try:
                    obs, reward, done, info = env.step(action)
                    total_reward += reward
                    
                    # Check if target was destroyed (success)
                    if done and reward > 0:
                        success = True
                        
                except Exception as e:
                    logger.error(f"Error during environment step: {e}")
                    break
                
                # Evaluate fitness of the genome
                telemetry = {
                    "hits": 1 if success else 0,
                    "attempts": step,
                    "weapons_used": 1,
                    "weapons_allocated": 3,
                    "actions_used": coa.phases if coa else [],
                }
                fitness = coa_gen.evaluate_fitness(coa_gen.active_genome, telemetry)
                
                # Track best genome
                if fitness > overall_best_fitness:
                    overall_best_fitness = fitness
                    overall_best_genome = coa_gen.active_genome
                    self.best_fitness = overall_best_fitness
                    self.best_genome = overall_best_genome
            
            # Record episode results
            self.episode_rewards.append(total_reward)
            self.episode_successes.append(success)
            
            # Evolve generation
            self.generation = coa_gen.active_genome.generation if coa_gen.active_genome else self.generation
            
            # Adapt mutation rate
            self._adapt_mutation_rate()
            
            # Update elite genome for next episode
            elite = coa_gen.active_genome
            
            # Print dashboard
            self._print_dashboard(episode)
        
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