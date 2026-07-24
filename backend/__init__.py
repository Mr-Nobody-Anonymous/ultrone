"""
Argus — Enterprise AI Video Analytics Platform
===============================================
Inspired by Argus Panoptes, the hundred-eyed giant of Greek mythology,
symbolizing constant vigilance and intelligent surveillance.

This package provides production-ready AI video analytics infrastructure
including detection, tracking, recognition, analytics, event management,
and multi-camera intelligence.
"""

__version__ = "2.0.0"
__author__ = "Argus Engineering Team"
__license__ = "MIT"

from .database import DatabaseManager, get_database
from .auth import AuthenticationManager
from .events import EventManager
from .pipeline import VideoPipeline
from .vision import VisionEngine
from .analytics import AnalyticsEngine
from .rules import RuleEngine
from .middleware import SecurityMiddleware
from .workers import WorkerManager
from .notifications import NotificationManager
from .cache import CacheManager
from .metrics import MetricsCollector

__all__ = [
    "DatabaseManager",
    "get_database",
    "AuthenticationManager",
    "EventManager",
    "VideoPipeline",
    "VisionEngine",
    "AnalyticsEngine",
    "RuleEngine",
    "SecurityMiddleware",
    "WorkerManager",
    "NotificationManager",
    "CacheManager",
    "MetricsCollector",
]

