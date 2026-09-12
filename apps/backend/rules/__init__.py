"""
Rule Engine — Polygon/rectangle zones, scheduling, boolean logic,
rule chaining, escalation, and cooldown timers.
"""

import re
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime, time as dt_time
import numpy as np

logger = logging.getLogger("argus.rules")


class ConditionType(Enum):
    TIME = "time"
    OBJECT = "object"
    FACE = "face"
    VEHICLE = "vehicle"
    PLATE = "plate"
    COUNT = "count"
    ZONE = "zone"
    DIRECTION = "direction"
    SPEED = "speed"
    CUSTOM = "custom"


class LogicOperator(Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
    NESTED = "nested"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class Zone:
    """A defined zone on the camera view."""
    name: str
    camera_id: int
    zone_type: str = "polygon"
    coordinates: List[tuple] = field(default_factory=list)
    priority: int = 0
    schedule: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def contains_point(self, x: float, y: float) -> bool:
        if self.zone_type == "rectangle" and len(self.coordinates) >= 2:
            x1, y1 = self.coordinates[0]
            x2, y2 = self.coordinates[1]
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)
            return x_min <= x <= x_max and y_min <= y <= y_max

        n = len(self.coordinates)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = self.coordinates[i]
            xj, yj = self.coordinates[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "camera_id": self.camera_id,
            "zone_type": self.zone_type,
            "coordinates": self.coordinates,
            "priority": self.priority,
            "schedule": self.schedule,
        }


@dataclass
class Condition:
    """A single rule condition."""
    condition_type: ConditionType
    field: str
    operator: str
    value: Any
    logic: LogicOperator = LogicOperator.AND

    def evaluate(self, context: Dict) -> bool:
        actual_value = context.get(self.field)
        try:
            if self.operator == "==":
                return actual_value == self.value
            elif self.operator == "!=":
                return actual_value != self.value
            elif self.operator == ">":
                return float(actual_value) > float(self.value)
            elif self.operator == "<":
                return float(actual_value) < float(self.value)
            elif self.operator == ">=":
                return float(actual_value) >= float(self.value)
            elif self.operator == "<=":
                return float(actual_value) <= float(self.value)
            elif self.operator == "contains":
                return self.value in str(actual_value)
            elif self.operator == "in":
                return actual_value in self.value
            elif self.operator == "not_in":
                return actual_value not in self.value
            elif self.operator == "regex":
                return bool(re.search(self.value, str(actual_value)))
            elif self.operator == "between":
                low, high = self.value
                return low <= float(actual_value) <= high
            elif self.operator == "is_set":
                return actual_value is not None
            elif self.operator == "is_not_set":
                return actual_value is None
        except (TypeError, ValueError) as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False
        return False


@dataclass
class Rule:
    """A configurable rule with conditions and actions."""
    name: str
    camera_id: int
    conditions: List[Condition] = field(default_factory=list)
    logic: LogicOperator = LogicOperator.AND
    actions: List[str] = field(default_factory=list)
    severity: Severity = Severity.INFO
    priority: int = 0
    enabled: bool = True
    schedule: Optional[str] = None
    cooldown_seconds: int = 30
    escalation_rule: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    _last_triggered: float = 0.0

    def evaluate(self, context: Dict) -> bool:
        if not self.enabled:
            return False
        if time.time() - self._last_triggered < self.cooldown_seconds:
            return False
        results = []
        for condition in self.conditions:
            result = condition.evaluate(context)
            if condition.logic == LogicOperator.NOT:
                result = not result
            results.append(result)
        if self.logic == LogicOperator.AND:
            return all(results)
        elif self.logic == LogicOperator.OR:
            return any(results)
        elif self.logic == LogicOperator.NOT:
            return not all(results)
        return all(results)

    def trigger(self) -> None:
        self._last_triggered = time.time()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "camera_id": self.camera_id,
            "conditions": [
                {"type": c.condition_type.value, "field": c.field,
                 "operator": c.operator, "value": c.value, "logic": c.logic.value}
                for c in self.conditions
            ],
            "logic": self.logic.value,
            "actions": self.actions,
            "severity": self.severity.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "cooldown_seconds": self.cooldown_seconds,
        }


