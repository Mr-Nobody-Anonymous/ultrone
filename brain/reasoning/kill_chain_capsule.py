# Copyright (c) Ultrone Contributors. All rights reserved.
"""Kill Chain Capsule - domain-specific evolution capsule for F2T2EA optimization.

Active evolution happens mid-battle when patterns are detected.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("Ultrone.Brain.Reasoning.KillChainCapsule")


@dataclass
class KillChainCapsule:
    """
    Kill Chain Capsule - active evolution parameters for F2T2EA execution.
    
    This capsule holds the evolvable parameters that directly affect the speed
    and accuracy of kill chain phases during active engagement. When a pattern
    is detected with >80% confidence, this capsule mutates to adapt to the
    specific threat type.
    
    Parameters:
    - target_confirmation_threshold: Confidence needed for target ID (lower = faster locks)
    - f2t2ea_phase_speed: Speed of kill chain phase transitions (higher = faster)
    - bda_rigor: Battle Damage Assessment thoroughness
    - reengage_decision_speed: Seconds between re-engagement checks
    """
    
    # Core parameters
    target_confirmation_threshold: float = 0.7  # Confidence threshold for target ID
    f2t2ea_phase_speed: float = 0.8  # Speed multiplier for phase transitions
    bda_rigor: float = 0.85  # Battle damage assessment thoroughness
    reengage_decision_speed: float = 2.0  # Time between re-engagement checks
    
    # Domain-specific adaptations
    domain_adaptations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Mutation tracking
    last_mutation_tick: int = 0
    mutation_reason: str = ""
    
    @classmethod
    def from_genome_genes(cls, genes: List[Any]) -> "KillChainCapsule":
        """Create a capsule from genome genes."""
        params = {
            "target_confirmation_threshold": 0.7,
            "f2t2ea_phase_speed": 0.8,
            "bda_rigor": 0.85,
            "reengage_decision_speed": 2.0,
        }
        
        for gene in genes:
            if gene.name in params:
                params[gene.name] = gene.value
        
        return cls(**params)
    
    def to_dict(self) -> dict:
        """Export capsule state as dict."""
        return {
            "target_confirmation_threshold": self.target_confirmation_threshold,
            "f2t2ea_phase_speed": self.f2t2ea_phase_speed,
            "bda_rigor": self.bda_rigor,
            "reengage_decision_speed": self.reengage_decision_speed,
            "domain_adaptations": self.domain_adaptations,
            "last_mutation_tick": self.last_mutation_tick,
            "mutation_reason": self.mutation_reason,
        }
    
    def mutate_for_pattern(
        self,
        pattern_domain: str,
        pattern_description: str,
        tick: int,
        mutation_strength: float = 1.0,
    ) -> bool:
        """
        Mutate capsule parameters for a specific threat pattern.
        
        Active evolution - changes happen mid-battle!
        """
        self.last_mutation_tick = tick
        self.mutation_reason = pattern_description
        mutated = False
        
        # Initialize domain adaptation if not exists
        if pattern_domain not in self.domain_adaptations:
            self.domain_adaptations[pattern_domain] = {
                "speed_multiplier": 1.0,
                "threshold_reduction": 0.0,
            }
        
        # Lower threshold for faster target confirmation against this threat
        old_threshold = self.target_confirmation_threshold
        self.target_confirmation_threshold = max(0.5, old_threshold - (0.15 * mutation_strength))
        
        if old_threshold != self.target_confirmation_threshold:
            logger.info(
                f"⚡ ACTIVE MUTATION: target_confirmation_threshold {old_threshold:.3f} -> "
                f"{self.target_confirmation_threshold:.3f} (domain: {pattern_domain})"
            )
            mutated = True
        
        # Increase phase speed for quicker response
        old_speed = self.f2t2ea_phase_speed
        self.f2t2ea_phase_speed = min(1.0, old_speed + (0.2 * mutation_strength))
        
        # Track adaptation for this domain
        self.domain_adaptations[pattern_domain]["speed_multiplier"] = self.f2t2ea_phase_speed
        self.domain_adaptations[pattern_domain]["threshold_reduction"] = old_threshold - self.target_confirmation_threshold
        
        if old_speed != self.f2t2ea_phase_speed:
            logger.info(
                f"⚡ ACTIVE MUTATION: f2t2ea_phase_speed {old_speed:.3f} -> "
                f"{self.f2t2ea_phase_speed:.3f} (domain: {pattern_domain})"
            )
            mutated = True
        
        return mutated
    
    def apply_to_kill_chain(self, kill_chain: Any, target_id: str) -> None:
        """
        Apply capsule parameters to an active kill chain.
        
        This is the key: the brain physically changes its parameters mid-battle!
        """
        # Update the kill chain's phase speed for this target
        if hasattr(kill_chain, "chains") and target_id in kill_chain.chains:
            chain = kill_chain.chains[target_id]
            # The phase speed affects timeout calculations
            if hasattr(chain, "max_duration_ms"):
                # Reduce max duration based on phase speed
                base_timeout = 300000  # 5 minutes base
                new_timeout = int(base_timeout / max(0.1, self.f2t2ea_phase_speed))
                old_timeout = chain.max_duration_ms
                chain.max_duration_ms = new_timeout
                logger.info(
                    f"⚡ APPLYING MUTATION to kill chain {target_id}: "
                    f"timeout {old_timeout}ms -> {new_timeout}ms"
                )


class ActiveEvolutionManager:
    """
    Manages active evolution during OODA loop.
    
    Listens for pattern detections and mutates kill chain capsules
    in real-time during battle.
    """
    
    def __init__(self, genome_engine: Any, kill_chain: Any):
        self.genome_engine = genome_engine
        self.kill_chain = kill_chain
        self.capsule: Optional[KillChainCapsule] = None
        self._initialized = False
    
    def initialize_capsule(self, agent_id: str = "orchestrator") -> None:
        """Initialize the kill chain capsule from the active genome."""
        if self.genome_engine.active_genome:
            genes = self.genome_engine.active_genome.get_all_genes()
            kill_chain_genes = [
                g for g in genes 
                if g.capsule == "kill_chain_efficiency"
            ]
            if kill_chain_genes:
                self.capsule = KillChainCapsule.from_genome_genes(kill_chain_genes)
                self._initialized = True
                logger.info("ActiveEvolutionManager: KillChainCapsule initialized")
    
    def process_pattern(
        self,
        pattern: Any,
        tick: int,
        threatening_contacts: List[Any],
    ) -> bool:
        """
        Process a detected pattern and mutate accordingly.
        
        This is called during the Orient phase of OODA loop.
        Returns True if mutation was applied.
        """
        if not self.capsule:
            # Try to initialize on-demand
            self.initialize_capsule()
            if not self.capsule:
                return False
        
        # Only mutate if confidence > 80%
        if pattern.confidence <= 0.8:
            return False
        
        # Mutate the capsule
        self.capsule.mutate_for_pattern(
            pattern_domain=pattern.domain,
            pattern_description=pattern.description,
            tick=tick,
            mutation_strength=pattern.confidence,  # Stronger patterns = stronger mutations
        )
        
        # Apply to ALL active kill chains in that domain
        self._apply_to_active_kill_chains(pattern.domain, threatening_contacts)
        
        # Sync back to genome if it exists
        self._sync_to_genome()
        
        return True
    
    def _apply_to_active_kill_chains(self, domain: str, contacts: List[Any]) -> None:
        """Apply capsule parameters to active kill chains for the threat domain."""
        # Get contact IDs for this domain
        domain_contact_ids = []
        for contact in contacts:
            if hasattr(contact, "contact") and contact.contact.domain.value == domain:
                domain_contact_ids.append(contact.contact.contact_id)
            elif hasattr(contact, "domain") and contact.domain.value == domain:
                domain_contact_ids.append(contact.contact_id)
        
        # Apply to each active kill chain
        for target_id in domain_contact_ids:
            if target_id in self.kill_chain.chains:
                self.capsule.apply_to_kill_chain(self.kill_chain, target_id)
        
        # Also apply to composite chains
        for target_id, composite in getattr(self.kill_chain, "engagements", {}).items():
            if hasattr(composite, "domain") and composite.domain == domain:
                # Could apply to composite kill chain phases here
                pass
    
    def _sync_to_genome(self) -> None:
        """Sync capsule state back to the genome after mutation."""
        if not self.genome_engine.active_genome or not self.capsule:
            return
        
        capsule_dict = self.capsule.to_dict()
        
        # Update genome genes
        for gene in self.genome_engine.active_genome.get_all_genes():
            gene_name = gene.name
            if gene_name in capsule_dict and gene.capsule == "kill_chain_efficiency":
                old_value = gene.value
                gene.value = capsule_dict[gene_name]
                if old_value != gene.value:
                    logger.info(
                        f"🧬 SYNCED to genome: {gene_name} {old_value:.3f} -> {gene.value:.3f}"
                    )
    
    def get_capability(self, capability_name: str) -> float:
        """Get current capability value for use by other systems."""
        if not self.capsule:
            return 0.0
        
        if capability_name == "target_confirmation_threshold":
            return self.capsule.target_confirmation_threshold
        elif capability_name == "f2t2ea_phase_speed":
            return self.capsule.f2t2ea_phase_speed
        elif capability_name == "bda_rigor":
            return self.capsule.bda_rigor
        
        return 0.0