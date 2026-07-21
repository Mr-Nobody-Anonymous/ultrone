# Copyright (c) Ultrone Contributors. All rights reserved.
"""Specialized AI analyzers for each sensor type."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger("Ultrone.Brain.Perception.SpecializedAnalyzers")


class SpecializedAnalyzer(ABC):
    """Base class for specialized sensor AI analyzers."""
    
    def __init__(self):
        self.confidence = 0.85
    
    @abstractmethod
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sensor-specific data and return assessment."""
        pass


class SatelliteImageAI(SpecializedAnalyzer):
    """AI specialized for satellite imagery analysis."""
    
    def __init__(self):
        super().__init__()
        self.pattern_templates = {
            "vehicle_formation": {"shape": "rectangular", "spacing": "uniform"},
            "infrastructure": {"grid_pattern": True, "regular_spacing": True},
            "artillery": {"circular_pattern": True, "depressions": True},
            "camouflage": {"color_abnormalities": True, "texture_anomalies": True},
        }
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze satellite image for military signatures."""
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        # Check for formations
        if isinstance(raw_data, dict):
            formation = raw_data.get("formation", "")
            if formation:
                if "tank" in formation or "ifv" in formation:
                    result["threat_indicator"] = 0.8
                    result["classification"] = "armor"
                elif "artillery" in formation:
                    result["threat_indicator"] = 0.7
                    result["classification"] = "artillery"
                result["confidence"] = 0.9
        
        # Movement detection
        movement = raw_data.get("movement", "") if isinstance(raw_data, dict) else ""
        if movement and metadata.get("speed", 0) > 30:
            result["threat_indicator"] = min(1.0, result["threat_indicator"] + 0.2)
        
        return result


class RadarAI(SpecializedAnalyzer):
    """AI specialized for radar detection analysis."""
    
    def __init__(self):
        super().__init__()
        self.radar_signatures = {
            "aircraft": {"doppler": "high", "rcs": "variable"},
            "missile": {"doppler": "very_high", "rcs": "small"},
            "vehicle": {"doppler": "low", "rcs": "medium"},
        }
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze radar return for contact classification."""
        result = {"threat_indicator": 0.3, "classification": "contact", "confidence": 0.0}
        
        speed = metadata.get("speed", 0)
        if speed > 100:
            result["threat_indicator"] = 0.7
            result["classification"] = "fast_air"
        elif speed > 50:
            result["threat_indicator"] = 0.5
            result["classification"] = "ground_vehicle"
        else:
            result["threat_indicator"] = 0.4
            result["classification"] = "slow_moving"
        
        # Heading toward friendly increases threat
        if metadata.get("heading_toward_friendly", False):
            result["threat_indicator"] = min(1.0, result["threat_indicator"] + 0.3)
        
        result["confidence"] = 0.85 if speed > 0 else 0.5
        
        return result


class GPSAI(SpecializedAnalyzer):
    """AI specialized for GPS track analysis."""
    
    def __init__(self):
        super().__init__()
        self.track_patterns = {}
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze GPS track for behavior patterns."""
        result = {"threat_indicator": 0.2, "classification": "track", "confidence": 0.95}
        
        speed = metadata.get("speed", 0)
        
        if speed > 80:
            result["classification"] = "rapid_movement"
            result["threat_indicator"] = 0.6
        elif speed > 20:
            result["classification"] = "normal_transit"
            result["threat_indicator"] = 0.4
        else:
            result["classification"] = "stationary"
            result["threat_indicator"] = 0.2
        
        # Pattern analysis
        if metadata.get("pattern") == "grid_search":
            result["threat_indicator"] = min(1.0, result["threat_indicator"] + 0.3)
            result["classification"] = "recon_pattern"
        
        return result


class VoiceAI(SpecializedAnalyzer):
    """AI specialized for voice/intelligence intercept analysis using Whisper."""
    
    def __init__(self):
        super().__init__()
        self.threat_keywords = ["attack", "strike", "engage", "destroy", "eliminate", "target", 
                                "hostile", "weapons", "fire", "bomb", "explosion"]
        self.non_threat_keywords = ["retreat", "withdraw", "cease", "hold", "monitor",
                                     "peace", "safe", "friendly", "neutral"]
        self._model = None
    
    def _load_model(self):
        """Lazy load Whisper model."""
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model("tiny")
            except Exception as e:
                logger.warning(f"Could not load Whisper model: {e}")
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze audio file using Whisper transcription + keyword matching.
        
        Args:
            raw_data: Path to audio file (WAV/MP3)
            metadata: Additional context
            
        Returns:
            {"threat_indicator": float, "classification": str, "confidence": float}
        """
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        self._load_model()
        
        if self._model is None:
            # Fallback to text input
            text = str(raw_data).lower()
        else:
            try:
                # Transcribe audio file
                if isinstance(raw_data, str):
                    transcription = self._model.transcribe(raw_data)
                    text = transcription["text"].lower()
                else:
                    text = str(raw_data).lower()
            except Exception as e:
                logger.error(f"VoiceAI transcription failed: {e}")
                text = ""
        
        # Count threat keywords
        threat_count = sum(1 for kw in self.threat_keywords if kw in text)
        non_threat_count = sum(1 for kw in self.non_threat_keywords if kw in text)
        
        # Calculate threat based on keyword density
        total_words = len(text.split()) if text else 1
        threat_density = threat_count / max(1, total_words)
        
        if threat_count > 0:
            # Scale threat indicator by how many threat words found
            result["threat_indicator"] = min(1.0, threat_density * 50)
            result["classification"] = "hostile_intent"
            result["confidence"] = 0.85
        elif non_threat_count > 0:
            result["threat_indicator"] = 0.1
            result["classification"] = "non_hostile"
            result["confidence"] = 0.75
        else:
            result["threat_indicator"] = 0.3
            result["classification"] = "neutral"
            result["confidence"] = 0.7
        
        return result


