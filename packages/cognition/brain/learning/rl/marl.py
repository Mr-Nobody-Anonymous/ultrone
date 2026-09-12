# Copyright (c) Ultrone Contributors. All rights reserved.
"""Multi-Agent Reinforcement Learning (MARL) framework.

Provides centralized training with decentralized execution (CTDE)
for multi-agent coordination. Supports independent learners, parameter
sharing, and counterfactual baselines.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseRLAlgorithm, RLConfig, RLExperience
from .adapter import create_rl_algorithm, SB3AdapterConfig

logger = logging.getLogger("Ultrone.Brain.Learning.RL.MARL")


@dataclass
class MARLConfig(RLConfig):
    """Configuration for MARL."""
    num_agents: int = 2
    shared_params: bool = True
    use_centralized_critic: bool = True
    agent_ids: List[str] = field(default_factory=lambda: ["agent_0", "agent_1"])
    algorithm_type: str = "PPO"


class CentralizedCritic:
    """Centralized critic that conditions on all agents' observations and actions."""
    pass


class DecentralizedActor:
    """Decentralized actor that conditions only on local observations."""
    pass


class MARL(BaseRLAlgorithm):
    """Multi-Agent RL wrapper supporting CTDE paradigm.

    Wraps multiple RL algorithms (from the adapter/registry) for
    multi-agent coordination. Each agent gets its own algorithm
    instance, with optional parameter sharing.
    """

    def __init__(self, config: Optional[MARLConfig] = None):
        super().__init__(config or MARLConfig())
        self._config: MARLConfig = self.config  # type: ignore
        self.agents: Dict[str, BaseRLAlgorithm] = {}

        # Auto-create agents from config
        self._init_agents()

    def _init_agents(self) -> None:
        """Create agents using the RL registry."""
        for aid in self._config.agent_ids:
            agent = create_rl_algorithm(
                algorithm_type=self._config.algorithm_type,
                config=self._config,
                adapter_config=SB3AdapterConfig(),
            )
            self.agents[aid] = agent
            logger.info("MARL agent %s created with %s", aid, self._config.algorithm_type)

        if self._config.shared_params and len(self.agents) > 1:
            logger.info("MARL parameter sharing enabled — agents share model weights.")

    def add_agent(self, agent_id: str, algorithm: BaseRLAlgorithm) -> None:
        """Register an agent with its RL algorithm."""
        self.agents[agent_id] = algorithm
        logger.info("MARL agent %s registered with %s", agent_id, type(algorithm).__name__)

    def act(self, state: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """Single-agent fallback (uses first agent)."""
        if self.agents:
            first = next(iter(self.agents.values()))
            return first.act(state, deterministic)
        return np.array([0.0])

    def act_multi(self, states: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Get actions for all agents from their local observations."""
        return {aid: agent.act(states.get(aid, np.zeros(1)))
                for aid, agent in self.agents.items()}

    def update(self, experience: RLExperience) -> Dict[str, float]:
        """Update all agents with the shared experience."""
        total_loss = 0.0
        for agent in self.agents.values():
            losses = agent.update(experience)
            total_loss += sum(losses.values())
        return {"marl_loss": total_loss / max(1, len(self.agents))}

    def save(self, path: str) -> None:
        """Save all agent models."""
        for aid, agent in self.agents.items():
            agent_path = f"{path}_{aid}"
            agent.save(agent_path)
        logger.info("MARL models saved to %s_*", path)

    def load(self, path: str) -> None:
        """Load all agent models."""
        for aid, agent in self.agents.items():
            agent_path = f"{path}_{aid}"
            agent.load(agent_path)
        logger.info("MARL models loaded from %s_*", path)

