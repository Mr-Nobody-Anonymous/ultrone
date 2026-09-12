# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE adapters layer — thin integration seams to external systems.

Every adapter here is a *port* (interface) plus placeholder implementations.
Implementations should wrap the concrete integrations that already exist in
the platform rather than reimplement them:

    adapters/llm/        -> orchestration/model_registry, core/llm_service
    adapters/vision/     -> backend/vision (object detector, satellite, thermal)
    adapters/vector_db/  -> knowledge_engine/vector_memory, memory_cluster
    adapters/database/   -> core/database + core/db_* modules, research_db
    adapters/external/   -> backend/integrations (REST client, webhooks)

Adapters are the only place new external-system code should appear; the
platform core stays free of vendor specifics.
"""
