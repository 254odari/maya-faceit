"""
core/bootstrap.py

Bootstrap phase: initialize core systems before Maya is fully loaded.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Bootstrap:
    """
    Bootstrap phase handler.

    Runs early initialization: logging, plugin directories, environment variables.
    """

    def __init__(self):
        self._initialized = False

    def run(self) -> bool:
        """Execute bootstrap."""
        if self._initialized:
            return True

        try:
            self._setup_logging()
            self._verify_environment()
            self._create_directories()
            self._load_config()
            self._initialized = True
            return True
        except Exception as e:
            logger.exception("Bootstrap failed: %s", e)
            return False

    def _setup_logging(self):
        """Configure logging for the plugin."""
        # Already configured in core.logging.logger; we can add file handlers here
        pass

    def _verify_environment(self):
        """Check Python version, required packages."""
        import sys
        if sys.version_info < (3, 7):
            logger.warning("Maya FaceIT works best with Python 3.7 or higher")

    def _create_directories(self):
        """Create required directories (cache, logs, preferences)."""
        home = Path.home() / ".faceit"
        dirs = [
            home / "cache",
            home / "logs",
            home / "preferences",
            home / "projects",
            home / "temp",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directories in %s", home)

    def _load_config(self):
        """Load default configuration."""
        # Placeholder: load from JSON or environment
        pass