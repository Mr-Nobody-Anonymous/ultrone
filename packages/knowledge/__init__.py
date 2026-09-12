"""
ULTRONE Knowledge Package.

Knowledge graph, RAG, memory management, and learning.

Sub-packages:
- knowledge_engine/  — KG, RAG, ontology, memory_manager, vector_memory
- learning/          — Continual learning, feedback
- memory_cluster/    — Redis/DuckDB backends
- automl/            — AutoML experiments
- mlops/             — ML operations
- training_platform/ — Training infrastructure
"""
try:
    from packages.knowledge.knowledge_engine.knowledge_graph import KnowledgeGraph
    from packages.knowledge.knowledge_engine.memory_manager import MemoryManager
    from packages.knowledge.knowledge_engine.rag import RAGPipeline
    from packages.knowledge.knowledge_engine.ontology import Ontology
except ImportError:
    KnowledgeGraph = None
    MemoryManager = None
    RAGPipeline = None
    Ontology = None

__all__ = [
    "KnowledgeGraph",
    "MemoryManager",
    "RAGPipeline",
    "Ontology",
]
