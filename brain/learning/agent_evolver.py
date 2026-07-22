# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Agent Evolver
=============
Dynamically creates and evolves sub-agents with domain specialization.
Extended with military domain agents.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .genome import Genome, GenomeEngine, Gene, Capsule
from .evolution_lab import EvolutionLab

logger = logging.getLogger("Ultrone.Brain.Learning.AgentEvolver")


# Military domain types for specialization
MILITARY_DOMAINS = ["air", "land", "sea", "cyber", "space"]


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
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "created_at": self.created_at,
            "task_count": self.task_count,
            "success_rate": self.success_rate,
            "genome_generation": self.genome.generation,
            "active_genes": len(self.genome.get_all_genes()),
        }


class AgentEvolver:
    """
    Creates and manages a population of specialized sub-agents.
    
    Each sub-agent has its own genome with domain-specific capsules,
    and can evolve independently based on its task performance.
    Extended with military domain specialization.
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
            domain_capsule = self._create_domain_capsule(domain)
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
    
    def _create_domain_capsule(self, domain: str) -> Capsule:
        """Create domain-specific gene capsule for an agent."""
        if domain == "air":
            capsule = Capsule(
                name="air",
                description="Air domain specialized operations",
            )
            capsule.add_gene(Gene("air_superiority_bias", 0.8, 0.3, 1.0, 0.15, "Preference for air-to-air over air-to-ground"))
            capsule.add_gene(Gene("patrol_efficiency", 0.75, 0.2, 1.0, 0.12, "Fuel-efficient patrol patterns"))
        
        elif domain == "land":
            capsule = Capsule(
                name="land",
                description="Land domain specialized operations",
            )
            capsule.add_gene(Gene("armor_versus_infantry", 0.6, 0.3, 0.9, 0.10, "Focus on armored targets"))
            capsule.add_gene(Gene("cover_discipline", 0.8, 0.4, 1.0, 0.12, "Use of terrain cover"))
        
        elif domain == "sea":
            capsule = Capsule(
                name="sea",
                description="Naval domain specialized operations",
            )
            capsule.add_gene(Gene("asw_focus", 0.7, 0.2, 1.0, 0.15, "Anti-submarine warfare focus"))
            capsule.add_gene(Gene("surface_engagement", 0.75, 0.3, 1.0, 0.12, "Surface target engagement priority"))
        
        elif domain == "cyber":
            capsule = Capsule(
                name="cyber",
                description="Cyber warfare specialized operations",
            )
            capsule.add_gene(Gene("stealth_priority", 0.9, 0.5, 1.0, 0.10, "Maintain anonymity during ops"))
            capsule.add_gene(Gene("persistence_factor", 0.8, 0.3, 1.0, 0.12, "Long-term presence vs quick strike"))
        
        elif domain == "space":
            capsule = Capsule(
                name="space",
                description="Space operations specialized",
            )
            capsule.add_gene(Gene("orbital_maneuver", 0.7, 0.3, 1.0, 0.15, "Precision of orbital changes"))
            capsule.add_gene(Gene("sensor_dwell_time", 5.0, 1.0, 30.0, 0.12, "Time spent imaging target"))
        
        else:
            capsule = Capsule(
                name="general",
                description="General operations",
            )
            capsule.add_gene(Gene("general_efficiency", 0.5, 0.1, 1.0, 0.15, "Baseline efficiency"))
        
        return capsule
    
    def record_task_result(
        self,
        agent_name: str,
        success: bool,
        response_time_ms: float,
        error_type: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a task result for a sub-agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"Agent '{agent_name}' not found"}
        
        agent.task_count += 1
        
        # Update success rate (exponential moving average)
        alpha = 1.0 / (agent.task_count + 1)
        agent.success_rate = (1 - alpha) * agent.success_rate + alpha * (1.0 if success else 0.0)
        
        # Log through evolution lab
        result = self.evolution_lab.log_action(
            action=f"agent_{agent_name}",
            domain=domain or agent.domain,
            success=success,
            response_time_ms=response_time_ms,
            agent_id=agent_name,
            error_type=error_type,
        )
        
        return result
    
    def create_domain_agents(self, base_name: str = "agent") -> List[AgentPersonality]:
        """Create agents for all military domains."""
        agents = []
        for domain in MILITARY_DOMAINS:
            agent = self.create_agent(
                name=f"{base_name}_{domain}",
                domain=domain,
                description=f"Specialized {domain} operations agent",
            )
            agents.append(agent)
        return agents
    
    def get_best_agent_for_domain(self, domain: str) -> Optional[AgentPersonality]:
        """Get the highest-performing agent for a domain."""
        domain_agents = [a for a in self.agents.values() if a.domain == domain]
        if not domain_agents:
            return None
        return max(domain_agents, key=lambda a: a.success_rate)
    
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