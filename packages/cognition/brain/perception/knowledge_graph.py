# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge graph for battlefield entity relationships."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict

logger = logging.getLogger("Ultrone.Brain.Perception.KnowledgeGraph")


class KnowledgeGraph:
    """
    Knowledge graph representing relationships between battlefield entities.
    
    Legacy lightweight version without networkx.
    Tracks entity relationships, hierarchies, and temporal dependencies.
    """
    
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
    
    def add_entity(self, entity_id: str, properties: Dict[str, Any]) -> None:
        """Add an entity node to the graph."""
        self.nodes[entity_id] = properties
    
    def add_relation(self, source_id: str, target_id: str, relation_type: str) -> None:
        """Add a relationship edge between entities."""
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "type": relation_type,
        })
    
    def get_entities_by_type(self, entity_type: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Get all entities of a given type."""
        return [
            (eid, props) for eid, props in self.nodes.items()
            if props.get("type") == entity_type
        ]
    
    def get_neighbors(self, entity_id: str) -> List[Tuple[str, str, Dict]]:
        """Get all entities connected to a given entity."""
        neighbors = []
        for edge in self.edges:
            if edge["source"] == entity_id:
                target_props = self.nodes.get(edge["target"], {})
                neighbors.append((edge["target"], edge["type"], target_props))
            elif edge["target"] == entity_id:
                source_props = self.nodes.get(edge["source"], {})
                neighbors.append((edge["source"], edge["type"], source_props))
        return neighbors


class MultiINTKnowledgeGraph:
    """
    Multi-INT knowledge graph built on networkx.
    
    Fuses entities from multiple intelligence domains (RADAR, SIGINT,
    VISUAL, COMINT, ELINT) into a unified graph with:
    
    - Node attributes: entity_id, position, domain, team, threat_level,
      signal_strength, velocity, last_seen
    - Edge attributes: relation_type, confidence, signal_frequency,
      temporal_proximity
    
    Key capabilities:
    - **Threat density**: Local clustering coefficient around red-force nodes
      within a configurable proximity radius.
    - **High-value comms links**: Edges between C2/command nodes with
      elevated signal strength (above threshold).
    - **Cluster detection**: Community detection using connected component
      analysis, gracefully handling fast-moving radar contacts vs.
      stationary SIGINT bursts without orphaned edges.
    """

    # : Threshold for "high-value" communication link signal strength
    HIGH_VALUE_SIGNAL_THRESHOLD: float = 0.7

    # : Proximity radius (grid units) for threat density calculations
    PROXIMITY_RADIUS: float = 25.0

    def __init__(self) -> None:
        self._nx: Any = None  # Lazy import of networkx
        self._import_networkx()
        
        self.graph: Any = self._nx.Graph() if self._nx else None
        self._entity_count: int = 0
        
        # Track entity domains to support graceful disconnected-component analysis
        self._domain_index: Dict[str, Set[str]] = defaultdict(set)
    
    def _import_networkx(self) -> None:
        """Lazy-import networkx so the module is loadable if nx is absent."""
        try:
            import networkx as nx
            self._nx = nx
        except ImportError:
            logger.warning(
                "networkx is not installed. MultiINTKnowledgeGraph will operate "
                "in degraded mode (no community detection). Install with: pip install networkx"
            )
    
    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------
    
    def add_entity(
        self,
        entity_id: str,
        domain: str = "general",
        team: str = "unknown",
        position: Optional[Tuple[float, float]] = None,
        threat_level: float = 0.0,
        signal_strength: float = 0.0,
        velocity: Optional[Tuple[float, float]] = None,
        entity_type: str = "contact",
        is_c2: bool = False,
    ) -> None:
        """Add or update an entity node in the knowledge graph.
        
        Args:
            entity_id: Unique identifier for the entity.
            domain: Intelligence domain (radar, sigint, visual, comint, elint, etc.).
            team: Affiliation (blue, red, neutral, unknown).
            position: (x, y) grid position.
            threat_level: 0.0 (none) to 1.0 (critical).
            signal_strength: 0.0–1.0 measured signal intensity.
            velocity: (vx, vy) velocity vector.
            entity_type: Classification (contact, command_node, supply, etc.).
            is_c2: Whether this entity is a command-and-control node.
        """
        if self.graph is None:
            logger.debug("Graph unavailable; skipping add_entity.")
            return
        
        attrs: Dict[str, Any] = {
            "domain": domain,
            "team": team,
            "position": position or (0.0, 0.0),
            "threat_level": threat_level,
            "signal_strength": signal_strength,
            "velocity": velocity or (0.0, 0.0),
            "entity_type": entity_type,
            "is_c2": is_c2,
        }
        
        self.graph.add_node(entity_id, **attrs)
        self._entity_count = self.graph.number_of_nodes()
        self._domain_index[domain].add(entity_id)
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str = "linked",
        confidence: float = 1.0,
        signal_frequency: float = 0.0,
        temporal_proximity: float = 0.0,
    ) -> None:
        """Add a relationship edge between two entities.
        
        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.
            relation_type: Type of relation (comms, radar_lock, visual_track, etc.).
            confidence: Confidence in this relation (0.0–1.0).
            signal_frequency: Communication frequency (for comms/ELINT edges).
            temporal_proximity: How close in time these entities were observed together.
        """
        if self.graph is None:
            return
        
        attrs: Dict[str, Any] = {
            "relation_type": relation_type,
            "confidence": confidence,
            "signal_frequency": signal_frequency,
            "temporal_proximity": temporal_proximity,
        }
        self.graph.add_edge(source_id, target_id, **attrs)
    
    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity and all its edges from the graph."""
        if self.graph is None:
            return
        
        node_data = self.graph.nodes.get(entity_id)
        if node_data:
            domain = node_data.get("domain", "general")
            if entity_id in self._domain_index.get(domain, set()):
                self._domain_index[domain].discard(entity_id)
        
        self.graph.remove_node(entity_id)
        self._entity_count = self.graph.number_of_nodes()
    
    def entity_count(self) -> int:
        """Return the number of entities in the graph."""
        return self._entity_count
    
    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the attributes of a specific entity."""
        if self.graph is None:
            return None
        data = self.graph.nodes.get(entity_id)
        if data is None:
            return None
        return dict(data)
    
    def get_entities_by_domain(self, domain: str) -> List[str]:
        """Get all entity IDs belonging to a given intelligence domain."""
        return list(self._domain_index.get(domain, set()))
    
    def get_entities_by_team(self, team: str) -> List[str]:
        """Get all entity IDs belonging to a given team."""
        if self.graph is None:
            return []
        return [
            n for n, d in self.graph.nodes(data=True)
            if d.get("team") == team
        ]
    
    def get_entities_near(
        self,
        position: Tuple[float, float],
        radius: float,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get all entities within a given radius of a position."""
        if self.graph is None:
            return []
        results: List[Tuple[str, Dict[str, Any]]] = []
        for n, d in self.graph.nodes(data=True):
            pos = d.get("position", (0.0, 0.0))
            dist = ((pos[0] - position[0]) ** 2 + (pos[1] - position[1]) ** 2) ** 0.5
            if dist <= radius:
                results.append((n, dict(d)))
        return results
    
    # ------------------------------------------------------------------
    # Summary generation (get_summary)
    # ------------------------------------------------------------------
    
    def get_summary(self) -> str:
        """Produce a multi-INT situational awareness text summary.
        
        The summary includes:
        1. **Threat density**: For each red-force entity, the local clustering
           coefficient of its neighbourhood is reported as a proxy for how
           concentrated threats are in that area.
        2. **High-value communications links**: Edges with signal_strength
           above HIGH_VALUE_SIGNAL_THRESHOLD that connect C2 nodes or
           command entities are flagged as high-value intercept targets.
        3. **Entity clusters**: NetworkX connected-component (or community)
           analysis enumerates distinct clusters, noting domain mixing
           (e.g., radar + sigint contacts in the same cluster).
        
        Returns:
            Human-readable summary string.
        """
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return (
                "Multi-INT Knowledge Graph: No entities to report. "
                "Awaiting sensor feeds."
            )
        
        nx = self._nx
        G = self.graph
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("📡 MULTI-INT KNOWLEDGE GRAPH SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Total entities: {G.number_of_nodes()}")
        lines.append(f"Total relations: {G.number_of_edges()}")
        
        # ---- 1. Domain breakdown ----
        domain_counts: Dict[str, int] = {}
        for _, d in G.nodes(data=True):
            dom = d.get("domain", "unknown")
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
        
        if domain_counts:
            lines.append("")
            lines.append("── Intelligence Domain Breakdown ──")
            for dom, cnt in sorted(domain_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  • {dom.upper()}: {cnt} entities")
        
        # ---- 2. Threat density (local clustering around red nodes) ----
        lines.append("")
        lines.append("── Threat Density Analysis ──")
        
        red_nodes = [
            n for n, d in G.nodes(data=True)
            if d.get("team") == "red"
        ]
        
        if red_nodes and nx:
            high_threat_zones = 0
            for red_id in red_nodes:
                red_data = G.nodes[red_id]
                red_pos = red_data.get("position", (0.0, 0.0))
                
                # Get neighbours within proximity radius (not just graph neighbours)
                nearby = self.get_entities_near(red_pos, self.PROXIMITY_RADIUS)
                nearby_ids = [nid for nid, _ in nearby if nid != red_id]
                
                if len(nearby_ids) >= 2:
                    # Build induced subgraph for local clustering coefficient
                    sub = G.subgraph(nearby_ids + [red_id])
                    try:
                        # Clustering coefficient of the red node within this subgraph
                        coeff = nx.clustering(sub, red_id)
                        lines.append(
                            f"  ⚠ Red entity '{red_id}': clustering coefficient = {coeff:.3f} "
                            f"(neighbourhood size={len(nearby_ids)})"
                        )
                        if coeff > 0.5:
                            high_threat_zones += 1
                    except (nx.NetworkXError, KeyError, Exception):
                        pass
                else:
                    lines.append(
                        f"  ○ Red entity '{red_id}': isolated (no nearby entities "
                        f"within {self.PROXIMITY_RADIUS} units)."
                    )
            
            if high_threat_zones == 0:
                lines.append("  ✓ No high-threat-density zones detected.")
            else:
                lines.append(
                    f"  🚨 {high_threat_zones} high-density threat zone(s) identified."
                )
        else:
            lines.append("  No red-force entities in the knowledge graph.")
        
        # ---- 3. High-value communications links ----
        lines.append("")
        lines.append("── High-Value Communications Links ──")
        
        hv_links: List[Tuple[str, str, float]] = []
        for u, v, d in G.edges(data=True):
            sig = d.get("signal_frequency", 0.0)
            u_is_c2 = G.nodes[u].get("is_c2", False)
            v_is_c2 = G.nodes[v].get("is_c2", False)
            edge_conf = d.get("confidence", 0.0)
            
            # A link is "high-value" if:
            #   a) signal_frequency >= threshold, OR
            #   b) it connects two C2 nodes, OR
            #   c) confidence is very high (>0.9) and signal_frequency > 0
            is_high_value = (
                sig >= self.HIGH_VALUE_SIGNAL_THRESHOLD
                or (u_is_c2 and v_is_c2)
                or (edge_conf > 0.9 and sig > 0.0)
            )
            if is_high_value:
                hv_links.append((u, v, sig))
        
        if hv_links:
            lines.append(f"  Found {len(hv_links)} high-value comms link(s):")
            for u, v, sig in sorted(hv_links, key=lambda x: -x[2])[:10]:  # top 10
                u_type = G.nodes[u].get("entity_type", "unknown")
                v_type = G.nodes[v].get("entity_type", "unknown")
                lines.append(
                    f"    • {u} ({u_type}) ⟷ {v} ({v_type}) "
                    f"signal={sig:.2f}"
                )
        else:
            lines.append("  No high-value communications links detected.")
        
        # ---- 4. Entity clusters (connected components) ----
        lines.append("")
        lines.append("── Entity Clusters ──")
        
        if nx:
            try:
                # Get connected components; filter out singletons for brevity
                components = list(nx.connected_components(G))
                non_trivial = [c for c in components if len(c) >= 2]
                singletons = [c for c in components if len(c) == 1]
                
                lines.append(
                    f"  {len(non_trivial)} cluster(s) with ≥2 entities, "
                    f"{len(singletons)} isolated entity/entities."
                )
                
                for i, comp in enumerate(non_trivial):
                    comp_list = list(comp)
                    # Determine the domain diversity of this cluster
                    domains_in_cluster: Set[str] = set()
                    teams_in_cluster: Set[str] = set()
                    for node_id in comp_list:
                        nd = G.nodes[node_id]
                        domains_in_cluster.add(nd.get("domain", "unknown"))
                        teams_in_cluster.add(nd.get("team", "unknown"))
                    
                    domain_str = ", ".join(sorted(d for d in domains_in_cluster if d != "unknown"))
                    team_str = ", ".join(sorted(t for t in teams_in_cluster if t != "unknown"))
                    
                    # Gracefully handle high-speed vs stationary mixing:
                    # If a cluster has both radar (high-speed) and sigint (stationary burst)
                    # entities, it indicates a legitimate multi-INT correlation, not an orphan.
                    has_radar = "radar" in domains_in_cluster
                    has_sigint = "sigint" in domains_in_cluster
                    mix_note = ""
                    if has_radar and has_sigint:
                        mix_note = " [multi-INT correlated: radar + sigint]"
                    
                    lines.append(
                        f"  [{i+1}] Cluster size={len(comp_list)}, "
                        f"domains=[{domain_str}], teams=[{team_str}]{mix_note}"
                    )
                    
                    # Show up to 5 representative entities per cluster
                    for node_id in comp_list[:5]:
                        nd = G.nodes[node_id]
                        pos = nd.get("position", (0.0, 0.0))
                        threat = nd.get("threat_level", 0.0)
                        lines.append(
                            f"       · {node_id}: pos=({pos[0]:.1f}, {pos[1]:.1f}), "
                            f"threat={threat:.2f}"
                        )
                    if len(comp_list) > 5:
                        lines.append(f"       ... and {len(comp_list) - 5} more entities.")
            except Exception as e:
                logger.debug(f"Cluster analysis failed: {e}")
                lines.append("  Cluster analysis unavailable (networkx error).")
        else:
            lines.append("  Install networkx for cluster analysis.")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    # ------------------------------------------------------------------
    # Data import from environment
    # ------------------------------------------------------------------
    
    def ingest_from_observation(self, observation: Dict[str, Any]) -> None:
        """Populate the knowledge graph from a battlefield observation dict.
        
        Processes:
        - red_force entity
        - blue_assets (drones, jammers, missiles)
        - supply nodes
        """
        if self.graph is None:
            return
        
        # Red force
        red = observation.get("red_force", {})
        if red:
            red_pos = red.get("position", (0, 0))
            self.add_entity(
                entity_id="red_force_main",
                domain="radar",
                team="red",
                position=(float(red_pos[0]), float(red_pos[1])),
                threat_level=red.get("health", 100) / 100.0,
                entity_type=red.get("type", "unknown"),
                signal_strength=0.5,  # nominal
                velocity=(0.0, 0.0),
            )
        
        # Blue assets
        blue = observation.get("blue_assets", {})
        for asset_type, assets in blue.items():
            for i, asset in enumerate(assets):
                asset_id = f"{asset_type}_{i}"
                pos = asset.get("position", (0, 0))
                self.add_entity(
                    entity_id=asset_id,
                    domain="visual",
                    team="blue",
                    position=(float(pos[0]), float(pos[1])),
                    threat_level=0.0,
                    entity_type=asset_type,
                    signal_strength=0.3,
                    velocity=(0.0, 0.0),
                )
        
        # Supply nodes
        supply_nodes = observation.get("supply_nodes", {})
        for sid, sn in supply_nodes.items():
            sn_pos = sn.get("position", (0, 0))
            self.add_entity(
                entity_id=sid,
                domain="logistics",
                team=sn.get("team", "unknown"),
                position=(float(sn_pos[0]), float(sn_pos[1])),
                threat_level=0.0,
                entity_type="supply_node",
                signal_strength=0.1,
                is_c2=True,
            )
        
        # Link blue assets to their supply node
        for asset_type, assets in blue.items():
            for i, asset in enumerate(assets):
                asset_id = f"{asset_type}_{i}"
                linked = asset.get("linked_supply", "blue_supply")
                if linked in supply_nodes:
                    self.add_relation(
                        source_id=asset_id,
                        target_id=linked,
                        relation_type="supply_chain",
                        confidence=0.9,
                    )
        
        # Link red force to its supply node
        if red and "red_supply" in supply_nodes:
            self.add_relation(
                source_id="red_force_main",
                target_id="red_supply",
                relation_type="supply_chain",
                confidence=0.9,
            )
        
        logger.debug(
            f"Ingested observation: {self._entity_count} entities, "
            f"{self.graph.number_of_edges() if self.graph else 0} relations."
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the knowledge graph."""
        if self.graph is None:
            return {"enabled": False, "reason": "networkx not installed"}
        
        nx = self._nx
        G = self.graph
        
        stats: Dict[str, Any] = {
            "enabled": True,
            "entity_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "domains": {
                dom: len(ids) for dom, ids in self._domain_index.items()
            },
        }
        
        if nx and G.number_of_nodes() > 0:
            try:
                stats["connected_components"] = nx.number_connected_components(G)
                stats["density"] = nx.density(G)
            except Exception:
                pass
        
        return stats


# Backward-compatible alias
MultiINTKG = MultiINTKnowledgeGraph

