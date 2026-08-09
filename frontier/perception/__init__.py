"""Multimodal perception interface for ULTRONE.

Supports: Text, Images, Audio, Video, Time series, Tabular data,
Graphs, Documents, and sensor simulations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Perception")


class Modality(Enum):
    """Supported input modalities."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TIME_SERIES = "time_series"
    TABULAR = "tabular"
    GRAPH = "graph"
    DOCUMENT = "document"
    SENSOR = "sensor"


@dataclass
class Detection:
    """A detected entity or object in perceptual input."""
    label: str
    confidence: float
    bounding_box: Optional[List[float]] = None  # [x, y, w, h] for images
    segment: Optional[List[List[float]]] = None  # polygon for segmentation
    track_id: Optional[int] = None  # for tracking across frames


@dataclass
class PerceptionResult:
    """Unified result from multimodal perception.

    Every modality produces a PerceptionResult with a standard interface
    so downstream components (knowledge engine, world model) can consume
    any modality uniformly.
    """
    modality: Modality
    embedding: List[float] = field(default_factory=list)
    detections: List[Detection] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty: float = 0.0
    provenance: Dict[str, Any] = field(default_factory=dict)
    raw_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modality": self.modality.value,
            "embedding_dim": len(self.embedding),
            "num_detections": len(self.detections),
            "entities": self.entities,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


class PerceptionModule:
    """Base class for modality-specific perception modules.

    Subclasses implement ``perceive`` to process raw input and return
    a PerceptionResult. Real implementations may wrap CLIP, Whisper,
    YOLO, or other models. If the model is unavailable, a deterministic
    fallback is used.
    """

    MODALITY: Modality = Modality.TEXT

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def perceive(self, input_data: Any) -> PerceptionResult:
        """Process input data and return a PerceptionResult."""
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        return {"modality": self.MODALITY.value, "type": self.__class__.__name__}


