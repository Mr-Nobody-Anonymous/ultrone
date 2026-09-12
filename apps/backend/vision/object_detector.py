"""Object detection for satellite and tactical imagery."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class DetectionBBox:
    """Bounding box for a detected object."""
    x: int
    y: int
    width: int
    height: int
    label: str
    confidence: float


@dataclass
class DetectionResult:
    """Result of object detection on an image."""
    detections: List[DetectionBBox] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    processing_time_ms: float = 0.0


class ObjectDetector:
    """Detects military objects in satellite/thermal imagery.

    Uses simulated detection for environments without GPU/ML frameworks.
    For production, connect to YOLO, DETR, or other CNN-based detectors.
    """

    # Military object classes
    MILITARY_CLASSES = [
        "tank", "armored_vehicle", "artillery", "missile_launcher",
        "radar", "air_defense", "soldier", "building", "bridge",
        "aircraft", "helicopter", "naval_vessel", "supply_truck",
        "command_post", "ammo_depot",
    ]

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self._detection_count = 0

    def detect(self, image: np.ndarray) -> DetectionResult:
        """Run object detection on an image array.

        Args:
            image: HxW or HxWxC numpy array

        Returns:
            DetectionResult with bounding boxes
        """
        h, w = image.shape[:2] if image.ndim >= 2 else (0, 0)
        result = DetectionResult(image_width=w, image_height=h)

        # Simulated detection - in production, this would call a model
        # We generate plausible detections based on image content
        if image.ndim == 3 and image.shape[-1] >= 3:
            gray = image.mean(axis=-1).astype(float)
        elif image.ndim == 2:
            gray = image.astype(float)
        else:
            return result

        # Find hot spots (bright areas) as potential targets
        threshold = np.percentile(gray, 95)
        hot_mask = gray > threshold

        if hot_mask.any():
            # Simple blob detection via connected components
            from scipy import ndimage
            labeled, num_features = ndimage.label(hot_mask)

            for i in range(1, num_features + 1):
                ys, xs = np.where(labeled == i)
                if len(ys) < 5:  # Skip tiny blobs
                    continue

                confidence = min(0.95, 0.5 + np.random.random() * 0.4)
                if confidence < self.confidence_threshold:
                    continue

                label = np.random.choice(self.MILITARY_CLASSES)
                bbox = DetectionBBox(
                    x=int(xs.min()),
                    y=int(ys.min()),
                    width=int(xs.max() - xs.min()),
                    height=int(ys.max() - ys.min()),
                    label=label,
                    confidence=float(confidence),
                )
                result.detections.append(bbox)
                self._detection_count += 1

        return result

    def detect_from_satellite(self, sat_image: Any) -> DetectionResult:
        """Detect objects from a SatelliteImage object."""
        rgb = sat_image.get_rgb() if hasattr(sat_image, 'get_rgb') else None
        if rgb is not None:
            return self.detect(rgb)
        # Try first available band
        bands = getattr(sat_image, 'bands', {})
        if bands:
            first_band = next(iter(bands.values()))
            return self.detect(first_band)
        return DetectionResult()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ObjectDetector",
            "detection_count": self._detection_count,
            "confidence_threshold": self.confidence_threshold,
            "classes": len(self.MILITARY_CLASSES),
        }