class RuleEngine:
    """Enterprise rule engine supporting complex boolean logic,
    zone-based conditions, scheduling, and escalation."""

    def __init__(self):
        self.rules: Dict[int, Rule] = {}
        self.zones: Dict[int, Zone] = {}
        self._camera_zones: Dict[int, List[int]] = {}
        self._on_trigger_callbacks: List[Callable] = []
        self._escalation_rules: Dict[str, List[Rule]] = {}
        self._rule_lock = threading.RLock()

    def add_rule(self, rule_id: int, rule: Rule) -> None:
        with self._rule_lock:
            self.rules[rule_id] = rule

    def remove_rule(self, rule_id: int) -> None:
        with self._rule_lock:
            self.rules.pop(rule_id, None)

    def add_zone(self, zone_id: int, zone: Zone) -> None:
        with self._rule_lock:
            self.zones[zone_id] = zone
            if zone.camera_id not in self._camera_zones:
                self._camera_zones[zone.camera_id] = []
            self._camera_zones[zone.camera_id].append(zone_id)

    def remove_zone(self, zone_id: int) -> None:
        with self._rule_lock:
            zone = self.zones.pop(zone_id, None)
            if zone and zone.camera_id in self._camera_zones:
                self._camera_zones[zone.camera_id] = [
                    zid for zid in self._camera_zones[zone.camera_id]
                    if zid != zone_id
                ]

    def evaluate(self, context: Dict) -> List[Rule]:
        triggered = []
        camera_id = context.get("camera_id")
        if camera_id and "detections" in context:
            context["zone_occupancy"] = self._compute_zone_occupancy(camera_id, context["detections"])
        for rule_id, rule in self.rules.items():
            try:
                if rule.camera_id == camera_id or rule.camera_id == -1:
                    if rule.evaluate(context):
                        rule.trigger()
                        triggered.append(rule)
                        if rule.escalation_rule and rule.escalation_rule in self._escalation_rules:
                            for escalation in self._escalation_rules[rule.escalation_rule]:
                                if escalation.evaluate(context):
                                    escalation.trigger()
                                    triggered.append(escalation)
            except Exception as e:
                logger.error(f"Rule evaluation error ({rule_id}): {e}")
        for rule in triggered:
            for callback in self._on_trigger_callbacks:
                try:
                    callback(rule)
                except Exception as e:
                    logger.error(f"Trigger callback error: {e}")
        return triggered

    def _compute_zone_occupancy(self, camera_id: int, detections: List[Dict]) -> Dict[int, int]:
        zone_ids = self._camera_zones.get(camera_id, [])
        occupancy = {zid: 0 for zid in zone_ids}
        for det in detections:
            bbox = det.get("bbox", [0, 0, 1, 1])
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            for zid in zone_ids:
                zone = self.zones.get(zid)
                if zone and zone.contains_point(cx, cy):
                    occupancy[zid] += 1
        return occupancy

    def on_rule_trigger(self, callback: Callable) -> None:
        self._on_trigger_callbacks.append(callback)

    def get_rules(self, camera_id: Optional[int] = None) -> List[Rule]:
        with self._rule_lock:
            if camera_id:
                return [r for r in self.rules.values() if r.camera_id == camera_id]
            return list(self.rules.values())

    def get_zones(self, camera_id: Optional[int] = None) -> List[Zone]:
        with self._rule_lock:
            if camera_id:
                zone_ids = self._camera_zones.get(camera_id, [])
                return [self.zones[zid] for zid in zone_ids if zid in self.zones]
            return list(self.zones.values())

    def load_from_db(self, db) -> None:
        """Load rules and zones from database."""
        zones_data = db.query("SELECT * FROM zones")
        for z in zones_data:
            try:
                coords = json.loads(z["coordinates"]) if isinstance(z["coordinates"], str) else z["coordinates"]
                zone = Zone(
                    name=z["name"],
                    camera_id=z["camera_id"],
                    zone_type=z.get("zone_type", "polygon"),
                    coordinates=[tuple(c) for c in coords],
                    priority=z.get("priority", 0),
                )
                self.add_zone(z["id"], zone)
            except Exception as e:
                logger.error(f"Failed to load zone {z.get('id')}: {e}")
        logger.info(f"Loaded {len(zones_data)} zones from database")

    def rules_to_dict(self) -> List[Dict]:
        return [r.to_dict() for r in self.rules.values()]

    def zones_to_dict(self) -> List[Dict]:
        return [z.to_dict() for z in self.zones.values()]
