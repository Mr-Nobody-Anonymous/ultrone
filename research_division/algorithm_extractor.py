# Copyright (c) Ultrone Contributors. All rights reserved.
"""Algorithm Extractor — extracts mathematical formulations, algorithm details,
architectures, datasets, and evaluation metrics from papers.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from comms.protocol import MessageType, Priority
from knowledge_engine.base import KnowledgeSource, KnowledgeCategory, ConfidenceLevel
from research_db.schema import PaperRecord
from .base_agent import ResearchAgent, ResearchAgentRole

logger = logging.getLogger("Ultrone.ResearchDivision.Extractor")


class AlgorithmExtractor(ResearchAgent):
    """Extracts structured algorithm details from papers."""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id=kwargs.pop("agent_id", "algorithm-extractor-001"),
            role=ResearchAgentRole.EXTRACTOR,
            **kwargs,
        )
        self.message_handlers[MessageType.RESEARCH_PAPER_ANALYZED] = self._on_paper_analyzed

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        paper_ids = kwargs.get("paper_ids")
        if paper_ids:
            papers = [self.research_db.get_paper(pid) for pid in paper_ids]
            papers = [p for p in papers if p is not None]
        else:
            papers = self.research_db.list_papers()

        extracted = []
        for paper in papers:
            result = self._extract_from_paper(paper)
            extracted.append(result)

        self._log_action("extract_cycle", {"papers": len(extracted)}, None)
        return {"extracted": len(extracted), "results": extracted}

    def _on_paper_analyzed(self, message: Any) -> Any:
        content = message.content
        paper_id = content.get("paper_id")
        paper = self.research_db.get_paper(paper_id) if paper_id else None
        if paper is None:
            return None
        result = self._extract_from_paper(paper)
        return result

    def _extract_from_paper(self, paper: PaperRecord) -> Dict[str, Any]:
        """Extract algorithm details from a paper record."""
        title = paper.title or "Untitled"

        # Extract equations (simulated from algorithms)
        equations = self._extract_equations(paper.algorithms)

        # Extract hyperparameters (simulated)
        hyperparameters = self._extract_hyperparameters(paper.algorithms)

        # Extract evaluation metrics
        metrics = self._extract_metrics(title)

        # Update paper record
        paper.equations = list(dict.fromkeys(paper.equations + equations))
        for k, v in hyperparameters.items():
            paper.hyperparameters.setdefault(k, []).append(v)
        paper.updated_at = time.time()
        self.research_db.save_paper(paper)

        # Store knowledge entries
        for algo in paper.algorithms:
            self.knowledge.store_auto_categorized(
                content=f"Algorithm '{algo}' from paper '{title}': equations={equations}, "
                        f"hyperparameters={hyperparameters}",
                source=KnowledgeSource.PAPER,
                tags=["algorithm", "equations", "hyperparameters"],
                entities=[algo],
                confidence_score=paper.confidence_score,
                layer="algorithm",
                metadata={"paper_id": paper.paper_id},
            )

        result = {
            "paper_id": paper.paper_id,
            "title": title,
            "equations": equations,
            "hyperparameters": hyperparameters,
            "metrics": metrics,
        }
        self._log_action("algorithm_extracted", {"paper_id": paper.paper_id}, result)
        return result

    @staticmethod
    def _extract_equations(algorithms: List[str]) -> List[str]:
        """Generate representative equations for algorithms (simulated)."""
        equations = []
        for algo in algorithms:
            if "Transformer" in algo:
                equations.append("Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V")
            elif "Rag" in algo or "RAG" in algo:
                equations.append("P(y|x) = sum_z P(z|x) * P(y|z,x)")
            elif "Diffusion" in algo:
                equations.append("dx_t = -f(x_t,t)dt + g(t)dw_t")
            elif "Filter" in algo:
                equations.append("x_k = A x_{k-1} + B u_k + w_k")
            elif "Evolutionary" in algo:
                equations.append("x' = x + sigma * N(0, I)")
            elif "Monte Carlo" in algo:
                equations.append("U(s) = (1/N) sum_i R_i")
        return equations

    @staticmethod
    def _extract_hyperparameters(algorithms: List[str]) -> Dict[str, Any]:
        """Generate representative hyperparameters (simulated)."""
        hps = {}
        for algo in algorithms:
            if "Transformer" in algo:
                hps.update({"learning_rate": 1e-4, "batch_size": 32, "num_layers": 12})
            elif "Rag" in algo or "RAG" in algo:
                hps.update({"top_k": 5, "retriever_weight": 0.3})
            elif "Diffusion" in algo:
                hps.update({"num_steps": 1000, "beta_start": 0.0001, "beta_end": 0.02})
            elif "Reinforcement" in algo:
                hps.update({"gamma": 0.99, "soft_update_tau": 0.001})
        return hps

    @staticmethod
    def _extract_metrics(title: str) -> List[str]:
        """Extract evaluation metrics from title (simulated)."""
        title_lower = title.lower()
        metrics = []
        if "classification" in title_lower or "image" in title_lower:
            metrics.extend(["accuracy", "f1", "precision", "recall"])
        if "language" in title_lower or "generation" in title_lower:
            metrics.extend(["perplexity", "bleu", "rouge"])
        if "reinforcement" in title_lower:
            metrics.extend(["reward", "success_rate", "episode_length"])
        if not metrics:
            metrics = ["accuracy", "f1"]
        return metrics