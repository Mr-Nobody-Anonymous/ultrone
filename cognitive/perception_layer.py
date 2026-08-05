# Copyright (c) Ultrone Contributors. All rights reserved.
"""Perception Layer — multimodal observation fusion.

Fuses observations from all perceptual modalities (vision, audio, text,
telemetry, graph, geospatial, time series, structured databases) into a
unified probabilistic scene graph with uncertainty estimates.
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
    Modality,
    Observation,
    SceneGraph,
    SceneGraphNode,
    SceneGraphEdge,
    UncertaintyEstimate,
    UncertaintyType,
)

logger = logging.getLogger("Ultrone.Cognitive.Perception")


@dataclass
class PerceptionLayerConfig(LayerConfig):
    """Configuration for the perception layer."""
    name: str = "perception"
    fusion_method: str = "bayesian"  # bayesian, weighted, max_confidence
    default_confidence: float = 0.8
    uncertainty_threshold: float = 0.3
    enable_anomaly_detection: bool = True
    anomaly_threshold: float = 0.85


class PerceptionLayer(CognitiveLayer):
    """Multimodal perception layer that fuses observations into a scene graph.

    The perception layer:
    1. Receives raw multimodal observations
    2. Normalizes each modality into a common representation
    3. Fuses observations into a unified probabilistic scene graph
    4. Estimates uncertainty for every observation
    5. Detects anomalies and novel patterns
    6. Publishes perception events
    """

    def __init__(self, config: Optional[PerceptionLayerConfig] = None):
        super().__init__(config or PerceptionLayerConfig())
        self._modality_processors: Dict[Modality, Any] = {}
        self._scene_graph_history: List[SceneGraph] = []
        self._anomalies_detected: List[Dict[str, Any]] = []

    def _layer_phase(self) -> CyclePhase:
        return CyclePhase.PERCEIVE

    def register_modality_processor(self, modality: Modality, processor: Any) -> None:
        """Register a custom processor for a specific modality."""
        self._modality_processors[modality] = processor

    def process(self, ctx: CycleContext) -> PhaseResult:
        """Execute the perception phase.

        Parameters
        ----------
        ctx : CycleContext
            The shared cycle context containing observations.

        Returns
        -------
        PhaseResult
            Result with the fused scene graph.
        """
        start = time.time()
        observations = ctx.observations

        if not observations:
            return PhaseResult(
                phase=self._phase,
                success=True,
                duration_seconds=time.time() - start,
                output={"scene_graph": None, "observations": 0, "message": "no observations"},
            )

        # 1. Normalize each observation
        normalized = [self._normalize_observation(obs) for obs in observations]

        # 2. Fuse into a unified scene graph
        scene_graph = self._fuse_observations(normalized)

        # 3. Estimate uncertainty
        scene_graph.uncertainty_estimate = self._estimate_uncertainty(normalized)
        scene_graph.overall_confidence = self._compute_overall_confidence(normalized)

        # 4. Detect anomalies
        if self.config.enable_anomaly_detection:
            anomalies = self._detect_anomalies(scene_graph)
            if anomalies:
                self._anomalies_detected.extend(anomalies)
                self._publish_event(
                    CognitiveEventType.ANOMALY_DETECTED,
                    {"anomalies": anomalies, "graph_id": scene_graph.graph_id},
                )

        # 5. Store in context
        ctx.scene_graph = scene_graph

        # 6. Publish perception event
        self._publish_event(
            CognitiveEventType.PERCEPTION,
            {
                "graph_id": scene_graph.graph_id,
                "nodes": len(scene_graph.nodes),
                "edges": len(scene_graph.edges),
                "confidence": scene_graph.overall_confidence,
                "uncertainty": scene_graph.uncertainty_estimate.total,
            },
        )

        # 7. Create decision trace
        trace = self._create_trace(
            decision="Perceive and fuse multimodal observations",
            confidence=scene_graph.overall_confidence,
            evidence=[
                {
                    "source": obs.source,
                    "description": f"Observation with {len(obs.modalities)} modalities",
                    "confidence": obs.confidence,
                }
                for obs in observations[:5]
            ],
        )
        trace.uncertainty = scene_graph.uncertainty_estimate
        trace.feature_importance = {
            "modalities": len(scene_graph.nodes),
            "entities": len(scene_graph.nodes),
            "relationships": len(scene_graph.edges),
        }

        self._scene_graph_history.append(scene_graph)
        if len(self._scene_graph_history) > 100:
            self._scene_graph_history = self._scene_graph_history[-100:]

        return PhaseResult(
            phase=self._phase,
            success=True,
            duration_seconds=time.time() - start,
            output={
                "scene_graph": scene_graph.to_dict(),
                "observations": len(observations),
                "nodes": len(scene_graph.nodes),
                "edges": len(scene_graph.edges),
                "anomalies": len(anomalies) if self.config.enable_anomaly_detection else 0,
            },
            trace=trace,
        )

    def _normalize_observation(self, obs: Observation) -> Dict[str, Any]:
        """Normalize a single observation into a common representation."""
        normalized = {
            "observation_id": obs.observation_id,
            "timestamp": obs.timestamp,
            "source": obs.source,
            "confidence": obs.confidence,
            "uncertainty": obs.uncertainty,
            "modalities": {},
            "entities": [],
            "relationships": [],
        }

        for modality, data in obs.modalities.items():
            if modality in self._modality_processors:
                # Use custom processor
                try:
                    result = self._modality_processors[modality](data)
                    normalized["modalities"][modality] = result
                except Exception as e:
                    logger.warning("Modality processor %s failed: %s", modality, e)
                    normalized["modalities"][modality] = self._default_process(modality, data)
            else:
                normalized["modalities"][modality] = self._default_process(modality, data)

        return normalized

    def _default_process(self, modality: Modality, data: Any) -> Dict[str, Any]:
        """Default processing for a modality."""
        if isinstance(data, dict):
            return {
                "type": "dict",
                "keys": list(data.keys()),
                "data": data,
            }
        elif isinstance(data, list):
            return {
                "type": "list",
                "length": len(data),
                "data": data,
            }
        elif isinstance(data, str):
            return {
                "type": "text",
                "length": len(data),
                "data": data,
            }
        else:
            return {
                "type": type(data).__name__,
                "data": data,
            }

    def _fuse_observations(self, normalized: List[Dict[str, Any]]) -> SceneGraph:
        """Fuse normalized observations into a unified scene graph."""
        graph = SceneGraph()
        entity_map: Dict[str, SceneGraphNode] = {}

        for obs in normalized:
            # Extract entities from observation
            entities = self._extract_entities(obs)
            for entity in entities:
                node_id = entity.get("id", f"entity-{len(graph.nodes)}")
                if node_id not in entity_map:
                    node = SceneGraphNode(
                        node_id=node_id,
                        label=entity.get("label", "unknown"),
                        entity_type=entity.get("type", "unknown"),
                        properties=entity.get("properties", {}),
                        confidence=entity.get("confidence", obs["confidence"]),
                        uncertainty=entity.get("uncertainty", obs["uncertainty"]),
                    )
                    entity_map[node_id] = node
                    graph.add_node(node)
                else:
                    # Merge properties
                    existing = entity_map[node_id]
                    existing.properties.update(entity.get("properties", {}))
                    # Update confidence (weighted average)
                    existing.confidence = (existing.confidence + entity.get("confidence", obs["confidence"])) / 2

            # Extract relationships
            relationships = self._extract_relationships(obs)
            for rel in relationships:
                edge = SceneGraphEdge(
                    source_id=rel.get("source", ""),
                    target_id=rel.get("target", ""),
                    relationship_type=rel.get("type", "related_to"),
                    confidence=rel.get("confidence", obs["confidence"]),
                    weight=rel.get("weight", 1.0),
                )
                graph.add_edge(edge)

        return graph

    def _extract_entities(self, obs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from a normalized observation."""
        entities = []
        for modality, data in obs.get("modalities", {}).items():
            if isinstance(data, dict) and "data" in data:
                inner = data["data"]
                if isinstance(inner, dict):
                    # Look for entity-like structures
                    for key, value in inner.items():
                        if isinstance(value, dict) and "id" in value:
                            entities.append({
                                "id": value["id"],
                                "label": value.get("label", key),
                                "type": value.get("type", modality),
                                "properties": value,
                                "confidence": value.get("confidence", obs["confidence"]),
                                "uncertainty": value.get("uncertainty", obs["uncertainty"]),
                            })
                        elif isinstance(value, (str, int, float)):
                            entities.append({
                                "id": f"{modality}:{key}",
                                "label": key,
                                "type": modality,
                                "properties": {"value": value},
                                "confidence": obs["confidence"],
                                "uncertainty": obs["uncertainty"],
                            })
                elif isinstance(inner, str):
                    # Text observation: create a text entity
                    entities.append({
                        "id": f"{modality}:text:{obs['observation_id']}",
                        "label": "text_observation",
                        "type": modality,
                        "properties": {"text": inner[:200]},
                        "confidence": obs["confidence"],
                        "uncertainty": obs["uncertainty"],
                    })
                elif isinstance(inner, list):
                    # List observation: create entities from list items
                    for i, item in enumerate(inner[:10]):
                        if isinstance(item, dict) and "id" in item:
                            entities.append({
                                "id": item["id"],
                                "label": item.get("label", f"item_{i}"),
                                "type": item.get("type", modality),
                                "properties": item,
                                "confidence": item.get("confidence", obs["confidence"]),
                                "uncertainty": item.get("uncertainty", obs["uncertainty"]),
                            })
                        elif isinstance(item, (str, int, float)):
                            entities.append({
                                "id": f"{modality}:item:{i}",
                                "label": f"item_{i}",
                                "type": modality,
                                "properties": {"value": item},
                                "confidence": obs["confidence"],
                                "uncertainty": obs["uncertainty"],
                            })
        return entities

    def _extract_relationships(self, obs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relationships from a normalized observation."""
        relationships = []
        for modality, data in obs.get("modalities", {}).items():
            if isinstance(data, dict) and "data" in data:
                inner = data["data"]
                if isinstance(inner, dict) and "relationships" in inner:
                    for rel in inner["relationships"]:
                        relationships.append(rel)
        return relationships

    def _estimate_uncertainty(self, normalized: List[Dict[str, Any]]) -> UncertaintyEstimate:
        """Estimate uncertainty from the observations."""
        epistemic = 0.0
        aleatoric = 0.0
        factors = []

        for obs in normalized:
            # Epistemic uncertainty from low confidence
            if obs["confidence"] < self.config.default_confidence:
                epistemic += (self.config.default_confidence - obs["confidence"])
                factors.append(f"low_confidence:{obs['source']}")

            # Aleatoric uncertainty from observation noise
            if obs["uncertainty"] > 0:
                aleatoric += obs["uncertainty"]
                factors.append(f"noise:{obs['source']}")

        # Normalize
        n = max(1, len(normalized))
        epistemic = min(1.0, epistemic / n)
        aleatoric = min(1.0, aleatoric / n)

        return UncertaintyEstimate(
            epistemic=epistemic,
            aleatoric=aleatoric,
            total=min(1.0, epistemic + aleatoric),
            type=UncertaintyType.EPISTEMIC if epistemic > aleatoric else UncertaintyType.ALEATORIC,
            contributing_factors=factors[:10],
        )

    def _compute_overall_confidence(self, normalized: List[Dict[str, Any]]) -> float:
        """Compute overall confidence from observations."""
        if not normalized:
            return 0.0
        confidences = [obs["confidence"] for obs in normalized]
        return sum(confidences) / len(confidences)

    def _detect_anomalies(self, graph: SceneGraph) -> List[Dict[str, Any]]:
        """Detect anomalies in the scene graph."""
        anomalies = []

        # Check for low-confidence nodes
        for node in graph.nodes:
            if node.confidence < self.config.anomaly_threshold:
                anomalies.append({
                    "type": "low_confidence",
                    "node_id": node.node_id,
                    "confidence": node.confidence,
                    "severity": "medium" if node.confidence > 0.5 else "high",
                })

        # Check for high uncertainty
        if graph.uncertainty_estimate.total > self.config.uncertainty_threshold:
            anomalies.append({
                "type": "high_uncertainty",
                "uncertainty": graph.uncertainty_estimate.total,
                "severity": "high",
            })

        # Check for isolated nodes (no relationships)
        connected_ids = set()
        for edge in graph.edges:
            connected_ids.add(edge.source_id)
            connected_ids.add(edge.target_id)
        for node in graph.nodes:
            if node.node_id not in connected_ids and len(graph.nodes) > 1:
                anomalies.append({
                    "type": "isolated_entity",
                    "node_id": node.node_id,
                    "severity": "low",
                })

        return anomalies

    def get_scene_graph_history(self) -> List[SceneGraph]:
        """Return the history of scene graphs."""
        return self._scene_graph_history

    def get_anomalies(self) -> List[Dict[str, Any]]:
        """Return all detected anomalies."""
        return self._anomalies_detected