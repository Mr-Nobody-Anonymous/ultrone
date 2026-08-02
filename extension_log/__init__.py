# Copyright (c) Ultrone Contributors. All rights reserved.
"""Extension Log — comprehensive logging system for the research platform.

Logs every decision, experiment, benchmark, code generation, file
modification, test result, deployment proposal, citation, reasoning
summary, recommendation, generated module, architecture update,
optimization, failure, warning, and exception.

Stores logs in JSON, Markdown, SQLite, Vector Database, and Knowledge Graph.
"""

from .audit import AuditLogger, LogLevel, LogCategory
from .stores import (
    JSONLogStore,
    MarkdownLogStore,
    SQLiteLogStore,
    VectorLogStore,
    KnowledgeGraphLogStore,
)

__all__ = [
    "AuditLogger",
    "LogLevel",
    "LogCategory",
    "JSONLogStore",
    "MarkdownLogStore",
    "SQLiteLogStore",
    "VectorLogStore",
    "KnowledgeGraphLogStore",
]