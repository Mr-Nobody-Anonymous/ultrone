# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base class for cyber domain agents."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent, AgentCapability
from agents.config import CyberAgentConfig
from data.entities import DomainType, Contact

logger = logging.getLogger("Ultrone.Agents.Cyber.Base")


class CyberAgent(BaseAgent):
    """
    Base class for all cyber domain agents.
    
    Provides common cyber-domain functionality:
    - Simulated network operations
    - Compute resource management
    - Stealth mode
    - Exploit and defense mechanics
    - Network topology awareness
    """
    
    def __init__(
        self,
        unit_id: str,
        position: tuple,
        team: str = "blue",
        config: Optional[CyberAgentConfig] = None,
        **kwargs,
    ):
        """
        Initialize cyber agent.
        
        Args:
            unit_id: Unique identifier
            position: (x, y, z) - abstract network position
            team: Team affiliation
            config: Cyber-specific configuration
        """
        super().__init__(
            unit_id=unit_id,
            domain=DomainType.CYBER,
            unit_type=self._get_unit_type(),
            position=position,
            team=team,
            capabilities=self._get_capabilities(),
            **kwargs,
        )
        
        # Cyber-specific configuration
        self.config = config or CyberAgentConfig(
            agent_id=unit_id,
            team=team,
            domain=DomainType.CYBER,
        )
        
        # Cyber-specific state
        self.compute_nodes: int = self.config.compute_nodes
        self.bandwidth_mbps: float = self.config.bandwidth_mbps
        self.encryption_strength: float = self.config.encryption_strength
        self.stealth_factor: float = self.config.stealth_factor
        self.exploit_success_rate: float = self.config.exploit_success_rate
        
        # Network state
        self.network_position: Tuple[float, float, float] = position
        self.connected_networks: List[str] = []
        self.compromised_nodes: List[str] = []
        self.firewall_integrity: float = 1.0
        
        # Operation state
        self.operation_phase: str = "idle"  # idle, scanning, exploiting, defending, exfiltrating
        self.target_host: Optional[str] = None
        self.access_level: float = 0.0  # 0.0-1.0
        self.detection_risk: float = 0.0  # 0.0-1.0
        
        # Statistics
        self.scans_performed: int = 0
        self.exploits_attempted: int = 0
        self.exploits_successful: int = 0
        self.defenses_mounted: int = 0
        self.intrusions_blocked: int = 0
    
    def _get_unit_type(self) -> str:
        """Return the unit type string. Override in subclasses."""
        return "cyber_generic"
    
    def _get_capabilities(self) -> List[AgentCapability]:
        """Return default capabilities. Override in subclasses."""
        return [
            AgentCapability.SENSE,
            AgentCapability.COMMUNICATE,
        ]
    
    def scan_network(self, network_id: str) -> Dict[str, Any]:
        """
        Perform network scan (simulated).
        
        Args:
            network_id: Target network identifier
            
        Returns:
            Scan results dictionary
        """
        self.scans_performed += 1
        self.operation_phase = "scanning"
        
        # Simulate scan results
        scan_result = {
            "network_id": network_id,
            "hosts_found": random.randint(5, 50),
            "vulnerabilities": random.randint(0, 5),
            "detection_risk": min(1.0, self.detection_risk + 0.1),
            "timestamp": self.unit.position,  # Using position as timestamp placeholder
        }
        
        logger.info(f"{self.unit.unit_id} scanned network {network_id}")
        return scan_result
    
    def attempt_exploit(self, target_host: str, vulnerability_id: str) -> Dict[str, Any]:
        """
        Attempt to exploit a vulnerability (simulated).
        
        Args:
            target_host: Target host identifier
            vulnerability_id: Vulnerability to exploit
            
        Returns:
            Exploit result dictionary
        """
        self.exploits_attempted += 1
        self.operation_phase = "exploiting"
        
        # Simulate exploit outcome
        success = random.random() < self.exploit_success_rate
        
        if success:
            self.exploits_successful += 1
            self.access_level = min(1.0, self.access_level + 0.3)
            self.compromised_nodes.append(target_host)
            result = {
                "success": True,
                "target_host": target_host,
                "access_gained": "user" if self.access_level < 0.7 else "admin",
                "access_level": self.access_level,
            }
            logger.info(f"{self.unit.unit_id} successfully exploited {target_host}")
        else:
            self.detection_risk = min(1.0, self.detection_risk + 0.2)
            result = {
                "success": False,
                "target_host": target_host,
                "reason": "exploit_failed",
                "detection_risk": self.detection_risk,
            }
            logger.warning(f"{self.unit.unit_id} exploit attempt failed on {target_host}")
        
        return result
    
    def mount_defense(self, target_node: str) -> Dict[str, Any]:
        """
        Mount defensive measures (simulated).
        
        Args:
            target_node: Node to defend
            
        Returns:
            Defense result dictionary
        """
        self.defenses_mounted += 1
        self.operation_phase = "defending"
        
        # Improve firewall and encryption
        self.firewall_integrity = min(1.0, self.firewall_integrity + 0.2)
        self.encryption_strength = min(1.0, self.encryption_strength + 0.1)
        self.detection_risk = max(0.0, self.detection_risk - 0.2)
        
        result = {
            "success": True,
            "target_node": target_node,
            "firewall_integrity": self.firewall_integrity,
            "encryption_strength": self.encryption_strength,
        }
        
        logger.info(f"{self.unit.unit_id} mounted defense on {target_node}")
        return result
    
    def block_intrusion(self, intrusion_attempt: Dict[str, Any]) -> bool:
        """
        Block an intrusion attempt.
        
        Args:
            intrusion_attempt: Intrusion attempt details
            
        Returns:
            True if intrusion blocked
        """
        # Success probability based on firewall and encryption
        block_probability = (self.firewall_integrity + self.encryption_strength) / 2.0
        blocked = random.random() < block_probability
        
        if blocked:
            self.intrusions_blocked += 1
            logger.info(f"{self.unit.unit_id} blocked intrusion attempt")
        else:
            self.detection_risk = min(1.0, self.detection_risk + 0.15)
            logger.warning(f"{self.unit.unit_id} failed to block intrusion")
        
        return blocked
    
    def enable_stealth(self) -> None:
        """Enable stealth mode (reduce detection risk)."""
        self.stealth_factor = 0.9
        self.detection_risk = max(0.0, self.detection_risk - 0.3)
        logger.info(f"{self.unit.unit_id} enabled stealth mode")
    
    def disable_stealth(self) -> None:
        """Disable stealth mode."""
        self.stealth_factor = 0.1
        logger.info(f"{self.unit.unit_id} disabled stealth mode")
    
    def update(self, world_state: Any, delta_time: float = 1.0) -> None:
        """
        Update cyber agent state.
        
        Handles:
        - Operation phase progression
        - Detection risk decay
        - Resource management
        """
        # Decay detection risk over time
        if self.detection_risk > 0.0:
            self.detection_risk = max(0.0, self.detection_risk - 0.01 * delta_time)
        
        # Consume compute resources for active operations
        if self.operation_phase != "idle":
            self.bandwidth_mbps = max(0.0, self.bandwidth_mbps - 5.0 * delta_time)
    
    def get_stats(self) -> dict:
        """Get cyber agent statistics."""
        stats = super().get_stats() if hasattr(super(), "get_stats") else {}
        stats.update({
            "compute_nodes": self.compute_nodes,
            "bandwidth_mbps": self.bandwidth_mbps,
            "encryption_strength": self.encryption_strength,
            "stealth_factor": self.stealth_factor,
            "firewall_integrity": self.firewall_integrity,
            "access_level": self.access_level,
            "detection_risk": self.detection_risk,
            "operation_phase": self.operation_phase,
            "scans_performed": self.scans_performed,
            "exploits_attempted": self.exploits_attempted,
            "exploits_successful": self.exploits_successful,
            "defenses_mounted": self.defenses_mounted,
            "intrusions_blocked": self.intrusions_blocked,
            "compromised_nodes": len(self.compromised_nodes),
        })
        return stats
    
    def to_dict(self) -> dict:
        """Serialize agent state."""
        data = super().to_dict()
        data.update({
            "compute_nodes": self.compute_nodes,
            "bandwidth_mbps": self.bandwidth_mbps,
            "encryption_strength": self.encryption_strength,
            "stealth_factor": self.stealth_factor,
            "exploit_success_rate": self.exploit_success_rate,
            "network_position": self.network_position,
            "connected_networks": self.connected_networks,
            "compromised_nodes": self.compromised_nodes,
            "firewall_integrity": self.firewall_integrity,
            "operation_phase": self.operation_phase,
            "target_host": self.target_host,
            "access_level": self.access_level,
            "detection_risk": self.detection_risk,
            "scans_performed": self.scans_performed,
            "exploits_attempted": self.exploits_attempted,
            "exploits_successful": self.exploits_successful,
            "defenses_mounted": self.defenses_mounted,
            "intrusions_blocked": self.intrusions_blocked,
        })
        return data
    
    def from_dict(self, data: dict) -> None:
        """Deserialize agent state."""
        super().from_dict(data)
        self.compute_nodes = data.get("compute_nodes", self.compute_nodes)
        self.bandwidth_mbps = data.get("bandwidth_mbps", self.bandwidth_mbps)
        self.encryption_strength = data.get("encryption_strength", self.encryption_strength)
        self.stealth_factor = data.get("stealth_factor", self.stealth_factor)
        self.exploit_success_rate = data.get("exploit_success_rate", self.exploit_success_rate)
        self.network_position = data.get("network_position", self.network_position)
        self.connected_networks = data.get("connected_networks", [])
        self.compromised_nodes = data.get("compromised_nodes", [])
        self.firewall_integrity = data.get("firewall_integrity", self.firewall_integrity)
        self.operation_phase = data.get("operation_phase", self.operation_phase)
        self.target_host = data.get("target_host", None)
        self.access_level = data.get("access_level", self.access_level)
        self.detection_risk = data.get("detection_risk", self.detection_risk)
        self.scans_performed = data.get("scans_performed", 0)
        self.exploits_attempted = data.get("exploits_attempted", 0)
        self.exploits_successful = data.get("exploits_successful", 0)
        self.defenses_mounted = data.get("defenses_mounted", 0)
        self.intrusions_blocked = data.get("intrusions_blocked", 0)


import random  # noqa: E402 - needed for cyber operations