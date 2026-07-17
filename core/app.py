"""
core/app.py

Main application controller for Maya Faceit.

Responsible for initializing the plugin, loading
configuration, managing global services, and launching
the main UI.

Also manages the plugin lifecycle: bootstrap, startup, shutdown.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .logging.logger import log
from .preferences import preferences
from .project import project
from .scene.scene_manager import scene_manager
from .pipeline.rig_pipeline import rig_pipeline
from ..application.bootstrap import Bootstrap
from ..application.startup import Startup
from ..application.shutdown import Shutdown
from ..application.registry import ServiceRegistry

from maya_faceit.version import __version__


class FaceitApp:
    """
    Main application controller.

    Manages the plugin lifecycle: bootstrap, startup, shutdown.
    Provides access to core services: preferences, project, registry.
    """

    APP_NAME = "Maya Faceit"

    def __init__(self):
        self.version = __version__
        self.initialized = False
        self.main_window = None
        self.root_directory = Path(__file__).parent.parent

        # Lifecycle components
        self._bootstrap = Bootstrap()
        self._startup = Startup()
        self._shutdown = Shutdown()
        self._registry = ServiceRegistry()
        self._running = False

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def bootstrap(self) -> bool:
        """Run bootstrap phase."""
        log.info("Bootstrapping Maya FaceIT...")
        try:
            result = self._bootstrap.run()
            if result:
                log.info("Bootstrap completed successfully.")
            else:
                log.error("Bootstrap failed.")
            return result
        except Exception as e:
            log.exception("Bootstrap error: %s", e)
            return False

    def startup(self) -> bool:
        """Run startup phase (after Maya is fully loaded)."""
        log.info("Starting Maya FaceIT...")
        try:
            result = self._startup.run()
            if result:
                self._running = True
                log.info("Startup completed successfully.")
            else:
                log.error("Startup failed.")
            return result
        except Exception as e:
            log.exception("Startup error: %s", e)
            return False

    def shutdown(self) -> bool:
        """Run shutdown phase."""
        if not self._running:
            return True
        log.info("Shutting down Maya FaceIT...")
        try:
            result = self._shutdown.run()
            if result:
                self._running = False
                log.info("Shutdown completed successfully.")
            else:
                log.error("Shutdown failed.")
            return result
        except Exception as e:
            log.exception("Shutdown error: %s", e)
            return False

    def restart(self) -> bool:
        """Restart the application."""
        self.shutdown()
        return self.startup()

    # =========================================================================
    # INITIALIZATION (Legacy compatibility)
    # =========================================================================

    def initialize(self) -> bool:
        """
        Initialize Faceit.
        """
        if self.initialized:
            return True

        log.info("=" * 60)
        log.info(f"{self.APP_NAME} {self.version}")
        log.info("=" * 60)

        # Use startup() to handle full initialization
        if not self.startup():
            return False

        self._load_preferences()
        self._initialize_scene()
        self._register_callbacks()

        self.initialized = True
        log.info("Faceit initialized.")
        return True

    # =========================================================================
    # UI
    # =========================================================================

    def show(self):
        """
        Show the main UI.
        """
        if not self.initialized:
            self.initialize()

        try:
            from maya_faceit.ui.main_window import FaceitMainWindow
        except ImportError:
            log.error("UI module not found.")
            return

        if self.main_window is None:
            self.main_window = FaceitMainWindow()

        self.main_window.show()
        self.main_window.raise_()

    # =========================================================================
    # SERVICES
    # =========================================================================

    @property
    def preferences(self):
        return preferences

    @property
    def project(self):
        return project

    @property
    def registry(self):
        return self._registry

    @property
    def is_running(self) -> bool:
        return self._running

    # =========================================================================
    # REGISTRY HELPERS
    # =========================================================================

    def get_service(self, name: str):
        """Get a registered service by name."""
        return self._registry.get(name)

    def register_service(self, name: str, service):
        """Register a service."""
        self._registry.register(name, service)

    def has_service(self, name: str) -> bool:
        return self._registry.has(name)

    # =========================================================================
    # RIG PIPELINE
    # =========================================================================

    def build_rig(self, mesh: str):
        return rig_pipeline.build(mesh)

    # =========================================================================
    # PROJECT
    # =========================================================================

    def open_project(self, path: str):
        return project.load(path)

    def save_project(self, path: Optional[str] = None):
        if path:
            return project.save_as(path)
        return project.save()

    # =========================================================================
    # SCENE
    # =========================================================================

    def current_scene(self):
        return scene_manager.current_scene()

    # =========================================================================
    # UTILITY
    # =========================================================================

    def plugin_directory(self) -> Path:
        return self.root_directory

    def version_string(self) -> str:
        return self.version

    # =========================================================================
    # INTERNAL
    # =========================================================================

    def _load_preferences(self):
        preferences.load()

    def _initialize_scene(self):
        scene_manager.refresh()

    def _register_callbacks(self):
        # Future: scene callbacks, selection callbacks, undo callbacks, ScriptJobs
        pass

    def _unregister_callbacks(self):
        pass


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

app = FaceitApp()

__all__ = ["FaceitApp", "app"]