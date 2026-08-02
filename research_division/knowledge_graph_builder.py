# Copyright (c) Ultrone Contributors. All rights reserved.
"""Knowledge Graph Builder — constructs and maintains the knowledge graph
from research findings, linking papers, algorithms, datasets, and concepts.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from knowledge_engine.knowledge_graph import NodeType, EdgeType
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.GraphBuilder")


class KnowledgeGraphBuilder(ResearchAgent):
    """Builds and maintains the knowledge graph from research data."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "graph-builder-001"),
            role=ResearchAgentRole.GRAPH_BUILDER,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_KNOWLEDGE_UPDATED] = self._on_knowledge_updated

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Build knowledge graph from all research records."""
        # Build from papers
        papers = self.research_db.list_papers()
        paper_nodes = 0
        for paper in papers:
            node_id = self._add_paper_node(paper)
            if node_id:
                paper_nodes += 1

        # Build from experiments
        experiments = self.research_db.list_experiments()
        for experiment in experiments:
            self._add_experiment_node(experiment)

        # Build from benchmarks
        benchmarks = self.research_db.list_benchmarks()
        for benchmark in benchmarks:
            self._add_benchmark_node(benchmark)

        stats = self.knowledge.knowledge_graph.get_stats()
        self._log_action("graph_build", {"paper_nodes": paper_nodes}, stats)
        return stats

    def _on_knowledge_updated(self, message: Any) -> Any:
        """Handle knowledge update events."""
        entry_id = message.content.get("entry_id")
        if entry_id:
            entry = self.knowledge._all_entries.get(entry_id)
            if entry:
                self.knowledge._index_in_graph(entry)
                return {"indexed": entry_id}
        return None

    def _add_paper_node(self, paper: Any) -> Optional[str]:
        """Add a paper node to the knowledge graph."""
        node_id = self.knowledge.add_graph_node(
            label=paper.title or "Untitled paper",
            node_type=NodeType.PAPER,
            properties={
                "paper_id": paper.paper_id,
                "venue": paper.venue,
                "year": paper.publication_date,
                "algorithms": paper.algorithms,
            },
            confidence_score=paper.confidence_score,
        )

        # Link algorithms
        for algo in paper.algorithms:
            algo_node = self.knowledge.knowledge_graph.lookup_node(algo, NodeType.ALGORITHM)
            if algo_node is None:
                algo_node_id = self.knowledge.add_graph_node(
                    label=algo,
                    node_type=NodeType.ALGORITHM,
                    confidence_score=0.5,
                )
            else:
                algo_node_id = algo_node.node_id
            self.knowledge.add_graph_edge(
                node_id, algo_node_id, edge_type=EdgeType.USES
            )

        # Link authors
        for author in paper.authors:
            author_node = self.knowledge.knowledge_graph.lookup_node(author, NodeType.AUTHOR)
            if author_node is None:
                author_node_id = self.knowledge.add_graph_node(
                    label=author,
                    node_type=NodeType.AUTHOR,
                    confidence_score=0.5,
                )
            else:
                author_node_id = author_node.node_id
            self.knowledge.add_graph_edge(
                node_id, author_node_id, edge_type=EdgeType.AUTHORS
            )

        return node_id

    def _add_experiment_node(self, experiment: Any) -> Optional[str]:
        """Add an experiment node to the knowledge graph."""
        return self.knowledge.add_graph_node(
            label=f"Experiment: {experiment.experiment_id}",
            node_type=NodeType.EXPERIMENT,
            properties={
                "experiment_id": experiment.experiment_id,
                "status": experiment.status,
                "dataset": experiment.dataset,
            },
            confidence_score=0.7,
        )

    def _add_benchmark_node(self, benchmark: Any) -> Optional[str]:
        """Add a benchmark node to the knowledge graph."""
        return self.knowledge.add_graph_node(
            label=f"Benchmark: {benchmark.name}",
            node_type=NodeType.BENCHMARK,
            properties={
                "benchmark_id": benchmark.benchmark_id,
                "improvement": benchmark.improvement,
            },
            confidence_score=0.8,
        )