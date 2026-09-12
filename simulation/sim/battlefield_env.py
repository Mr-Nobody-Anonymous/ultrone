# Copyright (c) Ultrone Contributors. All rights reserved.
"""Lightweight 2D battlefield simulation environment."""

from __future__ import annotations

import logging
import sys
from typing import Dict, Tuple, Optional, Any, List
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
    
    == Supply Nodes, Fuel & Resupply (Phase 6) ==
    Two fixed supply nodes exist: BLUE_SUPPLY (near friendly base) and RED_SUPPLY.
    - Each asset has a fuel level (0.0–1.0); fuel depletes each step.
    - The 'resupply' action returns an asset to its nearest friendly supply node
      when distance < PROXIMITY_THRESHOLD. If the asset is farther than the
      threshold, the action is **rejected** with a warning in info.
    - If a supply node is destroyed, a one-time 20% global effectiveness penalty
      is applied. Friendly assets may dynamically re-link to the other surviving
      supply node (if any).
    """
    
    GRID_SIZE = 100  # 100x100 grid
    MAX_STEPS = 200
    
    # Supply node positions (grid coordinates)
    BLUE_SUPPLY_COORDS: Tuple[int, int] = (20, 50)
    RED_SUPPLY_COORDS: Tuple[int, int] = (80, 50)
    
    # Proximity threshold for resupply (grid units)
    PROXIMITY_THRESHOLD: int = 10
    
    # Fuel constants
    FUEL_INITIAL: float = 1.0
    FUEL_DECAY_PER_MOVE: float = 0.02
    FUEL_DECAY_PER_IDLE: float = 0.01
    FUEL_DECAY_PER_STRIKE: float = 0.03
    FUEL_REFILL_RATE: float = 1.0  # instant on resupply
    
    # Supply node destruction penalty (one-time)
    SUPPLY_NODE_DESTROY_PENALTY: float = 0.20
    
    def __init__(self):
        self.grid = np.zeros((self.GRID_SIZE, self.GRID_SIZE), dtype=np.float32)
        self.red_force = None
        self.blue_assets: Dict[str, List[Dict[str, Any]]] = {
            "drones": [],
            "jammers": [],
            "missiles": [],
        }
        self.step_count = 0
        self.done = False
        self._perception_done = False
        
        # Phase 6: Supply node state
        self.supply_nodes: Dict[str, Dict[str, Any]] = {}
        self._supply_penalty_applied: bool = False
    
    def reset(self, red_position: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Reset environment and spawn forces.
        
        Args:
            red_position: Optional fixed position for Red Force (for testing)
        """
        self.grid.fill(0)
        self.step_count = 0
        self.done = False
        self._perception_done = False
        self._supply_penalty_applied = False
        
        # Phase 6: Initialize supply nodes
        self.supply_nodes = {
            "blue_supply": {
                "position": self.BLUE_SUPPLY_COORDS,
                "team": "blue",
                "alive": True,
                "health": 100,
                "capacity": 100,
            },
            "red_supply": {
                "position": self.RED_SUPPLY_COORDS,
                "team": "red",
                "alive": True,
                "health": 100,
                "capacity": 100,
            },
        }
        
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
            "fuel": self.FUEL_INITIAL,  # Phase 6
            "linked_supply": "red_supply",
        }
        
        # Spawn Blue Force assets (start closer to center)
        self.blue_assets = {
            "drones": [{
                "position": (50, 50),
                "ammo": 5,
                "range": 30,
                "fuel": self.FUEL_INITIAL,
                "linked_supply": "blue_supply",
            }],
            "jammers": [{
                "position": (55, 50),
                "ammo": 3,
                "range": 20,
                "fuel": self.FUEL_INITIAL,
                "linked_supply": "blue_supply",
            }],
            "missiles": [{
                "position": (60, 50),
                "ammo": 3,
                "range": 50,
                "fuel": self.FUEL_INITIAL,
                "linked_supply": "blue_supply",
            }],
        }
        
        # ECM state tracking
        self._ecm_active = False
        self._ecm_noise = 0.0
        
        return self._get_observation()
    
    def _get_observation(self) -> Dict[str, Any]:
        """Get current state with real AI perception applied."""
        # Late import to avoid circular dependency
        from brain.perception.specialized_analyzers import RadarAI, VisualAI
        
        observation: Dict[str, Any] = {
            "grid": self.grid.copy(),
            "red_force": dict(self.red_force),
            "blue_assets": {k: list(v) for k, v in self.blue_assets.items()},
            "radar_data": None,
            "visual_data": None,
            # Phase 6: Expose supply node state
            "supply_nodes": {
                sid: {
                    "position": sn["position"],
                    "team": sn["team"],
                    "alive": sn["alive"],
                    "health": sn["health"],
                }
                for sid, sn in self.supply_nodes.items()
            },
            "supply_penalty_active": self._supply_penalty_applied,
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
                    if isinstance(observation["radar_data"], dict):
                        observation["radar_data"]["threat_indicator"] = max(
                            0.0,
                            observation["radar_data"].get("threat_indicator", 0.5) - noise,
                        )
            if observation["visual_data"] is not None:
                if random.random() < noise:
                    observation["visual_data"] = None
        
        return observation
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between positions."""
        return np.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
    
    def _can_resupply(self, asset_pos: Tuple[int, int], supply_node_id: str) -> Tuple[bool, str]:
        """Check whether an asset is within proximity of its linked supply node.
        
        Returns:
            (can_resupply, reason) where reason explains denial if not possible.
        """
        node = self.supply_nodes.get(supply_node_id)
        if node is None:
            return False, f"Supply node '{supply_node_id}' does not exist."
        if not node["alive"]:
            return False, f"Supply node '{supply_node_id}' is destroyed."
        dist = self._distance(asset_pos, node["position"])
        if dist > self.PROXIMITY_THRESHOLD:
            return (
                False,
                f"Asset too far from '{supply_node_id}' (distance={dist:.1f}, "
                f"threshold={self.PROXIMITY_THRESHOLD}). Auto-route not supported; "
                f"move closer first.",
            )
        return True, "Within resupply range."
    
    def _consume_fuel(
        self,
        asset: Dict[str, Any],
        action_type: str,
        asset_type: str,
        is_red: bool = False,
    ) -> float:
        """Reduce fuel for an asset based on action type. Returns fuel consumed."""
        if action_type == "move":
            decay = self.FUEL_DECAY_PER_MOVE
        elif action_type in ("strike", "attack"):
            decay = self.FUEL_DECAY_PER_STRIKE
        else:
            decay = self.FUEL_DECAY_PER_IDLE
        
        consumed = min(asset.get("fuel", self.FUEL_INITIAL), decay)
        asset["fuel"] = max(0.0, asset.get("fuel", self.FUEL_INITIAL) - decay)
        return consumed
    
    def _process_supply_node_destruction(self, node_id: str) -> None:
        """Handle the destruction of a supply node.
        
        - Applies a one-time 20% global effectiveness penalty (if not already applied).
        - Re-links friendly assets to the other surviving supply node if available.
        """
        node = self.supply_nodes.get(node_id)
        if node is None or not node["alive"]:
            return
        
        node["alive"] = False
        team = node["team"]
        logger.info(f"Supply node '{node_id}' (team={team}) has been destroyed.")
        
        # Determine the other supply node for this team
        other_node_id: Optional[str] = None
        for sid, sn in self.supply_nodes.items():
            if sid != node_id and sn["team"] == team and sn["alive"]:
                other_node_id = sid
                break
        
        # One-time 20% penalty for loss of supply
        if not self._supply_penalty_applied:
            self._supply_penalty_applied = True
            logger.info(
                f"Supply node destruction: one-time {self.SUPPLY_NODE_DESTROY_PENALTY:.0%} "
                f"effectiveness penalty applied."
            )
        
        # Re-link friendly assets to the other surviving node
        if other_node_id:
            if team == "blue":
                for asset_list in self.blue_assets.values():
                    for asset in asset_list:
                        if asset.get("linked_supply") == node_id:
                            asset["linked_supply"] = other_node_id
                            logger.debug(f"Asset re-linked from '{node_id}' to '{other_node_id}'.")
            elif team == "red" and self.red_force:
                if self.red_force.get("linked_supply") == node_id:
                    self.red_force["linked_supply"] = other_node_id
                    logger.debug(f"Red force re-linked from '{node_id}' to '{other_node_id}'.")
    
    def step(
        self,
        coa_action: Optional[Dict] = None,
        red_action: Optional[Dict] = None,
    ) -> Tuple[Dict, float, bool, Dict]:
        """Apply COA and advance simulation.
        
        Args:
            coa_action: Legacy single action or swarm hierarchical COA:
                Legacy: {"action": "strike"|"jam"|"move"|"resupply", "asset_type": "drone", "target": (x,y)}
                Swarm: {"type": "swarm", "swarm_fleet": [...], "commander_genome": {...}}
                
                **Resupply action behaviour (Phase 6)**:
                If the asset's distance to its linked supply node is >= PROXIMITY_THRESHOLD,
                the action is **rejected** (fuel not restored) and the rejection reason
                is placed in info['resupply_rejected']. The asset must first move within
                range, then issue the "resupply" command.
                
            red_action: Red Force action from RedForceGenome:
                {"evade": bool, "ecm": bool, "target": (x,y) or None}
                
        Returns:
            observation, reward, done, info
        """
        self.step_count += 1
        reward = 0.0
        info: Dict[str, Any] = {
            "roe_violation": False,
            "action_applied": False,
            "swarm_collisions": 0,
            "ecm_active": False,
            # Phase 6 fields
            "fuel_consumed": 0.0,
            "resupply_rejected": None,
            "resupply_applied": False,
            "supply_node_destroyed": None,
            "supply_penalty_active": self._supply_penalty_applied,
        }
        
        # ---- Swarm hierarchical COA resolution ----
        if coa_action and coa_action.get("type") == "swarm":
            fleet = coa_action.get("swarm_fleet", [])
            applied_actions = 0
            collision_count = 0
            occupied_cells: Dict[Tuple[int, int], int] = {}
            total_fuel_consumed = 0.0
            
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
                
                # -- Consume fuel for any action --
                total_fuel_consumed += self._consume_fuel(asset, action, asset_type)
                
                if action == "move" and target is not None:
                    if isinstance(target, (list, tuple)) and len(target) == 2:
                        new_pos = (
                            int(max(0, min(self.GRID_SIZE - 1, target[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, target[1]))),
                        )
                        asset["position"] = new_pos
                        applied_actions += 1
                        cell = new_pos
                        occupied_cells[cell] = occupied_cells.get(cell, 0) + 1
                
                elif action == "resupply":
                    linked = asset.get("linked_supply", "blue_supply")
                    can_resupply, reason = self._can_resupply(asset["position"], linked)
                    if can_resupply:
                        asset["fuel"] = self.FUEL_REFILL_RATE
                        applied_actions += 1
                        info["resupply_applied"] = True
                    else:
                        info["resupply_rejected"] = reason
                        # Fuel is still consumed for attempting a denied resupply
                        reward -= 1.0  # small penalty for wasted action
                
                elif action == "strike":
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
                
                elif action == "jam":
                    if asset.get("ammo", 0) > 0:
                        asset["ammo"] -= 1
                        applied_actions += 1
            
            # Collision detection
            for cell, count in occupied_cells.items():
                if count > 1:
                    collision_count += count - 1
            info["action_applied"] = applied_actions > 0
            info["swarm_collisions"] = collision_count
            info["fuel_consumed"] = total_fuel_consumed
            if collision_count > 0:
                reward -= 50 * collision_count
        
        # ---- Legacy single-action mode ----
        elif coa_action:
            action = coa_action.get("action", "observe")
            asset_type = coa_action.get("asset_type", "drone")
            
            if asset_type in self.blue_assets:
                assets = self.blue_assets[asset_type]
                if not assets:
                    pass
                elif action == "resupply":
                    asset = assets[0]
                    linked = asset.get("linked_supply", "blue_supply")
                    can_resupply, reason = self._can_resupply(asset["position"], linked)
                    info["fuel_consumed"] += self._consume_fuel(asset, action, asset_type)
                    if can_resupply:
                        asset["fuel"] = self.FUEL_REFILL_RATE
                        info["action_applied"] = True
                        info["resupply_applied"] = True
                    else:
                        info["resupply_rejected"] = reason
                        reward -= 1.0
                
                elif action == "strike":
                    asset = assets[0]
                    info["fuel_consumed"] += self._consume_fuel(asset, action, asset_type)
                    if asset["ammo"] > 0:
                        asset_pos = asset["position"]
                        target_pos = self.red_force["position"]
                        distance = self._distance(asset_pos, target_pos)
                        if distance <= assets[0]["range"]:
                            self.red_force["health"] -= 50
                            asset["ammo"] -= 1
                            reward += 25
                            info["action_applied"] = True
                            if self.red_force["health"] <= 0:
                                reward += 100
                                self.done = True
                        else:
                            reward -= 500
                            info["roe_violation"] = True
                            info["action_applied"] = False
                            asset["ammo"] -= 1
                
                elif action == "jam":
                    asset = assets[0]
                    info["fuel_consumed"] += self._consume_fuel(asset, action, asset_type)
                    if asset["ammo"] > 0:
                        asset["ammo"] -= 1
                        info["action_applied"] = True
                
                elif action == "move":
                    asset = assets[0]
                    info["fuel_consumed"] += self._consume_fuel(asset, action, asset_type)
                    new_pos = coa_action.get("target", (50, 50))
                    if isinstance(new_pos, (list, tuple)) and len(new_pos) == 2:
                        assets[0]["position"] = (
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, new_pos[1]))),
                        )
                        info["action_applied"] = True
                else:
                    # observe / idle – still consume idle fuel
                    asset = assets[0]
                    info["fuel_consumed"] += self._consume_fuel(asset, action, asset_type)
        
        # ---- Consume fuel for Red Force ----
        if self.red_force and self.red_force["health"] > 0:
            red_action_type = "move" if (red_action and red_action.get("evade")) else "observe"
            info["fuel_consumed"] += self._consume_fuel(
                self.red_force, red_action_type, "red", is_red=True,
            )
        
        # ---- Resolve Red Force action ----
        if red_action:
            ecm_active = bool(red_action.get("ecm", False))
            self._ecm_active = ecm_active
            self._ecm_noise = red_action.get("ecm_noise", 0.3) if ecm_active else 0.0
            info["ecm_active"] = self._ecm_active
            
            if self.red_force and self.red_force["health"] > 0:
                if red_action.get("evade", False):
                    self.red_force["heading"] = (
                        self.red_force["heading"] + random.uniform(-45, 45)
                    ) % 360
                    burst = random.randint(0, 2)
                    new_x = max(
                        0,
                        min(
                            self.GRID_SIZE - 1,
                            int(
                                self.red_force["position"][0]
                                + random.uniform(-1, 1) * (self.red_force["speed"] + burst)
                            ),
                        ),
                    )
                    new_y = max(
                        0,
                        min(
                            self.GRID_SIZE - 1,
                            int(
                                self.red_force["position"][1]
                                + random.uniform(-1, 1) * (self.red_force["speed"] + burst)
                            ),
                        ),
                    )
                    self.red_force["position"] = (new_x, new_y)
                if red_action.get("target") is not None:
                    tgt = red_action.get("target")
                    if isinstance(tgt, (list, tuple)) and len(tgt) == 2:
                        self.red_force["position"] = (
                            int(max(0, min(self.GRID_SIZE - 1, tgt[0]))),
                            int(max(0, min(self.GRID_SIZE - 1, tgt[1]))),
                        )
        else:
            self._ecm_active = False
            self._ecm_noise = 0.0
            
            # Default random walk if no red action
            if self.red_force and self.red_force["health"] > 0:
                dx = random.randint(-self.red_force["speed"], self.red_force["speed"])
                dy = random.randint(-self.red_force["speed"], self.red_force["speed"])
                new_x = max(
                    0,
                    min(self.GRID_SIZE - 1, self.red_force["position"][0] + dx),
                )
                new_y = max(
                    0,
                    min(self.GRID_SIZE - 1, self.red_force["position"][1] + dy),
                )
                self.red_force["position"] = (new_x, new_y)
        
        # ---- Time penalty ----
        reward -= 1.0
        
        # ---- Apply supply node destruction penalty (one-time) ----
        if self._supply_penalty_applied:
            # Reduce overall reward as one-time penalty (applied only once after destruction)
            reward -= 20.0 * self.SUPPLY_NODE_DESTROY_PENALTY  # -4.0
        
        # ---- Check for destruction ----
        if self.red_force["health"] <= 0:
            reward += 100
            self.done = True
        
        # ---- Max steps reached ----
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
    
    def render_ascii_map(self) -> str:
        """
        Generate top-down text grid for LLM/VLM commanders.
        
        Shows terrain, Red Force (R), Blue Drones (D), Blue Missiles (M),
        ECM zones (E), Blue Supply Node (B), Red Supply Node (S).
        Uses 20x20 scaled view from 100x100 grid.
        """
        width, height = 20, 20
        grid_str = [["." for _ in range(width)] for _ in range(height)]
        
        # Supply nodes
        for sid, sn in self.supply_nodes.items():
            if sn["alive"]:
                sx, sy = sn["position"]
                marker = "B" if sn["team"] == "blue" else "S"
                grid_str[min(height - 1, sy // 5)][min(width - 1, sx // 5)] = marker
        
        # Red Force
        if self.red_force:
            rx, ry = self.red_force["position"]
            grid_str[min(height - 1, ry // 5)][min(width - 1, rx // 5)] = "R"
        
        # Blue assets
        for drone in self.blue_assets.get("drones", []):
            x, y = drone["position"]
            grid_str[min(height - 1, y // 5)][min(width - 1, x // 5)] = "D"
        
        for missile in self.blue_assets.get("missiles", []):
            x, y = missile["position"]
            grid_str[min(height - 1, y // 5)][min(width - 1, x // 5)] = "M"
        
        for jammer in self.blue_assets.get("jammers", []):
            x, y = jammer["position"]
            grid_str[min(height - 1, y // 5)][min(width - 1, x // 5)] = "J"
        
        # ECM zones (if active, mark area around Red)
        if getattr(self, "_ecm_active", False):
            if self.red_force:
                rx, ry = self.red_force["position"]
                cx = min(width - 1, rx // 5)
                cy = min(height - 1, ry // 5)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            if grid_str[ny][nx] == ".":
                                grid_str[ny][nx] = "E"
        
        return "\n" + "\n".join("".join(row) for row in grid_str)


def test_battlefield_env():
    """Quick test of the battlefield environment."""
    env = BattlefieldEnv()
    obs = env.reset(red_position=(65, 50))
    print(f"Initial Red Force: {obs['red_force']}")
    print(f"Blue Assets: {obs['blue_assets']}")
    print(f"Supply Nodes: {obs['supply_nodes']}")
    
    # Test resupply rejection when far
    obs, reward, done, info = env.step({"action": "resupply", "asset_type": "missiles"})
    print(f"Resupply (far): rejected={info['resupply_rejected']}, reward={reward:.1f}")
    
    # Move missile closer to supply node
    bsp = env.BLUE_SUPPLY_COORDS
    obs, reward, done, info = env.step({"action": "move", "asset_type": "missiles", "target": (bsp[0] + 3, bsp[1])})
    
    # Try resupply again
    obs, reward, done, info = env.step({"action": "resupply", "asset_type": "missiles"})
    print(f"Resupply (close): applied={info['resupply_applied']}, fuel={obs['blue_assets']['missiles'][0]['fuel']}")
    
    # Test supply node destruction
    env._process_supply_node_destruction("blue_supply")
    print(f"Supply penalty applied: {env._supply_penalty_applied}")
    print(f"Missile re-linked to: {obs['blue_assets']['missiles'][0].get('linked_supply', 'unknown')}")
    
    # Simulate a strike
    env.reset(red_position=(65, 50))
    for _ in range(5):
        obs, reward, done, info = env.step({"action": "strike", "asset_type": "missiles"})
        print(f"Step: reward={reward:.1f}, done={done}, red_health={obs['red_force']['health']}, fuel_consumed={info.get('fuel_consumed', 0):.3f}")
        if done:
            break
    
    print(env.render())
    print("Battlefield environment test complete!")


def test_with_evolutionary_coagen():
    """Test environment with evolutionary COA generation."""
    from brain.reasoning.evolutionary_coagen import EvolutionaryCOAGenerator
    from brain.reasoning.course_of_action import Action
    
    env = BattlefieldEnv()
    
    total_reward = 0
    for episode in range(3):
        obs = env.reset(red_position=(65, 50))
        
        generator = EvolutionaryCOAGenerator()
        coa = generator.generate_evolved_coa(obs, {})
        
        print(f"Episode {episode}: Generated COA: {coa.name if coa else 'None'}")
        print(f"  COA phases: {coa.phases if coa else 'None'}")
        print(f"  COA novelty: {coa.novelty_score if coa else 0}")
        
        if coa and coa.phases:
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

