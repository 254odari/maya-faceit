"""
diagnostics.py

RuntimeDiagnostics - stores historical runtime events and errors.
"""

import time
import traceback
from collections import deque
from typing import Dict, List, Optional, Any

from .enums import RuntimeEvent
from .models import RuntimeEventRecord, RuntimeErrorRecord


class RuntimeDiagnostics:
    """Stores historical runtime diagnostics."""

    def __init__(self, history_size: int = 1000):
        self.event_history = deque(maxlen=history_size)
        self.error_history = deque(maxlen=history_size)
        self.enabled = True

    def record_event(
        self,
        event: RuntimeEvent,
        source: str,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        self.event_history.append(
            RuntimeEventRecord(
                timestamp=time.time(),
                event=event,
                source=source,
                message=message,
                data=data,
            )
        )

    def record_error(self, exc: Exception) -> None:
        if not self.enabled:
            return
        self.error_history.append(
            RuntimeErrorRecord(
                timestamp=time.time(),
                exception_type=type(exc).__name__,
                message=str(exc),
                traceback_text=traceback.format_exc(),
            )
        )

    def clear(self) -> None:
        self.event_history.clear()
        self.error_history.clear()

    @property
    def event_count(self) -> int:
        return len(self.event_history)

    @property
    def error_count(self) -> int:
        return len(self.error_history)

    def latest_event(self) -> Optional[RuntimeEventRecord]:
        if not self.event_history:
            return None
        return self.event_history[-1]

    def latest_error(self) -> Optional[RuntimeErrorRecord]:
        if not self.error_history:
            return None
        return self.error_history[-1]

    def summary(self) -> Dict[str, Any]:
        return {
            "events": self.event_count,
            "errors": self.error_count,
            "latest_event": self.latest_event(),
            "latest_error": self.latest_error(),
        }