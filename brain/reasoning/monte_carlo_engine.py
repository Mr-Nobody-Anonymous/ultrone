# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Monte Carlo Forklift Engine - Palantir-Style Probabilistic Forecasting.

Phase 7 Upgrade: UCT (Upper Confidence Bound applied to Trees) selection
strategy across 50 forks. Instead of completely random friction injection,
bias the forks toward exploring high-uncertainty or high-reward battlefronts.

UCT Formula:  UCT = Q(s,a) + C * sqrt(ln(N_total) / n(s,a))

Where:
  Q(s,a) = average reward for this fork configuration
  n(s,a) = visit count for this fork configuration
  N_total = total visits across all configurations
  C = exploration constant (default sqrt(2))

Maintains zero-deepcopy, seed-based simulation reset to avoid memory
degradation.

Returns probabilistic metrics:
  - probability_of_success
  - expected_casualties (average effectiveness loss)
  - expected_resource_cost (fuel + ammo consumed)
  - conditional_success_rate (if supply node is destroyed)
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("Ultrone.Brain.Reasoning.MonteCarlo")


@dataclass
class MonteCarloResult:
    """Aggregated results from Monte Carlo forking (unchanged API)."""
    probability_of_success: float = 0.0
    expected_casualties: float = 0.0
    expected_resource_cost: float = 0.0
    conditional_success_rate: float = 0.0  # if supply node is destroyed
    num_forks: int = 0
    fitness_score: float = 0.0  # combined fitness for GA
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability_of_success": self.probability_of_success,
            "expected_casualties": self.expected_casualties,
            "expected_resource_cost": self.expected_resource_cost,
            "conditional_success_rate": self.conditional_success_rate,
            "num_forks": self.num_forks,
            "fitness_score": self.fitness_score,
        }


@dataclass
class ForkConfig:
    """
    Configuration for a single fork in the UCT tree.
    
    Each fork is identified by a combination of seed offset and friction
    configuration. UCT selects configurations that maximize exploration
    of high-uncertainty or high-reward regions.
    """
    fork_idx: int
    seed_offset: int          # How much to shift base_seed (0..49)
    friction_bias: float       # 0 = fully random, 1 = optimized for UCT
    friction_modifier: float   # Multiplier on base friction_level
    accuracy_noise: float      # Sigma for accuracy perturbation
    red_aggression: float      # Modifier for Red behavior unpredictability
    
    # UCT tracking
    visit_count: int = 0
    total_reward: float = 0.0
    
    @property
    def avg_reward(self) -> float:
        return self.total_reward / max(1, self.visit_count)
    
    def uct_score(self, total_visits: int, exploration_c: float) -> float:
        """
        Compute UCT score for this fork configuration.
        
        UCT = Q(s,a) + C * sqrt(ln(N_total) / n(s,a))
        
        For unvisited nodes, return infinity to guarantee exploration.
        """
        if self.visit_count == 0:
            return float("inf")
        exploitation = self.avg_reward
        if total_visits > 0:
            exploration = exploration_c * math.sqrt(
                math.log(max(1, total_visits)) / self.visit_count
            )
        else:
            exploration = exploration_c
        return exploitation + exploration


