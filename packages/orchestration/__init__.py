"""
ULTRONE Orchestration Package.

Agent/model/tool routing. Selects models, tools, memory and skills
based on task characteristics and records decisions.

Flattens the double-nesting so that:
  from packages.orchestration import router
works instead of:
  from packages.orchestration.orchestration import router
"""
try:
    from packages.orchestration.orchestration.router import SmartRouter
    from packages.orchestration.orchestration.task_classifier import TaskClassifier
    from packages.orchestration.orchestration.model_registry import ModelRegistry
    from packages.orchestration.orchestration.tool_registry import ToolRegistry
    from packages.orchestration.orchestration.memory_router import MemoryRouter
    from packages.orchestration.orchestration.skill_router import SkillRouter
    from packages.orchestration.orchestration.traces import TraceStore
    from packages.orchestration.orchestration.fallback import FallbackPolicy
    from packages.orchestration.orchestration.cost_policy import CostPolicy
    from packages.orchestration.orchestration.context_builder import ContextBuilder
    from packages.orchestration.orchestration.result_validator import ResultValidator
except ImportError:
    SmartRouter = None
    TaskClassifier = None
    ModelRegistry = None
    ToolRegistry = None
    MemoryRouter = None
    SkillRouter = None
    TraceStore = None
    FallbackPolicy = None
    CostPolicy = None
    ContextBuilder = None
    ResultValidator = None

__all__ = [
    "SmartRouter",
    "TaskClassifier",
    "ModelRegistry",
    "ToolRegistry",
    "MemoryRouter",
    "SkillRouter",
    "TraceStore",
    "FallbackPolicy",
    "CostPolicy",
    "ContextBuilder",
    "ResultValidator",
]
