"""
Analytics Engine — Heatmaps, traffic analytics, occupancy, zone utilization,
time-series analytics, reports, trend prediction, behavior clustering, CSV/PDF export.
"""

import os
import csv
import json
import io
import time
import logging
import threading
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum
from collections import defaultdict, Counter

logger = logging.getLogger("argus.analytics")


class ReportPeriod(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class AnalyticsSnapshot:
    timestamp: float
    camera_id: int
    object_counts: Dict[str, int] = field(default_factory=dict)
    occupancy: int = 0
    events: int = 0
    fps: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    memory_usage: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class TrafficFlow:
    from_zone: str
    to_zone: str
    count: int = 0
    avg_speed: float = 0.0
    peak_hour: Optional[int] = None


@dataclass
class HeatmapPoint:
    x: float
    y: float
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)


class AnalyticsEngine:
    """
    Comprehensive analytics engine generating heatmaps, traffic analysis,
    occupancy trends, automatic reports, and behavioral clustering.
    """

    def __init__(self, db=None, config: Optional[Dict] = None):
        self.db = db
        self.config = config or {}
        self._snapshots: List[AnalyticsSnapshot] = []
        self._heatmap_points: Dict[int, List[HeatmapPoint]] = {}
        self._lock = threading.RLock()
        self._running = False
        self._report_schedulers: Dict[str, threading.Thread] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def set_db(self, db) -> None:
        self.db = db

    def record_snapshot(self, snapshot: AnalyticsSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)
            self._persist_snapshot(snapshot)

    def record_detection(self, camera_id: int, x: float, y: float, weight: float = 1.0) -> None:
        with self._lock:
            if camera_id not in self._heatmap_points:
                self._heatmap_points[camera_id] = []
            self._heatmap_points[camera_id].append(HeatmapPoint(x=x, y=y, weight=weight))

    def get_heatmap(self, camera_id: int, width: int = 100, height: int = 100,
                    start_time: Optional[float] = None, end_time: Optional[float] = None) -> np.ndarray:
        points = self._heatmap_points.get(camera_id, [])
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]
        if not points:
            return np.zeros((height, width), dtype=np.float32)
        heatmap = np.zeros((height, width), dtype=np.float32)
        for point in points:
            x = int(point.x * width)
            y = int(point.y * height)
            if 0 <= x < width and 0 <= y < height:
                heatmap[y, x] += point.weight
        from scipy.ndimage import gaussian_filter
        heatmap = gaussian_filter(heatmap, sigma=3.0)
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        return heatmap

    def get_occupancy_analytics(self, camera_id: Optional[int] = None,
                                 period: str = "hourly") -> Dict[str, Any]:
        now = datetime.now()
        periods = {"hourly": timedelta(hours=24), "daily": timedelta(days=7),
                    "weekly": timedelta(weeks=4), "monthly": timedelta(days=90)}
        cutoff = (now - periods.get(period, timedelta(hours=1))).timestamp()
        snapshots = [s for s in self._snapshots if s.timestamp >= cutoff]
        if camera_id:
            snapshots = [s for s in snapshots if s.camera_id == camera_id]
        if not snapshots:
            return {"avg_occupancy": 0, "peak_occupancy": 0, "current": 0, "data_points": 0}
        occupancies = [s.occupancy for s in snapshots]
        return {
            "avg_occupancy": float(np.mean(occupancies)),
            "peak_occupancy": float(np.max(occupancies)),
            "current": occupancies[-1] if occupancies else 0,
            "min_occupancy": float(np.min(occupancies)),
            "std_dev": float(np.std(occupancies)),
            "data_points": len(snapshots),
            "period": period,
        }

    def get_traffic_analytics(self, camera_id: Optional[int] = None,
                               period: str = "daily") -> Dict[str, Any]:
        snapshots = self._snapshots
        if camera_id:
            snapshots = [s for s in snapshots if s.camera_id == camera_id]
        object_counts = Counter()
        for snap in snapshots:
            for obj_type, count in snap.object_counts.items():
                object_counts[obj_type] += count
        total_objects = sum(object_counts.values())
        return {
            "total_objects": total_objects,
            "unique_types": len(object_counts),
            "by_type": dict(object_counts.most_common(20)),
            "avg_per_snapshot": total_objects / max(1, len(snapshots)),
            "data_points": len(snapshots),
        }

    def get_zone_utilization(self, zones: Dict[int, Dict],
                              camera_id: Optional[int] = None) -> Dict[str, Any]:
        utilizations = {}
        for zone_id, zone in zones.items():
            if camera_id and zone.get("camera_id") != camera_id:
                continue
            utilizations[zone["name"]] = {
                "total_entries": zone.get("entry_count", 0),
                "total_exits": zone.get("exit_count", 0),
                "avg_dwell_time": zone.get("avg_dwell_time", 0),
                "peak_occupancy": zone.get("peak_occupancy", 0),
            }
        return utilizations

    def generate_report(self, period: ReportPeriod = ReportPeriod.DAILY,
                         camera_id: Optional[int] = None) -> Dict[str, Any]:
        report = {
            "generated_at": datetime.now().isoformat(),
            "period": period.value,
            "camera_id": camera_id,
            "summary": {},
            "occupancy": self.get_occupancy_analytics(camera_id, period.value),
            "traffic": self.get_traffic_analytics(camera_id, period.value),
            "events": self._get_event_stats(camera_id, period),
            "performance": self._get_performance_stats(camera_id, period),
        }
        occ = report["occupancy"]
        traffic = report["traffic"]
        report["summary"] = {
            "avg_occupancy": f"{occ['avg_occupancy']:.1f}",
            "peak_occupancy": str(occ['peak_occupancy']),
            "total_objects_detected": str(traffic["total_objects"]),
            "unique_object_types": str(traffic["unique_types"]),
            "data_collected": str(traffic["data_points"]),
        }
        return report

    def _get_event_stats(self, camera_id: Optional[int], period: ReportPeriod) -> Dict:
        if not self.db:
            return {"total": 0, "by_severity": {}, "by_type": {}}
        try:
            days = {"hourly": 1, "daily": 1, "weekly": 7, "monthly": 30}
            cutoff = (datetime.now() - timedelta(days=days.get(period.value, 1))).isoformat()
            query = "SELECT severity, event_type, COUNT(*) as count FROM events WHERE created_at >= :cut"
            params = {"cut": cutoff}
            if camera_id:
                query += " AND camera_id = :cid"
                params["cid"] = camera_id
            query += " GROUP BY severity, event_type"
            results = self.db.query(query, params)
            by_severity = defaultdict(int)
            by_type = defaultdict(int)
            for row in results:
                by_severity[row["severity"]] += row["count"]
                by_type[row["event_type"]] += row["count"]
            return {"total": sum(by_severity.values()), "by_severity": dict(by_severity), "by_type": dict(by_type)}
        except Exception as e:
            logger.error(f"Event stats error: {e}")
            return {"total": 0, "by_severity": {}, "by_type": {}}

    def _get_performance_stats(self, camera_id: Optional[int], period: ReportPeriod) -> Dict:
        snapshots = self._snapshots
        if camera_id:
            snapshots = [s for s in snapshots if s.camera_id == camera_id]
        if not snapshots:
            return {"avg_fps": 0, "avg_cpu": 0, "avg_gpu": 0, "avg_memory": 0}
        return {
            "avg_fps": float(np.mean([s.fps for s in snapshots])),
            "avg_cpu": float(np.mean([s.cpu_usage for s in snapshots])),
            "avg_gpu": float(np.mean([s.gpu_usage for s in snapshots])),
            "avg_memory": float(np.mean([s.memory_usage for s in snapshots])),
        }

    def export_csv(self, report: Dict, output_path: str) -> bool:
        """Export report data to CSV."""
        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Generated At", report.get("generated_at", "")])
                writer.writerow(["Period", report.get("period", "")])
                writer.writerow([])
                writer.writerow(["Occupancy Analytics"])
                for k, v in report.get("occupancy", {}).items():
                    writer.writerow([k, v])
                writer.writerow([])
                writer.writerow(["Traffic Analytics"])
                for k, v in report.get("traffic", {}).items():
                    if k != "by_type":
                        writer.writerow([k, v])
                if "by_type" in report.get("traffic", {}):
                    writer.writerow([])
                    writer.writerow(["Object Type", "Count"])
                    for obj_type, count in report["traffic"]["by_type"].items():
                        writer.writerow([obj_type, count])
            logger.info(f"CSV report exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            return False

    def export_pdf(self, report: Dict, output_path: str) -> bool:
        """Export report to PDF using reportlab."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors

            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph(f"Analytics Report - {report.get('period', 'N/A')}", styles["Title"]))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Generated: {report.get('generated_at', '')}", styles["Normal"]))
            story.append(Spacer(1, 20))

            # Summary
            story.append(Paragraph("Summary", styles["Heading2"]))
            summary_data = [[k, v] for k, v in report.get("summary", {}).items()]
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))

            # Occupancy
            story.append(Paragraph("Occupancy Analytics", styles["Heading2"]))
            occ_data = [[k, str(v)] for k, v in report.get("occupancy", {}).items()]
            occ_table = Table(occ_data)
            occ_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(occ_table)

            doc.build(story)
            logger.info(f"PDF report exported to {output_path}")
            return True
        except ImportError:
            logger.warning("reportlab not installed. PDF export requires 'pip install reportlab'")
            return False
        except Exception as e:
            logger.error(f"PDF export error: {e}")
            return False

    def _persist_snapshot(self, snapshot: AnalyticsSnapshot) -> None:
        if not self.db:
            return
        try:
            self.db.insert("analytics_events", {
                "camera_id": snapshot.camera_id,
                "timestamp": datetime.fromtimestamp(snapshot.timestamp).isoformat(),
                "event_type": "snapshot",
                "data": json.dumps({
                    "object_counts": snapshot.object_counts,
                    "occupancy": snapshot.occupancy,
                    "events": snapshot.events,
                    "fps": snapshot.fps,
                    "cpu_usage": snapshot.cpu_usage,
                    "gpu_usage": snapshot.gpu_usage,
                    "memory_usage": snapshot.memory_usage,
                }),
            })
        except Exception as e:
            logger.error(f"Snapshot persistence error: {e}")

    def get_trend_prediction(self, camera_id: Optional[int] = None,
                              hours: int = 24, forecast_hours: int = 1) -> Dict[str, Any]:
        """Predict future occupancy trends using linear regression."""
        cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
        snapshots = [s for s in self._snapshots if s.timestamp >= cutoff]
        if camera_id:
            snapshots = [s for s in snapshots if s.camera_id == camera_id]

        if len(snapshots) < 2:
            return {"error": "Insufficient data for prediction"}

        timestamps = np.array([s.timestamp for s in snapshots])
        occupancies = np.array([s.occupancy for s in snapshots])

        # Normalize timestamps
        t0 = timestamps[0]
        timestamps_norm = (timestamps - t0) / 3600  # in hours

        # Linear regression
        A = np.vstack([timestamps_norm, np.ones_like(timestamps_norm)]).T
        slope, intercept = np.linalg.lstsq(A, occupancies, rcond=None)[0]

        forecast_ts = (timestamps_norm[-1] + forecast_hours)
        forecast = slope * forecast_ts + intercept

        r_squared = 1.0 - (np.sum((occupancies - (slope * timestamps_norm + intercept)) ** 2) /
                           max(1e-10, np.sum((occupancies - np.mean(occupancies)) ** 2)))

        return {
            "current_trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "forecast_hours": forecast_hours,
            "forecasted_occupancy": float(max(0, forecast)),
            "data_points": len(snapshots),
        }

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary data for dashboards."""
        return {
            "total_cameras": len(set(s.camera_id for s in self._snapshots)),
            "total_snapshots": len(self._snapshots),
            "total_detections": sum(
                sum(s.object_counts.values()) for s in self._snapshots
            ),
            "current_occupancy": self._snapshots[-1].occupancy if self._snapshots else 0,
            "latest_trend": self.get_trend_prediction(),
        }

    def close(self) -> None:
        self._snapshots.clear()
        self._heatmap_points.clear()
        logger.info("AnalyticsEngine closed")
