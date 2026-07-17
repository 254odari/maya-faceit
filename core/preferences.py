"""
core/preferences.py

Preference manager for Maya Faceit.

Handles:

- Loading config.json
- User preferences
- Saving settings
- Validation
- Runtime cache

Author: Your Name
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import maya.cmds as cmds # type: ignore

    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

from maya_faceit.core.logger import log


class Preferences:
    """
    Singleton preference manager.
    """

    _instance = None

    DEFAULT_CONFIG = {
        "theme": "dark",
        "language": "en",
        "autosave": True,
        "autosave_interval": 10,
        "controller_scale": 1.0,
        "auto_mirror": True,
        "use_matrix_constraints": True,
        "undo_levels": 50,
        "logging": {
            "enabled": True,
            "level": "INFO"
        },
        "viewport": {
            "display_controls": True,
            "display_landmarks": True
        },
        "mocap": {
            "smoothing": True,
            "filter_strength": 0.5
        }
    }

    def __new__(cls):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        self.config = {}

        self.config_path = self.get_config_path()

        self.load()

    # ---------------------------------------------------------
    # Paths
    # ---------------------------------------------------------

    @staticmethod
    def get_config_directory() -> Path:

        if MAYA_AVAILABLE:

            prefs = Path(cmds.internalVar(userPrefDir=True))

            return prefs / "maya_faceit"

        return Path.home() / ".maya_faceit"

    @classmethod
    def get_config_path(cls) -> Path:

        return cls.get_config_directory() / "preferences.json"

    # ---------------------------------------------------------
    # Load / Save
    # ---------------------------------------------------------

    def load(self):

        directory = self.get_config_directory()

        directory.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():

            self.config = self.DEFAULT_CONFIG.copy()

            self.save()

            log.info("Created default preferences.")

            return

        with open(self.config_path, "r", encoding="utf-8") as file:

            self.config = json.load(file)

        log.info("Preferences loaded.")

    def save(self):

        with open(self.config_path, "w", encoding="utf-8") as file:

            json.dump(
                self.config,
                file,
                indent=4,
                sort_keys=True,
            )

        log.info("Preferences saved.")

    # ---------------------------------------------------------
    # Access
    # ---------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:

        return self.config.get(key, default)

    def set(self, key: str, value: Any):

        self.config[key] = value

        self.save()

    def exists(self, key: str) -> bool:

        return key in self.config

    def remove(self, key: str):

        if key in self.config:

            del self.config[key]

            self.save()

    # ---------------------------------------------------------
    # Nested Access
    # ---------------------------------------------------------

    def get_nested(self, *keys):

        data = self.config

        for key in keys:

            if key not in data:

                return None

            data = data[key]

        return data

    def set_nested(self, value, *keys):

        data = self.config

        for key in keys[:-1]:

            data = data.setdefault(key, {})

        data[keys[-1]] = value

        self.save()

    # ---------------------------------------------------------
    # Reset
    # ---------------------------------------------------------

    def reset(self):

        self.config = self.DEFAULT_CONFIG.copy()

        self.save()

        log.warning("Preferences reset to defaults.")

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    def validate(self):

        if self.get("controller_scale") <= 0:

            self.set("controller_scale", 1.0)

        if self.get("undo_levels") < 1:

            self.set("undo_levels", 50)

        smoothing = self.get_nested(
            "mocap",
            "filter_strength"
        )

        if smoothing is not None:

            smoothing = max(0.0, min(1.0, smoothing))

            self.set_nested(
                smoothing,
                "mocap",
                "filter_strength"
            )


preferences = Preferences()