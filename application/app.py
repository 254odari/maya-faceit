# -*- coding: utf-8 -*-
"""
maya_faceit.application.app

Main application class – owns the plugin lifecycle.
"""

import logging
from typing import Optional

from .bootstrap import Bootstrap
from .startup import Startup
from .shutdown import Shutdown
from .preferences import PreferenceManager
from .project import ProjectManager
from .session import SessionManager
from .registry import ServiceRegistry

logger = logging.getLogger(__name__)


class Application:
    """
    Singleton application instance.
    Manages bootstrap, startup, shutdown, and core services.
    """

    _instance: Optional['Application'] = None

    def __new__(cls) -> 'Application':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._bootstrap = Bootstrap()
        self._startup = Startup()
        self._shutdown = Shutdown()
        self._preferences = PreferenceManager()
        self._project = ProjectManager()
        self._session = SessionManager()
        self._registry = ServiceRegistry()
        self._running = False

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def bootstrap(self) -> bool:
        """Run bootstrap phase (early initialization)."""
        logger.info("Bootstrapping Maya FaceIT...")
        try:
            result = self._bootstrap.run()
            if result:
                logger.info("Bootstrap completed successfully.")
            else:
                logger.error("Bootstrap failed.")
            return result
        except Exception as e:
            logger.exception("Bootstrap error: %s", e)
            return False

    def startup(self) -> bool:
        """Run startup phase (after Maya is fully loaded)."""
        logger.info("Starting Maya FaceIT...")
        try:
            result = self._startup.run(self)
            if result:
                self._running = True
                logger.info("Startup completed successfully.")
            else:
                logger.error("Startup failed.")
            return result
        except Exception as e:
            logger.exception("Startup error: %s", e)
            return False

    def shutdown(self) -> bool:
        """Run shutdown phase (cleanup before unload)."""
        if not self._running:
            return True
        logger.info("Shutting down Maya FaceIT...")
        try:
            result = self._shutdown.run(self)
            if result:
                self._running = False
                logger.info("Shutdown completed successfully.")
            else:
                logger.error("Shutdown failed.")
            return result
        except Exception as e:
            logger.exception("Shutdown error: %s", e)
            return False

    def restart(self) -> bool:
        """Restart the application."""
        self.shutdown()
        return self.startup()

    # -------------------------------------------------------------------------
    # Core Services
    # -------------------------------------------------------------------------

    @property
    def preferences(self) -> PreferenceManager:
        return self._preferences

    @property
    def project(self) -> ProjectManager:
        return self._project

    @property
    def session(self) -> SessionManager:
        return self._session

    @property
    def registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def is_running(self) -> bool:
        return self._running

    # -------------------------------------------------------------------------
    # Registry Helpers
    # -------------------------------------------------------------------------

    def get_service(self, name: str):
        """Get a registered service by name."""
        return self._registry.get(name)

    def register_service(self, name: str, service) -> None:
        """Register a service."""
        self._registry.register(name, service)

    def has_service(self, name: str) -> bool:
        return self._registry.has(name)


# -----------------------------------------------------------------------------
# Global singleton access
# -----------------------------------------------------------------------------

_app: Optional[Application] = None


def get_application() -> Application:
    """Get the global Application instance."""
    global _app
    if _app is None:
        _app = Application()
    return _app

# Add this at the bottom of app.py
MayaFaceitApp = Application
__all__ = ["Application", "get_application"]