class MonteCarloForklift:
    """
    Forks the battlefield environment N times to evaluate a COA probabilistically.
    
    Phase 7: UCT-based fork configuration selection. Maintains a pool of
    ForkConfig objects and uses UCT to bias toward high-uncertainty or
    high-reward configurations.
    
    Uses seed-based reset instead of copy.deepcopy for memory efficiency.
    Injects friction: accuracy variance, sensor failures, unexpected red moves.
    """
    
    def __init__(self, num_forks: int = 50, friction_level: float = 0.15,
                 uct_exploration_c: float = math.sqrt(2.0)):
        """
        Args:
            num_forks: Number of parallel environment forks
            friction_level: Base probability of random friction events (0-1)
            uct_exploration_c: UCT exploration constant (default sqrt(2))
        """
        self.num_forks = num_forks
        self.friction_level = friction_level
        self.uct_exploration_c = uct_exploration_c
        
        # Phase 7: UCT tracking structures
        self._fork_pool: List[ForkConfig] = []
        self._total_uct_visits: int = 0
        self._uct_initialized: bool = False
    
    def _initialize_uct_pool(self) -> None:
        """
        Create a diverse pool of fork configurations.
        
        Each fork differs in:
        - seed_offset (0..num_forks-1) — ensures different random streams
        - friction_bias (0..1) — how much the fork leans toward UCT vs random
        - friction_modifier (0.5..2.0) — varying levels of injected friction
        - accuracy_noise (0.05..0.20) — varying sensor degradation
        - red_aggression (0.0..1.0) — varying Red unpredictability
        """
        self._fork_pool = []
        for i in range(self.num_forks):
            # Create diverse configurations covering the exploration space
            config = ForkConfig(
                fork_idx=i,
                seed_offset=i * 7,  # staggered seed offsets
                friction_bias=random.uniform(0.3, 1.0),
                friction_modifier=random.uniform(0.5, 2.0),
                accuracy_noise=random.uniform(0.05, 0.20),
                red_aggression=random.uniform(0.0, 1.0),
                visit_count=0,
                total_reward=0.0,
            )
            self._fork_pool.append(config)
        self._total_uct_visits = 0
        self._uct_initialized = True
    
    def _select_uct_forks(self) -> List[ForkConfig]:
        """
        Select fork configurations using UCT.
        
        - 5% of forks are purely random (exploration floor)
        - 95% are selected by highest UCT score
        
        For unvisited configurations, UCT returns infinity, guaranteeing
        that all configurations are visited at least once.
        """
        if not self._uct_initialized:
            self._initialize_uct_pool()
        
        # Count how many forks have been visited
        unvisited = [c for c in self._fork_pool if c.visit_count == 0]
        
        # If there are unvisited forks, prioritize exploring those first
        if unvisited:
            # Use round-robin to ensure all get explored
            selected = []
            # Take unvisited first (up to 95% of num_forks)
            num_explore = min(len(unvisited), max(1, int(self.num_forks * 0.95)))
            selected.extend(random.sample(unvisited, num_explore))
            
            # Fill remaining with UCT-based selection
            remaining = self.num_forks - len(selected)
            if remaining > 0:
                visited = [c for c in self._fork_pool if c.visit_count > 0]
                if visited:
                    # Sort by UCT score descending
                    visited.sort(
                        key=lambda c: c.uct_score(self._total_uct_visits, self.uct_exploration_c),
                        reverse=True
                    )
                    selected.extend(visited[:remaining])
                else:
                    # Fallback: random selection
                    selected.extend(random.sample(self._fork_pool, remaining))
            return selected
        
        # All forks have been visited at least once — use UCT
        # Sort by UCT score
        scored = sorted(
            self._fork_pool,
            key=lambda c: c.uct_score(self._total_uct_visits, self.uct_exploration_c),
            reverse=True
        )
        
        # 95% top UCT, 5% random exploration
        num_uct = int(self.num_forks * 0.95)
        num_random = self.num_forks - num_uct
        
        selected = scored[:num_uct]
        selected.extend(random.sample(self._fork_pool, num_random))
        
        return selected
    
    def _friction_from_config(self, config: ForkConfig) -> Dict[str, float]:
        """
        Derive friction parameters from a fork configuration.
        
        The config's parameters modulate the base friction_level to create
        diverse simulation outcomes.
        """
        # Base friction uses the fork's modifier
        effective_friction = self.friction_level * config.friction_modifier
        
        # Sensor failure probability scales with friction
        sensor_fail_prob = effective_friction * 0.33
        
        # Accuracy variance scales with accuracy_noise
        accuracy_variance = config.accuracy_noise
        
        # Red behavior unpredictability
        red_unpredictability = config.red_aggression
        
        return {
            "effective_friction": min(0.5, effective_friction),
            "sensor_fail_prob": min(0.3, sensor_fail_prob),
            "accuracy_variance": accuracy_variance,
            "red_unpredictability": red_unpredictability,
        }
    
    def evaluate_coa(self, env_class: type, coa_action: Optional[Dict],
                     red_action: Optional[Dict],
                     commander: Any = None,
                     base_seed: int = 42,
                     initial_red_position: Optional[Tuple[int, int]] = None) -> MonteCarloResult:
        """
        Evaluate a COA using Monte Carlo forking with UCT selection.
        
        Phase 7: Fork configurations are selected via UCT to bias toward
        high-uncertainty or high-reward battlefronts.
        
        Args:
            env_class: BattlefieldEnv class (not instance)
            coa_action: The COA action dict to evaluate
            red_action: Red Force action dict
            commander: The commander genome (for fitness tracking)
            base_seed: Base seed for reproducible forking
            initial_red_position: Fixed red position for consistency
            
        Returns:
            MonteCarloResult with aggregated probabilistic metrics (UNCHANGED)
        """
        # Phase 7: Select fork configurations via UCT
        selected_forks = self._select_uct_forks()
        
        successes = 0
        total_casualties = 0.0
        total_resource_cost = 0.0
        supply_node_lost_count = 0
        supply_node_lost_successes = 0
        
        for config in selected_forks:
            # Get friction parameters from UCT config
            friction_params = self._friction_from_config(config)
            effective_friction = friction_params["effective_friction"]
            sensor_fail_prob = friction_params["sensor_fail_prob"]
            accuracy_variance = friction_params["accuracy_variance"]
            red_unpredictability = friction_params["red_unpredictability"]
            
            # Create fresh environment with unique seed (no deepcopy needed)
            fork_seed = base_seed + config.seed_offset
            env = env_class()
            obs = env.reset(red_position=initial_red_position, seed=fork_seed)
            
            # Run the episode with friction from UCT config
            done = False
            step = 0
            fork_reward = 0.0
            fork_success = False
            fuel_consumed = 0.0
            effectiveness_loss = 0.0
            supply_node_lost = False
            
            while not done and step < env.MAX_STEPS:
                step += 1
                
                # --- Inject Sensor Friction (modulated by UCT config) ---
                if random.random() < sensor_fail_prob:
                    obs["radar_data"] = None
                    obs["visual_data"] = None
                
                # --- Inject Accuracy Friction (modulated by UCT config) ---
                coa = coa_action
                if coa and (coa.get("action") == "strike" or 
                           any(a.get("action") == "strike" for a in coa.get("swarm_fleet", []))):
                    if random.random() < effective_friction:
                        accuracy_mod = 1.0 + random.uniform(-accuracy_variance, accuracy_variance) * 2.0
                        if coa.get("type") == "swarm":
                            for asset_action in coa.get("swarm_fleet", []):
                                if asset_action.get("action") == "strike":
                                    asset_action["_accuracy_mod"] = accuracy_mod
                        else:
                            coa["_accuracy_mod"] = accuracy_mod
                
                # --- Inject Red Behavior Friction (modulated by UCT config) ---
                red = red_action
                if red and random.random() < effective_friction * red_unpredictability:
                    mutated_red = dict(red)
                    mutated_red["evade"] = not red.get("evade", False)
                    if random.random() < 0.5:
                        mutated_red["heading_offset"] = random.uniform(-90, 90)
                    red = mutated_red
                
                # Step the environment
                obs, reward, done, info = env.step(coa, red)
                fork_reward += reward
                
                fuel_consumed += info.get("fuel_consumed", 0.0)
                
                if info.get("supply_node_destroyed", False):
                    supply_node_lost = True
                
                if done and reward > 0:
                    fork_success = True
            
            # Update UCT tracking for this fork configuration
            config.visit_count += 1
            self._total_uct_visits += 1
            # Normalize fork_reward to [0,1] for UCT
            normalized_reward = max(0.0, min(1.0, (fork_reward + 100.0) / 200.0))
            config.total_reward += normalized_reward
            
            # Aggregate
            if fork_success:
                successes += 1
            
            total_fuel = env.get_total_fuel_consumed() if hasattr(env, 'get_total_fuel_consumed') else fuel_consumed
            total_resource_cost += total_fuel
            
            # Casualties: average effectiveness loss across all blue assets
            total_eff = 0.0
            count = 0
            for asset_list in env.blue_assets.values():
                for asset in asset_list:
                    total_eff += asset.get("effectiveness", 1.0)
                    count += 1
            avg_effectiveness = total_eff / max(1, count)
            effectiveness_loss = 1.0 - avg_effectiveness
            total_casualties += effectiveness_loss
            
            if supply_node_lost:
                supply_node_lost_count += 1
                if fork_success:
                    supply_node_lost_successes += 1
        
        # Aggregate results (identical to Phase 6 — no API change)
        prob_success = successes / max(1, self.num_forks)
        avg_casualties = total_casualties / max(1, self.num_forks)
        avg_resource_cost = total_resource_cost / max(1, self.num_forks)
        
        cond_success = 0.0
        if supply_node_lost_count > 0:
            cond_success = supply_node_lost_successes / supply_node_lost_count
        
        # Combined fitness score (identical weighting — no API change)
        fitness = (
            0.60 * prob_success
            - 0.20 * avg_casualties
            - 0.20 * (avg_resource_cost / 100.0)
        )
        fitness = max(0.0, min(1.0, fitness))
        
        return MonteCarloResult(
            probability_of_success=prob_success,
            expected_casualties=round(avg_casualties, 4),
            expected_resource_cost=round(avg_resource_cost, 2),
            conditional_success_rate=round(cond_success, 4),
            num_forks=self.num_forks,
            fitness_score=round(fitness, 4),
        )
    
    def get_uct_stats(self) -> Dict[str, Any]:
        """
        Get UCT statistics for debugging and monitoring.
        """
        if not self._uct_initialized:
            return {"initialized": False}
        
        visited = [c for c in self._fork_pool if c.visit_count > 0]
        unvisited = [c for c in self._fork_pool if c.visit_count == 0]
        
        return {
            "initialized": True,
            "total_visits": self._total_uct_visits,
            "visited_forks": len(visited),
            "unvisited_forks": len(unvisited),
            "avg_reward_across_visited": (
                sum(c.avg_reward for c in visited) / len(visited) if visited else 0.0
            ),
            "best_config": (
                max(visited, key=lambda c: c.avg_reward).fork_idx if visited else -1
            ),
            "worst_config": (
                min(visited, key=lambda c: c.avg_reward).fork_idx if visited else -1
            ),
        }


