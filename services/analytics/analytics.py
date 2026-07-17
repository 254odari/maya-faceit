"""
maya_faceit/services/analytics/analytics.py

Anonymous usage analytics collection (opt‑in).
"""

import logging
import time
import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnalyticsEventType(Enum):
    APP_LAUNCH = "app_launch"
    PROJECT_OPEN = "project_open"
    PROJECT_SAVE = "project_save"
    RIG_BUILD = "rig_build"
    BLENDSHAPE_CREATE = "blendshape_create"
    ARKIT_GENERATE = "arkit_generate"
    MOCAP_CONNECT = "mocap_connect"
    EXPORT = "export"
    ERROR = "error"


@dataclass
class AnalyticsEvent:
    """An analytics event."""
    type: AnalyticsEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AnalyticsService:
    """
    Anonymous usage analytics collection.
    Data is stored locally and can be optionally sent to a remote server.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._enabled = False  # opt‑in by default
        self._storage_path: Optional[str] = None
        self._events: list = []
        self._max_events = 100
        logger.debug("AnalyticsService initialized (disabled)")

    def enable(self, storage_path: Optional[str] = None) -> None:
        """Enable analytics collection."""
        self._enabled = True
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
        logger.info("Analytics enabled.")

    def disable(self) -> None:
        self._enabled = False
        logger.info("Analytics disabled.")

    def track(self, event_type: AnalyticsEventType, data: Optional[Dict[str, Any]] = None) -> None:
        """Record an analytics event."""
        if not self._enabled:
            return
        event = AnalyticsEvent(type=event_type, data=data or {})
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._flush_events()
        logger.debug(f"Analytics: {event_type.value} {event.data}")

    def _flush_events(self) -> None:
        """Write events to disk (if storage path is set)."""
        if not self._storage_path:
            return
        if not self._events:
            return
        filepath = os.path.join(self._storage_path, f"analytics_{int(time.time())}.json")
        try:
            with open(filepath, "w") as f:
                json.dump([{"type": e.type.value, "data": e.data, "timestamp": e.timestamp} for e in self._events], f, indent=2)
            self._events.clear()
        except Exception as e:
            logger.error(f"Failed to flush analytics: {e}")

    def flush(self) -> None:
        """Manually flush all pending events."""
        self._flush_events()

    def get_pending_count(self) -> int:
        return len(self._events)

    # ---------- Convenience Methods ----------

    def track_app_launch(self, version: str) -> None:
        self.track(AnalyticsEventType.APP_LAUNCH, {"version": version})

    def track_project_open(self, name: str) -> None:
        self.track(AnalyticsEventType.PROJECT_OPEN, {"name": name})

    def track_rig_build(self, template: str) -> None:
        self.track(AnalyticsEventType.RIG_BUILD, {"template": template})

    def track_blendshape_create(self, count: int) -> None:
        self.track(AnalyticsEventType.BLENDSHAPE_CREATE, {"count": count})

    def track_arkit_generate(self, num_shapes: int) -> None:
        self.track(AnalyticsEventType.ARKIT_GENERATE, {"num_shapes": num_shapes})

    def track_export(self, format: str) -> None:
        self.track(AnalyticsEventType.EXPORT, {"format": format})

    def track_error(self, error: str) -> None:
        self.track(AnalyticsEventType.ERROR, {"error": error})