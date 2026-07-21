# Copyright (c) Ultrone Contributors. All rights reserved.
"""Course of Action generation and scoring."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import random

logger = logging.getLogger("Ultrone.Brain.Reasoning.COA")


@dataclass
class CourseOfAction:
    """A tactical plan to achieve an objective."""
    coa_id: str
    name: str
    description: str
    domain: str
    phases: List[str]  # Actions to take
    required_assets: List[str]  # Asset types needed
    estimated_time_ms: float
    risk_level: float  # 0.0-1.0
    
    # Scoring axes (0.0-1.0)
    effectiveness_score: float = 0.0
    efficiency_score: float = 0.0
    surprise_score: float = 0.0
    simplicity_score: float = 0.0
    sustainability_score: float = 0.0
    scalability_score: float = 0.0
    
    def get_total_score(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "effectiveness": 0.25,
            "efficiency": 0.15,
            "surprise": 0.15,
            "simplicity": 0.10,
            "sustainability": 0.20,
            "scalability": 0.15,
        }
        return (
            self.effectiveness_score * weights["effectiveness"] +
            self.efficiency_score * weights["efficiency"] +
            self.surprise_score * weights["surprise"] +
            self.simplicity_score * weights["simplicity"] +
            self.sustainability_score * weights["sustainability"] +
            self.scalability_score * weights["scalability"]
        )
    
    def to_dict(self) -> dict:
        return {
            "coa_id": self.coa_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "total_score": self.get_total_score(),
            "risk_level": self.risk_level,
            "estimated_time_ms": self.estimated_time_ms,
        }


class COAScorer:
    """Reviews and scores COAs against effectiveness criteria."""
    
    def __init__(self):
        self.scoring_history: List[Dict] = []
    
    def score(self, coa: CourseOfAction, context: Dict[str, Any] = None) -> CourseOfAction:
        """Score a COA based on context and effectiveness factors."""
        # Simulate scoring based on context
        context = context or {}
        
        # Adjust scores based on enemy disposition if available
        enemy_strength = context.get("enemy_strength", 0.5)
        friendly_strength = context.get("friendly_strength", 0.8)
        
        # Effectiveness - how well it achieves the objective
        coa.effectiveness_score = min(1.0, friendly_strength / max(0.1, enemy_strength))
        
        # Efficiency - resource utilization
        coa.efficiency_score = random.uniform(0.4, 0.95)
        
        # Surprise - unexpected nature
        coa.surprise_score = random.uniform(0.3, 0.9)
        
        # Simplicity - ease of execution
        coa.simplicity_score = random.uniform(0.5, 0.95)
        
        # Sustainability - can maintain over time
        coa.sustainability_score = random.uniform(0.4, 0.9)
        
        # Scalability - can expand if needed
        coa.scalability_score = random.uniform(0.3, 0.85)
        
        return coa


class COAGenerator:
    """
    Generates multiple Courses of Action for a given situation.
    
    Creates 3+ COAs with different approaches.
    """
    
    def __init__(self):
        self._scorer = COAScorer()
    
    def generate(self, target_info: Dict[str, Any], context: Dict[str, Any] = None) -> List[CourseOfAction]:
        """Generate COAs for a target."""
        target_type = target_info.get("type", "unknown")
        domain = target_info.get("domain", "air")
        
        coas = []
        
        # COA 1: Direct approach
        coas.append(CourseOfAction(
            coa_id=f"COA-DIRECT-{random.randint(1000, 9999)}",
            name="Direct Engagement",
            description="Use primary assets directly against target",
            domain=domain,
            phases=["locate", "track", "engage", "assess"],
            required_assets=["primary"],
            estimated_time_ms=random.uniform(10000, 60000),
            risk_level=random.uniform(0.4, 0.8),
        ))
        
        # COA 2: Standoff approach
        coas.append(CourseOfAction(
            coa_id=f"COA-STANDOFF-{random.randint(1000, 9999)}",
            name="Standoff Attack",
            description="Use long-range weapons to engage from distance",
            domain=domain,
            phases=["locate", "track", "standoff_engage", "assess"],
            required_assets=["long_range"],
            estimated_time_ms=random.uniform(15000, 90000),
            risk_level=random.uniform(0.2, 0.5),
        ))
        
        # COA 3: Coordinated approach
        coas.append(CourseOfAction(
            coa_id=f"COA-COORD-{random.randint(1000, 9999)}",
            name="Coordinated Multi-Domain",
            description="Use assets from multiple domains for saturation",
            domain="all",
            phases=["locate", "coordinate", "multi_domain_engage", "assess"],
            required_assets=["multi_domain"],
            estimated_time_ms=random.uniform(30000, 120000),
            risk_level=random.uniform(0.3, 0.7),
        ))
        
        # Additional COA: Asymmetric/Evasive
        coas.append(CourseOfAction(
            coa_id=f"COA-EVASIVE-{random.randint(1000, 9999)}",
            name="Asymmetric Approach",
            description="Use unconventional tactics to exploit weaknesses",
            domain=domain,
            phases=["recon", "exploit_weakness", "precision_strike", "assess"],
            required_assets=["specialized"],
            estimated_time_ms=random.uniform(20000, 100000),
            risk_level=random.uniform(0.5, 0.9),
        ))
        
        # Score all COAs
        for coa in coas:
            self._scorer.score(coa, context)
        
        # Sort by score descending
        coas.sort(key=lambda c: c.get_total_score(), reverse=True)
        
        return coas
    
    def select_best(self, coas: List[CourseOfAction]) -> Optional[CourseOfAction]:
        """Select the highest-scoring COA."""
        if not coas:
            return None
        return coas[0]