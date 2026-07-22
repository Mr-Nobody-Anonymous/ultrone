# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Battlefield Environment with Operational Readiness Ontology
Phase 6: Supply nodes, fuel, effectiveness, resupply mechanics

Designed for multi-agent simulation with full operational readiness modeling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import random
import math

logger = logging.getLogger("Ultrone.Sim.BattlefieldEnv")


@dataclass
class SupplyNode:
    """Logistics hub that sustains linked assets"""
    node_id: str
    position: Tuple[int, int]
    health: float = 100.0
    assets_linked: List[str] = field(default_factory=list)
    team: str = "unknown"
    
    @property
    def is_destroyed(self) -> bool:
        return self.health <= 0
    
    def is_operational(self) -> bool:
        return self.health > 0
    
    def take_damage(self, damage: float) -> float:
        """Apply damage and return actual damage dealt."""
        dealt = min(self.health, damage)
        self.health -= dealt
        return dealt


@dataclass
class AssetState:
    """Full operational state for a military asset"""
    asset_id: str
    asset_type: str  # "fighter", "sam", "jammer", "uav", etc.
    position: Tuple[int, int]
    health: float = 100.0
    ammo: float = 100.0
    fuel: float = 100.0
    supply_node_id: Optional[str] = None
    effectiveness: float = 1.0  # 0.0 to 1.0
    range: int = 5
    speed: int = 2
    fuel_max: float = 100.0
    ammo_max: float = 100.0
    
    def can_move(self) -> bool:
        return self.fuel > 0 and self.health > 0
    
    def can_attack(self) -> bool:
        return self.ammo > 0 and self.health > 0 and self.effectiveness > 0.1
    
    def is_combat_capable(self) -> bool:
        return self.health > 0 and self.effectiveness > 0.1


def create_asset(asset_type: str, asset_id: str, position: Tuple[int, int],
                 supply_node_id: str, **kwargs) -> Dict:
    """Backward-compatible factory for legacy dict-based asset creation."""
    return {
        "asset_id": asset_id,
        "type": asset_type,
        "position": position,
        "health": 100.0,
        "ammo": 100.0,
        "fuel": 100.0,
        "fuel_max": 100.0,
        "ammo_max": 100.0,
        "supply_node_id": supply_node_id,
        "effectiveness": 1.0,
        "range": 5,
        "speed": 2,
        **kwargs
    }


