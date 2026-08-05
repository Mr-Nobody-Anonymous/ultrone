# Copyright (c) Ultrone Contributors. All rights reserved.
"""Situational Awareness Layer — continuous environment understanding.

Maintains a continuously updated representation containing objects,
relationships, temporal events, environmental conditions, confidence,
unknown regions, and prediction horizon. Supports entity tracking,
event detection, context recognition, novelty detection, anomaly
detection, and uncertainty estimation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base_layer import CognitiveLayer, LayerConfig
from .cycle_context import CycleContext, CyclePhase, PhaseResult
from .event_types import CognitiveEventType
from .types import (
    SceneGraph,
    SituationalContext,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.SituationalAwareness")


@dataclass
class SituationalAwarenessConfig(LayerConfig):
    """Configuration for the situational awareness layer."""
    name: str = "situational_awareness"
    prediction_horizon: float = 300.0  # seconds
    entity_tracking_enabled: bool = True
    event_detection_enabled: bool = True
    novelty_detection_enabled: bool = True
    anomaly_detection_enabled: bool = True
    context_recognition_enabled: bool = True
    max_entities: int = 1000
    max_events: int = 500


class SituationalAwarenessLayer(CognitiveLayer):
    """Maintains a continuously updated situational context.

    The situational awareness layer:
    1. Updates the situational context from the scene graph
    2. Tracks entities over time
    3. Detects temporal events
    4. Recognizes environmental conditions
    5. Identifies unknown regions
    6. Detects novelty and anomalies
    7. Estimates uncertainty
    """

    def __init__(self, config: Optional[SituationalAwarenessConfig] = None):
        super().__init__(config or SituationalAwarenessConfig())
        self._context_history: List[SituationalContext] = []
        self._entity_tracks: Dict[str, List[Dict[str, Any]]] = {}
        self._detected_events: List[Dict[str, Any]] = []
        self._novelty_events: List[Dict[str, Any]] = []
        self._anomaly_events: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.UNDERSTAND

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the situational awareness phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context containing the scene graph.

        Returns
        -------
        PhaseResult
            Result with the updated situational context.
        """
        start = time.time()
        scene_graph = ctx.scene_graph

        if scene_graph is None:
            return PhaseResult(
                phase=self._phase,
                success=True,
                duration_seconds=time.time() - start,
                output={"situational_context": None, "message": "no scene graph"},
            )

        # 1. Build/update situational context
        situational = self._build_situational_context(scene_graph, ctx)

        # 2. Track entities
        if self.config.entity_tracking_enabled:
            self._track_entities(scene_graph, situational)

        # 3. Detect events
        if self.config.event_detection_enabled:
            events = self._detect_events(scene_graph, situational)
            situational.temporal_events.extend(events)
            self._detected_events.extend(events)

        # 4. Detect novelty
        if self.config.novelty_detection_enabled:
            novelty = self._detect_novelty(scene_graph, situational)
            if novelty:
                self._novelty_events.extend(novelty)
                situational.metadata["novelty"] = novelty

        # 5. Detect anomalies
        if self.config.anomaly_detection_enabled:
            anomalies = self._detect_anomalies(scene_graph, situational)
            if anomalies:
                self._anomaly_events.extend(anomalies)
                situational.metadata["anomalies"] = anomalies
                self._publish_event(
                    CognitiveEventType.ANOMALY_DETECTED,
                    {"anomalies": anomalies, "context_id": situational.context_id},
                )

        # 6. Recognize context
        if self.config.context_recognition_enabled:
            context_type = self._recognize_context(situational)
            situational.metadata["context_type"] = context_type

        # 7. Store in context
        ctx.situational_context = situational

        # 8. Publish event
        self._publish_event(
            CognitiveEventType.UNDERSTAND,
            {
                "context_id": situational.context_id,
                "entities": len(situational.entities),
                "relationships": len(situational.relationships),
                "events": len(situational.temporal_events),
                "confidence": situational.confidence,
            },
        )

        # 9. Create decision trace
        trace = self._create_trace(
            decision="Understand the current situation",
            confidence=situational.confidence,
            evidence=[
                {
                    "source": "scene_graph",
                    "description": f"Scene graph with {len(scene_graph.nodes)} nodes and {len(scene_graph.edges)} edges",
                    "confidence": scene_graph.overall_confidence,
                }
            ],
        )
        trace.uncertainty = UncertaintyEstimate(
            epistemic=1.0 - situational.confidence,
            aleatoric=0.0,
            total=1.0 - situational.confidence,
            type=UncertaintyType.EPISTEMIC,
            contributing_factors=["situational_uncertainty"],
        )

        self._context_history.append(situational)
        if len(self._context_history) > 100:
            self._context_history = self._context_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "situational_context": situational.to_dict(),
                "entities": len(situational.entities),
                "relationships": len(situational.relationships),
                "events": len(situational.temporal_events),
                "novelty": len(self._novelty_events),
                "anomalies": len(self._anomaly_events),
            },
            trace=trace,
        )

    def _build_situational_context(self, scene_graph: SceneGraph, ctx: CycleContext) -> SituationalContext:
        """Build a situational context from the scene graph."""
        situational = SituationalContext(
            prediction_horizon=self.config.prediction_horizon,
            scene_graph=scene_graph,
            confidence=scene_graph.overall_confidence,
        )

        # Extract entities
        for node in scene_graph.nodes:
            situational.entities[node.node_id] = {
                "label": node.label,
                "type": node.entity_type,
                "properties": node.properties,
                "confidence": node.confidence,
                "uncertainty": node.uncertainty,
                "first_seen": node.temporal_bounds[0],
                "last_seen": node.temporal_bounds[1],
            }

        # Extract relationships
        for edge in scene_graph.edges:
            situational.relationships.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.relationship_type,
                "confidence": edge.confidence,
                "weight": edge.weight,
            })

        # Extract environmental conditions from metadata
        if scene_graph.metadata:
            situational.environmental_conditions = scene_graph.metadata.get(
                "environmental_conditions", {}
            )

        # Identify unknown regions (low confidence areas)
        situational.unknown_regions = self._identify_unknown_regions(scene_graph)

        return situational

    def _track_entities(self, scene_graph: SceneGraph, situational: SituationalContext) -> None:
        """Track entities over time."""
        now = time.time()
        for node in scene_graph.nodes:
            if node.node_id not in self._entity_tracks:
                self._entity_tracks[node.node_id] = []
            self._entity_tracks[node.node_id].append({
                "timestamp": now,
                "confidence": node.confidence,
                "properties": node.properties,
            })
            # Limit track length
            if len(self._entity_tracks[node.node_id]) > 100:
                self._entity_tracks[node.node_id] = self._entity_tracks[node.node_id][-100:]

    def _detect_events(self, scene_graph: SceneGraph, situational: SituationalContext) -> List[Dict[str, Any]]:
        """Detect temporal events from the scene graph."""
        events = []

        # Detect entity appearance
        for node in scene_graph.nodes:
            if node.node_id not in self._entity_tracks:
                events.append({
                    "type": "entity_appeared",
                    "entity_id": node.node_id,
                    "entity_type": node.entity_type,
                    "timestamp": time.time(),
                    "confidence": node.confidence,
                })

        # Detect entity disappearance (entities in tracks but not in current graph)
        current_ids = {node.node_id for node in scene_graph.nodes}
        for entity_id in self._entity_tracks:
            if entity_id not in current_ids:
                events.append({
                    "type": "entity_disappeared",
                    "entity_id": entity_id,
                    "timestamp": time.time(),
                    "confidence": 0.5,
                })

        # Detect relationship changes
        current_rels = {(e.source_id, e.target_id, e.relationship_type) for e in scene_graph.edges}
        for rel in situational.relationships:
            rel_key = (rel["source"], rel["target"], rel["type"])
            if rel_key not in current_rels:
                events.append({
                    "type": "relationship_changed",
                    "source": rel["source"],
                    "target": rel["target"],
                    "relationship": rel["type"],
                    "timestamp": time.time(),
                })

        return events

    def _detect_novelty(self, scene_graph: SceneGraph, situational: SituationalContext) -> List[Dict[str, Any]]:
        """Detect novel patterns in the scene graph."""
        novelty = []

        # Check for new entity types
        known_types = set()
        for ctx in self._context_history:
            for entity in ctx.entities.values():
                known_types.add(entity.get("type", "unknown"))

        for node in scene_graph.nodes:
            if node.entity_type not in known_types:
                novelty.append({
                    "type": "novel_entity_type",
                    "entity_id": node.node_id,
                    "entity_type": node.entity_type,
                    "timestamp": time.time(),
                    "confidence": node.confidence,
                })

        # Check for new relationship types
        known_rels = set()
        for ctx in self._context_history:
            for rel in ctx.relationships:
                known_rels.add(rel.get("type", ""))

        for edge in scene_graph.edges:
            if edge.relationship_type not in known_rels:
                novelty.append({
                    "type": "novel_relationship",
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship_type,
                    "timestamp": time.time(),
                })

        return novelty

    def _detect_anomalies(self, scene_graph: SceneGraph, situational: SituationalContext) -> List[Dict[str, Any]]:
        """Detect anomalies in the situational context."""
        anomalies = []

        # Check for low confidence
        if situational.confidence < 0.5:
            anomalies.append({
                "type": "low_situational_confidence",
                "confidence": situational.confidence,
                "severity": "high",
            })

        # Check for high uncertainty
        if scene_graph.uncertainty_estimate.total > 0.5:
            anomalies.append({
                "type": "high_uncertainty",
                "uncertainty": scene_graph.uncertainty_estimate.total,
                "severity": "high",
            })

        # Check for unknown regions
        if len(situational.unknown_regions) > 0:
            anomalies.append({
                "type": "unknown_regions",
                "count": len(situational.unknown_regions),
                "severity": "medium",
            })

        return anomalies

    def _identify_unknown_regions(self, scene_graph: SceneGraph) -> List[Dict[str, Any]]:
        """Identify regions with low confidence or missing information."""
        unknown = []
        for node in scene_graph.nodes:
            if node.confidence < 0.5:
                unknown.append({
                    "region": node.node_id,
                    "reason": "low_confidence",
                    "confidence": node.confidence,
                })
        return unknown

    def _recognize_context(self, situational: SituationalContext) -> str:
        """Recognize the type of context from the situational data."""
        entity_types = {e.get("type", "unknown") for e in situational.entities.values()}

        if "threat" in entity_types or "enemy" in entity_types:
            return "threat"
        elif "resource" in entity_types or "supply" in entity_types:
            return "resource_management"
        elif "agent" in entity_types or "robot" in entity_types:
            return "multi_agent"
        elif "sensor" in entity_types:
            return "sensing"
        else:
            return "general"

    def get_context_history(self) -> List[SituationalContext]:
        """Return the history of situational contexts."""
        return self._context_history

    def get_entity_tracks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return entity tracking data."""
        return self._entity_tracks

    def get_detected_events(self) -> List[Dict[str, Any]]:
        """Return all detected events."""
        return self._detected_events

    def get_novelty_events(self) -> List[Dict[str, Any]]:
        """Return all novelty events."""
        return self._novelty_events

    def get_anomaly_events(self) -> List[Dict[str, Any]]:
        """Return all anomaly events."""
        return self._anomaly_events