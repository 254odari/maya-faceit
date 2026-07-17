# -*- coding: utf-8 -*-
"""Utilities mixin."""

import copy
import threading
from typing import Any, Dict, Optional
from .models import AutosavePolicy, AutosaveEntry, AutosaveState, IOResult
from .constants import IO_VERSION, IO_SCHEMA_VERSION
from .manager import IOManager
class UtilsMixin:
    """Mixin providing utility methods."""

    def clone(self) -> "IOManager":
        clone = copy.deepcopy(self)
        clone._autosave_lock = threading.RLock()
        clone._autosave_timer = None
        clone._initialized = False
        clone._shutdown = False
        clone.initialize()
        return clone

    def copy_configuration(self, other: "IOManager") -> None:
        self._autosave_policy = copy.deepcopy(other._autosave_policy)
        self._recent_file = getattr(other, "_recent_file", None)

    def default_settings(self) -> Dict[str, Any]:
        return {
            "autosave": {k: v for k, v in AutosavePolicy().__dict__.items() if not k.startswith("_")},
            "compression": None,
            "schema_version": IO_SCHEMA_VERSION,
        }

    def apply_default_settings(self) -> None:
        self._autosave_policy = AutosavePolicy()

    @classmethod
    def create_manager(cls, **kwargs) -> "IOManager":
        manager = cls(**kwargs)
        manager.initialize()
        return manager

    @classmethod
    def instance(cls) -> "IOManager":
        if cls._instance is None:
            cls._instance = cls.create_manager()
        return cls._instance

    @classmethod
    def destroy_instance(cls) -> None:
        if cls._instance is not None:
            cls._instance.shutdown()
            cls._instance = None

    def version(self) -> str:
        return IO_VERSION

    def metadata(self) -> Dict[str, Any]:
        return {
            "module": self.__class__.__name__,
            "version": self.version(),
            "schema": IO_SCHEMA_VERSION,
            "initialized": getattr(self, "_initialized", False),
            "session": self.session_identifier(),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(version={self.version()!r}, initialized={getattr(self, '_initialized', False)}, autosave={self.autosave_enabled()})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} (v{self.version()})"

    def __enter__(self) -> "IOManager":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.shutdown()
        return False

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass