"""Algorithm registry API - discover and configure every algorithm in ULTRONE."""

import importlib
import inspect
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Registry of all algorithm modules in the platform
ALGORITHM_CATEGORIES = {
    "search_planning": {
        "module": "brain.reasoning.search",
        "algorithms": [
            "MCTS", "HTNPlanner", "AStar", "DLite", "LPAStar",
            "MAPFPlanner", "BeamSearch", "BidirectionalSearch",
            "PDDLPlanner", "AnytimePlanner", "RecedingHorizonPlanner",
            "DPPlanner", "RRTPlanner", "PRMPlanner"
        ]
    },
    "reinforcement_learning": {
        "module": "brain.learning.rl",
        "algorithms": [
            "PPO", "SAC", "TD3", "DDPG", "DQN", "RainbowDQN",
            "MARL", "SelfPlay", "CurriculumLearning",
            "QMIX", "MADDPG", "VDN"
        ]
    },
    "coordination": {
        "module": "brain.reasoning.coordination",
        "algorithms": [
            "ConsensusProtocol", "TaskAllocation", "ContractNet",
            "CoalitionFormation", "BlackboardSystem", "RoleAssignment",
            "FormationControl", "SwarmCoordination",
            "TeamReasoning", "DynamicLeadership"
        ]
    },
    "optimization": {
        "module": "brain.learning.optimization",
        "algorithms": [
            "GeneticAlgorithm", "CMAES", "DifferentialEvolution",
            "ParticleSwarm", "SimulatedAnnealing", "BayesianOptimization",
            "AntColony", "NSGA2", "CrossEntropyMethod", "MAPElites"
        ]
    },
    "game_theory": {
        "module": "brain.reasoning.game_theory",
        "algorithms": [
            "NashEquilibrium", "StackelbergGame", "MinimaxSearch",
            "CFR", "AuctionMechanism", "ZeroSumGame", "CooperativeGame"
        ]
    },
    "probabilistic": {
        "module": "brain.perception.probabilistic",
        "algorithms": [
            "BayesianNetwork", "HiddenMarkovModel", "KalmanFilter",
            "ExtendedKalmanFilter", "UnscentedKalmanFilter",
            "ParticleFilter", "BeliefPropagation"
        ]
    },
    "graph_intelligence": {
        "module": "brain.perception.graph_intelligence",
        "algorithms": [
            "GraphNeuralNetwork", "GraphAttentionNetwork",
            "KnowledgeEmbeddings", "CommunityDetection", "TemporalGraph"
        ]
    },
    "decision_intelligence": {
        "module": "brain.reasoning.decision_intelligence",
        "algorithms": [
            "InfluenceDiagram", "CausalBayesianNetwork",
            "StructuralCausalModel", "CounterfactualReasoner",
            "DynamicInfluenceGraph", "DecisionNetwork"
        ]
    },
    "xai": {
        "module": "brain.xai",
        "algorithms": [
            "DecisionTrace", "SHAPExplainer", "LIMEExplainer",
            "CounterfactualExplainer", "ConfidenceCalibration",
            "ReasoningGraph"
        ]
    },
    "memory": {
        "module": "brain.memory",
        "algorithms": [
            "EpisodicMemory", "SemanticMemory", "WorkingMemory",
            "AssociativeMemory", "MemoryConsolidation"
        ]
    },
    "knowledge": {
        "module": "brain.perception.knowledge",
        "algorithms": [
            "VectorDatabase", "RAGMemory", "SemanticSearch"
        ]
    },
    "ai_architectures": {
        "module": "ai_architectures",
        "algorithms": [
            "BehaviorTree", "GOAPPlanner", "UtilityAISystem",
            "BDIAgent", "FSMController", "HierarchicalFSM",
            "BlackboardSystemArch", "ReactivePlanner"
        ]
    },
    "ml_adapters": {
        "module": "brain.learning.ml",
        "algorithms": [
            "PyTorchAdapter", "LightningAdapter", "SB3Adapter",
            "RayRLlibAdapter", "PyGAdapter", "ONNXAdapter",
            "XGBoostAdapter"
        ]
    },
    "research": {
        "module": "research",
        "algorithms": [
            "ExperimentManager", "HyperparameterOptimizer",
            "ScenarioBenchmark", "ReproducibilityTools",
            "StatisticalEvaluation", "AblationFramework",
            "AutomatedReport"
        ]
    }
}


class AlgorithmDiscovery(BaseModel):
    """Discovered algorithm metadata."""
    name: str
    category: str
    module_path: str
    config_fields: List[Dict[str, Any]]
    available: bool


@router.get("/")
async def list_categories() -> Dict[str, Any]:
    """List all algorithm categories with counts."""
    return {
        category: {
            "count": len(info["algorithms"]),
            "algorithms": info["algorithms"]
        }
        for category, info in ALGORITHM_CATEGORIES.items()
    }


@router.get("/discover")
async def discover_algorithms() -> List[AlgorithmDiscovery]:
    """Discover and validate all available algorithms."""
    results = []
    for category, info in ALGORITHM_CATEGORIES.items():
        try:
            mod = importlib.import_module(info["module"])
            for algo_name in info["algorithms"]:
                available = hasattr(mod, algo_name)
                config_fields = []
                if available:
                    cls = getattr(mod, algo_name)
                    if hasattr(cls, "__init__"):
                        sig = inspect.signature(cls.__init__)
                        for param in sig.parameters.values():
                            if param.name != "self" and param.name != "config":
                                config_fields.append({
                                    "name": param.name,
                                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                                    "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                                })
                results.append(AlgorithmDiscovery(
                    name=algo_name,
                    category=category,
                    module_path=f"{info['module']}.{algo_name}",
                    config_fields=config_fields,
                    available=available,
                ))
        except ImportError:
            for algo_name in info["algorithms"]:
                results.append(AlgorithmDiscovery(
                    name=algo_name, category=category,
                    module_path=f"{info['module']}.{algo_name}",
                    config_fields=[], available=False,
                ))
    return results


@router.get("/{category}")
async def get_category(category: str) -> Dict[str, Any]:
    """Get algorithms for a specific category."""
    info = ALGORITHM_CATEGORIES.get(category)
    if not info:
        raise HTTPException(404, f"Category '{category}' not found")
    return {"category": category, **info}