class SIGINTAI(SpecializedAnalyzer):
    """AI specialized for signals intelligence."""
    
    def __init__(self):
        super().__init__()
        self.signal_patterns = {
            "fire_control": ["targeting", "lock", "missile"],
            "command_net": ["command", "orders", "execute"],
            "surveillance": ["scan", "detect", "monitor"],
        }
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze SIGINT for tactical indicators."""
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        text = str(raw_data).lower()
        
        for pattern_name, keywords in self.signal_patterns.items():
            if any(kw in text for kw in keywords):
                result["classification"] = pattern_name
                if pattern_name == "fire_control":
                    result["threat_indicator"] = 0.9
                elif pattern_name == "command_net":
                    result["threat_indicator"] = 0.6
                elif pattern_name == "surveillance":
                    result["threat_indicator"] = 0.4
                break
        
        if result["threat_indicator"] == 0.0:
            result["threat_indicator"] = 0.3
            result["classification"] = "generic_traffic"
        
        result["confidence"] = 0.75
        
        return result


class CyberFeedAI(SpecializedAnalyzer):
    """AI specialized for cyber threat intelligence."""
    
    def __init__(self):
        super().__init__()
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cyber feed for attack indicators."""
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        text = str(raw_data).lower()
        
        if "attack" in text or "breach" in text:
            result["threat_indicator"] = 0.9
            result["classification"] = "active_attack"
        elif "scan" in text or "probe" in text:
            result["threat_indicator"] = 0.6
            result["classification"] = "recon"
        elif "malware" in text or "exploit" in text:
            result["threat_indicator"] = 0.8
            result["classification"] = "malware_detected"
        else:
            result["threat_indicator"] = 0.3
            result["classification"] = "normal_traffic"
        
        result["confidence"] = 0.85
        
        return result


