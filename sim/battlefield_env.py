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
        
        # ECM state tracking
        self._ecm_active = False
        self._ecm_noise = 0.0
        
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
        
        # Apply ECM noise if active
        if getattr(self, "_ecm_active", False) and getattr(self, "_ecm_noise", 0.0) > 0:
            noise = self._ecm_noise
            if observation["radar_data"] is not None:
                if random.random() < noise:
                    observation["radar_data"] = None
                else:
                    # Degrade radar confidence proportional to noise strength
                    if isinstance(observation["radar_data"], dict):
                        observation["radar_data"]["threat_indicator"] = max(0.0, observation["radar_data"].get("threat_indicator", 0.5) - noise)
            if observation["visual_data"] is not None:
                if random.random() < noise:
                    observation["visual_data"] = None
        
        return observation
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between positions."""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def step(self, coa_action: Optional[Dict] = None, red_action: Optional[Dict] = None) -> Tuple[Dict, float, bool, Dict]:
        """Apply COA and advance simulation.
        
        Args:
            coa_action: Legacy single action or swarm hierarchical COA:
                Legacy: {"action": "strike"|"jam"|"move", "asset_type": "drone", "target": (x,y)}
                Swarm: {
                    "type": "swarm",
                    "swarm_fleet": [
                        {"asset_type": "drone", "action": "move", "target": (x,y)},
                        ...
                    ],
                    "commander_genome": {...}
                }
            red_action: Red Force action from RedForceGenome:
                {
                    "evade": bool,
                    "ecm": bool,
                    "target": (x,y) or None
                }
                
        Returns:
            observation, reward, done, info
        """
        self.step_count += 1
        reward = 0.0
        info = {"roe_violation": False, "action_applied": False, "swarm_collisions": 0, "ecm_active": False}
        
        # Swarm hierarchical COA resolution
        if coa_action and coa_action.get("type") == "swarm":
            fleet = coa_action.get("swarm_fleet", [])
            applied_actions = 0
            collision_count = 0
            occupied_cells = {}
            
            # First pass: resolve all fleet actions and detect collisions
            for asset_action in fleet:
                asset_type = asset_action.get("asset_type", "drone")
                action = asset_action.get("action", "observe")
                target = asset_action.get("target")
                
                if asset_type not in self.blue_assets or not self.blue_assets[asset_type]:
                    continue
                
                assets = self.blue_assets[asset_type]
                if not assets:
                    continue
                
                asset = assets[0]
                
                if action == "move" and target is not None:
                    if isinstance(target, (list, tuple)) and len(target) == 2:
                        new_pos = (
                            int(max(0, min(self.GRID_SIZE - 1, target[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, target[1])))
                        )
                        asset["position"] = new_pos
                        applied_actions += 1
                        
                        # Track occupied cells for collision detection
                        cell = new_pos
                        occupied_cells[cell] = occupied_cells.get(cell, 0) + 1
                
                elif action == "strike" and asset_type in self.blue_assets:
                    if asset.get("ammo", 0) > 0:
                        asset_pos = asset["position"]
                        target_pos = self.red_force["position"]
                        distance = self._distance(asset_pos, target_pos)
                        
                        if distance <= asset.get("range", 9999):
                            self.red_force["health"] -= 50
                            asset["ammo"] -= 1
                            reward += 25
                            applied_actions += 1
                            
                            if self.red_force["health"] <= 0:
                                reward += 100
                                self.done = True
                        else:
                            reward -= 500
                            info["roe_violation"] = True
                            asset["ammo"] -= 1
                
                elif action == "jam" and asset_type in self.blue_assets:
                    if asset.get("ammo", 0) > 0:
                        asset["ammo"] -= 1
                        applied_actions += 1
            
            # Count collisions (multiple assets in same cell)
            for cell, count in occupied_cells.items():
                if count > 1:
                    collision_count += (count - 1)
            
            info["action_applied"] = applied_actions > 0
            info["swarm_collisions"] = collision_count
            
            # Swarm collision penalty: discourage stacking
            if collision_count > 0:
                reward -= 50 * collision_count
        
        # Legacy single-action mode
        elif coa_action:
            action = coa_action.get("action", "observe")
            asset_type = coa_action.get("asset_type", "drone")
            
            if action == "strike" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets and assets[0]["ammo"] > 0:
                    asset_pos = assets[0]["position"]
                    target_pos = self.red_force["position"]
                    distance = self._distance(asset_pos, target_pos)
                    
                    if distance <= assets[0]["range"]:
                        self.red_force["health"] -= 50
                        assets[0]["ammo"] -= 1
                        reward += 25
                        info["action_applied"] = True
                        
                        if self.red_force["health"] <= 0:
                            reward += 100
                            self.done = True
                    else:
                        reward -= 500
                        info["roe_violation"] = True
                        info["action_applied"] = False
                        assets[0]["ammo"] -= 1
            
            elif action == "jam" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets and assets[0]["ammo"] > 0:
                    assets[0]["ammo"] -= 1
                    info["action_applied"] = True
            
            elif action == "move" and asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if assets:
                    new_pos = coa_action.get("target", (50, 50))
                    if isinstance(new_pos, (list, tuple)) and len(new_pos) == 2:
                        assets[0]["position"] = (
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[1])))
                        )
                        info["action_applied"] = True
        
        # Resolve Red Force action if provided
        if red_action:
            ecm_active = bool(red_action.get("ecm", False))
            self._ecm_active = ecm_active
            self._ecm_noise = red_action.get("ecm_noise", 0.3) if ecm_active else 0.0
            info["ecm_active"] = self._ecm_active
            
            if self.red_force and self.red_force["health"] > 0:
                if red_action.get("evade", False):
                    self.red_force["heading"] = (self.red_force["heading"] + random.uniform(-45, 45)) % 360
                    burst = random.randint(0, 2)
                    new_x = max(0, min(self.GRID_SIZE - 1, int(self.red_force["position"][0] + random.uniform(-1, 1) * (self.red_force["speed"] + burst))))
                    new_y = max(0, min(self.GRID_SIZE - 1, int(self.red_force["position"][1] + random.uniform(-1, 1) * (self.red_force["speed"] + burst))))
                    self.red_force["position"] = (new_x, new_y)
                if red_action.get("target") is not None:
                    tgt = red_action.get("target")
                    if isinstance(tgt, (list, tuple)) and len(tgt) == 2:
                        self.red_force["position"] = (
                            int(max(0, min(self.GRID_SIZE - 1, tgt[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, tgt[1])))
                        )
        else:
            self._ecm_active = False
            self._ecm_noise = 0.0
            
            # Default random walk if no red action
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
