"""Machine-checkable causal boundary and epistemic provenance verification.

Enforces strict temporal separation:
TIME t:
  - observations available at t
  - belief state available at t
  - policy / model versions available at t
  - action generated
ACTION
TIME t+1:
  - new observations
  - actual outcome
  - evaluation / reward

Hard Invariant:
pre_action_decision_inputs MUST NOT contain post_action_outcome fields or future observations.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CausalBoundaryViolationError(Exception):
    """Raised when post-action outcome fields or future observations contaminate pre-action decisions."""
    pass


class TaintTag(str, Enum):
    """Epistemic classifications for data that cannot enter pre-action decisions."""
    GROUND_TRUTH = "GROUND_TRUTH"
    FUTURE_OUTCOME = "FUTURE_OUTCOME"
    REWARD = "REWARD"
    POST_ACTION_STATE = "POST_ACTION_STATE"
    UNVERIFIED = "UNVERIFIED"


@dataclass
class TaintedValue:
    """Explicitly wrapped value carrying taint metadata regardless of its attribute names."""
    value: Any
    tag: TaintTag = TaintTag.GROUND_TRUTH
    source: str = "oracle"
    timestamp: float = field(default_factory=time.time)

    def is_tainted(self) -> bool:
        return True


class TaintTracker:
    """Registry and taint propagation engine to identify post-action or oracle data."""
    _tainted_ids: Set[int] = set()

    @classmethod
    def taint(cls, obj: Any) -> Any:
        if obj is not None:
            cls._tainted_ids.add(id(obj))
            if hasattr(obj, "__dict__"):
                obj.__dict__["__is_tainted__"] = True
            elif isinstance(obj, dict):
                obj["__is_tainted__"] = True
        return obj

    @classmethod
    def is_tainted(cls, obj: Any) -> bool:
        if isinstance(obj, TaintedValue):
            return True
        if id(obj) in cls._tainted_ids:
            return True
        if hasattr(obj, "__dict__") and getattr(obj, "__is_tainted__", False):
            return True
        if isinstance(obj, dict) and obj.get("__is_tainted__", False):
            return True
        return False


# Disallowed post-action outcome keys in pre-action inputs (fallback blacklist defense-in-depth)
FORBIDDEN_POST_ACTION_KEYS: Set[str] = {
    "actual_outcome",
    "outcome",
    "ground_truth_outcome",
    "post_action_damage",
    "hits",
    "actual_hits",
    "battle_damage_assessment",
    "post_state",
    "future_observation",
    "ground_truth_hit",
    "actual_casualties",
}


@dataclass(frozen=True)
class ConfidenceProvenance:
    """Explicit cryptographic provenance backing any probabilistic confidence claim.

    Chain of Trust:
    sensor measurement -> measurement hash -> model hash -> calibration hash -> confidence -> decision
    """
    confidence: float
    confidence_source: str
    observation_ids: List[str]
    model_version: str = "v1.0.0"
    calibration_version: str = "isotonic-v1"
    timestamp: float = field(default_factory=time.time)
    ttl_seconds: float = 10.0
    # Cryptographic provenance hashes & hardware identity
    observation_hash: Optional[str] = None          # SHA-256 of sensor raw input
    model_artifact_hash: Optional[str] = None       # SHA-256 of model weights
    calibration_artifact_hash: Optional[str] = None # SHA-256 of calibration artifact
    sensor_id: Optional[str] = None                 # Hardware sensor identifier
    sensor_calibration_version: Optional[str] = None# Sensor calibration curve version

    def is_fresh(self, now: Optional[float] = None) -> bool:
        t = time.time() if now is None else now
        return (t - self.timestamp) <= self.ttl_seconds

    def is_valid(self, require_crypto: bool = False) -> bool:
        """Returns True only if confidence has explicit source, backing observations, and fresh timestamps."""
        if not self.confidence_source or self.confidence_source in ("fallback", "synthetic", "default"):
            return False
        if not self.observation_ids:
            return False
        if not (0.0 <= self.confidence <= 1.0):
            return False
        if require_crypto:
            if not self.observation_hash or not self.model_artifact_hash:
                return False
        return self.is_fresh()


class CausalBoundaryValidator:
    """Enforces causal invariants on agent decision inputs and confidence values."""

    @staticmethod
    def inspect_decision_inputs(inputs: Any, path: str = "") -> None:
        """Recursively checks that no post-action outcome fields or tainted objects exist in pre-action context."""
        if inputs is None:
            return

        if TaintTracker.is_tainted(inputs):
            raise CausalBoundaryViolationError(
                f"Causal violation at '{path or 'root'}': Pre-action decision inputs "
                f"contain tainted data (ground truth / future outcome / post-action state)"
            )

        if isinstance(inputs, dict):
            for k, v in inputs.items():
                cur_path = f"{path}.{k}" if path else str(k)
                if TaintTracker.is_tainted(k) or TaintTracker.is_tainted(v):
                    raise CausalBoundaryViolationError(
                        f"Causal violation at '{cur_path}': Pre-action decision inputs "
                        f"contain tainted key or value"
                    )
                if isinstance(k, str) and k.lower() in FORBIDDEN_POST_ACTION_KEYS:
                    raise CausalBoundaryViolationError(
                        f"Causal violation at '{cur_path}': Pre-action decision inputs "
                        f"contain post-action outcome field '{k}'"
                    )
                CausalBoundaryValidator.inspect_decision_inputs(v, cur_path)
        elif isinstance(inputs, (list, tuple, set)):
            for idx, item in enumerate(inputs):
                cur_path = f"{path}[{idx}]"
                CausalBoundaryValidator.inspect_decision_inputs(item, cur_path)
        elif hasattr(inputs, "__dict__"):
            for attr_name, attr_val in inputs.__dict__.items():
                if attr_name.startswith("__"):
                    continue
                cur_path = f"{path}.{attr_name}" if path else attr_name
                if TaintTracker.is_tainted(attr_val):
                    raise CausalBoundaryViolationError(
                        f"Causal violation at '{cur_path}': Object attribute is tainted"
                    )
                if attr_name.lower() in FORBIDDEN_POST_ACTION_KEYS:
                    raise CausalBoundaryViolationError(
                        f"Causal violation at '{cur_path}': Object property is forbidden post-action field '{attr_name}'"
                    )
                CausalBoundaryValidator.inspect_decision_inputs(attr_val, cur_path)

    @staticmethod
    def extract_calibrated_confidence(
        action: Dict[str, Any],
        require_source: bool = True,
        require_crypto: bool = False,
    ) -> Tuple[float, Optional[str]]:
        """Extracts confidence with strict provenance requirements.
        
        If source provenance is missing or invalid:
        Returns confidence = 0.0 (conservative rejection) with an explanation reason.
        """
        prov_obj = action.get("confidence_provenance")
        if isinstance(prov_obj, ConfidenceProvenance):
            if not prov_obj.is_valid(require_crypto=require_crypto):
                return 0.0, "Confidence provenance invalid or stale; defaulting to conservative 0.0"
            return prov_obj.confidence, None

        if isinstance(prov_obj, dict):
            prov = ConfidenceProvenance(
                confidence=float(prov_obj.get("confidence", 0.0)),
                confidence_source=str(prov_obj.get("confidence_source", "")),
                observation_ids=list(prov_obj.get("observation_ids", [])),
                model_version=str(prov_obj.get("model_version", "unknown")),
                calibration_version=str(prov_obj.get("calibration_version", "unknown")),
                timestamp=float(prov_obj.get("timestamp", time.time())),
                observation_hash=prov_obj.get("observation_hash"),
                model_artifact_hash=prov_obj.get("model_artifact_hash"),
                calibration_artifact_hash=prov_obj.get("calibration_artifact_hash"),
                sensor_id=prov_obj.get("sensor_id"),
                sensor_calibration_version=prov_obj.get("sensor_calibration_version"),
            )
            if not prov.is_valid(require_crypto=require_crypto):
                return 0.0, "Confidence provenance invalid or stale; defaulting to conservative 0.0"
            return prov.confidence, None

        # Check inline action fields
        conf = action.get("confidence")
        source = action.get("confidence_source")
        obs_ids = action.get("observation_ids")

        if conf is None:
            return 0.0, "No confidence provided; defaulting to conservative 0.0"

        if require_source:
            if not source or not obs_ids:
                return 0.0, (
                    f"Unbacked confidence ({conf}) without verified source or observation_ids; "
                    "defaulting to conservative 0.0"
                )

        return float(conf), None
