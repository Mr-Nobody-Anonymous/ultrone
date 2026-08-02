# Copyright (c) Ultrone Contributors. All rights reserved.
"""Schema definitions for the ULTRONE research database.

Structured records for papers, experiments, benchmarks, and implementation
plans with versioning, timestamps, source attribution, and confidence.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PaperRecord:
    """Structured record for a research paper."""
    paper_id: str = field(default_factory=lambda: f"P-{uuid.uuid4().hex[:12]}")
    title: str = ""
    authors: List[str] = field(default_factory=list)
    venue: str = ""
    publication_date: Optional[str] = None
    citations: int = 0
    abstract: str = ""
    summary: str = ""
    algorithms: List[str] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    architectures: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    future_work: List[str] = field(default_factory=list)
    implementation_ideas: List[str] = field(default_factory=list)
    related_papers: List[str] = field(default_factory=list)
    github_repositories: List[str] = field(default_factory=list)
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.5
    knowledge_graph_links: List[str] = field(default_factory=list)
    arxiv_id: str = ""
    doi: str = ""
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "venue": self.venue,
            "publication_date": self.publication_date,
            "citations": self.citations,
            "abstract": self.abstract,
            "summary": self.summary,
            "algorithms": self.algorithms,
            "equations": self.equations,
            "architectures": self.architectures,
            "datasets": self.datasets,
            "hyperparameters": self.hyperparameters,
            "limitations": self.limitations,
            "future_work": self.future_work,
            "implementation_ideas": self.implementation_ideas,
            "related_papers": self.related_papers,
            "github_repositories": self.github_repositories,
            "benchmark_results": self.benchmark_results,
            "confidence_score": self.confidence_score,
            "knowledge_graph_links": self.knowledge_graph_links,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "url": self.url,
            "metadata": self.metadata,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperRecord":
        return cls(
            paper_id=data.get("paper_id", f"P-{uuid.uuid4().hex[:12]}"),
            title=data.get("title", ""),
            authors=data.get("authors", []),
            venue=data.get("venue", ""),
            publication_date=data.get("publication_date"),
            citations=data.get("citations", 0),
            abstract=data.get("abstract", ""),
            summary=data.get("summary", ""),
            algorithms=data.get("algorithms", []),
            equations=data.get("equations", []),
            architectures=data.get("architectures", []),
            datasets=data.get("datasets", []),
            hyperparameters=data.get("hyperparameters", {}),
            limitations=data.get("limitations", []),
            future_work=data.get("future_work", []),
            implementation_ideas=data.get("implementation_ideas", []),
            related_papers=data.get("related_papers", []),
            github_repositories=data.get("github_repositories", []),
            benchmark_results=data.get("benchmark_results", {}),
            confidence_score=data.get("confidence_score", 0.5),
            knowledge_graph_links=data.get("knowledge_graph_links", []),
            arxiv_id=data.get("arxiv_id", ""),
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            metadata=data.get("metadata", {}),
            version=data.get("version", 1),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class ExperimentRecord:
    """Structured record for a research experiment."""
    experiment_id: str = field(default_factory=lambda: f"E-{uuid.uuid4().hex[:12]}")
    hypothesis: str = ""
    research_motivation: str = ""
    implementation: str = ""
    dataset: str = ""
    training_config: Dict[str, Any] = field(default_factory=dict)
    evaluation_metrics: Dict[str, Any] = field(default_factory=dict)
    benchmark_comparison: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    execution_logs: List[str] = field(default_factory=list)
    performance_graphs: List[str] = field(default_factory=list)
    success_criteria: str = ""
    rollback_strategy: str = ""
    conclusion: str = ""
    recommendation: str = ""
    status: str = "proposed"  # proposed, running, completed, failed, rejected
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "research_motivation": self.research_motivation,
            "implementation": self.implementation,
            "dataset": self.dataset,
            "training_config": self.training_config,
            "evaluation_metrics": self.evaluation_metrics,
            "benchmark_comparison": self.benchmark_comparison,
            "resource_usage": self.resource_usage,
            "execution_logs": self.execution_logs,
            "performance_graphs": self.performance_graphs,
            "success_criteria": self.success_criteria,
            "rollback_strategy": self.rollback_strategy,
            "conclusion": self.conclusion,
            "recommendation": self.recommendation,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentRecord":
        return cls(
            experiment_id=data.get("experiment_id", f"E-{uuid.uuid4().hex[:12]}"),
            hypothesis=data.get("hypothesis", ""),
            research_motivation=data.get("research_motivation", ""),
            implementation=data.get("implementation", ""),
            dataset=data.get("dataset", ""),
            training_config=data.get("training_config", {}),
            evaluation_metrics=data.get("evaluation_metrics", {}),
            benchmark_comparison=data.get("benchmark_comparison", {}),
            resource_usage=data.get("resource_usage", {}),
            execution_logs=data.get("execution_logs", []),
            performance_graphs=data.get("performance_graphs", []),
            success_criteria=data.get("success_criteria", ""),
            rollback_strategy=data.get("rollback_strategy", ""),
            conclusion=data.get("conclusion", ""),
            recommendation=data.get("recommendation", ""),
            status=data.get("status", "proposed"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class BenchmarkRecord:
    """Structured record for a benchmark run."""
    benchmark_id: str = field(default_factory=lambda: f"B-{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    task_type: str = ""
    dataset: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    baseline_results: Dict[str, Any] = field(default_factory=dict)
    candidate_results: Dict[str, Any] = field(default_factory=dict)
    improvement: Optional[float] = None
    environment: Dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "dataset": self.dataset,
            "metrics": self.metrics,
            "baseline_results": self.baseline_results,
            "candidate_results": self.candidate_results,
            "improvement": self.improvement,
            "environment": self.environment,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkRecord":
        return cls(
            benchmark_id=data.get("benchmark_id", f"B-{uuid.uuid4().hex[:12]}"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            task_type=data.get("task_type", ""),
            dataset=data.get("dataset", ""),
            metrics=data.get("metrics", {}),
            baseline_results=data.get("baseline_results", {}),
            candidate_results=data.get("candidate_results", {}),
            improvement=data.get("improvement"),
            environment=data.get("environment", {}),
            status=data.get("status", "completed"),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class ImplementationPlan:
    """Structured implementation plan for a research finding."""
    plan_id: str = field(default_factory=lambda: f"IP-{uuid.uuid4().hex[:12]}")
    title: str = ""
    description: str = ""
    source_paper_ids: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_effort: str = ""
    dependencies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    expected_improvements: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed, in_progress, completed, rejected
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "description": self.description,
            "source_paper_ids": self.source_paper_ids,
            "steps": self.steps,
            "estimated_effort": self.estimated_effort,
            "dependencies": self.dependencies,
            "risks": self.risks,
            "expected_improvements": self.expected_improvements,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImplementationPlan":
        return cls(
            plan_id=data.get("plan_id", f"IP-{uuid.uuid4().hex[:12]}"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            source_paper_ids=data.get("source_paper_ids", []),
            steps=data.get("steps", []),
            estimated_effort=data.get("estimated_effort", ""),
            dependencies=data.get("dependencies", []),
            risks=data.get("risks", []),
            expected_improvements=data.get("expected_improvements", []),
            status=data.get("status", "proposed"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class ResearchDatabaseSchema:
    """Schema metadata for the research database."""

    RECORD_TYPES = {
        "paper": PaperRecord,
        "experiment": ExperimentRecord,
        "benchmark": BenchmarkRecord,
        "implementation_plan": ImplementationPlan,
    }

    @classmethod
    def create_record(cls, record_type: str, **kwargs: Any) -> Any:
        """Factory method to create a record of the given type."""
        record_cls = cls.RECORD_TYPES.get(record_type)
        if record_cls is None:
            raise ValueError(f"Unknown record type: {record_type}")
        return record_cls(**kwargs)

    @classmethod
    def get_schema_summary(cls) -> Dict[str, Any]:
        """Return schema summary for documentation."""
        return {
            "record_types": {
                name: {
                    "class": record_cls.__name__,
                    "fields": list(record_cls.__dataclass_fields__.keys()),
                }
                for name, record_cls in cls.RECORD_TYPES.items()
            }
        }