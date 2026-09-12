# Copyright (c) Ultrone Contributors. All rights reserved.
"""Base interfaces for AI decision architectures.

This module provides unified abstract interfaces for all decision-making
architectures (Behavior Trees, GOAP, FSM, Utility AI, BDI), enabling
dynamic selection and hybridization of architectures based on context.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.AI.Architectures.Base")


class AIArchitectureConfig:
    """Base configuration for AI architectures."""
    def __init__(self, name: str = "base", **kwargs):
        self.name = name
        for key, value in kwargs.items():
            setattr(self, key, value)


class DecisionArchitecture:
    """Unified interface for all decision-making architectures.
    
    All decision architectures (BehaviorTree, GOAP, FSM, UtilityAI, BDI)
    can implement this interface to enable dynamic selection and hybridization.
    """

    def __init__(self, config: Optional[AIArchitectureConfig] = None):
        self.config = config or AIArchitectureConfig()
        self._last_action: Any = None

    def decide(self, state: Dict[str, Any], goals: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a decision given current state, goals, and context.
        
        Parameters
        ----------
        state : Dict[str, Any]
            Current world state (observations, sensor data, etc.)
        goals : List[str], optional
            Active goals/objectives to achieve
        context : Dict[str, Any], optional
            Additional context (threat level, terrain, resources, etc.)
            
        Returns
        -------
        Dict[str, Any]
            Decision/action to execute with metadata
        """
        raise NotImplementedError(f"{type(self).__name__} must implement decide()")

    def reset(self) -> None:
        """Reset architecture to initial state."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about architecture performance."""
        return {
            "type": type(self).__name__,
            "last_action": self._last_action,
        }


# Backward compatibility alias
AIArchitecture = DecisionArchitecture
AIArchitectureConfig = AIArchitectureConfig


class ArchitectureRouter:
    """Routes decision-making to optimal architecture based on context.
    
    Uses a meta-learner to select the best architecture for each situation,
    enabling hybrid decision-making that adapts to scenario requirements.
    
    Example
    -------
    >>> router = ArchitectureRouter()
    >>> router.register("behavior_tree", BehaviorTree(config), metadata)
    >>> router.register("goap", GOAP(config), metadata)
    >>> arch = router.select_architecture(context)
    >>> decision = arch.decide(state, goals, context)
    """

    def __init__(self):
        self.architectures: Dict[str, DecisionArchitecture] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._selection_history: List[tuple] = []

    def register(self, name: str, architecture: DecisionArchitecture, metadata: Dict[str, Any]) -> None:
        """Register an architecture with its capabilities.
        
        Parameters
        ----------
        name : str
            Unique architecture identifier
        architecture : DecisionArchitecture
            Architecture instance
        metadata : Dict[str, Any]
            Capability metadata (domains, sample_complexity, latency, etc.)
        """
        self.architectures[name] = architecture
        self.metadata[name] = metadata
        logger.info(f"Registered architecture: {name}")

    def select_architecture(self, context: Dict[str, Any]) -> DecisionArchitecture:
        """Select optimal architecture for given context.
        
        Parameters
        ----------
        context : Dict[str, Any]
            Scenario context (domain, threat_level, time_pressure, etc.)
            
        Returns
        -------
        DecisionArchitecture
            Selected architecture instance
        """
        # Simple rule-based selection (can be replaced with meta-learner)
        domain = context.get("domain", "default")
        threat_level = context.get("threat_level", 0.0)
        time_pressure = context.get("time_pressure", False)
        
        # Select based on context
        if domain == "tactical" and threat_level > 0.7:
            # High threat → reactive architectures
            if "behavior_tree" in self.architectures:
                self._selection_history.append(("behavior_tree", context))
                return self.architectures["behavior_tree"]
        
        elif domain == "strategic" and not time_pressure:
            # Strategic planning → deliberative architectures
            if "goap" in self.architectures:
                self._selection_history.append(("goap", context))
                return self.architectures["goap"]
        
        elif domain == "reactive":
            # Fast response → utility AI or FSM
            if "utility_ai" in self.architectures:
                self._selection_history.append(("utility_ai", context))
                return self.architectures["utility_ai"]
        
        # Default: return first available architecture
        if self.architectures:
            first_name = list(self.architectures.keys())[0]
            self._selection_history.append((first_name, context))
            return self.architectures[first_name]
        
        raise RuntimeError("No architectures registered")

    def get_stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        return {
            "num_architectures": len(self.architectures),
            "architecture_names": list(self.architectures.keys()),
            "selection_history_length": len(self._selection_history),
            "recent_selections": self._selection_history[-10:],
        }