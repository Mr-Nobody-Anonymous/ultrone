"""
ULTRONE Cognition Package.

Unified public API for the cognitive architecture.

Sub-packages:
- brain/           — Orchestrator, perception, reasoning, learning, memory, XAI, strategy
- cognitive/       — 15-layer cognitive architecture (the crown jewel)
- frontier/        — Frontier reasoning, adaptation, agents, decision
- adaptive/        — Adaptive parameter optimization, promotion
- self_improvement/ — Self-improvement loop, neural, self-training
- evolution/       — Genome evolution protocol
- sandbox/         — Evaluation sandbox, UCL, machines
- game_ai/         — Game AI arena, commander
- generative/      — Scenario/briefing generation
- ultrone_ai/      — Code intelligence, reasoning
"""

try:
    from packages.cognition.cognitive.cognitive_loop import CognitiveLoop
    from packages.cognition.cognitive.cognitive_agent import CognitiveAgent
    from packages.cognition.brain.orchestrator import BrainOrchestrator
except ImportError:
    CognitiveLoop = None
    CognitiveAgent = None
    BrainOrchestrator = None

__all__ = [
    # Core cognitive components
    "CognitiveLoop",
    "CognitiveAgent",
    "BrainOrchestrator",
]
