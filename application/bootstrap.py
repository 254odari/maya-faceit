# -*- coding: utf-8 -*-
"""
maya_faceit.application.bootstrap

Early initialization: logging, directories, environment checks.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class Bootstrap:
    """Bootstrap phase handler."""

    def __init__(self) -> None:
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

    def _setup_logging(self) -> None:
        """Configure logging (additional handlers)."""
        # Already set up by core.logging; we can add file handler here.
        home = Path.home() / ".faceit" / "logs"
        home.mkdir(parents=True, exist_ok=True)
        log_file = home / "faceit.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(handler)

    def _verify_environment(self) -> None:
        """Check Python version and Maya version."""
        if sys.version_info < (3, 7):
            logger.warning("Maya FaceIT works best with Python 3.7 or higher.")

        # Optionally check Maya version
        try:
            import maya.cmds as cmds # type: ignore
            maya_ver = cmds.about(version=True)
            logger.info("Maya version: %s", maya_ver)
        except ImportError:
            logger.warning("Maya not available during bootstrap.")

    def _create_directories(self) -> None:
        """Create required directories."""
        home = Path.home() / ".faceit"
        for sub in ["cache", "logs", "preferences", "projects", "temp"]:
            (home / sub).mkdir(parents=True, exist_ok=True)
        logger.debug("Created directories in %s", home)

    def _load_config(self) -> None:
        """Load default configuration (could be from JSON)."""
        # Placeholder
        pass