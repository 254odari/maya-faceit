# -*- coding: utf-8 -*-
"""
maya_faceit.application.preferences

Global user preferences (stored as JSON).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PreferenceManager:
    """Manages user preferences."""

    def __init__(self) -> None:
        self._path = Path.home() / ".faceit" / "preferences" / "prefs.json"
        self._data: Dict[str, Any] = {}

    def load(self) -> bool:
        """Load preferences from disk."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                return True
            else:
                self._data = self._get_defaults()
                return False
        except Exception as e:
            logger.warning("Failed to load preferences: %s", e)
            self._data = self._get_defaults()
            return False

    def save(self) -> bool:
        """Save preferences to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            return True
        except Exception as e:
            logger.warning("Failed to save preferences: %s", e)
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a preference value."""
        self._data[key] = value

    def _get_defaults(self) -> Dict[str, Any]:
        """Return default preferences."""
        return {
            "language": "en",
            "theme": "dark",
            "auto_save": True,
            "auto_save_interval": 300,
            "recent_projects": [],
            "mocap_device": "LiveLink",
            "export_format": "FBX",
        }