# Copyright (c) Ultrone Contributors. All rights reserved.
"""Feature Store — centralized storage and management of features."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.FeatureStore")


@dataclass
class Feature:
    """A feature definition."""
    feature_id: str = field(default_factory=lambda: f"f-{uuid.uuid4().hex[:8]}")
    name: str = ""
    dtype: str = "float"
    description: str = ""
    created_at: float = field(default_factory=time.time)


class FeatureStore:
    """Stores feature definitions and value statistics."""

    def __init__(self):
        self._features: Dict[str, Feature] = {}
        self._values: Dict[str, List[float]] = {}

    def register_feature(self, name: str, dtype: str = "float", description: str = "") -> Feature:
        """Register a feature definition."""
        feature = Feature(name=name, dtype=dtype, description=description)
        self._features[feature.feature_id] = feature
        logger.info("Registered feature %s", name)
        return feature

    def log_values(self, feature_name: str, values: List[float]) -> None:
        """Log values for a feature."""
        self._values.setdefault(feature_name, []).extend(values)

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        return self._features.get(feature_id)

    def get_feature_by_name(self, name: str) -> Optional[Feature]:
        for f in self._features.values():
            if f.name == name:
                return f
        return None

    def list_features(self) -> List[Feature]:
        return list(self._features.values())

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "FeatureStore",
            "features_registered": len(self._features),
            "features_with_values": len(self._values),
        }
