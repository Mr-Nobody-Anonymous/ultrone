# Copyright (c) Ultrone Contributors. All rights reserved.
"""Lightweight 2D battlefield simulation environment."""

from __future__ import annotations

import logging
import sys
from typing import Dict, Tuple, Optional, Any
import numpy as np
import random

# Add parent directory for direct execution
if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("Ultrone.Sim.BattlefieldEnv")


class BattlefieldEnv:
    """Lightweight 2D grid-based battlefield simulation.
    
    OpenAI Gym-style interface for testing evolutionary COAs.
    """
    
    GRID_SIZE = 100  # 100x100 grid
    MAX_STEPS = 200
    
    def __init__(self):
        self.grid = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.float32)
        self.red_force = None
        self.blue_assets = {"drones": [], "jammers": [], "missiles": []}
        self.step_count = 0
        self.done = False
        self._perception_done = False
    
    def reset(self, red_position: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Reset environment and spawn forces.
        
        Args:
            red_position: Optional fixed position for Red Force (for testing)
        """
        self.grid.fill(0)
        self.step_count = 0
        self.done = False
        self._perception_done = False
        
        # Spawn Red Force - optionally at specified position for testing
        if red_position:
            red_pos = red_position
        else:
            red_pos = (random.randint(10, 90), random.randint(10, 90))
        
        self.red_force = {
            "position": red_pos,
            "speed": random.randint(1, 5),
            "type": random.choice(["armor", "artillery", "air_defense"]),
            "health": 100,
            "heading": random.uniform(0, 360),
        }
        
        # Spawn Blue Force assets (start closer to center)
        self.blue_assets = {
            "drones": [{"position": (50, 50), "ammo": 5, "range": 30}],
            "jammers": [{"position": (55, 50), "ammo": 3, "range": 20}],
            "missiles": [{"position": (60, 50), "ammo": 3, "range": 50}],
        }
        
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, Any]:
        """Get current state with real AI perception applied."""
        # Late import to avoid circular dependency
        from brain.perception.specialized_analyzers import RadarAI, VisualAI
        
        observation = {
            "grid": self.grid.copy(),
            "red_force": dict(self.red_force),
            "blue_assets": {k: list(v) for k, v in self.blue_assets.items()},
            "radar_data": None,
            "visual_data": None,
        }
        
        # Simulate radar return and apply RadarAI
        if not self._perception_done:
            try:
                radar_ai = RadarAI()
                # Simulate radar signal based on red force speed
                radar_signal = np.random.randn(100) * self.red_force["speed"]
                radar_result = radar_ai.analyze(radar_signal, {"speed": self.red_force["speed"]})
                observation["radar_data"] = radar_result
            except Exception as e:
                logger.warning(f"RadarAI failed: {e}")
                observation["radar_data"] = {"threat_indicator": 0.5, "classification": "contact"}
            
            # Simulate visual detection
            try:
                visual_ai = VisualAI()
                # Simulate image data (no real file, use mock)
                visual_result = visual_ai.analyze(None, {"detected_objects": [self.red_force["type"]]})
                observation["visual_data"] = visual_result
            except Exception as e:
                logger.warning(f"VisualAI failed: {e}")
                observation["visual_data"] = {"threat_indicator": 0.5, "classification": "contact"}
            
            self._perception_done = True
        
        return observation
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between positions."""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def step(self, coa_action: Optional[Dict] = None) -> Tuple[Dict, float, bool, Dict]:
        """Apply COA and advance simulation.
        
        Args:
            coa_action: Dict with action details:
                {"action": "strike"|"jam"|"move", "asset_type": "drone", "target": (x,y)}
                
        Returns:
            observation, reward, done, info
        """
        self.step_count += 1
        reward = 0.0
        info = {"roe_violation": False, "action_applied": False}
        
        # Apply COA action if provided
        if coa_action:
            action = coa_action.get("action", "observe")
            asset_type = coa_action.get("asset_type", "drone")
            
            if action == "strike" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets and assets[0]["ammo"] > 0:
                    # Check range
                    asset_pos = assets[0]["position"]
                    target_pos = self.red_force["position"]
                    distance = self._distance(asset_pos, target_pos)
                    
                    if distance <= assets[0]["range"]:
                        # Hit!
                        self.red_force["health"] -= 50
                        assets[0]["ammo"] -= 1
                        reward += 25  # Partial reward for hit
                        info["action_applied"] = True
                        
                        if self.red_force["health"] <= 0:
                            reward += 100  # Kill bonus
                            self.done = True
                    else:
                        # Out of range - ROE violation
                        reward -= 500  # Heavy penalty for ROE violation
                        info["roe_violation"] = True
                        info["action_applied"] = False
                        assets[0]["ammo"] -= 1  # Still consumes ammo
            
            elif action == "jam" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets and assets[0]["ammo"] > 0:
                    assets[0]["ammo"] -= 1
                    info["action_applied"] = True
            
            elif action == "move" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets:
                    new_pos = coa_action.get("target", (50, 50))
                    # Validate position is within grid
                    if isinstance(new_pos, (list, tuple)) and len(new_pos) == 2:
                        assets[0]["position"] = (
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[1])))
                        )
                        info["action_applied"] = True
        
        # Red Force moves randomly
        if self.red_force and self.red_force["health"] > 0:
            dx = random.randint(-self.red_force["speed"], self.red_force["speed"])
            dy = random.randint(-self.red_force["speed"], self.red_force["speed"])
            
            new_x = max(0, min(self.GRID_SIZE - 1, self.red_force["position"][0] + dx))
            new_y = max(0, min(self.GRID_SIZE - 1, self.red_force["position"][1] + dy))
            self.red_force["position"] = (new_x, new_y)
        
        # Time penalty
        reward -= 1.0
        
        # Check for destruction
        if self.red_force["health"] <= 0:
            reward += 100
            self.done = True
        
        # Max steps reached
        if self.step_count >= self.MAX_STEPS:
            self.done = True
        
        return self._get_observation(), reward, self.done, info
    
    def render(self) -> str:
        """Return ASCII representation of battlefield."""
        grid_str = [["." for _ in range(10)] for _ in range(10)]
        
        # Scale positions to 10x10 view
        fx, fy = self.red_force["position"]
        grid_str[fy // 10][fx // 10] = "R"
        
        for drone in self.blue_assets["drones"]:
            x, y = drone["position"]
            grid_str[y // 10][x // 10] = "D"
        
        return "\n" + "\n".join("".join(row) for row in grid_str)


def test_battlefield_env():
    """Quick test of the battlefield environment."""
    env = BattlefieldEnv()
    # Spawn Red Force close to Blue assets for testing
    obs = env.reset(red_position=(65, 50))
    print(f"Initial Red Force: {obs['red_force']}")
    print(f"Blue Assets: {obs['blue_assets']}")
    print(f"Radar Detection: {obs.get('radar_data')}")
    print(f"Visual Detection: {obs.get('visual_data')}")
    
    # Simulate a strike
    for _ in range(5):
        obs, reward, done, info = env.step({"action": "strike", "asset_type": "missiles"})
        print(f"Step: reward={reward:.1f}, done={done}, red_health={obs['red_force']['health']}, roe={info['roe_violation']}")
        if done:
            break
    
    print(env.render())
    print(f"Final observation keys: {list(obs.keys())}")
    print("Battlefield environment test complete!")


def test_with_evolutionary_coagen():
    """Test environment with evolutionary COA generation."""
    from brain.reasoning.evolutionary_coagen import EvolutionaryCOAGenerator
    from brain.reasoning.course_of_action import Action
    
    env = BattlefieldEnv()
    
    # Run a few episodes
    total_reward = 0
    for episode in range(3):
        obs = env.reset(red_position=(65, 50))
        
        # Generate COA using evolutionary algorithm
        generator = EvolutionaryCOAGenerator()
        coa = generator.generate_evolved_coa(obs, {})
        
        print(f"Episode {episode}: Generated COA: {coa.name if coa else 'None'}")
        print(f"  COA phases: {coa.phases if coa else 'None'}")
        print(f"  COA novelty: {coa.novelty_score if coa else 0}")
        
        # Apply the COA - map phases to action strings
        if coa and coa.phases:
            # Find first actionable phase
            first_action = None
            for phase in coa.phases:
                if phase in ["strike", "jam"]:
                    first_action = phase
                    break
            
            if first_action == "strike":
                obs, reward, done, info = env.step({"action": "strike", "asset_type": "missiles"})
                total_reward += reward
                print(f"  Applied strike: reward={reward:.1f}, done={done}, roe={info['roe_violation']}")
            elif first_action == "jam":
                obs, reward, done, info = env.step({"action": "jam", "asset_type": "jammers"})
                total_reward += reward
                print(f"  Applied jam: reward={reward:.1f}")
        
        if done:
            break
    
    print(f"\nTotal reward across episodes: {total_reward:.1f}")
    print("Evolutionary COAGenerator integration test complete!")


if __name__ == "__main__":
    test_battlefield_env()
    print("\n--- Testing with Evolutionary COAGenerator ---")
    test_with_evolutionary_coagen()
