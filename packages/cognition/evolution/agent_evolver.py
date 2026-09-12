# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Agent Evolver
=============
Dynamically creates and evolves sub-agents, inspired by Agent Zero's
approach of creating sub-agents to solve complex tasks.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .genome import Genome, GenomeEngine, Gene, Capsule
from .evolution_lab import EvolutionLab

logger = logging.getLogger("Ultrone.Evolution.AgentEvolver")


@dataclass
class AgentPersonality:
    """A specialized sub-agent with its own genome and focus."""
    name: str
    description: str
    domain: str
    genome: Genome
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    task_count: int = 0
    success_rate: float = 1.0


class AgentEvolver:
    """
    Creates and manages a population of specialized sub-agents.
    
    Each sub-agent has its own genome with domain-specific capsules,
    and can evolve independently based on its task performance.
    """
    
    def __init__(self, evolution_lab: EvolutionLab):
        self.evolution_lab = evolution_lab
        self.agents: Dict[str, AgentPersonality] = {}
    
    def create_agent(
        self,
        name: str,
        domain: str,
        description: str = "",
        parent_genome: Optional[Genome] = None,
    ) -> AgentPersonality:
        """Create a new specialized sub-agent with its own genome."""
        base_genome = parent_genome or self.evolution_lab.genome_engine.active_genome
        if not base_genome:
            raise ValueError("No base genome available to create agent")
        
        new_genome = base_genome.clone()
        new_genome.agent_id = f"{name}-{domain}"
        new_genome.parent_genome_id = base_genome.agent_id
        
        # Add domain-specialized capsule if it doesn't exist
        if not new_genome.get_capsule(domain):
            domain_capsule = Capsule(
                name=domain,
                description=f"{domain} specialized operations",
            )
            domain_capsule.add_gene(Gene(
                f"{domain}_expertise", 0.8, 0.1, 1.0, 0.15,
                f"Specialization level for {domain}",
            ))
            domain_capsule.add_gene(Gene(
                f"{domain}_autonomy", 0.5, 0.1, 1.0, 0.12,
                f"Autonomy level for {domain} tasks",
            ))
            new_genome.add_capsule(domain_capsule)
        
        agent = AgentPersonality(
            name=name,
            description=description,
            domain=domain,
            genome=new_genome,
        )
        self.agents[name] = agent
        
        logger.info("Created sub-agent '%s' (domain=%s, genes=%d)",
                     name, domain, len(new_genome.get_all_genes()))
        return agent
    
    def record_task_result(
        self,
        agent_name: str,
        success: bool,
        response_time_ms: float,
        error_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a task result for a sub-agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}
        
        agent.task_count += 1
        
        # Update success rate
        alpha = 1.0 / (agent.task_count + 1)
        agent.success_rate = (1 - alpha) * agent.success_rate + alpha * (1.0 if success else 0.0)
        
        # Log through evolution lab
        result = self.evolution_lab.log_action(
            action=f"agent_{agent_name}",
            domain=agent.domain,
            success=success,
            response_time_ms=response_time_ms,
            agent_id=agent_name,
            error_type=error_type,
        )
        
        return result
    
    def get_agent_report(self) -> str:
        """Get a report on all sub-agents."""
        if not self.agents:
            return "No sub-agents created."
        
        lines = ["=" * 60, "🤖 SUB-AGENT POPULATION REPORT", "=" * 60]
        for name, agent in self.agents.items():
            lines.extend([
                f"\nAgent: {name}",
                f"  Domain: {agent.domain}",
                f"  Description: {agent.description}",
                f"  Tasks Completed: {agent.task_count}",
                f"  Success Rate: {agent.success_rate:.1%}",
                f"  Genome Genes: {len(agent.genome.get_all_genes())}",
                f"  Generation: {agent.genome.generation}",
            ])
            genes = agent.genome.get_all_genes()
            if genes:
                lines.append("  Key Parameters:")
                for g in genes[:5]:
                    lines.append(f"    {g.name} = {g.value:.3f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)