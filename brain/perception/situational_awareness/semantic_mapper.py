# Copyright (c) Ultrone Contributors. All rights reserved.
"""Semantic mapping of the observed environment.

Builds and maintains a semantic map that associates spatial regions with
semantic labels (terrain, infrastructure, weather, resources, etc.). Supports
semantic segmentation masks, label confidence, and region queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import numpy as np

from .types import EntityCategory, TrackedEntity, Vector3, utc_now

__all__ = [
    "SemanticRegion",
    "SemanticMap",
    "SemanticMapConfig",
]


@dataclass
class SemanticRegion:
    """A spatial region with a semantic label."""

    region_id: str
    label: str
    category: EntityCategory
    center: Vector3
    radius: float
    confidence: float = 0.5
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=utc_now)
    last_updated: datetime = field(default_factory=utc_now)
    entity_ids: Set[str] = field(default_factory=set)

    def contains(self, position: Vector3) -> bool:
        return self.center.distance_to(position) <= self.radius

    def update(
        self,
        *,
        confidence: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, confidence))
        if attributes:
            self.attributes.update(attributes)
        self.last_updated = utc_now()


class SemanticMapConfig:
    """Configuration for the semantic map."""

    def __init__(
        self,
        *,
        max_regions: int = 10_000,
        default_radius: float = 10.0,
        merge_threshold: float = 0.5,
    ) -> None:
        self.max_regions = max_regions
        self.default_radius = default_radius
        self.merge_threshold = merge_threshold


class SemanticMap:
    """Spatial-semantic map of the environment."""

    def __init__(self, *, config: Optional[SemanticMapConfig] = None) -> None:
        self._config = config or SemanticMapConfig()
        self._regions: Dict[str, SemanticRegion] = {}

    def add_region(
        self,
        *,
        label: str,
        category: EntityCategory,
        center: Vector3,
        radius: Optional[float] = None,
        confidence: float = 0.5,
        attributes: Optional[Dict[str, Any]] = None,
        region_id: Optional[str] = None,
    ) -> SemanticRegion:
        """Add a new semantic region to the map."""
        region_id = region_id or f"{label}-{len(self._regions)}"
        region = SemanticRegion(
            region_id=region_id,
            label=label,
            category=category,
            center=center,
            radius=radius or self._config.default_radius,
            confidence=confidence,
            attributes=attributes or {},
        )
        self._regions[region_id] = region
        return region

    def update_region(
        self,
        region_id: str,
        *,
        confidence: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[SemanticRegion]:
        region = self._regions.get(region_id)
        if region is None:
            return None
        region.update(confidence=confidence, attributes=attributes)
        return region

    def remove_region(self, region_id: str) -> bool:
        return self._regions.pop(region_id, None) is not None

    def get_region(self, region_id: str) -> Optional[SemanticRegion]:
        return self._regions.get(region_id)

    def region_at(self, position: Vector3) -> Optional[SemanticRegion]:
        """Find the region containing the given position."""
        for region in self._regions.values():
            if region.contains(position):
                return region
        return None

    def regions_at(self, position: Vector3) -> List[SemanticRegion]:
        return [r for r in self._regions.values() if r.contains(position)]

    def label_at(self, position: Vector3) -> Optional[str]:
        region = self.region_at(position)
        return region.label if region else None

    def category_at(self, position: Vector3) -> Optional[EntityCategory]:
        region = self.region_at(position)
        return region.category if region else None

    def regions_by_label(self, label: str) -> List[SemanticRegion]:
        return [r for r in self._regions.values() if r.label == label]

    def regions_by_category(self, category: EntityCategory) -> List[SemanticRegion]:
        return [r for r in self._regions.values() if r.category == category]

    def associate_entity(self, region_id: str, entity: TrackedEntity) -> bool:
        """Associate an entity with a region."""
        region = self._regions.get(region_id)
        if region is None:
            return False
        region.entity_ids.add(str(entity.entity_id))
        return True

    def entities_in_region(self, region_id: str) -> List[str]:
        region = self._regions.get(region_id)
        return list(region.entity_ids) if region else []

    def apply_segmentation_mask(
        self,
        mask: np.ndarray,
        *,
        label: str,
        category: EntityCategory,
        origin: Vector3,
        resolution: float = 1.0,
        confidence: float = 0.5,
    ) -> int:
        """Create regions from a semantic segmentation mask.

        Each connected component in the mask becomes a semantic region.
        Returns the number of regions created.
        """
        from scipy import ndimage

        labeled, num_features = ndimage.label(mask > 0)
        created = 0
        for i in range(1, num_features + 1):
            coords = np.argwhere(labeled == i)
            if coords.size == 0:
                continue
            center_local = coords.mean(axis=0)
            center = Vector3(
                x=origin.x + center_local[1] * resolution,
                y=origin.y + center_local[0] * resolution,
                z=origin.z,
            )
            extent = coords.max(axis=0) - coords.min(axis=0)
            radius = float(np.linalg.norm(extent) * resolution / 2.0) + 1.0
            self.add_region(
                label=f"{label}_{i}",
                category=category,
                center=center,
                radius=radius,
                confidence=confidence,
            )
            created += 1
        return created

    def all(self) -> List[SemanticRegion]:
        return list(self._regions.values())

    def count(self) -> int:
        return len(self._regions)

    def clear(self) -> None:
        self._regions.clear()