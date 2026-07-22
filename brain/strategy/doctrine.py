# Copyright (c) Ultrone Contributors. All rights reserved.
"""Doctrine - rules of engagement and tactical rules."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

from ...config.doctrine_presets import DoctrinePreset, DoctrineType
from ...data.entities import Contact, ThreatLevel


class ROE(Enum):
    """Rules of Engagement levels."""
    WEAPONS_HOLD = "weapons_hold"
    WEAPONS_TIGHT = "weapons_tight"
    WEAPONS_FREE = "weapons_free"
    IMMEDIATE_ACTION = "immediate_action"


class EngagementRules:
    """Specific rules for when to engage targets."""
    
    def __init__(self, roe: ROE):
        self.roe = roe
        self._rules = self._load_rules(roe)
    
    def _load_rules(self, roe: ROE) -> Dict[str, any]:
        """Load engagement rules based on ROE."""
        if roe == ROE.WEAPONS_HOLD:
            return {
                "engage_immediate": False,
                "require_positive_id": True,
                "collateral_threshold": 0.0,  # No collateral allowed
                "self_defense_only": True,
            }
        elif roe == ROE.WEAPONS_TIGHT:
            return {
                "engage_immediate": True,
                "require_positive_id": True,
                "collateral_threshold": 0.1,  # 10% max
                "self_defense_only": False,
            }
        elif roe == ROE.WEAPONS_FREE:
            return {
                "engage_immediate": True,
                "require_positive_id": False,
                "collateral_threshold": 0.25,  # 25% max
                "self_defense_only": False,
            }
        else:
            return {
                "engage_immediate": True,
                "require_positive_id": False,
                "collateral_threshold": 0.5,
                "self_defense_only": False,
            }
    
    def can_engage(self, contact: Contact, context: Dict = None) -> bool:
        """Check if target can be engaged under current ROE."""
        context = context or {}
        
        if self._rules["engage_immediate"]:
            return True
        
        if self._rules["self_defense_only"]:
            # Only engage if posing imminent threat
            if contact.threat_level in [ThreatLevel.IMMINENT, ThreatLevel.CRITICAL]:
                return True
        
        if self._rules["require_positive_id"]:
            # Would check for positive ID
            if context.get("friendly_bleed_through", False):
                return False
        
        return True


class Doctrine:
    """
    Rules of engagement and tactical doctrine.
    
    Integrates with DoctrinePreset to apply tactical behavior.
    """
    
    def __init__(self, preset: Optional[DoctrinePreset] = None):
        self.preset = preset or DoctrinePreset(
            name="Default",
            doctrine_type=DoctrineType.BALANCED,
            description="Balanced doctrine",
            aggression=0.5, risk_tolerance=0.5,
            initiative=0.5, conservation=0.5,
            detection_sensitivity=0.7,
            confirmation_threshold=0.7,
            engage_on_sight=False,
            prefer_standoff=True,
            innovation_rate=0.3,
        )
        
        # Default to weapons tight
        self.roe = EngagementRules(ROE.WEAPONS_TIGHT)
    
    def set_roe(self, roe: ROE) -> None:
        """Set Rules of Engagement."""
        self.roe = EngagementRules(roe)
    
    def should_engage(self, contact: Contact, context: Dict = None) -> bool:
        """Determine if contact should be engaged."""
        context = context or {}
        
        # Check ROE
        if not self.roe.can_engage(contact, context):
            return False
        
        # Check doctrine aggression threshold
        threat_score = context.get("threat_score", 0.5)
        if threat_score < self.preset.aggression_threshold:
            return False
        
        # Check if we prefer standoff
        if self.preset.prefer_standoff and context.get("close_range", True):
            # Would look for standoff options
            pass
        
        return True
    
    def get_engagement_delay(self) -> float:
        """Get delay before engagement based on doctrine."""
        # More cautious doctrines have longer delays
        base_delay = 0.2  # seconds
        if self.preset.doctrine_type == DoctrineType.DEFENSIVE:
            return base_delay * 2
        elif self.preset.doctrine_type == DoctrineType.AGGRESSIVE:
            return base_delay * 0.5
        return base_delay
    
    def to_dict(self) -> dict:
        return {
            "name": self.preset.name,
            "doctrine_type": self.preset.doctrine_type.value,
            "roe": self.roe.roe.value,
            "aggression": self.preset.aggression,
            "risk_tolerance": self.preset.risk_tolerance,
        }
    
    def get_stats(self) -> dict:
        return {
            "name": self.preset.name,
            "doctrine_type": self.preset.doctrine_type.value,
            "roe": self.roe.roe.value,
        }