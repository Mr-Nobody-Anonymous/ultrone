"""Research Tooling for experiment management and benchmarking.

Provides infrastructure for reproducible AI research:

- ``ExperimentManager``: Experiment lifecycle management
- ``HyperparameterOptimizer``: Hyperparameter search and optimization
- ``ScenarioBenchmark``: Scenario-based benchmarking
- ``ReproducibilityManager``: Experiment reproducibility tools
- ``StatisticalEvaluator``: Statistical analysis of results
- ``AblationFramework``: Ablation testing infrastructure
- ``AutomatedReport``: Automated experiment report generation
"""

from .experiment_manager import ExperimentManager, ExperimentConfig
from .hyperparameter_optimizer import HyperparameterOptimizer, HPOConfig
from .scenario_benchmark import ScenarioBenchmark, BenchmarkConfig
from .reproducibility import ReproducibilityManager, ReproducibilityConfig
from .statistical_evaluation import StatisticalEvaluator, EvalConfig
from .ablation_framework import AblationFramework, AblationConfig
from .automated_report import AutomatedReport, ReportConfig

__all__ = [
    "ExperimentManager", "ExperimentConfig",
    "HyperparameterOptimizer", "HPOConfig",
    "ScenarioBenchmark", "BenchmarkConfig",
    "ReproducibilityManager", "ReproducibilityConfig",
    "StatisticalEvaluator", "EvalConfig",
    "AblationFramework", "AblationConfig",
    "AutomatedReport", "ReportConfig",
]
