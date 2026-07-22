# Copyright (c) Ultrone Contributors. All rights reserved.
"""
Multi-INT Knowledge Graph - Palantir-Style Link Analysis.

Builds a dynamic networkx.DiGraph where nodes are battlefield entities
(Radar detections, SIGINT emissions, Visual IDs) and edges represent
relationship patterns like COMMS_LINKED, SPATIALLY_COLOCATED, or THREAT_CORRELATED.

The graph updates every simulation step. The LLM Commander consumes
graph summaries for enhanced tactical awareness.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter

import networkx as nx
import random

logger = logging.getLogger("Ultrone.Brain.Perception.KnowledgeGraph")

# Edge type labels
EDGE_COMMS_LINKED = "COMMS_LINKED"
EDGE_SPATIALLY_COLOCATED = "SPATIALLY_COLOCATED"
EDGE_THREAT_CORRELATED = "THREAT_CORRELATED"
EDGE_SUPPLY_LINK = "SUPPLY_LINK"
EDGE_EVOLUTION_TREND = "EVOLUTION_TREND"

# Proximity threshold for linking nodes (grid units)
PROXIMITY_THRESHOLD = 15


class MultiINTKnowledgeGraph:
    """
    Dynamic battlefield knowledge graph built from multi-INT sensor data.
    
    Fuses RadarAI, SIGINTAI, VisualAI detections into a unified graph
    where edges encode operational relationships (comms links, spatial
    colocation, threat correlation).
    
    Phase 8: Supports evolutionary_telemetry nodes for generational
    fitness deltas, fuel conservation behaviors, and supply node
    vulnerability profiles. Telemetry is window-capped at MAX_TELEMETRY
    entries to maintain flat memory profile.
    
    The graph is rebuilt each step from current sensor assessments;
    old nodes decay out if not re-detected.
    """
    
    # Phase 8: Maximum evolutionary telemetry nodes to retain
    MAX_TELEMETRY = 50
    
    def __init__(self, decay_steps: int = 5):
        self.graph = nx.DiGraph()
        self.decay_steps = decay_steps  # steps before a node without refresh is removed
        self._node_age: Dict[str, int] = {}  # node_id -> steps since last update
        self._step_count = 0
        
        # Persistent entity registry: maps canonical names to node ids
        self._entity_registry: Dict[str, str] = {}
        
        # Phase 8: Evolutionary telemetry ring buffer (ordered list of node IDs)
        self._telemetry_node_ids: List[str] = []
    
    def update(self, env: Any, radar_assessments: List[Dict[str, Any]],
               sigint_assessments: List[Dict[str, Any]],
               visual_assessments: Optional[List[Dict[str, Any]]] = None,
               supply_nodes: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the knowledge graph from current sensor assessments.
        
        Args:
            env: BattlefieldEnv instance (for positions, supply nodes)
            radar_assessments: List of RadarAI analysis results with position data
            sigint_assessments: List of SIGINTAI analysis results with bearing data
            visual_assessments: Optional VisualAI detection results
            supply_nodes: Optional dict of supply node data
        """
        self._step_count += 1
        
        # Age all existing nodes
        for node_id in list(self.graph.nodes()):
            self._node_age[node_id] = self._node_age.get(node_id, 0) + 1
            if self._node_age[node_id] > self.decay_steps:
                self.graph.remove_node(node_id)
                del self._node_age[node_id]
        
        # ── Add Radar nodes ──
        for i, radar in enumerate(radar_assessments):
            entity_id = f"RADAR-{i}-S{self._step_count}"
            speed = radar.get("speed", 0) if isinstance(radar, dict) else 0
            threat = radar.get("threat_indicator", 0.5) if isinstance(radar, dict) else 0.5
            classification = radar.get("classification", "contact") if isinstance(radar, dict) else "contact"
            
            # Try to find existing node for this entity
            canonical_key = f"radar_{classification}_{int(speed / 10)}"
            existing = self._entity_registry.get(canonical_key)
            
            if existing and existing in self.graph:
                node_id = existing
                self._node_age[node_id] = 0
                # Update attributes
                self.graph.nodes[node_id]["speed"] = speed
                self.graph.nodes[node_id]["threat"] = threat
                self.graph.nodes[node_id]["last_seen"] = self._step_count
            else:
                node_id = entity_id
                self.graph.add_node(node_id, 
                                    entity_type="radar_contact",
                                    classification=classification,
                                    speed=speed,
                                    threat=threat,
                                    position=(random.randint(0, 100), random.randint(0, 100)),
                                    last_seen=self._step_count)
                self._node_age[node_id] = 0
                self._entity_registry[canonical_key] = node_id
        
        # ── Add SIGINT nodes ──
        for i, sigint in enumerate(sigint_assessments):
            entity_id = f"SIGINT-{i}-S{self._step_count}"
            classification = sigint.get("classification", "unknown") if isinstance(sigint, dict) else "unknown"
            threat = sigint.get("threat_indicator", 0.5) if isinstance(sigint, dict) else 0.5
            encryption = sigint.get("encryption_level", 0.3) if isinstance(sigint, dict) else 0.3
            
            canonical_key = f"sigint_{classification}"
            existing = self._entity_registry.get(canonical_key)
            
            if existing and existing in self.graph:
                node_id = existing
                self._node_age[node_id] = 0
                self.graph.nodes[node_id]["threat"] = threat
                self.graph.nodes[node_id]["encryption"] = encryption
            else:
                node_id = entity_id
                self.graph.add_node(node_id,
                                    entity_type="sigint_contact",
                                    classification=classification,
                                    encryption=encryption,
                                    threat=threat,
                                    position=(random.randint(0, 100), random.randint(0, 100)),
                                    last_seen=self._step_count)
                self._node_age[node_id] = 0
                self._entity_registry[canonical_key] = node_id
        
        # ── Add Supply Node nodes ──
        if supply_nodes:
            for node_id, node_data in supply_nodes.items():
                if node_data.get("is_destroyed", False):
                    continue  # skip destroyed nodes
                
                canonical_key = f"supply_{node_id}"
                existing = self._entity_registry.get(canonical_key)
                
                if existing and existing in self.graph:
                    self._node_age[existing] = 0
                    self.graph.nodes[existing]["health"] = node_data.get("health", 100)
                    self.graph.nodes[existing]["threat"] = 0.0  # friendly nodes are not threats
                else:
                    nid = f"SUPPLY-{node_id}"
                    self.graph.add_node(nid,
                                        entity_type="supply_node",
                                        team=node_data.get("team", "unknown"),
                                        health=node_data.get("health", 100),
                                        threat=0.0,
                                        position=node_data.get("position", (50, 50)),
                                        assets_linked=len(node_data.get("assets_linked", [])),
                                        last_seen=self._step_count)
                    self._node_age[nid] = 0
                    self._entity_registry[canonical_key] = nid
        
        # ── Link spatially close Radar + SIGINT nodes ──
        self._link_proximal_nodes()
        
        # ── Link supply nodes to their assets ──
        self._link_supply_chains(env)
    
    def _link_proximal_nodes(self) -> None:
        """Draw COMMS_LINKED edges between spatially close Radar and SIGINT nodes."""
        radar_nodes = [n for n, d in self.graph.nodes(data=True) 
                       if d.get("entity_type") == "radar_contact"]
        sigint_nodes = [n for n, d in self.graph.nodes(data=True)
                        if d.get("entity_type") == "sigint_contact"]
        
        for r_node in radar_nodes:
            r_pos = self.graph.nodes[r_node].get("position")
            if not r_pos:
                continue
            for s_node in sigint_nodes:
                s_pos = self.graph.nodes[s_node].get("position")
                if not s_pos:
                    continue
                
                dist = math.sqrt((r_pos[0] - s_pos[0])**2 + (r_pos[1] - s_pos[1])**2)
                if dist < PROXIMITY_THRESHOLD:
                    # Add edge in both directions with label
                    if not self.graph.has_edge(r_node, s_node):
                        self.graph.add_edge(r_node, s_node, 
                                            label=EDGE_COMMS_LINKED,
                                            weight=1.0 / max(1.0, dist))
                        logger.debug(f"COMMS_LINKED: {r_node} <-> {s_node} (dist={dist:.1f})")
                    
                    # Also add spatially colocated edge
                    if not self.graph.has_edge(r_node, s_node) and not self.graph.has_edge(s_node, r_node):
                        self.graph.add_edge(r_node, s_node, 
                                            label=EDGE_SPATIALLY_COLOCATED,
                                            weight=1.0)
    
    def _link_supply_chains(self, env: Any) -> None:
        """Link supply nodes to their assets (via env supply_nodes data)."""
        supply_nodes_entities = [n for n, d in self.graph.nodes(data=True)
                                 if d.get("entity_type") == "supply_node"]
        
        # If env has supply nodes, link them
        if hasattr(env, 'supply_nodes'):
            for node_id, supply_node in env.supply_nodes.items():
                supply_entity_id = f"SUPPLY-{node_id}"
                if supply_entity_id not in self.graph:
                    continue
                
                for asset_id in supply_node.assets_linked:
                    # Check if this asset has a corresponding node in the graph
                    for gnode, gdata in self.graph.nodes(data=True):
                        if gdata.get("entity_type") in ("radar_contact",) and gnode.endswith(asset_id[-8:]):
                            continue
                    
                    # Create a shadow asset node if not present
                    asset_entity_id = f"ASSET-{asset_id}"
                    if asset_entity_id not in self.graph:
                        self.graph.add_node(asset_entity_id,
                                            entity_type="blue_asset",
                                            asset_id=asset_id,
                                            threat=0.0,
                                            position=supply_node.position,
                                            last_seen=self._step_count)
                        self._node_age[asset_entity_id] = 0
                    
                    if not self.graph.has_edge(supply_entity_id, asset_entity_id):
                        self.graph.add_edge(supply_entity_id, asset_entity_id,
                                            label=EDGE_SUPPLY_LINK,
                                            weight=1.0)
    
    def get_summary(self) -> str:
        """
        Generate a natural-language summary of the knowledge graph.
        
        Extracts:
        - Total nodes and edges
        - Threat density (proportion of high-threat nodes)
        - High-value comms links (COMMS_LINKED edges involving high-threat nodes)
        - Cluster analysis (connected components with supply chain structures)
        
        Returns:
            Summary string like "Detected 5 nodes, 2 confirmed comms links, 1 supply route"
        """
        if self.graph.number_of_nodes() == 0:
            return "No entities detected in the knowledge graph."
        
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()
        
        # Node type breakdown
        node_types = Counter()
        threats = []
        radar_count = 0
        sigint_count = 0
        supply_count = 0
        
        for nid, data in self.graph.nodes(data=True):
            etype = data.get("entity_type", "unknown")
            node_types[etype] += 1
            threat = data.get("threat", 0.0)
            threats.append(threat)
            
            if etype == "radar_contact":
                radar_count += 1
            elif etype == "sigint_contact":
                sigint_count += 1
            elif etype == "supply_node":
                supply_count += 1
        
        # Threat density: proportion of nodes with threat > 0.6
        high_threat = sum(1 for t in threats if t > 0.6)
        threat_density = high_threat / max(1, len(threats))
        
        # High-value COMMS_LINKED edges (involving high-threat nodes)
        comms_edges = []
        for u, v, d in self.graph.edges(data=True):
            if d.get("label") == EDGE_COMMS_LINKED:
                u_threat = self.graph.nodes[u].get("threat", 0)
                v_threat = self.graph.nodes[v].get("threat", 0)
                if u_threat > 0.6 or v_threat > 0.6:
                    comms_edges.append((u, v, u_threat + v_threat))
        
        # Cluster analysis: connected components
        components = list(nx.weakly_connected_components(self.graph))
        
        # Build summary
        lines = []
        lines.append(f"Knowledge Graph: {total_nodes} nodes, {total_edges} edges")
        lines.append(f"  Types: {radar_count} radar, {sigint_count} sigint, {supply_count} supply nodes")
        lines.append(f"  Threat density: {threat_density:.0%} ({high_threat} high-threat nodes)")
        
        if comms_edges:
            top_edges = sorted(comms_edges, key=lambda x: x[2], reverse=True)[:3]
            lines.append(f"  High-value COMMS links: {len(comms_edges)} confirmed")
            for u, v, score in top_edges:
                u_class = self.graph.nodes[u].get("classification", "contact")
                v_class = self.graph.nodes[v].get("classification", "contact")
                lines.append(f"    • {u} ({u_class}) ↔ {v} ({v_class}) [threat_score: {score:.2f}]")
        
        if supply_count > 0:
            total_linked = sum(1 for u, v, d in self.graph.edges(data=True) 
                               if d.get("label") == EDGE_SUPPLY_LINK)
            lines.append(f"  Supply chains: {supply_count} nodes, {total_linked} supply links")
        
        # Cluster info
        clusters = [c for c in components if len(c) > 1]
        if clusters:
            lines.append(f"  Operational clusters: {len(clusters)} multi-node formations detected")
            for i, cluster in enumerate(clusters[:3]):
                types_in_cluster = Counter()
                for nid in cluster:
                    types_in_cluster[self.graph.nodes[nid].get("entity_type", "?")] += 1
                type_str = ", ".join(f"{k}:{v}" for k, v in types_in_cluster.most_common())
                lines.append(f"    Cluster {i+1}: {len(cluster)} nodes ({type_str})")
        
        return "\n".join(lines)
    
    def get_graph_data(self) -> Dict[str, Any]:
        """
        Get structured graph data for LLM consumption.
        
        Returns:
            Dict with nodes list, edges list, and summary stats
        """
        nodes_list = []
        for nid, data in self.graph.nodes(data=True):
            nodes_list.append({
                "id": nid,
                "type": data.get("entity_type", "unknown"),
                "classification": data.get("classification", "unknown"),
                "threat": data.get("threat", 0.0),
                "position": data.get("position", (0, 0)),
            })
        
        edges_list = []
        for u, v, data in self.graph.edges(data=True):
            edges_list.append({
                "source": u,
                "target": v,
                "label": data.get("label", "unknown"),
                "weight": data.get("weight", 1.0),
            })
        
        return {
            "node_count": len(nodes_list),
            "edge_count": len(edges_list),
            "nodes": nodes_list,
            "edges": edges_list,
            "summary": self.get_summary(),
        }
    
    def get_nodes_by_type(self, entity_type: str) -> List[str]:
        """Get all node IDs of a given entity type."""
        return [n for n, d in self.graph.nodes(data=True) if d.get("entity_type") == entity_type]
    
    def get_high_value_targets(self, threat_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """Get nodes that exceed a threat threshold, sorted by threat."""
        targets = []
        for nid, data in self.graph.nodes(data=True):
            threat = data.get("threat", 0.0)
            if threat > threat_threshold:
                targets.append({
                    "node_id": nid,
                    "type": data.get("entity_type", "unknown"),
                    "classification": data.get("classification", "unknown"),
                    "threat": threat,
                })
        return sorted(targets, key=lambda x: x["threat"], reverse=True)
    
    # ------------------------------------------------------------------
    # Phase 8: Evolutionary Telemetry Ingestion
    # ------------------------------------------------------------------
    def add_evolutionary_telemetry(self, generation: int, avg_fitness: float,
                                   bottleneck_risk: float,
                                   fuel_conservation: float = 0.0,
                                   supply_vulnerability: float = 0.0) -> str:
        """
        Add an evolutionary telemetry node to the knowledge graph.
        
        Phase 8: Stores generational fitness deltas, fuel conservation
        behaviors, and supply node vulnerability profiles.
        
        Telemetry nodes are window-capped at MAX_TELEMETRY (50) entries.
        When the cap is exceeded, the oldest telemetry node is evicted
        to maintain a flat memory profile.
        
        Args:
            generation: The generation number
            avg_fitness: Average population fitness for this generation
            bottleneck_risk: Risk score [0,1] for evolutionary bottlenecks
            fuel_conservation: Average fuel conservation behavior [0,1]
            supply_vulnerability: Supply node vulnerability profile [0,1]
            
        Returns:
            Node ID of the created telemetry node
        """
        node_id = f"EVO-TELE-G{generation}"
        
        # Compute fitness delta from previous telemetry if available
        fitness_delta = 0.0
        prev_node_id = None
        if self._telemetry_node_ids:
            prev_node_id = self._telemetry_node_ids[-1]
            if prev_node_id in self.graph:
                prev_fitness = self.graph.nodes[prev_node_id].get("avg_fitness", 0.0)
                fitness_delta = avg_fitness - prev_fitness
        
        # Add or update the telemetry node
        if node_id in self.graph:
            # Update existing
            self.graph.nodes[node_id].update({
                "avg_fitness": avg_fitness,
                "bottleneck_risk": bottleneck_risk,
                "fitness_delta": fitness_delta,
                "fuel_conservation": fuel_conservation,
                "supply_vulnerability": supply_vulnerability,
                "last_seen": self._step_count,
            })
            self._node_age[node_id] = 0
        else:
            # Create new node
            self.graph.add_node(
                node_id,
                entity_type="evolutionary_telemetry",
                generation=generation,
                avg_fitness=avg_fitness,
                bottleneck_risk=bottleneck_risk,
                fitness_delta=fitness_delta,
                fuel_conservation=fuel_conservation,
                supply_vulnerability=supply_vulnerability,
                threat=0.0,  # telemetry has no threat value
                last_seen=self._step_count,
            )
            self._node_age[node_id] = 0
            self._telemetry_node_ids.append(node_id)
        
        # ── Window cap: evict oldest telemetry if exceeding MAX_TELEMETRY ──
        while len(self._telemetry_node_ids) > self.MAX_TELEMETRY:
            oldest_id = self._telemetry_node_ids.pop(0)
            if oldest_id in self.graph:
                self.graph.remove_node(oldest_id)
                self._node_age.pop(oldest_id, None)
        
        # ── Link consecutive telemetry nodes for trend analysis ──
        if prev_node_id and prev_node_id in self.graph and prev_node_id != node_id:
            if not self.graph.has_edge(prev_node_id, node_id):
                self.graph.add_edge(
                    prev_node_id, node_id,
                    label="EVOLUTION_TREND",
                    weight=max(0.01, abs(fitness_delta)),
                )
        
        return node_id
    
    def get_evolutionary_telemetry(self, n_last: int = 10) -> List[Dict[str, Any]]:
        """
        Get the last N evolutionary telemetry data points.
        
        Args:
            n_last: Number of recent telemetry entries to retrieve (default 10)
            
        Returns:
            List of telemetry dicts sorted by generation ascending
        """
        recent_ids = self._telemetry_node_ids[-n_last:]
        results = []
        for nid in recent_ids:
            if nid in self.graph:
                data = self.graph.nodes[nid]
                results.append({
                    "node_id": nid,
                    "generation": data.get("generation", 0),
                    "avg_fitness": data.get("avg_fitness", 0.0),
                    "bottleneck_risk": data.get("bottleneck_risk", 0.0),
                    "fitness_delta": data.get("fitness_delta", 0.0),
                    "fuel_conservation": data.get("fuel_conservation", 0.0),
                    "supply_vulnerability": data.get("supply_vulnerability", 0.0),
                })
        return results
    
    def clear(self) -> None:
        """Reset the knowledge graph."""
        self.graph.clear()
        self._node_age.clear()
        self._entity_registry.clear()
        self._telemetry_node_ids.clear()
        self._step_count = 0

