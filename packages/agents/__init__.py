"""
ULTRONE Agents Package.

Agent runtime, multi-domain agents, AI architectures, coding agent,
plugins, skills, and robotics interface.

Sub-packages:
- agents/           — Multi-domain agents (air, land, sea, space, cyber, ...)
- ai_architectures/ — BDI, behavior tree, FSM, GOAP, utility AI
- coding_agent/     — AST analysis, repository indexing, bug localization
- plugin_sdk/       — Plugin development SDK
- plugins/          — Installed plugins
- skills/           — Agent skills
- robotics/         — Robot interface/controller
"""
try:
    from packages.agents.agents.base_agent import BaseAgent
    from packages.agents.agents.platform_agent import PlatformAgent
    from packages.agents.agents.registry import AgentRegistry
except ImportError:
    BaseAgent = None
    PlatformAgent = None
    AgentRegistry = None

__all__ = [
    "BaseAgent",
    "PlatformAgent",
    "AgentRegistry",
]
