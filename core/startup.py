"""
core/startup.py

Startup phase: initialize UI, load preferences, restore session.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Startup:
    """
    Startup phase handler.

    Runs after Maya is fully loaded: creates UI, loads preferences,
    restores last session, registers tools.
    """

    def __init__(self):
        self._initialized = False

    def run(self) -> bool:
        """Execute startup."""
        if self._initialized:
            return True

        try:
            self._load_preferences()
            self._load_project()
            self._load_session()
            self._register_components()
            self._create_ui()
            self._init_events()
            self._initialized = True
            return True
        except Exception as e:
            logger.exception("Startup failed: %s", e)
            return False

    def _load_preferences(self):
        """Load user preferences."""
        from .preferences import preferences
        preferences.load()
        logger.debug("Preferences loaded.")

    def _load_project(self):
        """Load the current project."""
        from .project import project
        project.load()
        logger.debug("Project loaded.")

    def _load_session(self):
        """Restore the last session."""
        # Placeholder: session restore will be implemented later
        logger.debug("Session restored (placeholder).")

    def _register_components(self):
        """Register core components (tools, services)."""
        from .registry import ServiceRegistry
        registry = ServiceRegistry()
        # Register core services
        registry.register('preferences', self._load_preferences)
        registry.register('project', self._load_project)
        logger.debug("Components registered.")

    def _create_ui(self):
        """Create the main UI."""
        try:
            from maya_faceit.ui import create_main_window
            create_main_window()
            logger.debug("UI created.")
        except ImportError:
            logger.warning("UI module not found; running in headless mode.")

    def _init_events(self):
        """Initialize the event system."""
        # Placeholder: event system initialization
        logger.debug("Event system initialized (placeholder).")