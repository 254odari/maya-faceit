# -*- coding: utf-8 -*-
"""Session management mixin."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from .models import AutosavePolicy, AutosaveEntry, AutosaveState, IOResult

class SessionMixin:
    """Mixin providing session lifecycle management."""

    def _init_session(self):
        self._session_started = datetime.now()
        self._session_identifier = str(uuid.uuid4())
        self._initialized = True
        self._shutdown = False

    def initialize(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._init_session()

    def shutdown(self) -> None:
        if not getattr(self, "_initialized", False):
            return
        self.flush()
        self.shutdown_autosave()
        self._shutdown = True
        self._initialized = False

    def flush(self) -> None:
        if self.autosave_enabled() and self.is_dirty():
            try:
                self.perform_autosave()
            except Exception:
                pass

    def reset(self) -> None:
        self.cancel_autosave_timer()
        self.clear_autosave_history()
        self.clear_autosave_callbacks()
        self._autosave_successes = 0
        self._autosave_failures = 0
        self._recent_file = None
        self._session_started = datetime.now()
        self._session_identifier = str(uuid.uuid4())
        self._autosave_state = AutosaveState.IDLE

    def reload(self) -> None:
        self.shutdown()
        self.initialize()

    def close(self) -> None:
        self.shutdown()

    def session_active(self) -> bool:
        return getattr(self, "_initialized", False) and not getattr(self, "_shutdown", False)

    def session_identifier(self) -> str:
        return self._session_identifier

    def session_duration(self) -> timedelta:
        return datetime.now() - self._session_started

    def session_summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_identifier(),
            "started": self._session_started,
            "duration": str(self.session_duration()),
            "initialized": getattr(self, "_initialized", False),
            "shutdown": getattr(self, "_shutdown", False),
            "autosave": self.autosave_enabled(),
            "dirty": self.is_dirty(),
        }