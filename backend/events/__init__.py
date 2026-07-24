"""
Event Management — Event lifecycle, severity levels, acknowledgment,
escalation, evidence snapshots, video clips, timeline, search, and case management.
"""

import os
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Any, Set
from enum import Enum

logger = logging.getLogger("argus.events")


class EventSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EventStatus(Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"
    ARCHIVED = "archived"


class EventType(Enum):
    OBJECT_DETECTED = "object_detected"
    FACE_MATCHED = "face_matched"
    PLATE_MATCHED = "plate_matched"
    ZONE_ENTRY = "zone_entry"
    ZONE_EXIT = "zone_exit"
    LINE_CROSSING = "line_crossing"
    LOITERING = "loitering"
    ABANDONED_OBJECT = "abandoned_object"
    REMOVED_OBJECT = "removed_object"
    FIGHT_DETECTED = "fight_detected"
    WEAPON_DETECTED = "weapon_detected"
    SMOKE_DETECTED = "smoke_detected"
    FIRE_DETECTED = "fire_detected"
    FALL_DETECTED = "fall_detected"
    CROWD_FORMATION = "crowd_formation"
    SPEEDING = "speeding"
    WRONG_DIRECTION = "wrong_direction"
    TAILGATING = "tailgating"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    CRIMINAL_PREDICTION = "criminal_prediction"
    SYSTEM_ALERT = "system_alert"
    CAMERA_OFFLINE = "camera_offline"
    CUSTOM = "custom"


@dataclass
class EventEvidence:
    """Evidence attached to an event."""
    snapshot_path: Optional[str] = None
    video_clip_path: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Event:
    """A detected event with full lifecycle support."""
    id: int
    event_type: EventType
    camera_id: int
    severity: EventSeverity = EventSeverity.INFO
    status: EventStatus = EventStatus.NEW
    title: str = ""
    description: str = ""
    source: str = "ai"
    confidence: float = 0.0
    bbox: Optional[List[float]] = None
    track_id: Optional[int] = None
    face_name: Optional[str] = None
    plate_number: Optional[str] = None
    zone_name: Optional[str] = None
    evidence: EventEvidence = field(default_factory=EventEvidence)
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    escalated_to: Optional[str] = None
    case_id: Optional[str] = None
    parent_event_id: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def acknowledge(self, user: str) -> None:
        self.status = EventStatus.ACKNOWLEDGED
        self.acknowledged_by = user
        self.acknowledged_at = time.time()
        self.updated_at = time.time()

    def resolve(self) -> None:
        self.status = EventStatus.RESOLVED
        self.resolved_at = time.time()
        self.updated_at = time.time()

    def escalate(self, target: str) -> None:
        self.status = EventStatus.ESCALATED
        self.escalated_to = target
        self.updated_at = time.time()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "camera_id": self.camera_id,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "track_id": self.track_id,
            "face_name": self.face_name,
            "plate_number": self.plate_number,
            "zone_name": self.zone_name,
            "tags": self.tags,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "escalated_to": self.escalated_to,
            "case_id": self.case_id,
            "parent_event_id": self.parent_event_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EventManager:
    """
    Central event management system with lifecycle, search, and retention.
    """

    def __init__(self, db=None, config: Optional[Dict] = None):
        self.db = db
        self.config = config or {}
        self._events: Dict[int, Event] = {}
        self._event_counter = 0
        self._lock = threading.RLock()
        self._on_event_callbacks: List[Callable] = []
        self._retention_days = self.config.get("retention_days", 30)
        self._archive_path = self.config.get("archive_path", "events_archive")
        self._cases: Dict[str, Dict] = {}  # case_id -> case data

    def set_db(self, db) -> None:
        self.db = db

    def create_event(self, event_type: EventType, camera_id: int, **kwargs) -> Event:
        """Create a new event."""
        with self._lock:
            self._event_counter += 1
            event = Event(
                id=self._event_counter,
                event_type=event_type,
                camera_id=camera_id,
                **kwargs,
            )
            self._events[event.id] = event
            self._persist_event(event)
            self._notify_callbacks(event)
            logger.info(f"Event created: [{event.severity.value}] {event.event_type.value} @ camera {camera_id}")
            return event

    def get_event(self, event_id: int) -> Optional[Event]:
        return self._events.get(event_id)

    def get_events(
        self,
        camera_id: Optional[int] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[EventSeverity] = None,
        status: Optional[EventStatus] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        """Query events with filters."""
        results = list(self._events.values())

        if camera_id:
            results = [e for e in results if e.camera_id == camera_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if severity:
            results = [e for e in results if e.severity == severity]
        if status:
            results = [e for e in results if e.status == status]
        if start_time:
            results = [e for e in results if e.created_at >= start_time]
        if end_time:
            results = [e for e in results if e.created_at <= end_time]

        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[offset:offset + limit]

    def search_events(self, query: str, limit: int = 50) -> List[Event]:
        """Full-text search through events."""
        query = query.lower()
        results = []
        for event in self._events.values():
            if (query in event.title.lower() or
                query in event.description.lower() or
                query in str(event.tags).lower() or
                (event.face_name and query in event.face_name.lower()) or
                (event.plate_number and query in event.plate_number.lower())):
                results.append(event)
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    def acknowledge_event(self, event_id: int, user: str) -> bool:
        event = self._events.get(event_id)
        if event:
            event.acknowledge(user)
            self._update_event_db(event)
            return True
        return False

    def resolve_event(self, event_id: int) -> bool:
        event = self._events.get(event_id)
        if event:
            event.resolve()
            self._update_event_db(event)
            return True
        return False

    def escalate_event(self, event_id: int, target: str) -> bool:
        event = self._events.get(event_id)
        if event:
            event.escalate(target)
            self._update_event_db(event)
            return True
        return False

    def add_tag_to_event(self, event_id: int, tag: str) -> bool:
        event = self._events.get(event_id)
        if event:
            event.add_tag(tag)
            return True
        return False

    def create_case(self, event_ids: List[int], title: str, description: str = "") -> str:
        """Group events into a case for investigation."""
        import uuid
        case_id = str(uuid.uuid4())[:8]
        self._cases[case_id] = {
            "id": case_id,
            "title": title,
            "description": description,
            "event_ids": event_ids,
            "created_at": time.time(),
            "updated_at": time.time(),
            "status": "open",
        }
        for eid in event_ids:
            event = self._events.get(eid)
            if event:
                event.case_id = case_id
        logger.info(f"Case created: {case_id} with {len(event_ids)} events")
        return case_id

    def get_case(self, case_id: str) -> Optional[Dict]:
        return self._cases.get(case_id)

    def get_cases(self) -> List[Dict]:
        return list(self._cases.values())

    def attach_snapshot(self, event_id: int, snapshot_path: str) -> bool:
        event = self._events.get(event_id)
        if event:
            event.evidence.snapshot_path = snapshot_path
            return True
        return False

    def attach_video_clip(self, event_id: int, clip_path: str) -> bool:
        event = self._events.get(event_id)
        if event:
            event.evidence.video_clip_path = clip_path
            return True
        return False

    def on_event(self, callback: Callable) -> None:
        self._on_event_callbacks.append(callback)

    def _notify_callbacks(self, event: Event) -> None:
        for cb in self._on_event_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    def _persist_event(self, event: Event) -> None:
        if self.db:
            try:
                self.db.insert("events", {
                    "event_type": event.event_type.value,
                    "camera_id": event.camera_id,
                    "severity": event.severity.value,
                    "status": event.status.value,
                    "title": event.title,
                    "description": event.description,
                    "source": event.source,
                    "confidence": event.confidence,
                    "bbox": json.dumps(event.bbox),
                    "track_id": event.track_id,
                    "face_name": event.face_name,
                    "plate_number": event.plate_number,
                    "zone_name": event.zone_name,
                    "metadata": json.dumps(event.metadata),
                    "created_at": datetime.fromtimestamp(event.created_at).isoformat(),
                })
            except Exception as e:
                logger.error(f"Event persistence error: {e}")

    def _update_event_db(self, event: Event) -> None:
        if self.db:
            try:
                self.db.update("events", {
                    "status": event.status.value,
                    "acknowledged_by": event.acknowledged_by,
                    "acknowledged_at": datetime.fromtimestamp(event.acknowledged_at).isoformat() if event.acknowledged_at else None,
                    "resolved_at": datetime.fromtimestamp(event.resolved_at).isoformat() if event.resolved_at else None,
                    "updated_at": datetime.now().isoformat(),
                }, {"id": event.id})
            except Exception as e:
                logger.error(f"Event update error: {e}")

    def cleanup_old_events(self) -> int:
        """Archive and remove events older than retention period."""
        cutoff = time.time() - (self._retention_days * 86400)
        old_events = [e for e in self._events.values() if e.created_at < cutoff]
        for event in old_events:
            if event.evidence.snapshot_path and os.path.exists(event.evidence.snapshot_path):
                try:
                    os.remove(event.evidence.snapshot_path)
                except OSError:
                    pass
            del self._events[event.id]
        logger.info(f"Cleaned up {len(old_events)} old events")
        return len(old_events)

    def get_stats(self) -> Dict[str, Any]:
        """Get event statistics."""
        counts = {}
        status_counts = {}
        for event in self._events.values():
            et = event.event_type.value
            counts[et] = counts.get(et, 0) + 1
            st = event.status.value
            status_counts[st] = status_counts.get(st, 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": counts,
            "by_status": status_counts,
            "open_cases": len(self._cases),
            "retention_days": self._retention_days,
        }
