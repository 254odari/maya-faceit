# -*- coding: utf-8 -*-
"""
maya_faceit.application.startup

Startup phase: initialize services, UI, and load preferences.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import Application

logger = logging.getLogger(__name__)


class Startup:
    """Startup phase handler."""

    def __init__(self) -> None:
        self._initialized = False

    def run(self, app: 'Application') -> bool:
        """Execute startup."""
        if self._initialized:
            return True

        try:
            # 1. Load preferences
            app.preferences.load()

            # 2. Register core services
            self._register_services(app)

            # 3. Initialize UI
            self._init_ui(app)

            # 4. Load session
            app.session.load()

            # 5. Load project (if auto-open)
            # app.project.load_last()

            self._initialized = True
            logger.info("Startup completed.")
            return True

        except Exception as e:
            logger.exception("Startup failed: %s", e)
            return False

    def _register_services(self, app: 'Application') -> None:
        """Register all feature services."""
        # Example: register blendshape service
        try:
            from ..blendshapes.blendshape_manager import BlendshapeManager
            app.register_service("blendshapes", BlendshapeManager())
        except ImportError as e:
            logger.warning("Blendshape service not available: %s", e)

        # Register other services as needed
        # app.register_service("rig", RigService())
        # app.register_service("arkit", ARKitService())
        # etc.

    def _init_ui(self, app: 'Application') -> None:
        """Initialize the UI (lazy – wait for main window creation)."""
        # We'll create the main window only when needed.
        # For now, store a reference to the app.
        # The UI will be created by the controller or via a command.
        pass