# -*- coding: utf-8 -*-
"""Autosave mixin for IOManager."""

import threading
import uuid
import copy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .models import AutosavePolicy, AutosaveEntry, AutosaveState, IOResult


class AutosaveMixin:
    """Mixin providing autosave functionality."""

    def _init_autosave(self):
        self._autosave_policy = AutosavePolicy()
        self._autosave_state = AutosaveState.IDLE
        self._autosave_history: List[AutosaveEntry] = []
        self._autosave_callbacks: List[Callable[[AutosaveEntry], None]] = []
        self._autosave_timer = None
        self._autosave_last_save = None
        self._autosave_next_save = None
        self._autosave_dirty = False
        self._autosave_lock = threading.RLock()
        self._autosave_failures = 0
        self._autosave_successes = 0
        self._autosave_session_id = str(uuid.uuid4())

    def autosave_policy(self) -> AutosavePolicy:
        return self._autosave_policy

    def enable_autosave(self) -> None:
        with self._autosave_lock:
            self._autosave_policy.enabled = True
            self._autosave_state = AutosaveState.IDLE
            self.schedule_next_autosave()

    def disable_autosave(self) -> None:
        with self._autosave_lock:
            self._autosave_policy.enabled = False
            self._autosave_state = AutosaveState.DISABLED
            self.cancel_autosave_timer()

    def pause_autosave(self) -> None:
        with self._autosave_lock:
            if self._autosave_state == AutosaveState.PAUSED:
                return
            self.cancel_autosave_timer()
            self._autosave_state = AutosaveState.PAUSED

    def resume_autosave(self) -> None:
        with self._autosave_lock:
            if not self._autosave_policy.enabled:
                return
            self._autosave_state = AutosaveState.IDLE
            self.schedule_next_autosave()

    def autosave_enabled(self) -> bool:
        return self._autosave_policy.enabled

    def schedule_next_autosave(self) -> Optional[datetime]:
        with self._autosave_lock:
            if not self.autosave_enabled():
                return None
            self.cancel_autosave_timer()
            interval = timedelta(seconds=self._autosave_policy.interval_seconds)
            self._autosave_next_save = datetime.now() + interval
            self._autosave_timer = threading.Timer(interval.total_seconds(), self._autosave_timer_callback)
            self._autosave_timer.daemon = True
            self._autosave_timer.start()
            self._autosave_state = AutosaveState.WAITING
            return self._autosave_next_save

    def cancel_autosave_timer(self) -> None:
        if self._autosave_timer:
            self._autosave_timer.cancel()
            self._autosave_timer = None

    def _autosave_timer_callback(self) -> None:
        if self.should_autosave():
            self.perform_autosave()
        elif self.autosave_enabled():
            self.schedule_next_autosave()

    def should_autosave(self) -> bool:
        if not self.autosave_enabled():
            return False
        if self._autosave_state in (AutosaveState.SAVING, AutosaveState.PAUSED, AutosaveState.ERROR):
            return False
        if not self.is_dirty():
            return False
        if self._autosave_next_save is None:
            return False
        return datetime.now() >= self._autosave_next_save

    def is_dirty(self) -> bool:
        return self._autosave_dirty

    def mark_dirty(self) -> None:
        self._autosave_dirty = True

    def clear_dirty(self) -> None:
        self._autosave_dirty = False

    def perform_autosave(self, obj: Optional[Any] = None) -> Optional[IOResult]:
        with self._autosave_lock:
            if not self.autosave_enabled() or self._autosave_state == AutosaveState.SAVING:
                return None
            self._autosave_state = AutosaveState.SAVING
        try:
            if obj is None:
                obj = {}  # Placeholder: get current data
            result = self._execute_autosave(obj)
            self._autosave_successes += 1
            self._autosave_failures = 0
            self._autosave_last_save = datetime.now()
            self.clear_dirty()
            self.schedule_next_autosave()
            self._autosave_state = AutosaveState.IDLE
            return result
        except Exception:
            self._autosave_failures += 1
            self._autosave_state = AutosaveState.ERROR
            raise

    def _execute_autosave(self, obj: Any) -> IOResult:
        path = self.autosave_path()
        if isinstance(obj, dict) and self._autosave_policy.use_versioning:
            obj = self.embed_version_metadata(copy.deepcopy(obj))
        return self.smart_save(path, obj, compression=self.default_compression() if self._autosave_policy.compress else None,
                               atomic=self._autosave_policy.atomic)

    def autosave_path(self) -> Path:
        directory = self._autosave_policy.autosave_directory or Path.cwd() / "autosaves"
        directory.mkdir(parents=True, exist_ok=True)
        prefix = self._autosave_policy.filename_prefix
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{stamp}.bin"
        return directory / filename