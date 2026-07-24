"""
AI Vision Engine — Core detection, tracking, recognition, and behavioral analysis.
Supports YOLO, DeepSORT/ByteTrack, face recognition, OCR, pose estimation, and more.
"""

import os
import cv2
import numpy as np
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger("argus.vision")


class DetectionModel(Enum):
    YOLOV8N = "yolov8n"
    YOLOV8S = "yolov8s"
    YOLOV8M = "yolov8m"
    YOLOV8L = "yolov8l"
    YOLOV8X = "yolov8x"
    YOLO_NAS = "yolo_nas"
    DETR = "detr"


class TrackingType(Enum):
    DEEPSORT = "deepsort"
    BYTETRACK = "bytetrack"
    BOT_SORT = "bot_sort"
    OCSORT = "ocsort"


@dataclass
class Detection:
    """Single detection result."""
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2 (normalized)
    confidence: float
    class_id: int
    class_name: str
    track_id: Optional[int] = None
    velocity: Optional[float] = None
    features: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    keypoints: Optional[List[Tuple[float, float, float]]] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        return {
            "bbox": list(self.bbox),
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "track_id": self.track_id,
            "velocity": self.velocity,
            "timestamp": self.timestamp,
        }


@dataclass
class FaceDetection:
    """Face detection with recognition data."""
    bbox: Tuple[float, float, float, float]
    confidence: float
    landmarks: Optional[List[Tuple[float, float]]] = None
    encoding: Optional[np.ndarray] = None
    name: Optional[str] = None
    is_blacklisted: bool = False
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None
    mask_worn: Optional[bool] = None


@dataclass
class LicensePlate:
    """License plate detection result."""
    bbox: Tuple[float, float, float, float]
    plate_number: str
    confidence: float
    country: Optional[str] = None
    state: Optional[str] = None
    is_watchlisted: bool = False


