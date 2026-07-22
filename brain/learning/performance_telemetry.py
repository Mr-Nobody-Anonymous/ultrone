# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Performance Telemetry System
=============================
Continuous monitoring of agent actions, outcomes, and response times.
Extended with military kill chain metrics.
"""

import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("Ultrone.Brain.Learning.Telemetry")


@dataclass
class TelemetryEvent:
    """A single telemetry data point from an agent action."""
    event_id: str
    action: str
    domain: str  # "air", "land", "sea", "cyber", "space", "general"
    success: bool
    response_time_ms: float
    timestamp: datetime
    agent_id: str = ""
    genome_generation: int = 0
    error_type: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "action": self.action,
            "domain": self.domain,
            "success": self.success,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "genome_generation": self.genome_generation,
            "error_type": self.error_type,
            "context": self.context,
        }


@dataclass
class TelemetryMetrics:
    """Aggregated performance metrics for a given window."""
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    avg_response_time_ms: float = 0.0
    success_rate: float = 1.0
    domain_performance: Dict[str, float] = field(default_factory=dict)
    failure_patterns: Dict[str, int] = field(default_factory=dict)
    worst_performing_domain: str = ""
    best_performing_domain: str = ""
    
    # Military-specific metrics
    kill_chain_success_rate: float = 0.0
    collateral_rate: float = 0.0
    avg_phase_time_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate,
            "domain_performance": self.domain_performance,
            "failure_patterns": self.failure_patterns,
            "worst_performing_domain": self.worst_performing_domain,
            "best_performing_domain": self.best_performing_domain,
            "kill_chain_success_rate": self.kill_chain_success_rate,
            "collateral_rate": self.collateral_rate,
            "avg_phase_time_ms": self.avg_phase_time_ms,
        }


class PerformanceTelemetry:
    """
    Continuous performance monitoring and analysis system.
    
    Tracks every agent action, computes rolling metrics, detects
    failure patterns, and provides fitness feedback to the GenomeEngine.
    Extended with kill chain and military-specific metrics.
    """
    
    def __init__(self, window_size: int = 100, decay_factor: float = 0.95):
        self.window_size = window_size
        self.decay_factor = decay_factor
        self.events: List[TelemetryEvent] = []
        self.domain_events: Dict[str, List[TelemetryEvent]] = defaultdict(list)
        self.kill_chain_events: List[TelemetryEvent] = []
        self._fitness_history: List[float] = []
    
    def record_event(self, event: TelemetryEvent) -> None:
        """Record a telemetry event and maintain rolling window."""
        self.events.append(event)
        self.domain_events[event.domain].append(event)
        
        # Track kill chain events separately
        if "kill_chain" in event.action or "engage" in event.action:
            self.kill_chain_events.append(event)
        
        # Maintain window size
        if len(self.events) > self.window_size:
            self.events = self.events[-self.window_size:]
        for domain in list(self.domain_events.keys()):
            if len(self.domain_events[domain]) > self.window_size // 2:
                self.domain_events[domain] = self.domain_events[domain][-(self.window_size // 2):]
    
    def log_action(
        self,
        action: str,
        domain: str,
        success: bool,
        response_time_ms: float,
        agent_id: str = "",
        genome_generation: int = 0,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Log an action and compute its fitness impact.
        
        Returns a fitness score compatible with GenomeEngine.record_fitness().
        """
        event = TelemetryEvent(
            event_id=f"evt-{len(self.events)}",
            action=action,
            domain=domain,
            success=success,
            response_time_ms=response_time_ms,
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            genome_generation=genome_generation,
            error_type=error_type,
            context=context or {},
        )
        self.record_event(event)
        
        # Compute fitness for this action
        base_fitness = 1.0 if success else 0.0
        time_penalty = min(0.3, response_time_ms * 0.0001)  # 1s = 0.1 penalty
        
        # Collateral penalty
        collateral_count = len(context.get("collateral", [])) if context else 0
        collateral_penalty = min(0.5, collateral_count * 0.1)
        
        fitness = max(0.0, base_fitness - time_penalty - collateral_penalty)
        
        logger.debug(
            "Telemetry: %s/%s %s (%.0fms) = fitness %.3f",
            domain, action, "✓" if success else "✗", response_time_ms, fitness,
        )
        
        return {
            "event_id": event.event_id,
            "fitness": fitness,
            "success": success,
            "response_time_ms": response_time_ms,
        }
    
    def get_metrics(self, domain: Optional[str] = None) -> TelemetryMetrics:
        """Get aggregated metrics for a domain or all domains."""
        events = self.domain_events.get(domain, self.events) if domain else self.events
        
        if not events:
            return TelemetryMetrics()
        
        total = len(events)
        successful = sum(1 for e in events if e.success)
        failed = total - successful
        avg_time = sum(e.response_time_ms for e in events) / total
        
        # Domain performance breakdown
        domain_perf = {}
        failure_patterns: Dict[str, int] = {}
        
        for event in events:
            if not event.success:
                failure_patterns[event.error_type or "unknown"] = \
                    failure_patterns.get(event.error_type or "unknown", 0) + 1
        
        if domain:
            domain_perf[domain] = successful / total if total > 0 else 0.0
        else:
            for d, evts in self.domain_events.items():
                if evts:
                    domain_perf[d] = sum(1 for e in evts if e.success) / len(evts)
        
        worst = min(domain_perf, key=domain_perf.get) if domain_perf else ""
        best = max(domain_perf, key=domain_perf.get) if domain_perf else ""
        
        # Kill chain metrics
        kcs_rate = 0.0
        if self.kill_chain_events:
            kcs_success = sum(1 for e in self.kill_chain_events if e.success)
            kcs_rate = kcs_success / len(self.kill_chain_events)
        
        # Collateral rate
        collateral_events = [e for e in events if "collateral" in (e.context or {})]
        coll_rate = sum(len(e.context.get("collateral", [])) for e in collateral_events) / max(1, total)
        
        return TelemetryMetrics(
            total_actions=total,
            successful_actions=successful,
            failed_actions=failed,
            avg_response_time_ms=avg_time,
            success_rate=successful / total if total > 0 else 0.0,
            domain_performance=domain_perf,
            failure_patterns=failure_patterns,
            worst_performing_domain=worst,
            best_performing_domain=best,
            kill_chain_success_rate=kcs_rate,
            collateral_rate=coll_rate,
        )
    
    def get_overall_fitness(self) -> float:
        """Compute overall fitness score across all recent events."""
        metrics = self.get_metrics()
        if metrics.total_actions == 0:
            return 1.0
        
        # Success rate weighted 70%, response time weighted 30%
        success_score = metrics.success_rate
        time_score = max(0.0, 1.0 - (metrics.avg_response_time_ms / 5000.0))  # 5s = 0
        
        return 0.7 * success_score + 0.3 * time_score
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """
        Analyze recent failures to identify patterns and suggest improvements.
        
        Returns actionable insights for the evolution engine.
        """
        metrics = self.get_metrics()
        
        if metrics.failed_actions == 0:
            return {"has_failures": False, "message": "No failures detected"}
        
        analysis = {
            "has_failures": True,
            "total_failures": metrics.failed_actions,
            "failure_rate": metrics.failed_actions / max(1, metrics.total_actions),
            "most_common_failure": max(metrics.failure_patterns, key=metrics.failure_patterns.get)
                if metrics.failure_patterns else None,
            "worst_domain": metrics.worst_performing_domain,
            "domain_rankings": dict(sorted(
                metrics.domain_performance.items(),
                key=lambda x: x[1],
            )),
            "suggestions": [],
        }
        
        # Generate suggestions based on patterns
        if metrics.worst_performing_domain and metrics.domain_performance.get(metrics.worst_performing_domain, 1.0) < 0.6:
            analysis["suggestions"].append(
                f"Increase mutation rate for '{metrics.worst_performing_domain}' capsule"
            )
        
        if metrics.avg_response_time_ms > 2000:
            analysis["suggestions"].append(
                "Response time degradation detected. Consider reducing engagement_delay"
            )
        
        if metrics.kill_chain_success_rate < 0.6:
            analysis["suggestions"].append(
                "Kill chain efficiency low. Optimize phase transitions"
            )
        
        failure_rate = metrics.failed_actions / max(1, metrics.total_actions)
        if failure_rate > 0.3:
            analysis["suggestions"].append(
                "High failure rate. Triggering emergency genome evolution cycle"
            )
        
        return analysis
    
    def get_stats(self) -> dict:
        metrics = self.get_metrics()
        return {
            "total_events": len(self.events),
            "domains": list(self.domain_events.keys()),
            "metrics": metrics.to_dict(),
            "failure_analysis": self.get_failure_analysis(),
        }