def test_monte_carlo():
    """Quick test of the Monte Carlo Forklift with UCT."""
    from sim.battlefield_env import BattlefieldEnv
    
    forklift = MonteCarloForklift(num_forks=10)
    result = forklift.evaluate_coa(
        BattlefieldEnv,
        {"action": "strike", "asset_type": "missiles"},
        {"evade": True, "ecm": False, "ecm_noise": 0.0, "target": None},
        base_seed=42,
        initial_red_position=(65, 50),
    )
    
    print("=== Monte Carlo Forklift Test (Phase 7: UCT) ===")
    print(f"  Probability of Success: {result.probability_of_success:.1%}")
    print(f"  Expected Casualties:    {result.expected_casualties:.3f}")
    print(f"  Expected Resource Cost: {result.expected_resource_cost:.1f}")
    print(f"  Conditional Success:    {result.conditional_success_rate:.1%}")
    print(f"  Fitness Score:          {result.fitness_score:.4f}")
    print(f"  Forks:                  {result.num_forks}")
    
    uct_stats = forklift.get_uct_stats()
    print(f"  UCT Visited Forks:      {uct_stats.get('visited_forks', 0)}/{uct_stats.get('unvisited_forks', 0) + uct_stats.get('visited_forks', 0)}")
    print(f"  UCT Avg Reward:         {uct_stats.get('avg_reward_across_visited', 0):.3f}")
    print("Test complete!")


if __name__ == "__main__":
    test_monte_carlo()