class VisionEngine:
    """
    Central vision processing engine combining multiple AI models.
    Supports detection, tracking, recognition, and behavior analysis.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.detection_model = None
        self.tracker = None
        self.face_model = None
        self.face_recognizer = None
        self.ocr_model = None
        self.pose_model = None
        self.reid_model = None
        self.face_database: Dict[str, np.ndarray] = {}
        self._initialized = False
        self._device = self.config.get("device", "cuda" if self._cuda_available() else "cpu")

    def _cuda_available(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def initialize(self) -> None:
        """Initialize all AI models. Uses lazy loading to manage memory."""
        if self._initialized:
            return

        model_type = self.config.get("detection_model", "yolov8n")
        tracking_type = self.config.get("tracking_type", "bytetrack")

        self._init_detector(model_type)
        self._init_tracker(tracking_type)
        self._init_face_model()
        self._init_ocr()
        self._init_pose()
        self._init_reid()

        self._initialized = True
        logger.info(f"VisionEngine initialized on device: {self._device}")

    def _init_detector(self, model_type: str) -> None:
        """Initialize object detection model."""
        try:
            from ultralytics import YOLO
            model_path = self.config.get("model_path", f"{model_type}.pt")
            self.detection_model = YOLO(model_path)
            logger.info(f"Detection model loaded: {model_type}")
        except ImportError:
            logger.warning("ultralytics not installed. Detection will use fallback.")
            self.detection_model = None

    def _init_tracker(self, tracking_type: str) -> None:
        """Initialize object tracker."""
        try:
            if tracking_type == "bytetrack":
                from .trackers.byte_track import ByteTrack
                self.tracker = ByteTrack(
                    track_thresh=self.config.get("track_thresh", 0.5),
                    match_thresh=self.config.get("match_thresh", 0.8),
                    track_buffer=self.config.get("track_buffer", 30),
                )
            elif tracking_type == "deepsort":
                from .trackers.deep_sort import DeepSort
                self.tracker = DeepSort(
                    max_dist=self.config.get("max_dist", 0.2),
                    max_iou_distance=self.config.get("max_iou", 0.7),
                )
            else:
                from .trackers.byte_track import ByteTrack
                self.tracker = ByteTrack()
            logger.info(f"Tracker initialized: {tracking_type}")
        except ImportError:
            logger.warning("Tracker import failed. Disabling tracking.")
            self.tracker = None

    def _init_face_model(self) -> None:
        """Initialize face detection and recognition models."""
        try:
            import face_recognition
            self.face_model = face_recognition
            self._load_face_database()
            logger.info("Face recognition model loaded")
        except ImportError:
            logger.warning("face_recognition not installed. Face features disabled.")

    def _init_ocr(self) -> None:
        """Initialize OCR for license plate recognition."""
        try:
            import easyocr
            self.ocr_model = easyocr.Reader(
                ["en"],
                gpu=(self._device == "cuda"),
            )
            logger.info("OCR model loaded")
        except ImportError:
            try:
                import pytesseract
                self.ocr_model = pytesseract
                logger.info("Tesseract OCR loaded")
            except ImportError:
                logger.warning("OCR libraries not installed. Plate recognition disabled.")

    def _init_pose(self) -> None:
        """Initialize pose estimation model."""
        try:
            from ultralytics import YOLO
            self.pose_model = YOLO("yolov8n-pose.pt")
            logger.info("Pose estimation model loaded")
        except ImportError:
            self.pose_model = None

    def _init_reid(self) -> None:
        """Initialize person re-identification model."""
        try:
            import torch
            self.reid_model = torch.hub.load(
                "bubbliiiing/deep-person-reid", "resnet50",
                pretrained=True
            )
            self.reid_model.eval()
            if self._device == "cuda":
                self.reid_model.cuda()
            logger.info("ReID model loaded")
        except (ImportError, Exception):
            self.reid_model = None

    def _load_face_database(self) -> None:
        """Load known face encodings from database."""
        from ..database import get_database
        db = get_database()
        faces = db.query("SELECT id, name, encoding, is_blacklisted FROM known_faces")
        for face in faces:
            try:
                encoding = np.frombuffer(
                    bytes(face["encoding"]), dtype=np.float64
                )
                name = face["name"]
                self.face_database[name] = encoding
            except Exception as e:
                logger.warning(f"Failed to load face {face.get('name')}: {e}")
        logger.info(f"Loaded {len(self.face_database)} known faces")

    def detect(self, frame: np.ndarray, classes: Optional[List[int]] = None) -> List[Detection]:
        """
        Run object detection on a frame.
        Returns list of Detection objects.
        """
        if self.detection_model is None:
            return []

        results = self.detection_model(frame, classes=classes, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                conf = float(boxes.conf[i])
                cls_id = int(boxes.cls[i])
                cls_name = result.names[cls_id]

                h, w = frame.shape[:2]
                detection = Detection(
                    bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                    confidence=conf,
                    class_id=cls_id,
                    class_name=cls_name,
                )

                # Extract mask if available
                if result.masks is not None:
                    detection.mask = result.masks[i].data.cpu().numpy()

                # Extract keypoints if pose model
                if result.keypoints is not None:
                    kps = result.keypoints[i].data.cpu().numpy()
                    detection.keypoints = [(kp[0], kp[1], kp[2]) for kp in kps]

                detections.append(detection)

        return detections

    def track(self, frame: np.ndarray, detections: List[Detection]) -> List[Detection]:
        """
        Update tracker with new detections.
        Assigns track_id to each detection.
        """
        if self.tracker is None:
            for i, det in enumerate(detections):
                det.track_id = i
            return detections

        # Convert to tracker format
        bboxes = []
        scores = []
        classes = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            h, w = frame.shape[:2]
            bboxes.append([x1 * w, y1 * h, x2 * w, y2 * h])
            scores.append(det.confidence)
            classes.append(det.class_id)

        if not bboxes:
            return detections

        bboxes_arr = np.array(bboxes, dtype=float)
        scores_arr = np.array(scores, dtype=float)
        classes_arr = np.array(classes, dtype=int)

        tracked = self.tracker.update(bboxes_arr, scores_arr, classes_arr, frame)

        # Map track IDs back to detections
        track_id_map = {}
        if len(tracked) > 0:
            for t in tracked:
                track_idx = int(t[4]) if len(t) > 4 else int(t[-1])
                track_id_map[track_idx] = int(t[4]) if len(t) > 5 else int(t[0])

        for i, det in enumerate(detections):
            if i in track_id_map:
                det.track_id = track_id_map[i]

        return detections

    def detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect and recognize faces in frame."""
        if self.face_model is None:
            return []

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = self.face_model.face_locations(rgb_frame)
            encodings = self.face_model.face_encodings(rgb_frame, locations)

            faces = []
            for i, ((top, right, bottom, left), encoding) in enumerate(zip(locations, encodings)):
                face = FaceDetection(
                    bbox=(left / frame.shape[1], top / frame.shape[0],
                          right / frame.shape[1], bottom / frame.shape[0]),
                    confidence=1.0,
                    encoding=encoding,
                )

                # Match against known faces
                name, is_blacklisted = self._match_face(encoding)
                face.name = name
                face.is_blacklisted = is_blacklisted
                faces.append(face)

            return faces
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def _match_face(self, encoding: np.ndarray, tolerance: float = 0.6) -> Tuple[Optional[str], bool]:
        """Match face encoding against database."""
        if not self.face_database:
            return None, False

        best_match = None
        best_dist = float("inf")

        for name, db_encoding in self.face_database.items():
            dist = np.linalg.norm(encoding - db_encoding)
            if dist < best_dist:
                best_dist = dist
                best_match = name

        if best_dist < tolerance:
            face_data = next(
                (f for f in self._get_face_data() if f["name"] == best_match),
                None,
            )
            is_blacklisted = face_data.get("is_blacklisted", False) if face_data else False
            return best_match, is_blacklisted
        return None, False

    def _get_face_data(self) -> List[Dict]:
        """Get face data from database."""
        from ..database import get_database
        db = get_database()
        return db.query("SELECT name, is_blacklisted FROM known_faces")

    def recognize_plate(self, frame: np.ndarray) -> List[LicensePlate]:
        """Detect and recognize license plates."""
        if self.ocr_model is None:
            return []

        plates = []

        try:
            if hasattr(self.ocr_model, "readtext"):
                # EasyOCR
                results = self.ocr_model.readtext(frame)
                for (bbox, text, confidence) in results:
                    if confidence > 0.5 and len(text) > 3:
                        x1, y1 = bbox[0]
                        x2, y2 = bbox[2]
                        plate = LicensePlate(
                            bbox=(x1 / frame.shape[1], y1 / frame.shape[0],
                                  x2 / frame.shape[1], y2 / frame.shape[0]),
                            plate_number=text.strip().upper(),
                            confidence=float(confidence),
                        )
                        plate.is_watchlisted = self._check_plate_watchlist(plate.plate_number)
                        plates.append(plate)
            else:
                # Tesseract fallback
                import re
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                text = self.ocr_model.image_to_string(gray, config="--psm 7")
                text = re.sub(r'[^A-Z0-9]', '', text.upper().strip())
                if len(text) >= 4:
                    plate = LicensePlate(
                        bbox=(0, 0, 1, 1),
                        plate_number=text,
                        confidence=0.7,
                    )
                    plate.is_watchlisted = self._check_plate_watchlist(text)
                    plates.append(plate)

        except Exception as e:
            logger.error(f"Plate recognition error: {e}")

        return plates

    def _check_plate_watchlist(self, plate: str) -> bool:
        """Check if plate is on watchlist."""
        from ..database import get_database
        db = get_database()
        result = db.query(
            "SELECT is_watchlisted FROM license_plates WHERE plate_number = :plate",
            {"plate": plate},
        )
        return result[0]["is_watchlisted"] if result else False

    def estimate_pose(self, frame: np.ndarray) -> List[Detection]:
        """Estimate human pose keypoints."""
        if self.pose_model is None:
            return []

        results = self.pose_model(frame, verbose=False)
        poses = []

        for result in results:
            if result.keypoints is None:
                continue
            for kps in result.keypoints.data:
                keypoints = [(kp[0].item(), kp[1].item(), kp[2].item()) for kp in kps]
                pose = Detection(
                    bbox=(0, 0, 1, 1),
                    confidence=1.0,
                    class_id=0,
                    class_name="person",
                    keypoints=keypoints,
                )
                poses.append(pose)

        return poses

    def extract_reid_features(self, frame: np.ndarray, bbox: Tuple) -> Optional[np.ndarray]:
        """Extract person ReID features for cross-camera matching."""
        if self.reid_model is None:
            return None

        try:
            import torch
            x1, y1, x2, y2 = [int(v) for v in bbox]
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return None

            crop = cv2.resize(crop, (256, 128))
            crop = crop.transpose(2, 0, 1)
            crop = torch.from_numpy(crop).float().unsqueeze(0) / 255.0

            if self._device == "cuda":
                crop = crop.cuda()

            with torch.no_grad():
                features = self.reid_model(crop)
                features = features.cpu().numpy().flatten()

            return features
        except Exception as e:
            logger.error(f"ReID feature extraction error: {e}")
            return None

    def compute_crowd_density(self, frame: np.ndarray) -> Dict[str, Any]:
        """Compute crowd density map and count."""
        detections = self.detect(frame, classes=[0])  # person class
        h, w = frame.shape[:2]

        # Generate density heatmap
        density_map = np.zeros((h, w), dtype=np.float32)
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cx, cy = int((x1 + x2) * w / 2), int((y1 + y2) * h / 2)
            cv2.circle(density_map, (cx, cy), 15, 1.0, -1)

        # Apply Gaussian blur for smooth density
        density_map = cv2.GaussianBlur(density_map, (31, 31), 0)

        return {
            "count": len(detections),
            "density_map": density_map.tolist(),
            "max_density": float(np.max(density_map)),
            "mean_density": float(np.mean(density_map)),
        }

    def detect_motion(self, frame: np.ndarray, background: Optional[np.ndarray] = None) -> np.ndarray:
        """Detect motion using background subtraction."""
        if background is None:
            return np.zeros(frame.shape[:2], dtype=np.uint8)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bg_gray = cv2.cvtColor(background, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray, bg_gray)
        _, motion = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        motion = cv2.morphologyEx(motion, cv2.MORPH_OPEN, kernel)
        motion = cv2.morphologyEx(motion, cv2.MORPH_CLOSE, kernel)

        return motion

    def estimate_speed(self, detections: List[Detection], fps: float, pixels_per_meter: float = 50.0) -> List[float]:
        """Estimate speed of tracked objects in m/s."""
        speeds = []
        for det in detections:
            if det.velocity is not None:
                speed_px_per_frame = det.velocity
                speed_m_per_s = (speed_px_per_frame * fps) / pixels_per_meter
                speeds.append(speed_m_per_s)
            else:
                speeds.append(0.0)
        return speeds

    def detect_abandoned_objects(
        self,
        current_detections: List[Detection],
        history: List[List[Detection]],
        threshold_frames: int = 150,
    ) -> List[Detection]:
        """Detect abandoned objects by analyzing detection persistence."""
        abandoned = []

        for det in current_detections:
            if det.class_name not in ["backpack", "handbag", "suitcase", "bag"]:
                continue

            # Check if this static object has been present for threshold_frames
            static_count = 0
            for past_dets in history[-threshold_frames:]:
                for past_det in past_dets:
                    if past_det.class_name == det.class_name:
                        static_count += 1
                        break

            if static_count >= threshold_frames:
                abandoned.append(det)

        return abandoned

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Full frame processing pipeline.
        Returns all detections, tracks, faces, plates, and analytics.
        """
        if not self._initialized:
            self.initialize()

        results = {
            "detections": [],
            "faces": [],
            "plates": [],
            "poses": [],
            "crowd": {"count": 0},
            "motion": None,
        }

        # Object detection
        detections = self.detect(frame)
        detections = self.track(frame, detections)
        results["detections"] = [d.to_dict() for d in detections]

        # Face detection
        results["faces"] = [
            {"bbox": f.bbox, "confidence": f.confidence, "name": f.name,
             "is_blacklisted": f.is_blacklisted}
            for f in self.detect_faces(frame)
        ]

        # License plate recognition
        results["plates"] = [
            {"bbox": p.bbox, "plate": p.plate_number,
             "confidence": p.confidence, "is_watchlisted": p.is_watchlisted}
            for p in self.recognize_plate(frame)
        ]

        # Pose estimation
        results["poses"] = [
            {"keypoints": p.keypoints} for p in self.estimate_pose(frame)
        ]

        # Crowd density
        results["crowd"] = self.compute_crowd_density(frame)

        return results

    def close(self) -> None:
        """Release model resources."""
        self.detection_model = None
        self.tracker = None
        self.face_model = None
        self.ocr_model = None
        self.pose_model = None
        self.reid_model = None
        self._initialized = False
        logger.info("VisionEngine resources released")