class SonarAI(SpecializedAnalyzer):
    """AI specialized for sonar/underwater detection."""
    
    def __init__(self):
        super().__init__()
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sonar for underwater contact classification."""
        result = {"threat_indicator": 0.5, "classification": "unknown", "confidence": 0.0}
        
        signature = metadata.get("signature", "")
        
        if "torpedo" in signature:
            result["threat_indicator"] = 1.0
            result["classification"] = "torpedo"
        elif "submarine" in signature:
            result["threat_indicator"] = 0.7
            result["classification"] = "submarine"
        elif "vessel" in signature:
            result["threat_indicator"] = 0.4
            result["classification"] = "surface_vessel"
        else:
            result["threat_indicator"] = 0.5
            result["classification"] = "contact"
        
        result["confidence"] = 0.8
        
        return result


class VisualAI(SpecializedAnalyzer):
    """AI specialized for visual/optical analysis using HuggingFace OWL-ViT."""
    
    # Military-relevant object labels for detection
    MILITARY_LABELS = [
        "tank", "military vehicle", "fighter jet", "missile launcher", 
        "soldier", "military aircraft", "artillery", "radar system",
        "truck", "vehicle", "person", "weapon", "truck", "bus"
    ]
    
    def __init__(self):
        super().__init__()
        self._model = None
        self._processor = None
    
    def _load_model(self):
        """Lazy load the OWL-ViT model."""
        if self._model is None:
            try:
                from transformers import OwlViTForObjectDetection, OwlViTProcessor
                import torch
                
                self._model = OwlViTForObjectDetection.from_pretrained(
                    "google/owlvit-base-patch32"
                )
                self._processor = OwlViTProcessor.from_pretrained(
                    "google/owlvit-base-patch32"
                )
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                self._model.to(self._device)
            except Exception as e:
                logger.warning(f"Could not load OWL-ViT model: {e}")
                # Graceful fallback
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze visual data using OWL-ViT zero-shot object detection.
        
        Args:
            raw_data: base64 encoded image string or file path to image
            metadata: Additional context (confidence, etc.)
            
        Returns:
            {"threat_indicator": float, "classification": str, "confidence": float}
        """
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        # Try to use real model if available
        self._load_model()
        
        if self._model is None:
            # Graceful fallback to mock if model unavailable
            objects = metadata.get("detected_objects", [])
            weapons = metadata.get("weapons_visible", False)
            
            if weapons:
                result["threat_indicator"] = 0.8
                result["classification"] = "armed"
            elif "military_vehicle" in objects:
                result["threat_indicator"] = 0.7
                result["classification"] = "military"
            elif "personnel" in objects:
                result["threat_indicator"] = 0.5
                result["classification"] = "personnel"
            
            result["confidence"] = 0.85 if result["classification"] != "unknown" else 0.5
            return result
        
        try:
            import base64
            from PIL import Image
            import io
            import torch
            import numpy as np
            
            # Load image from base64 or file path
            if isinstance(raw_data, str):
                if raw_data.startswith("/"):  # File path
                    image = Image.open(raw_data).convert("RGB")
                else:  # base64
                    image_data = base64.b64decode(raw_data)
                    image = Image.open(io.BytesIO(image_data)).convert("RGB")
            else:
                image = raw_data
            
            # Run detection
            inputs = self._processor(
                text=self.MILITARY_LABELS,
                images=image,
                return_tensors="pt"
            ).to(self._device)
            
            with torch.no_grad():
                outputs = self._model(**inputs)
            
            # Post-process results
            target_sizes = torch.tensor([image.size[::-1]])
            results = self._processor.post_process_object_detection(
                outputs, 
                threshold=0.1,
                target_sizes=target_sizes
            )[0]
            
            # Extract threat indicator from highest confidence detection
            scores = results["scores"].cpu().numpy()
            labels = results["labels"].cpu().numpy()
            
            if len(scores) > 0:
                max_idx = np.argmax(scores)
                max_score = float(scores[max_idx])
                label = self.MILITARY_LABELS[int(labels[max_idx])]
                
                # Map military objects to threat levels
                high_threat = ["tank", "missile launcher", "artillery", "fighter jet"]
                medium_threat = ["military vehicle", "military aircraft", "radar system"]
                
                if any(obj in label.lower() for obj in high_threat):
                    result["threat_indicator"] = min(1.0, max_score * 1.2)
                    result["classification"] = label.replace(" ", "_")
                elif any(obj in label.lower() for obj in medium_threat):
                    result["threat_indicator"] = min(1.0, max_score)
                    result["classification"] = label.replace(" ", "_")
                else:
                    result["threat_indicator"] = max_score * 0.5
                    result["classification"] = label.replace(" ", "_")
                
                result["confidence"] = max_score
            else:
                result["threat_indicator"] = 0.0
                result["classification"] = "no_objects_detected"
                result["confidence"] = 0.9
                
        except Exception as e:
            logger.error(f"VisualAI analysis failed: {e}")
            # Fallback to mock
            result["threat_indicator"] = 0.3
            result["classification"] = "fallback"
            result["confidence"] = 0.5
        
        return result


