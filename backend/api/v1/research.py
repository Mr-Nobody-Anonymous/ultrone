"""Research division API — endpoints for the autonomous research platform."""

import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from research_db.store import ResearchDatabase
from research_db.schema import PaperRecord, ExperimentRecord, BenchmarkRecord, ImplementationPlan

router = APIRouter(prefix="/research", tags=["research"])

# Shared research database instance
_research_db = ResearchDatabase()


class PaperCreate(BaseModel):
    """Create a paper record."""
    title: str
    authors: List[str] = []
    venue: str = ""
    publication_date: Optional[str] = None
    abstract: str = ""
    arxiv_id: str = ""
    doi: str = ""
    url: str = ""


class ExperimentCreate(BaseModel):
    """Create an experiment record."""
    hypothesis: str
    research_motivation: str = ""
    implementation: str = ""
    dataset: str = ""
    success_criteria: str = ""


class BenchmarkCreate(BaseModel):
    """Create a benchmark record."""
    name: str
    description: str = ""
    task_type: str = ""
    dataset: str = ""


class PlanCreate(BaseModel):
    """Create an implementation plan."""
    title: str
    description: str = ""
    source_paper_ids: List[str] = []


@router.get("/papers")
async def list_papers() -> List[Dict[str, Any]]:
    """List all research papers."""
    return [p.to_dict() for p in _research_db.list_papers()]


@router.post("/papers")
async def create_paper(paper: PaperCreate) -> Dict[str, Any]:
    """Create a new paper record."""
    record = PaperRecord(
        title=paper.title,
        authors=paper.authors,
        venue=paper.venue,
        publication_date=paper.publication_date,
        abstract=paper.abstract,
        arxiv_id=paper.arxiv_id,
        doi=paper.doi,
        url=paper.url,
    )
    stored = _research_db.save_paper(record)
    return stored.to_dict()


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str) -> Dict[str, Any]:
    """Get a specific paper."""
    paper = _research_db.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, f"Paper {paper_id} not found")
    return paper.to_dict()


@router.get("/experiments")
async def list_experiments() -> List[Dict[str, Any]]:
    """List all experiments."""
    return [e.to_dict() for e in _research_db.list_experiments()]


@router.post("/experiments")
async def create_experiment(experiment: ExperimentCreate) -> Dict[str, Any]:
    """Create a new experiment."""
    record = ExperimentRecord(
        hypothesis=experiment.hypothesis,
        research_motivation=experiment.research_motivation,
        implementation=experiment.implementation,
        dataset=experiment.dataset,
        success_criteria=experiment.success_criteria,
    )
    stored = _research_db.save_experiment(record)
    return stored.to_dict()


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str) -> Dict[str, Any]:
    """Get a specific experiment."""
    experiment = _research_db.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(404, f"Experiment {experiment_id} not found")
    return experiment.to_dict()


@router.get("/benchmarks")
async def list_benchmarks() -> List[Dict[str, Any]]:
    """List all benchmarks."""
    return [b.to_dict() for b in _research_db.list_benchmarks()]


@router.post("/benchmarks")
async def create_benchmark(benchmark: BenchmarkCreate) -> Dict[str, Any]:
    """Create a new benchmark."""
    record = BenchmarkRecord(
        name=benchmark.name,
        description=benchmark.description,
        task_type=benchmark.task_type,
        dataset=benchmark.dataset,
    )
    stored = _research_db.save_benchmark(record)
    return stored.to_dict()


@router.get("/plans")
async def list_plans() -> List[Dict[str, Any]]:
    """List all implementation plans."""
    return [p.to_dict() for p in _research_db.list_implementation_plans()]


@router.post("/plans")
async def create_plan(plan: PlanCreate) -> Dict[str, Any]:
    """Create a new implementation plan."""
    record = ImplementationPlan(
        title=plan.title,
        description=plan.description,
        source_paper_ids=plan.source_paper_ids,
    )
    stored = _research_db.save_implementation_plan(record)
    return stored.to_dict()


@router.get("/stats")
async def get_research_stats() -> Dict[str, Any]:
    """Get research database statistics."""
    return _research_db.get_stats()