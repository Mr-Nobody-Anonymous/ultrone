# Copyright (c) Ultrone Contributors. All rights reserved.
"""Capability-based registry for RL algorithms with metadata.

This module provides a registry system for RL algorithms that supports
querying by capabilities (discrete/continuous actions, multi-agent, etc.)
rather than just by name.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Learning.RL.Registry")


@dataclass
class RLAlgorithmMetadata:
    """Metadata describing RL algorithm capabilities."""
    name: str
    supports_discrete: bool = False
    supports_continuous: bool = False
    supports_multiagent: bool = False
    model_based: bool = False
    offline_capable: bool = False
    sample_efficiency: str = "medium"  # high/medium/low
    description: str = ""


class RLAlgorithmRegistry:
    """Registry for RL algorithms with capability-based querying.
    
    Example
    -------
    >>> registry = RLAlgorithmRegistry()
    >>> registry.register(PPOAdapter, RLAlgorithmMetadata(
    ...     name="PPO",
    ...     supports_discrete=True,
    ...     supports_continuous=True,
    ...     sample_efficiency="medium"
    ... ))
    >>> matching = registry.query(["supports_continuous", "supports_discrete"])
    >>> print(matching)  # ["PPO"]
    """

    def __init__(self):
        self._algorithms: Dict[str, Any] = {}
        self._metadata: Dict[str, RLAlgorithmMetadata] = {}

    def register(self, algorithm: Any, meta: RLAlgorithmMetadata) -> None:
        """Register an RL algorithm with metadata.
        
        Parameters
        ----------
        algorithm : Any
            RL algorithm class or factory
        meta : RLAlgorithmMetadata
            Algorithm capabilities and description
        """
        self._algorithms[meta.name] = algorithm
        self._metadata[meta.name] = meta
        logger.info(f"Registered RL algorithm: {meta.name}")

    def unregister(self, name: str) -> None:
        """Remove an algorithm from the registry."""
        if name in self._algorithms:
            del self._algorithms[name]
            del self._metadata[name]
            logger.info(f"Unregistered RL algorithm: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Get algorithm by name."""
        return self._algorithms.get(name)

    def query(self, capabilities: List[str]) -> List[str]:
        """Find algorithms matching all required capabilities.
        
        Parameters
        ----------
        capabilities : List[str]
            List of required capability attribute names
            
        Returns
        -------
        List[str]
            Names of algorithms matching all capabilities
        """
        matching = []
        for name, meta in self._metadata.items():
            if all(getattr(meta, cap, False) for cap in capabilities):
                matching.append(name)
        return matching

    def get_metadata(self, name: str) -> Optional[RLAlgorithmMetadata]:
        """Get metadata for an algorithm."""
        return self._metadata.get(name)

    def list_all(self) -> List[str]:
        """List all registered algorithm names."""
        return list(self._algorithms.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "total_algorithms": len(self._algorithms),
            "algorithms": self.list_all(),
            "capabilities": {
                "discrete": self.query(["supports_discrete"]),
                "continuous": self.query(["supports_continuous"]),
                "multiagent": self.query(["supports_multiagent"]),
                "model_based": self.query(["model_based"]),
                "offline": self.query(["offline_capable"]),
            }
        }


# Global registry instance
_registry = RLAlgorithmRegistry()


def register(algorithm: Any, meta: RLAlgorithmMetadata) -> None:
    """Register an algorithm in the global registry."""
    _registry.register(algorithm, meta)


def query(capabilities: List[str]) -> List[str]:
    """Query global registry for algorithms matching capabilities."""
    return _registry.query(capabilities)


def get(name: str) -> Optional[Any]:
    """Get algorithm from global registry by name."""
    return _registry.get(name)


def get_registry() -> RLAlgorithmRegistry:
    """Get the global registry instance."""
    return _registry