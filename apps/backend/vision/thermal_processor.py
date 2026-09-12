"""Thermal image processor - handles thermal/IR imagery for target detection."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class ThermalSignature:
    """A thermal signature detected in thermal imagery."""
    x: int
    y: int
    width: int
    height: int
    temperature_c: float
    confidence: float
    classification: str  # e.g., "engine", "personnel", "muzzle_flash"


@dataclass
class ThermalAnalysisResult:
    """Result of thermal image analysis."""
    signatures: List[ThermalSignature] = field(default_factory=list)
    ambient_temp_c: float = 25.0
    max_temp_c: float = 0.0
    min_temp_c: float = 0.0
    hot_spot_count: int = 0
    image_width: int = 0
    image_height: int = 0


class ThermalImageProcessor:
    """Processes thermal/IR imagery for military target detection.

    Identifies heat signatures, classifies them, and estimates
    temperature values from pixel intensities.
    """

    # Typical temperature ranges for military objects (°C)
    SIGNATURE_TEMPS = {
        "engine": (60, 120),
        "exhaust": (150, 400),
        "personnel": (30, 38),
        "muzzle_flash": (300, 800),
        "electronics": (40, 70),
        "friction": (45, 90),
    }

    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity
        self._processed_count = 0

    def analyze(self, thermal_image: np.ndarray, ambient_temp: float = 25.0) -> ThermalAnalysisResult:
        """Analyze a thermal image for heat signatures.

        Args:
            thermal_image: 2D numpy array of thermal pixel values
            ambient_temp: Ambient temperature in Celsius

        Returns:
            ThermalAnalysisResult with detected signatures
        """
        if thermal_image.ndim != 2:
            if thermal_image.ndim == 3:
                thermal_image = thermal_image.mean(axis=-1)
            else:
                return ThermalAnalysisResult()

        h, w = thermal_image.shape
        img_f = thermal_image.astype(float)

        # Normalize to temperature-like values
        img_min, img_max = img_f.min(), img_f.max()
        if img_max > img_min:
            temp_range = 60.0  # Assume 60°C dynamic range
            temp_map = ambient_temp + (img_f - img_min) / (img_max - img_min) * temp_range
        else:
            temp_map = np.full_like(img_f, ambient_temp)

        result = ThermalAnalysisResult(
            ambient_temp_c=ambient_temp,
            max_temp_c=float(temp_map.max()),
            min_temp_c=float(temp_map.min()),
            image_width=w,
            image_height=h,
        )

        # Find hot spots above threshold
        threshold = ambient_temp + 15 * self.sensitivity
        hot_mask = temp_map > threshold

        if not hot_mask.any():
            return result

        from scipy import ndimage
        labeled, num_features = ndimage.label(hot_mask)

        for i in range(1, num_features + 1):
            ys, xs = np.where(labeled == i)
            if len(ys) < 3:
                continue

            avg_temp = float(temp_map[ys, xs].mean())
            max_temp = float(temp_map[ys, xs].max())

            # Classify based on temperature
            classification = self._classify_signature(avg_temp, max_temp)
            confidence = min(0.95, 0.5 + (max_temp - ambient_temp) / 100)

            signature = ThermalSignature(
                x=int(xs.min()),
                y=int(ys.min()),
                width=int(xs.max() - xs.min()),
                height=int(ys.max() - ys.min()),
                temperature_c=avg_temp,
                confidence=confidence,
                classification=classification,
            )
            result.signatures.append(signature)

        result.hot_spot_count = len(result.signatures)
        self._processed_count += 1
        return result

    def _classify_signature(self, avg_temp: float, max_temp: float) -> str:
        """Classify a thermal signature based on temperature."""
        for cls, (t_min, t_max) in self.SIGNATURE_TEMPS.items():
            if t_min <= avg_temp <= t_max or t_min <= max_temp <= t_max:
                return cls
        if avg_temp < 40:
            return "personnel"
        return "unknown_heat_source"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ThermalImageProcessor",
            "processed_count": self._processed_count,
            "sensitivity": self.sensitivity,
            "signature_classes": list(self.SIGNATURE_TEMPS.keys()),
        }
