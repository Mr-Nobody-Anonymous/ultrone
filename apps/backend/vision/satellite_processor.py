"""Satellite imagery processor - handles image loading, filtering, and enhancement."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum


class Band(Enum):
    """Common satellite imagery bands."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    NIR = "nir"  # Near-Infrared
    SWIR = "swir"  # Short-Wave Infrared
    TIR = "tir"  # Thermal Infrared
    PAN = "pan"  # Panchromatic


@dataclass
class SatelliteImage:
    """Represents a satellite image with multiple bands."""
    width: int
    height: int
    bands: Dict[str, np.ndarray] = field(default_factory=dict)
    resolution_m: float = 1.0  # meters per pixel
    timestamp: Optional[str] = None
    cloud_cover: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_rgb(self) -> Optional[np.ndarray]:
        """Get RGB composite image (HxWx3)."""
        if all(b in self.bands for b in [Band.RED.value, Band.GREEN.value, Band.BLUE.value]):
            return np.stack([
                self.bands[Band.RED.value],
                self.bands[Band.GREEN.value],
                self.bands[Band.BLUE.value],
            ], axis=-1)
        return None

    def get_ndvi(self) -> Optional[np.ndarray]:
        """Calculate Normalized Difference Vegetation Index."""
        nir = self.bands.get(Band.NIR.value)
        red = self.bands.get(Band.RED.value)
        if nir is not None and red is not None:
            nir_f = nir.astype(float)
            red_f = red.astype(float)
            return np.divide(nir_f - red_f, nir_f + red_f + 1e-10, out=np.zeros_like(nir_f), where=(nir_f + red_f) > 0)
        return None


class SatelliteImageProcessor:
    """Processes satellite imagery for battlefield analysis."""

    def __init__(self):
        self._processed_count = 0

    def load_image(self, data: np.ndarray, band: str = Band.RED.value) -> SatelliteImage:
        """Load a single-band image into a SatelliteImage."""
        h, w = data.shape[:2]
        img = SatelliteImage(width=w, height=h)
        img.bands[band] = data
        self._processed_count += 1
        return img

    def enhance_contrast(self, image: SatelliteImage, band: Optional[str] = None) -> SatelliteImage:
        """Apply histogram equalization for contrast enhancement."""
        bands_to_process = [band] if band else list(image.bands.keys())
        for b in bands_to_process:
            if b in image.bands:
                data = image.bands[b].astype(float)
                p2, p98 = np.percentile(data, [2, 98])
                enhanced = np.clip((data - p2) / (p98 - p2 + 1e-10), 0, 1)
                image.bands[b] = (enhanced * 255).astype(np.uint8)
        return image

    def pansharpen(self, pan: np.ndarray, ms: SatelliteImage) -> SatelliteImage:
        """Pansharpen multispectral bands using panchromatic band."""
        if pan.ndim != 2 or ms.width != pan.shape[1] or ms.height != pan.shape[0]:
            raise ValueError("Panchromatic and multispectral dimensions must match")
        pan_f = pan.astype(float)
        pan_norm = pan_f / (pan_f.max() + 1e-10)
        for b in ms.bands:
            ms_band = ms.bands[b].astype(float)
            ms.bands[b] = (ms_band * pan_norm).astype(np.uint8)
        return ms

    def detect_clouds(self, image: SatelliteImage) -> np.ndarray:
        """Simple cloud detection using brightness threshold."""
        rgb = image.get_rgb()
        if rgb is None:
            return np.zeros((image.height, image.width), dtype=bool)
        brightness = rgb.mean(axis=-1)
        return brightness > 200

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "SatelliteImageProcessor",
            "processed_count": self._processed_count,
            "capabilities": ["contrast_enhancement", "pansharpening", "cloud_detection", "ndvi"],
        }
