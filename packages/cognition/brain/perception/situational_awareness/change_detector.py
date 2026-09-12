# Copyright (c) Ultrone Contributors. All rights reserved.
"""Change detection in the world model.

Detects and reports changes in entity state, attributes, relationships, and
classification. Supports:

* entity appearance / disappearance
* position movement
* attribute changes
* state changes
* relationship changes
* classification changes
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .events import ChangeReported, EventBus
from .types import (
    ChangeReport,
    ChangeType,
    EntityID,
    TrackedEntity,
)

__all__ = [
    "ChangeDetector",
    "ChangeDetectorConfig",
]


class ChangeDetectorConfig:
    """Configuration for the change detector."""

    def __init__(
        self,
        *,
        movement_threshold: float = 1.0,
        attribute_change_threshold: float = 0.1,
        classification_change_threshold: float = 0.2,
        min_significance: float = 0.1,
    ) -> None:
        self.movement_threshold = movement_threshold
        self.attribute_change_threshold = attribute_change_threshold
        self.classification_change_threshold = classification_change_threshold
        self.min_significance = min_significance


class ChangeDetector:
    """Detects changes between consecutive entity states."""

    def __init__(
        self,
        *,
        config: Optional[ChangeDetectorConfig] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._config = config or ChangeDetectorConfig()
        self._event_bus = event_bus
        self._previous: Dict[str, TrackedEntity] = {}
        self._reports: List[ChangeReport] = []

    def detect(
        self, entity: TrackedEntity
    ) -> List[ChangeReport]:
        """Detect changes for an entity compared to its previous state."""
        key = str(entity.entity_id)
        previous = self._previous.get(key)
        reports: List[ChangeReport] = []

        if previous is None:
            # New entity appeared.
            report = ChangeReport(
                change_type=ChangeType.APPEARED,
                entity_id=entity.entity_id,
                significance=1.0,
                new_value=entity.state.position.as_array().tolist(),
            )
            reports.append(report)
        else:
            # Movement detection.
            movement = entity.state.position.distance_to(previous.state.position)
            if movement > self._config.movement_threshold:
                reports.append(
                    ChangeReport(
                        change_type=ChangeType.MOVED,
                        entity_id=entity.entity_id,
                        previous_value=previous.state.position.as_array().tolist(),
                        new_value=entity.state.position.as_array().tolist(),
                        significance=min(1.0, movement / (2 * self._config.movement_threshold)),
                    )
                )

            # Attribute changes.
            for attr, new_val in entity.state.attributes.items():
                old_val = previous.state.attributes.get(attr)
                if old_val is not None and old_val != new_val:
                    significance = self._attribute_significance(old_val, new_val)
                    if significance >= self._config.min_significance:
                        reports.append(
                            ChangeReport(
                                change_type=ChangeType.ATTRIBUTE_CHANGED,
                                entity_id=entity.entity_id,
                                attribute=attr,
                                previous_value=old_val,
                                new_value=new_val,
                                significance=significance,
                            )
                        )

            # Classification change.
            if entity.entity_type != previous.entity_type:
                reports.append(
                    ChangeReport(
                        change_type=ChangeType.CLASSIFICATION_CHANGED,
                        entity_id=entity.entity_id,
                        previous_value=previous.entity_type.value,
                        new_value=entity.entity_type.value,
                        significance=self._config.classification_change_threshold,
                    )
                )

            # Disposition change.
            if entity.disposition != previous.disposition:
                reports.append(
                    ChangeReport(
                        change_type=ChangeType.STATE_CHANGED,
                        entity_id=entity.entity_id,
                        previous_value=previous.disposition.value,
                        new_value=entity.disposition.value,
                        significance=self._config.classification_change_threshold,
                    )
                )

        self._previous[key] = entity

        for report in reports:
            self._reports.append(report)
            if self._event_bus is not None:
                self._event_bus.publish_sync(
                    ChangeReported(
                        change_id=report.change_id,
                        change_type=report.change_type.value,
                        entity_id=str(report.entity_id) if report.entity_id else None,
                        significance=report.significance,
                    )
                )

        return reports

    def detect_disappearance(
        self, active_entity_ids: Sequence[EntityID]
    ) -> List[ChangeReport]:
        """Detect entities that have disappeared from the world."""
        active = {str(eid) for eid in active_entity_ids}
        reports: List[ChangeReport] = []
        for key, entity in list(self._previous.items()):
            if key not in active:
                report = ChangeReport(
                    change_type=ChangeType.DISAPPEARED,
                    entity_id=entity.entity_id,
                    significance=1.0,
                )
                reports.append(report)
                self._reports.append(report)
                self._previous.pop(key, None)
        return reports

    @staticmethod
    def _attribute_significance(old_val: Any, new_val: Any) -> float:
        """Estimate the significance of an attribute change."""
        try:
            old_f = float(old_val)
            new_f = float(new_val)
            return min(1.0, abs(new_f - old_f) / max(abs(old_f), 1e-6))
        except (TypeError, ValueError):
            return 1.0 if old_val != new_val else 0.0

    def reports(self, limit: Optional[int] = None) -> List[ChangeReport]:
        reports = self._reports
        if limit is not None:
            reports = reports[-limit:]
        return list(reports)

    def clear(self) -> None:
        self._previous.clear()
        self._reports.clear()