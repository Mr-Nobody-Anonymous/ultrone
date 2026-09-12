# Copyright (c) Ultrone Contributors. All rights reserved.
"""Agentic Layer — specialized agent collaboration.

Each specialized agent has perception, memory, reasoning, planning,
tools, goals, policies, and self-evaluation. Agents collaborate using
blackboard systems, consensus, auctions, task allocation, coalition
formation, message passing, and knowledge sharing.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType

logger = logging.getLogger("Ultrone.Cognitive.Agentic")


@dataclass
class AgentSpec:
    """Specification for a specialized agent."""
    agent_id: str
    role: str
    capabilities: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    policies: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class AgenticLayerConfig(LayerConfig):
    """Configuration for the agentic layer."""
    name: str = "agentic"
    enable_blackboard: bool = True
    enable_consensus: bool = True
    enable_auctions: bool = True
    enable_task_allocation: bool = True
    enable_coalition_formation: bool = True
    enable_message_passing: bool = True
    enable_knowledge_sharing: bool = True
    max_agents: int = 20


class AgenticLayer(CognitiveLayer):
    """Agentic collaboration layer.

    The agentic layer:
    1. Manages specialized agents
    2. Facilitates blackboard communication
    3. Enables consensus building
    4. Supports task allocation
    5. Forms coalitions
    6. Shares knowledge between agents
    """

    def __init__(self, config: Optional[AgenticLayerConfig] = None):
        super().__init__(config or AgenticLayerConfig())
        self._agents: Dict[str, AgentSpec] = {}
        self._blackboard: Dict[str, Any] = {}
        self._messages: List[Dict[str, Any]] = []
        self._task_allocations: List[Dict[str, Any]] = []
        self._coalitions: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.EVALUATE

    def register_agent(self, agent: AgentSpec) -> None:
        """Register a specialized agent."""
        if len(self._agents) < self.config.max_agents:
            self._agents[agent.agent_id] = agent

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the agentic collaboration phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context.

        Returns
        -------
        PhaseResult
            Result with agentic collaboration outputs.
        """
        start = time.time()

        # 1. Update blackboard with current context
        if self.config.enable_blackboard:
            self._update_blackboard(ctx)

        # 2. Allocate tasks to agents
        allocations = []
        if self.config.enable_task_allocation:
            allocations = self._allocate_tasks(ctx)

        # 3. Form coalitions
        coalitions = []
        if self.config.enable_coalition_formation:
            coalitions = self._form_coalitions(ctx)

        # 4. Share knowledge
        if self.config.enable_knowledge_sharing:
            self._share_knowledge(ctx)

        # 5. Build consensus
        consensus = None
        if self.config.enable_consensus:
            consensus = self._build_consensus(ctx)

        # 6. Store in context
        ctx.metadata["agentic"] = {
            "agents": len(self._agents),
            "allocations": allocations,
            "coalitions": coalitions,
            "consensus": consensus,
            "blackboard_keys": list(self._blackboard.keys()),
        }

        # 7. Publish event
        self._publish_event(
            CognitiveEventType.EVALUATION,
            {
                "agents": len(self._agents),
                "allocations": len(allocations),
                "coalitions": len(coalitions),
            },
        )

        # 8. Create decision trace
        trace = self._create_trace(
            decision="Agentic collaboration and task allocation",
            confidence=0.7,
            evidence=[
                {
                    "source": "agentic",
                    "description": f"Coordinated {len(self._agents)} agents",
                    "confidence": 0.7,
                }
            ],
        )

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "agents": len(self._agents),
                "allocations": allocations,
                "coalitions": coalitions,
                "consensus": consensus,
                "blackboard_keys": list(self._blackboard.keys()),
            },
            trace=trace,
        )

    def _update_blackboard(self, ctx: CycleContext) -> None:
        """Update the blackboard with current context."""
        self._blackboard["goals"] = ctx.context.goals
        self._blackboard["constraints"] = ctx.context.constraints
        self._blackboard["confidence"] = ctx.confidence
        self._blackboard["uncertainty"] = ctx.uncertainty

        if ctx.world_state:
            self._blackboard["world_state"] = ctx.world_state.to_dict()

        if ctx.situational_context:
            self._blackboard["situational"] = ctx.situational_context.to_dict()

    def _allocate_tasks(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Allocate tasks to agents based on capabilities."""
        allocations = []
        goals = ctx.context.goals

        for goal in goals:
            best_agent = None
            best_score = 0.0

            for agent in self._agents.values():
                if not agent.enabled:
                    continue
                # Score agent capability match
                score = 0.0
                for capability in agent.capabilities:
                    if capability.lower() in goal.lower():
                        score += 1.0
                if score > best_score:
                    best_score = score
                    best_agent = agent

            if best_agent:
                allocation = {
                    "task": goal,
                    "agent": best_agent.agent_id,
                    "role": best_agent.role,
                    "score": best_score,
                }
                allocations.append(allocation)
                self._task_allocations.append(allocation)

        return allocations

    def _form_coalitions(self, ctx: CycleContext) -> List[Dict[str, Any]]:
        """Form coalitions of agents for complex tasks."""
        coalitions = []
        goals = ctx.context.goals

        for goal in goals:
            # Find agents that can contribute
            members = []
            for agent in self._agents.values():
                if not agent.enabled:
                    continue
                for capability in agent.capabilities:
                    if capability.lower() in goal.lower():
                        members.append(agent.agent_id)
                        break

            if len(members) >= 2:
                coalition = {
                    "goal": goal,
                    "members": members,
                    "size": len(members),
                }
                coalitions.append(coalition)
                self._coalitions.append(coalition)

        return coalitions

    def _share_knowledge(self, ctx: CycleContext) -> None:
        """Share knowledge between agents via the blackboard."""
        if ctx.reasoning_trace:
            self._blackboard["reasoning"] = {
                "conclusion": ctx.reasoning_trace.decision,
                "confidence": ctx.reasoning_trace.confidence,
            }

        if ctx.plan:
            self._blackboard["plan"] = ctx.plan.to_dict()

    def _build_consensus(self, ctx: CycleContext) -> Optional[Dict[str, Any]]:
        """Build consensus among agents."""
        if not self._agents:
            return None

        # Simple consensus: average confidence
        confidences = [ctx.confidence]
        if ctx.reasoning_trace:
            confidences.append(ctx.reasoning_trace.confidence)
        if ctx.plan:
            confidences.append(ctx.plan.confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        return {
            "reached": avg_confidence > 0.6,
            "confidence": avg_confidence,
            "participants": len(self._agents),
        }

    def get_agents(self) -> Dict[str, AgentSpec]:
        """Return all registered agents."""
        return self._agents

    def get_blackboard(self) -> Dict[str, Any]:
        """Return the current blackboard state."""
        return self._blackboard

    def get_messages(self) -> List[Dict[str, Any]]:
        """Return all messages."""
        return self._messages

    def get_task_allocations(self) -> List[Dict[str, Any]]:
        """Return all task allocations."""
        return self._task_allocations

    def get_coalitions(self) -> List[Dict[str, Any]]:
        """Return all coalitions."""
        return self._coalitions