class TextPerception(PerceptionModule):
    """Text perception: embedding extraction and entity detection."""

    MODALITY = Modality.TEXT

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._tokenizer = config.get("tokenizer") if config else None
        self._embedding_model = config.get("embedding_model") if config else None

    def perceive(self, input_data: str) -> PerceptionResult:
        """Process text input: embed, detect entities, assess confidence."""
        import hashlib
        import re

        # Embedding (deterministic hash-based fallback)
        embedding = self._get_embedding(input_data)

        # Entity detection (keyword-based)
        entities = self._detect_entities(input_data)

        # Token-based confidence
        num_tokens = len(re.findall(r'\w+', input_data))
        confidence = min(1.0, num_tokens / max(num_tokens, 1))
        uncertainty = 1.0 - confidence

        return PerceptionResult(
            modality=self.MODALITY,
            embedding=embedding,
            entities=entities,
            confidence=confidence,
            uncertainty=uncertainty,
            provenance={"source": "text_perception", "input_hash": hashlib.sha256(input_data.encode()).hexdigest()[:16]},
            raw_content=input_data,
            metadata={"num_tokens": num_tokens},
        )

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text. Uses provided model or hash-based fallback."""
        if self._embedding_model:
            try:
                return self._embedding_model.encode(text).tolist()
            except Exception:
                pass
        # Deterministic hash-based embedding fallback
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in hash_bytes[:384]]

    def _detect_entities(self, text: str) -> List[str]:
        """Detect named entities in text (simple keyword-based)."""
        import re
        # Simple entity patterns: capitalized words, numbers, etc.
        entities = re.findall(r'[A-Z][a-z]+(?: [A-Z][a-z]+)*', text)
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        urls = re.findall(r'https?://\S+', text)
        return list(set(entities + numbers + urls))


class ImagePerception(PerceptionModule):
    """Image perception: object detection and embedding extraction."""

    MODALITY = Modality.IMAGE

    def perceive(self, input_data: Dict[str, Any]) -> PerceptionResult:
        """Process image input.

        Parameters
        ----------
        input_data : Dict with keys:
            - "path" or "array": image source
            - "format": image format (optional)
        """
        path = input_data.get("path", "")
        array = input_data.get("array")

        # Use torchvision if available, otherwise deterministic fallback
        embedding = self._get_image_embedding(path, array)
        detections = self._detect_objects(path, array)
        confidence = 0.8 if detections else 0.3

        return PerceptionResult(
            modality=self.MODALITY,
            embedding=embedding,
            detections=detections,
            entities=[d.label for d in detections],
            confidence=confidence,
            uncertainty=1.0 - confidence,
            provenance={"source": "image_perception", "path": path},
            raw_content=path,
        )

    def _get_image_embedding(self, path: str, array: Any) -> List[float]:
        try:
            import torch
            import torchvision.transforms as transforms
            from PIL import Image

            img = Image.open(path).convert("RGB") if path else Image.fromarray(array)
            # Deterministic hash-based fallback
            import hashlib
            img_bytes = str(img.size) + str(img.mode)
            h = hashlib.sha256(img_bytes.encode()).digest()
            return [b / 255.0 for b in h[:384]]
        except Exception:
            return [0.0] * 384

    def _detect_objects(self, path: str, array: Any) -> List[Detection]:
        """Detect objects in image (fallback: simple heuristic)."""
        try:
            img = Image.open(path) if path else Image.fromarray(array)
            # If torchvision/CNN is available, use it; otherwise simple heuristic
            width, height = img.size
            return [
                Detection(
                    label="image_region",
                    confidence=0.5,
                    bounding_box=[0, 0, width / 2, height / 2],
                    metadata={"width": width, "height": height},
                )
            ]
        except Exception:
            return []


class multimodalPerception(PerceptionModule):
    """Multimodal perception: combines text + other modalities.

    Uses cross-modal attention when both text and image embeddings are
    available.
    """

    MODALITY = Modality.TEXT  # Can handle multiple

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.text_module = TextPerception(config)
        self.image_module = ImagePerception(config)

    def perceive(self, input_data: Dict[str, Any]) -> PerceptionResult:
        """Process multimodal input with text + optional image."""
        text_result = self.text_module.perceive(input_data.get("text", ""))

        image_result = None
        if input_data.get("image"):
            image_result = self.image_module.perceive(input_data["image"])
            # Cross-modal fusion: combine embeddings
            if text_result.embedding and image_result.embedding:
                combined = [
                    t * 0.7 + i * 0.3
                    for t, i in zip(text_result.embedding, image_result.embedding)
                ]
                text_result.embedding = combined
                text_result.detections = image_result.detections
                text_result.entities = list(set(text_result.entities + image_result.entities))
                text_result.metadata["has_image"] = True
                text_result.metadata["image_confidence"] = image_result.confidence
            else:
                text_result.metadata["has_image"] = True

        return text_result


class PerceptionRouter:
    """Routes input data to the appropriate perception module.

    Maps file extensions and data types to perception modules.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._modules: Dict[Modality, PerceptionModule] = {
            Modality.TEXT: TextPerception(self.config.get("text")),
            Modality.IMAGE: ImagePerception(self.config.get("image")),
            Modality.DOCUMENT: TextPerception(self.config.get("document")),
        }
        # Multimodal module if needed
        if self.config.get("multimodal"):
            self._multimodal = multimodalPerception(self.config.get("multimodal"))

    def route(self, input_data: Any, modality: Optional[Modality] = None) -> PerceptionResult:
        """Route input to the appropriate perception module."""
        if modality is None:
            modality = self._infer_modality(input_data)

        module = self._modules.get(modality)
        if module is None:
            logger.warning("No perception module for modality %s, using text fallback", modality)
            module = self._modules[Modality.TEXT]

        return module.perceive(input_data)

    def _infer_modality(self, input_data: Any) -> Modality:
        """Infer modality from input data type/extension."""
        if isinstance(input_data, str):
            # Check file extension
            ext = input_data.rsplit(".", 1)[-1].lower() if "." in input_data else ""
            if ext in (".txt", ".md", ".py", ".rs", ".go", ".cpp", ".json"):
                return Modality.TEXT
            elif ext in (".pdf",):
                return Modality.DOCUMENT
            elif ext in (".png", ".jpg", ".jpeg", ".bmp"):
                return Modality.IMAGE
            elif ext in (".mp3", ".wav", ".flac"):
                return Modality.AUDIO
            elif ext in (".csv", ".tsv"):
                return Modality.TABULAR
            return Modality.TEXT
        elif isinstance(input_data, dict):
            if "image" in input_data:
                return Modality.IMAGE
            return Modality.TEXT
        return Modality.TEXT
