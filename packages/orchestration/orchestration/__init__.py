# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model + Tool Orchestration layer.

Selects among interchangeable models, tools, memory strategies, and
skills *per task*, instead of hard-coding one provider -- then proves
each routing decision through the same governed pipeline as every
other adaptive subsystem::

    Task -> TaskClassifier -> RoutingPolicy -> execute -> Validator
       -> accept | retry/fallback -> Trace -> ExperienceMemory

Every tunable routing knob lives in a ``ParameterRegistry`` (see
``orchestration.router.default_routing_registry``), which means the
existing ``AdaptiveOptimizer`` can evolve the routing *policy* --
thresholds, cost aversion, planning depth -- exactly the way it evokes
patrol configurations, with training/holdout separation, regression
suites, reproducibility checks, and gated promotion via BrainStore.

Package contents map 1:1 onto the orchestration charter:

- ``task_classifier``   TaskProfile extraction (deterministic)
- ``model_registry``    ModelSpec catalog (interchangeable backends)
- ``tool_registry``     ToolSpec catalog + selection
- ``memory_router``     Memory strategy selection
- ``skill_router``      Skill selection
- ``context_builder``   Context assembly under a token budget
- ``cost_policy``       Cost/latency estimation + budget pressure
- ``result_validator``  Structured-result contract enforcement
- ``fallback``          Ordered retry chains across candidates
- ``router``            RoutingPolicy + Orchestrator (the loop)
- ``traces``            Reproducible per-decision audit records
"""

from orchestration.task_classifier import TaskProfile, classify
from orchestration.traces import AttemptRecord, OrchestrationTrace, TraceLog

__all__ = [
    "TaskProfile",
    "classify",
    "AttemptRecord",
    "OrchestrationTrace",
    "TraceLog",
]