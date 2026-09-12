# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Enhanced Ultrone core with Self-Evolution capabilities.
Integrated with:
- Genome Evolution Protocol (GEP) engine — treats agent logic as genes/capsules
- Performance Telemetry — continuous monitoring and failure analysis
- Evolution Lab — automated evolution cycles with zero human intervention
- Agent Evolver — dynamic sub-agent creation and autonomous self-improvement

Inspired by:
- A-Evolve: Universal infrastructure for evolving AI agents
- evolver (GEP): Genome Evolution Protocol
- Agent Zero: Dynamic sub-agent creation
- SuperAGI: Performance telemetry loop
"""
# --- Monorepo import bootstrap (see _ultrone_paths) ---
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent
while not (_ROOT / "pyproject.toml").is_file() and _ROOT != _ROOT.parent:
    _ROOT = _ROOT.parent
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
from _ultrone_paths import ensure_on_syspath  # noqa: E402
ensure_on_syspath(_ROOT)
del _sys, _Path, _ROOT

import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from ultron.config import UltronConfig, default_config
from ultron.core.models import MemoryRecord, MemoryType, MemoryTier, MemoryStatus, KnowledgeCluster, EvolutionRecord
from evolution import (
    EvolutionLab,
    EvolutionConfig,
    GenomeEngine,
    Genome,
    PerformanceTelemetry,
)

logger = logging.getLogger("Ultrone")


class Ultrone:
    """
    Self-evolving AI agent core.
    
    Features:
    - Autonomous genome evolution based on performance telemetry
    - Multi-capsule architecture for domain-specific parameters
    - Automated mutation/crossover cycles when fitness drops
    - Failure pattern analysis and adaptive optimization
    - Cross-generation knowledge retention
    """
    
    def __init__(self, config=None):
        self.config = config or default_config
        self.config.ensure_directories()
        if not hasattr(self.config, "reasoning_depth"):
            self.config.reasoning_depth = 5
        if not hasattr(self.config, "prediction_confidence_threshold"):
            self.config.prediction_confidence_threshold = 0.7
        
        self._memories = {}
        self._clusters = {}
        self._evolution_history = []
        
        # ── Initialize Self-Evolution Infrastructure ──
        self.evolution_config = EvolutionConfig(
            enabled=getattr(self.config, 'evolution_enabled', True),
            auto_evolve=True,
            evolution_interval_actions=10,
            min_fitness_threshold=getattr(self.config, 'min_fitness_threshold', 0.75),
            population_size=10,
            mutation_strategy="adaptive",
            crossover_strategy="blend",
            selection_strategy="tournament",
            telemetry_window_size=100,
        )
        
        self.evolution_lab = EvolutionLab(config=self.evolution_config)
        self.evolution_lab.initialize(agent_id="ultrone-agent")
        
        logger.info(
            "🧬 Ultrone initialized with Self-Evolution: %d capsules, %d genes",
            len(self.evolution_lab.genome_engine.active_genome.capsules),
            len(self.evolution_lab.genome_engine.active_genome.get_all_genes()),
        )

    def think(self, query, context=None):
        """
        Analyze a query and return predictions.
        
        Leverages evolved genome parameters for decision making.
        """
        context = context or {}
        predictions = []
        params = self.evolution_lab.get_genome_parameters()
        
        # Use evolved parameters for prediction sensitivity
        pattern_sensitivity = params.get("pattern_sensitivity", 0.7)
        innovation_rate = params.get("innovation_rate", 0.3)
        
        if getattr(self.config, "prediction_enabled", False):
            query_lower = query.lower()
            
            # Pattern detection with evolved sensitivity
            if any(kw in query_lower for kw in ["error", "bug", "exception", "fail", "crash"]):
                confidence = 0.7 + (pattern_sensitivity * 0.2)
                predictions.append({
                    "id": str(uuid.uuid4()),
                    "prediction_text": "Similar errors may recur - consider preventive patterns",
                    "confidence": round(confidence, 2),
                    "actionable": True,
                    "category": "error_prevention",
                })
            
            if any(kw in query_lower for kw in ["pattern", "recurring"]):
                confidence = 0.7 + (innovation_rate * 0.25)
                predictions.append({
                    "id": str(uuid.uuid4()),
                    "prediction_text": "Detected recurring pattern - clustering for crystallization",
                    "confidence": round(confidence, 2),
                    "actionable": True,
                    "category": "clustering",
                })
        
        # Log this thinking action to telemetry
        self.evolution_lab.log_action(
            action="think",
            domain="reasoning",
            success=True,
            response_time_ms=50.0,  # Placeholder
        )
        
        return {
            "query": query,
            "conclusion": {"action": "proceed"},
            "predictions": predictions,
            "confidence": 0.7,
            "genome_generation": self.evolution_lab.genome_engine.generation,
        }

    def remember(self, content, context="", resolution="", tags=None, memory_type="pattern"):
        """Store a memory record with prediction confidence."""
        tags = tags or []
        pred_conf = 0.5
        
        # Use evolved pattern sensitivity
        params = self.evolution_lab.get_genome_parameters()
        pattern_sens = params.get("pattern_sensitivity", 0.7)
        
        if ":" in content or "error" in content.lower():
            pred_conf += 0.15 * (1 + pattern_sens)
        pred_conf = min(1.0, pred_conf)
        
        auto_tags = list(tags)
        if "error" in content.lower():
            auto_tags.append("error")
        
        record = MemoryRecord(
            id=str(uuid.uuid4()), memory_type=memory_type, content=content,
            context=context, resolution=resolution, tier=MemoryTier.WARM.value,
            hit_count=1, status=MemoryStatus.ACTIVE.value, tags=auto_tags,
            embedding=[],
            summary_l0=content[:100], overview_l1=content[:200],
        )
        self._memories[record.id] = record
        
        # Track memory retention
        self.evolution_lab.log_action(
            action="remember",
            domain="memory",
            success=True,
            response_time_ms=10.0,
        )
        
        return record

    def predict(self, content):
        """Generate predictions for a given content using evolved parameters."""
        params = self.evolution_lab.get_genome_parameters()
        innovation = params.get("innovation_rate", 0.3)
        
        self.evolution_lab.log_action(
            action="predict",
            domain="prediction",
            success=True,
            response_time_ms=20.0,
        )
        
        return []

    def learn(self, trajectory_data):
        """
        Process trajectory data and trigger evolution based on results.
        
        This is the primary learning loop — every trajectory feeds
        into the performance telemetry and may trigger evolution.
        """
        success = trajectory_data.get("success", True)
        latency = trajectory_data.get("latency_ms", 100)
        domain = trajectory_data.get("domain", "general")
        action = trajectory_data.get("action", "execute")
        
        result = self.evolution_lab.log_action(
            action=action,
            domain=domain,
            success=success,
            response_time_ms=latency,
            error_type=None if success else trajectory_data.get("error_type"),
        )
        
        evolution_status = self.evolution_lab.get_stats()
        
        return {
            "processed": True,
            "fitness": result.get("fitness", 0.5),
            "evolved": result.get("evolved", False),
            "generation": self.evolution_lab.genome_engine.generation,
            "evolution_count": self.evolution_lab.evolution_count,
        }

    def evolve(self):
        """
        Manually trigger an evolution cycle.
        
        Returns evolution results including genome changes.
        """
        evolved = self.evolution_lab.run_evolution_cycle()
        stats = self.evolution_lab.get_stats()
        
        return {
            "evolved": evolved,
            "memories_processed": len(self._memories),
            "generation": stats["genome_engine"]["generation"],
            "best_fitness": stats["genome_engine"]["best_fitness"],
            "evolution_count": stats["lab"]["evolution_count"],
        }

    def get_stats(self):
        """Get comprehensive statistics including evolution status."""
        base = {
            "memories": {"total": len(self._memories)},
            "clusters": len(self._clusters),
        }
        evolution_stats = self.evolution_lab.get_stats()
        base["evolution"] = {
            "generation": evolution_stats["genome_engine"]["generation"],
            "best_fitness": evolution_stats["genome_engine"]["best_fitness"],
            "evolution_count": evolution_stats["lab"]["evolution_count"],
            "population_size": evolution_stats["genome_engine"]["population_size"],
            "active_capsules": evolution_stats["genome_engine"]["active_capsules"],
            "active_genes": evolution_stats["genome_engine"]["active_genes"],
        }
        telemetry = evolution_stats.get("telemetry", {})
        metrics = telemetry.get("metrics", {})
        if metrics:
            base["evolution"]["success_rate"] = metrics.get("success_rate", 1.0)
            base["evolution"]["total_actions"] = metrics.get("total_actions", 0)
        return base

    def search(self, query, limit=10):
        """Search memories (placeholder for integration with memory service)."""
        return []

    def get_genome_parameters(self) -> Dict[str, float]:
        """Get current evolved genome parameters."""
        return self.evolution_lab.get_genome_parameters()

    def get_evolution_summary(self) -> str:
        """Get a human-readable evolution status report."""
        return self.evolution_lab.get_evolution_summary()

