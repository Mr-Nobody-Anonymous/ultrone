"""Knowledge engine API — endpoints for the knowledge engine."""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from knowledge_engine.memory_manager import KnowledgeMemoryManager
from knowledge_engine.base import KnowledgeEntry, KnowledgeSource, KnowledgeCategory

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# Shared knowledge manager instance
_knowledge = KnowledgeMemoryManager()


class KnowledgeCreate(BaseModel):
    """Create a knowledge entry."""
    content: str
    category: str = "theory"
    source: str = "other"
    tags: List[str] = []
    entities: List[str] = []
    confidence_score: float = 0.5
    layer: str = "semantic"


@router.get("/entries")
async def list_entries(layer: Optional[str] = None) -> List[Dict[str, Any]]:
    """List knowledge entries."""
    if layer:
        layer_obj = _knowledge._layers.get(layer)
        if layer_obj:
            return [e.to_dict() for e in layer_obj.all_entries()]
        return []
    return [e.to_dict() for e in _knowledge._all_entries.values()]


@router.post("/entries")
async def create_entry(entry: KnowledgeCreate) -> Dict[str, Any]:
    """Create a new knowledge entry."""
    try:
        category = KnowledgeCategory(entry.category)
        source = KnowledgeSource(entry.source)
    except ValueError:
        raise HTTPException(400, "Invalid category or source")

    ke = KnowledgeEntry(
        content=entry.content,
        category=category,
        source=source,
        tags=entry.tags,
        entities=entry.entities,
        confidence_score=entry.confidence_score,
    )
    stored = _knowledge.store(ke, layer=entry.layer)
    return stored.to_dict()


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str) -> Dict[str, Any]:
    """Get a specific knowledge entry."""
    entry = _knowledge._all_entries.get(entry_id)
    if not entry:
        raise HTTPException(404, f"Entry {entry_id} not found")
    return entry.to_dict()


@router.get("/search")
async def search_entries(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search knowledge entries."""
    results = _knowledge.recall(query, limit=limit)
    return [e.to_dict() for e in results]


@router.get("/semantic-search")
async def semantic_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Semantic search using vector memory."""
    results = _knowledge.semantic_search(query, limit=limit)
    return [
        {"entry": entry.to_dict(), "score": score}
        for entry, score in results
    ]


@router.get("/graph")
async def get_graph() -> Dict[str, Any]:
    """Get the knowledge graph."""
    return _knowledge.knowledge_graph.to_dict()


@router.get("/graph/stats")
async def get_graph_stats() -> Dict[str, Any]:
    """Get knowledge graph statistics."""
    return _knowledge.knowledge_graph.get_stats()


@router.get("/stats")
async def get_knowledge_stats() -> Dict[str, Any]:
    """Get knowledge engine statistics."""
    return _knowledge.get_stats()