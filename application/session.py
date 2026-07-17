# -*- coding: utf-8 -*-
"""
maya_faceit.application.session

Session state (UI layout, open panels, selection, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Session data container."""
    layout: str = ""
    selected_tools: List[str] = field(default_factory=list)
    open_panels: List[str] = field(default_factory=list)
    camera_position: tuple = (0, 0, 0)
    zoom_level: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages the UI session state."""

    def __init__(self) -> None:
        self._path = Path.home() / ".faceit" / "session.json"
        self._session: Optional[Session] = None

    def get(self) -> Optional[Session]:
        """Get the current session."""
        return self._session

    def set(self, session: Session) -> None:
        """Set the current session."""
        self._session = session

    def load(self) -> bool:
        """Load session from disk."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._session = Session(**data)
                return True
        except Exception as e:
            logger.warning("Failed to load session: %s", e)
        return False

    def save(self) -> bool:
        """Save session to disk."""
        if not self._session:
            return False
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._session.__dict__, f, indent=2)
            return True
        except Exception as e:
            logger.warning("Failed to save session: %s", e)
            return False

    def restore(self) -> bool:
        """Apply session state to the UI."""
        if not self._session:
            return False
        # Placeholder: would interact with UI manager
        return True

    def clear(self) -> None:
        """Clear the current session."""
        self._session = None
        if self._path.exists():
            self._path.unlink()