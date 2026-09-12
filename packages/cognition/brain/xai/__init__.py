# Copyright (c) Ultrone Contributors. All rights reserved.
"""Explainable AI (XAI) module for model interpretability.

Provides explainability modules including:

- ``DecisionTrace``: Step-by-step decision path generation
- ``SHAPExplainer``: SHAP value-based explanations
- ``LIMEExplainer``: Local Interpretable Model-agnostic Explanations
- ``CounterfactualExplainer``: Counterfactual explanations
- ``ConfidenceCalibration``: Confidence calibration
- ``ReasoningGraph``: Decision reasoning graph visualization
"""

from .decision_trace import DecisionTrace, DecisionTraceConfig
from .shap_explainer import SHAPExplainer
from .lime_explainer import LIMEExplainer
from .counterfactual import CounterfactualExplainer, CounterfactualConfig
from .confidence_calibration import ConfidenceCalibration
from .reasoning_graph import ReasoningGraph

__all__ = [
    "DecisionTrace", "DecisionTraceConfig",
    "SHAPExplainer",
    "LIMEExplainer",
    "CounterfactualExplainer", "CounterfactualConfig",
    "ConfidenceCalibration",
    "ReasoningGraph",
]