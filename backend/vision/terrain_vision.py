"""Terrain vision analysis - classify terrain features from satellite/heightmap data."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class TerrainClassification(Enum):
    """Terrain type classifications from visual analysis."""
    URBAN = "urban"
    FOREST = "forest"
    WATER = "water"
    DESERT = "desert"
    MOUNTAIN = "mountain"
    FARMLAND = "farmland"
    MARSH = "marsh"
    SNOW = "snow"


@dataclass
class TerrainSegment:
    """A classified terrain region."""
    classification: TerrainClassification
    confidence: float
    bounds: Tuple[int, int, int, int]  # x1, y1, x2, y2
    area_pixels: int = 0
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class TerrainVisionResult:
    """Result of terrain vision analysis."""
    segments: List[TerrainSegment] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    dominant_classification: Optional[TerrainClassification] = None


class TerrainVisionAnalyzer:
    """Analyzes satellite imagery to classify terrain features."""

    def __init__(self):
        self._analysis_count = 0

    def analyze(self, image: np.ndarray) -> TerrainVisionResult:
        """Classify terrain types in an image.

        Uses spectral indices and texture analysis for classification.
        """
        h, w = image.shape[:2] if image.ndim >= 2 else (0, 0)
        result = TerrainVisionResult(image_width=w, image_height=h)

        if image.ndim < 2 or image.size == 0:
            return result

        # Convert to float for analysis
        if image.ndim == 3:
            img_f = image.astype(float)
            gray = img_f.mean(axis=-1)
        else:
            gray = image.astype(float)
            img_f = np.stack([gray, gray, gray], axis=-1)

        # Simple spectral classification
        # Water: low reflectance across all bands
        water_mask = gray < np.percentile(gray, 10)

        # Vegetation: high NIR, low red (simulated via green channel dominance)
        if img_f.shape[-1] >= 3:
            r, g, b = img_f[:, :, 0], img_f[:, :, 1], img_f[:, :, 2]
            vegetation_mask = (g > r) & (g > b) & ~water_mask
            urban_mask = (r > g) & (r > b) & ~water_mask & ~vegetation_mask
        else:
            vegetation_mask = np.zeros_like(gray, dtype=bool)
            urban_mask = np.zeros_like(gray, dtype=bool)

        # Brightness-based classification
        bright = gray > np.percentile(gray, 85)
        dark = gray < np.percentile(gray, 15)

        # Build segments
        if vegetation_mask.any():
            veg_pixels = int(vegetation_mask.sum())
            result.segments.append(TerrainSegment(
                classification=TerrainClassification.FOREST,
                confidence=0.75,
                bounds=(0, 0, w, h),
                area_pixels=veg_pixels,
            ))

        if water_mask.any():
            water_pixels = int(water_mask.sum())
            result.segments.append(TerrainSegment(
                classification=TerrainClassification.WATER,
                confidence=0.85,
                bounds=(0, 0, w, h),
                area_pixels=water_pixels,
            ))

        if urban_mask.any():
            urban_pixels = int(urban_mask.sum())
            result.segments.append(TerrainSegment(
                classification=TerrainClassification.URBAN,
                confidence=0.7,
                bounds=(0, 0, w, h),
                area_pixels=urban_pixels,
            ))

        # Determine dominant classification
        if result.segments:
            result.dominant_classification = max(
                result.segments,
                key=lambda s: s.area_pixels,
            ).classification

        self._analysis_count += 1
        return result

    def analyze_satellite(self, sat_image: Any) -> TerrainVisionResult:
        """Analyze terrain from a SatelliteImage object."""
        rgb = sat_image.get_rgb() if hasattr(sat_image, 'get_rgb') else None
        if rgb is not None:
            return self.analyze(rgb)
        bands = getattr(sat_image, 'bands', {})
        if bands:
            return self.analyze(next(iter(bands.values())))
        return TerrainVisionResult()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "TerrainVisionAnalyzer",
            "analysis_count": self._analysis_count,
            "classifications": [c.value for c in TerrainClassification],
        }