class AcousticAI(SpecializedAnalyzer):
    """AI specialized for acoustic signature analysis using librosa/scipy."""
    
    # Frequency thresholds for threat detection (Hz)
    GUNSHOT_FREQ_MIN = 1500   # Gunshots have high-frequency spikes
    EXPLOSION_FREQ_MIN = 200   # Explosions have low-mid frequency
    ENGINE_FREQ_MAX = 500        # Engines are lower frequency
    
    def __init__(self):
        super().__init__()
        self._librosa_available = True
    
    def _check_dependencies(self):
        """Check if librosa/scipy are available."""
        try:
            import librosa
            import numpy as np
            from scipy import signal
            return True
        except ImportError:
            self._librosa_available = False
            return False
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze audio file using real signal processing.
        
        Args:
            raw_data: Path to WAV file or raw audio data
            metadata: Additional context
            
        Returns:
            {"threat_indicator": float, "classification": str, "confidence": float}
        """
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        if not self._check_dependencies():
            # Fallback to simple analysis
            if isinstance(raw_data, dict):
                activity = raw_data.get("detected_activity", "")
                if "artillery" in activity:
                    result["threat_indicator"] = 0.7
                    result["classification"] = "artillery_firing"
                elif "engine" in activity:
                    result["threat_indicator"] = 0.4
                    result["classification"] = "mechanical"
                else:
                    result["threat_indicator"] = 0.3
                    result["classification"] = "ambient"
            else:
                result["threat_indicator"] = 0.3
                result["classification"] = "ambient"
            result["confidence"] = 0.5
            return result
        
        try:
            import librosa
            import numpy as np
            from scipy import signal
            
            # Load audio file
            if isinstance(raw_data, str):
                y, sr = librosa.load(raw_data, sr=None)
            elif isinstance(raw_data, (list, np.ndarray)):
                y = np.array(raw_data)
                sr = metadata.get("sample_rate", 22050)
            else:
                result["threat_indicator"] = 0.3
                result["classification"] = "fallback"
                result["confidence"] = 0.5
                return result
            
            # Calculate RMS (volume in dB)
            rms = librosa.feature.rms(y=y)[0]
            avg_db = librosa.amplitude_to_db(rms).mean()
            
            # High volume increases threat
            volume_threat = min(1.0, max(0, (avg_db + 50) / 50))
            
            # Spectral analysis for gunshot/explosion detection
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            avg_centroid = spectral_centroid.mean()
            
            # High frequency centroid suggests gunfire
            freq_threat = 0.0
            if avg_centroid > self.GUNSHOT_FREQ_MIN:
                freq_threat = 0.8  # High-frequency = gunshots
                result["classification"] = "gunfire_detected"
            elif avg_centroid > self.EXPLOSION_FREQ_MIN:
                freq_threat = 0.6  # Mid frequency = explosions
                if result["classification"] == "unknown":
                    result["classification"] = "explosion_detected"
            else:
                # Low frequency could be engines/vehicles
                freq_threat = 0.3
                if result["classification"] == "unknown":
                    result["classification"] = "mechanical_noise"
            
            # Combined threat indicator
            result["threat_indicator"] = min(1.0, (volume_threat + freq_threat) / 2)
            result["confidence"] = 0.85
            
        except Exception as e:
            logger.error(f"AcousticAI analysis failed: {e}")
            result["threat_indicator"] = 0.3
            result["classification"] = "fallback"
            result["confidence"] = 0.5
        
        return result


class ThermalAI(SpecializedAnalyzer):
    """AI specialized for thermal signature analysis."""
    
    def __init__(self):
        super().__init__()
    
    def analyze(self, raw_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze thermal signatures for heat source classification."""
        result = {"threat_indicator": 0.0, "classification": "unknown", "confidence": 0.0}
        
        temp_anomaly = metadata.get("temperature_anomaly", 0)
        
        if temp_anomaly > 500:  # Hot engine/exhaust
            result["threat_indicator"] = 0.8
            result["classification"] = "active_vehicle"
        elif temp_anomaly > 100:
            result["threat_indicator"] = 0.5
            result["classification"] = "recent_activity"
        
        result["confidence"] = 0.8
        
        return result


# Registry of all specialized analyzers
ANALYZER_REGISTRY = {
    "satellite_image": SatelliteImageAI(),
    "radar": RadarAI(),
    "gps": GPSAI(),
    "voice": VoiceAI(),
    "sigint": SIGINTAI(),
    "cyber_feed": CyberFeedAI(),
    "sonar": SonarAI(),
    "visual": VisualAI(),
    "acoustic": AcousticAI(),
    "thermal": ThermalAI(),
}


def get_specialized_analyzer(source_type: str) -> Optional[SpecializedAnalyzer]:
    """Get the specialized analyzer for a data source type."""
    return ANALYZER_REGISTRY.get(source_type.lower())