class BattlefieldEnv:
    """
    2D grid battlefield with red/blue forces, supply logistics,
    and operational readiness modeling.
    """
    
    GRID_SIZE = 100
    MAX_STEPS = 200
    RESUPPLY_STEPS = 3
    
    def __init__(self, width: int = 100, height: int = 100):
        self.width = width
        self.height = height
        self.step_count = 0
        self.max_steps = 200
        
        self.grid = np.zeros((width, height), dtype=np.float32)
        
        self.blue_supply_nodes: Dict[str, SupplyNode] = {}
        self.red_supply_nodes: Dict[str, SupplyNode] = {}
        
        self.blue_assets: Dict[str, List[Dict]] = {}
        self.red_assets: Dict[str, List[Dict]] = {}
        
        self.red_force: Dict[str, Any] = {}
        
        self._ecm_active = False
        self._ecm_noise = 0.0
        self._perception_done = False
        
        self.action_types = ["move", "strike", "jam", "evade", "resupply", "hold"]
        
        # Resupply tracking: asset_id -> steps completed
        self._resupply_progress: Dict[str, int] = {}
    
    @property
    def supply_nodes(self) -> Dict[str, SupplyNode]:
        """Combined supply nodes for backward compatibility."""
        combined = {}
        combined.update(self.blue_supply_nodes)
        combined.update(self.red_supply_nodes)
        return combined
    
    def _create_default_assets(self) -> None:
        """Create default blue/red assets for simulation."""
        # Blue supply nodes
        self.blue_supply_nodes = {
            "BLUE-SUPPLY-A": SupplyNode(
                node_id="BLUE-SUPPLY-A",
                position=(10, 10),
                health=100.0,
                assets_linked=["drone-0", "drone-1", "jammer-0", "missile-0", "missile-1"],
                team="blue",
            ),
            "BLUE-SUPPLY-B": SupplyNode(
                node_id="BLUE-SUPPLY-B",
                position=(15, 85),
                health=100.0,
                assets_linked=["drone-0", "drone-1", "jammer-0", "missile-0", "missile-1"],
                team="blue",
            ),
        }
        
        # Blue assets
        self.blue_assets = {
            "drones": [
                create_asset("drone", "drone-0", (30, 40), "BLUE-SUPPLY-A", speed=3, range=8),
                create_asset("drone", "drone-1", (35, 45), "BLUE-SUPPLY-A", speed=3, range=8),
            ],
            "jammers": [
                create_asset("jammer", "jammer-0", (25, 35), "BLUE-SUPPLY-B", speed=1, range=12),
            ],
            "missiles": [
                create_asset("missile", "missile-0", (20, 50), "BLUE-SUPPLY-B", speed=5, range=15),
                create_asset("missile", "missile-1", (22, 52), "BLUE-SUPPLY-B", speed=5, range=15),
            ],
        }
        
        # Red supply nodes
        self.red_supply_nodes = {
            "RED-SUPPLY-A": SupplyNode(
                node_id="RED-SUPPLY-A",
                position=(80, 20),
                health=100.0,
                assets_linked=[],
                team="red",
            ),
            "RED-SUPPLY-B": SupplyNode(
                node_id="RED-SUPPLY-B",
                position=(85, 80),
                health=100.0,
                assets_linked=[],
                team="red",
            ),
        }
    
    def reset(self, red_position: Optional[Tuple[int, int]] = None,
              seed: Optional[int] = None) -> Dict:
        """Reset the environment for a new episode."""
        self.step_count = 0
        
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        # Create fresh assets
        self._create_default_assets()
        
        # Red force as a single entity (dict-based for backward compat)
        red_pos = red_position or (65, 50)
        self.red_force = {
            "position": red_pos,
            "fuel": 100.0,
            "fuel_max": 100.0,
            "ammo": 100.0,
            "ammo_max": 100.0,
            "supply_node_id": "RED-SUPPLY-A",
            "effectiveness": 1.0,
            "health": 100.0,
            "type": "armored",
        }
        
        self._ecm_active = False
        self._ecm_noise = 0.0
        
        return self._get_obs()
    
    def _get_obs(self) -> Dict:
        """Get current observation."""
        # Convert blue assets to dict format for observation
        blue_assets_obs: Dict[str, List[Dict]] = {}
        for atype, assets in self.blue_assets.items():
            blue_assets_obs[atype] = [
                {
                    "asset_id": a["asset_id"],
                    "type": a["type"],
                    "position": a["position"],
                    "health": a["health"],
                    "ammo": a["ammo"],
                    "fuel": a["fuel"],
                    "fuel_max": a["fuel_max"],
                    "ammo_max": a["ammo_max"],
                    "supply_node_id": a["supply_node_id"],
                    "effectiveness": a["effectiveness"],
                    "range": a.get("range", 5),
                    "speed": a.get("speed", 2),
                }
                for a in assets
            ]
        
        # Supply nodes snapshot
        supply_nodes_snapshot: Dict[str, Dict] = {}
        for node_id, node in self.supply_nodes.items():
            supply_nodes_snapshot[node_id] = {
                "position": node.position,
                "health": node.health,
                "is_destroyed": node.is_destroyed,
                "team": "blue" if node_id.startswith("BLUE") else "red",
                "assets_linked": list(node.assets_linked),
            }
        
        return {
            "blue_assets": blue_assets_obs,
            "red_force": dict(self.red_force),
            "supply_nodes": supply_nodes_snapshot,
            "ecm_active": self._ecm_active,
            "ecm_noise": self._ecm_noise,
            "step": self.step_count,
        }
    
    def step(self, blue_action: Optional[Dict] = None,
             red_action: Optional[Dict] = None) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute one simulation step.
        
        Args:
            blue_action: Dict with action type and params
            red_action: Dict with evade/ECM params
            
        Returns:
            (obs, reward, done, info) tuple
        """
        self.step_count += 1
        info = {
            "fuel_consumed": 0.0,
            "supply_node_destroyed": False,
            "swarm_collisions": 0,
            "ecm_active": False,
        }
        
        # Process Red actions
        if red_action:
            self._ecm_active = red_action.get("ecm", False)
            self._ecm_noise = red_action.get("ecm_noise", 0.0)
            if self._ecm_active:
                info["ecm_active"] = True
            self._process_red_evasion(red_action)
        
        # Process Blue actions
        reward = 0.0
        if blue_action:
            action_type = blue_action.get("action", "hold")
            try:
                if action_type == "move":
                    reward = self._process_blue_move(blue_action, info)
                elif action_type == "strike":
                    reward = self._process_blue_strike(blue_action, info)
                elif action_type == "jam":
                    reward = self._process_blue_jam(blue_action)
                elif action_type == "resupply":
                    reward = self._process_resupply(blue_action, info)
                elif action_type == "swarm":
                    reward = self._process_swarm(blue_action, info)
            except Exception as e:
                logger.warning(f"Step action failed: {e}")
        
        # Check done conditions
        done = False
        if self.step_count >= self.MAX_STEPS:
            done = True
        elif self.red_force.get("health", 100) <= 0:
            done = True
            reward = 50.0  # Success reward
        
        # Supply node resupply logic
        self._resolve_resupply()
        
        obs = self._get_obs()
        return obs, reward, done, info
    
    def _process_red_evasion(self, red_action: Dict) -> None:
        """Process Red evasion maneuver."""
        if red_action.get("evade", False):
            pos = self.red_force.get("position", (50, 50))
            heading_offset = red_action.get("heading_offset", 0)
            angle = math.radians(heading_offset + random.uniform(-30, 30))
            dx = int(math.cos(angle) * 3)
            dy = int(math.sin(angle) * 3)
            new_pos = (
                max(0, min(self.width - 1, pos[0] + dx)),
                max(0, min(self.height - 1, pos[1] + dy)),
            )
            self.red_force["position"] = new_pos
            # Fuel cost for evasion
            self.red_force["fuel"] = max(0, self.red_force.get("fuel", 100) - 1)
    
    def _process_blue_move(self, blue_action: Dict, info: Dict) -> float:
        """Process Blue movement actions."""
        target = blue_action.get("target")
        asset_type = blue_action.get("asset_type", "missiles")
        
        if asset_type not in self.blue_assets or not self.blue_assets[asset_type]:
            return 0.0
        
        total_fuel = 0.0
        for asset in self.blue_assets[asset_type]:
            if not asset.get("can_move", True):
                continue
            if target:
                cur = asset["position"]
                dx = target[0] - cur[0]
                dy = target[1] - cur[1]
                dist = math.sqrt(dx*dx + dy*dy)
                speed = asset.get("speed", 2)
                step_dist = min(dist, speed)
                if dist > 0:
                    ratio = step_dist / dist
                    asset["position"] = (
                        int(cur[0] + dx * ratio),
                        int(cur[1] + dy * ratio),
                    )
                fuel_cost = step_dist * 0.5
                asset["fuel"] = max(0, asset["fuel"] - fuel_cost)
                total_fuel += fuel_cost
        
        info["fuel_consumed"] = total_fuel
        return -total_fuel * 0.1  # Small penalty for movement
    
    def _process_blue_strike(self, blue_action: Dict, info: Dict) -> float:
        """Process Blue strike actions."""
        asset_type = blue_action.get("asset_type", "missiles")
        accuracy_mod = blue_action.get("_accuracy_mod", 1.0)
        
        if asset_type not in self.blue_assets or not self.blue_assets[asset_type]:
            return 0.0
        
        red_pos = self.red_force.get("position", (50, 50))
        total_damage = 0.0
        
        for asset in self.blue_assets[asset_type]:
            if not asset.get("can_attack", True):
                continue
            # Check range
            asset_pos = asset["position"]
            dist = math.sqrt((asset_pos[0] - red_pos[0])**2 + (asset_pos[1] - red_pos[1])**2)
            max_range = asset.get("range", 5)
            if dist > max_range * 5:  # generous range check
                continue
            
            # Apply ECM degradation
            ecm_factor = 1.0 - (self._ecm_noise if self._ecm_active else 0.0)
            
            # Base damage
            damage = random.uniform(5, 15) * accuracy_mod * ecm_factor
            red_health = self.red_force.get("health", 100)
            self.red_force["health"] = max(0, red_health - damage)
            total_damage += damage
            
            # Ammo consumption
            asset["ammo"] = max(0, asset["ammo"] - 10)
            
            # Apply effectiveness loss
            asset["effectiveness"] = max(0.1, asset.get("effectiveness", 1.0) - 0.05)
        
        # Reward proportional to damage inflicted
        reward = total_damage * 0.5 - 2.0  # minus ammo cost
        return reward
    
    def _process_blue_jam(self, blue_action: Dict) -> float:
        """Process Blue jamming actions."""
        asset_type = blue_action.get("asset_type", "jammers")
        
        if asset_type not in self.blue_assets or not self.blue_assets[asset_type]:
            return 0.0
        
        for asset in self.blue_assets[asset_type]:
            asset["effectiveness"] = max(0.1, asset.get("effectiveness", 1.0) - 0.02)
        
        # Suppress Red ECM
        self._ecm_active = False
        self._ecm_noise = max(0, self._ecm_noise - 0.2)
        
        return 2.0  # Reward for jamming
    
    def _process_swarm(self, blue_action: Dict, info: Dict) -> float:
        """Process swarm actions (multi-asset coordinated)."""
        fleet = blue_action.get("swarm_fleet", [])
        total_reward = 0.0
        
        for asset_action in fleet:
            sub_action = {
                "action": asset_action.get("action", "move"),
                "asset_type": asset_action.get("asset_type", "drones"),
                "target": asset_action.get("target"),
                "_accuracy_mod": asset_action.get("_accuracy_mod", 1.0),
            }
            
            if sub_action["action"] == "strike":
                total_reward += self._process_blue_strike(sub_action, info)
            elif sub_action["action"] == "move":
                total_reward += self._process_blue_move(sub_action, info)
            elif sub_action["action"] == "jam":
                total_reward += self._process_blue_jam(sub_action)
        
        # Track swarm collisions (same-grid stacking)
        positions = []
        for atype, assets in self.blue_assets.items():
            for a in assets:
                positions.append(a["position"])
        collision_count = len(positions) - len(set(positions))
        info["swarm_collisions"] = max(0, collision_count)
        
        return total_reward
    
    def _process_resupply(self, blue_action: Dict, info: Dict) -> float:
        """Process resupply action for a specific asset type.
        
        Full resupply is achieved after RESUPPLY_STEPS consecutive resupply
        steps. Each step increments a progress counter; on completion the
        asset's fuel, ammo, and effectiveness are fully restored.
        """
        asset_type = blue_action.get("asset_type", "missiles")
        
        if asset_type not in self.blue_assets:
            return 0.0
        
        resupplied = 0
        for asset in self.blue_assets[asset_type]:
            supply_id = asset.get("supply_node_id")
            if supply_id and supply_id in self.supply_nodes:
                node = self.supply_nodes[supply_id]
                if node.is_operational():
                    asset_pos = asset["position"]
                    node_pos = node.position
                    dist = math.sqrt((asset_pos[0] - node_pos[0])**2 +
                                     (asset_pos[1] - node_pos[1])**2)
                    if dist < 10:  # within resupply range
                        aid = asset["asset_id"]
                        self._resupply_progress[aid] = self._resupply_progress.get(aid, 0) + 1
                        if self._resupply_progress[aid] >= self.RESUPPLY_STEPS:
                            # Full resupply!
                            asset["fuel"] = float(asset["fuel_max"])
                            asset["ammo"] = float(asset["ammo_max"])
                            asset["effectiveness"] = 1.0
                            self._resupply_progress[aid] = 0  # reset for next cycle
                            resupplied += 1
        
        return resupplied * 3.0  # Reward per fully resupplied asset
    
    def _resolve_resupply(self) -> None:
        """Auto-resupply for assets near their supply nodes."""
        for atype, assets in self.blue_assets.items():
            for asset in assets:
                supply_id = asset.get("supply_node_id")
                if supply_id and supply_id in self.supply_nodes:
                    node = self.supply_nodes[supply_id]
                    if node.is_operational():
                        asset_pos = asset["position"]
                        node_pos = node.position
                        dist = math.sqrt((asset_pos[0] - node_pos[0])**2 +
                                         (asset_pos[1] - node_pos[1])**2)
                        if dist < 8:
                            # Gradual resupply
                            asset["fuel"] = min(asset["fuel_max"], asset["fuel"] + 0.5)
                            asset["ammo"] = min(asset["ammo_max"], asset["ammo"] + 0.5)
    
    def get_total_fuel_consumed(self) -> float:
        """Get total fuel consumed across all blue assets."""
        total = 0.0
        for atype, assets in self.blue_assets.items():
            for asset in assets:
                total += asset.get("fuel_max", 100) - asset.get("fuel", 100)
        return total
    
    def render_ascii_map(self) -> str:
        """Render the battlefield as an ASCII map for LLM consumption."""
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        
        # Place supply nodes
        for nid, node in self.blue_supply_nodes.items():
            x, y = node.position
            if 0 <= x < self.width and 0 <= y < self.height:
                grid[y][x] = "S"
        
        for nid, node in self.red_supply_nodes.items():
            x, y = node.position
            if 0 <= x < self.width and 0 <= y < self.height:
                if not node.is_destroyed:
                    grid[y][x] = "s"
        
        # Place red force
        rx, ry = self.red_force.get("position", (50, 50))
        if 0 <= rx < self.width and 0 <= ry < self.height:
            grid[ry][rx] = "R"
        
        # Place blue assets
        for atype, assets in self.blue_assets.items():
            for asset in assets:
                x, y = asset["position"]
                if 0 <= x < self.width and 0 <= y < self.height:
                    code = "D" if atype == "drones" else ("M" if atype == "missiles" else "J")
                    grid[y][x] = code
        
        # ECM zones
        if self._ecm_active:
            for _ in range(3):
                ex = random.randint(0, self.width - 1)
                ey = random.randint(0, self.height - 1)
                grid[ey][ex] = "E"
        
        # Render as compact grid (show only populated region)
        lines = []
        for row in grid:
            line = "".join(row)
            if any(c != "." for c in line):
                lines.append(line)
        
        return "\n".join(lines[:20]) if lines else "Empty battlefield"
    
    def render(self, mode: str = "ascii") -> str:
        """Legacy render support."""
        if mode == "ascii":
            return self.render_ascii_map()
        return ""

