"""
core/shutdown.py

Shutdown phase: save preferences, close sessions, cleanup.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class Shutdown:
    """
    Shutdown phase handler.

    Runs when Maya closes: save preferences, close project, cleanup resources.
    """

    def __init__(self):
        self._shutdown = False

    def run(self) -> bool:
        """Execute shutdown."""
        if self._shutdown:
            return True

        try:
            self._save_session()
            self._save_project()
            self._save_preferences()
            self._cleanup()
            self._close_ui()
            self._shutdown = True
            return True
        except Exception as e:
            logger.exception("Shutdown failed: %s", e)
            return False

    def _save_session(self):
        """Save the current session."""
        # Placeholder: session save will be implemented later
        logger.debug("Session saved (placeholder).")

    def _save_project(self):
        """Save the current project state."""
        from .project import project
        project.save()
        logger.debug("Project saved.")

    def _save_preferences(self):
        """Save user preferences."""
        from .preferences import preferences
        preferences.save()
        logger.debug("Preferences saved.")

    def _cleanup(self):
        """Cleanup resources (temp files, caches)."""
        temp_dir = Path.home() / ".faceit" / "temp"
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug("Temp directory cleaned.")
            except:
                pass

    def _close_ui(self):
        """Close any UI windows."""
        try:
            from maya_faceit.ui import close_all_windows
            close_all_windows()
            logger.debug("UI closed.")
        except:
            pass