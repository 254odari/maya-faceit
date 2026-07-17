"""
core/logger.py

Central logging system for Maya Faceit.

Supports:

- Maya Script Editor
- Console
- File logging
- Exception logging
- Performance timing

Author: Your Name
"""

from __future__ import annotations

import logging
import os
import sys
import time
from functools import wraps
from pathlib import Path

try:
    import maya.cmds as cmds # type: ignore

    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


LOGGER_NAME = "MayaFaceit"


class FaceitLogger:
    """
    Singleton logger used throughout the plugin.
    """

    _instance = None

    def __new__(cls):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        self.logger = logging.getLogger(LOGGER_NAME)

        self.logger.setLevel(logging.DEBUG)

        self.logger.handlers.clear()

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            "%H:%M:%S",
        )

        # -----------------------------------------------------
        # Console
        # -----------------------------------------------------

        console = logging.StreamHandler(sys.stdout)

        console.setLevel(logging.INFO)

        console.setFormatter(formatter)

        self.logger.addHandler(console)

        # -----------------------------------------------------
        # File
        # -----------------------------------------------------

        log_dir = self.get_log_directory()

        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(
            log_dir / "maya_faceit.log",
            mode="w",
            encoding="utf-8",
        )

        file_handler.setFormatter(formatter)

        file_handler.setLevel(logging.DEBUG)

        self.logger.addHandler(file_handler)

    # ---------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------

    @staticmethod
    def get_log_directory() -> Path:

        if MAYA_AVAILABLE:

            prefs = cmds.internalVar(userPrefDir=True)

            return Path(prefs) / "maya_faceit" / "logs"

        return Path.cwd() / "logs"

    # ---------------------------------------------------------
    # Logging API
    # ---------------------------------------------------------

    def debug(self, message: str):

        self.logger.debug(message)

    def info(self, message: str):

        self.logger.info(message)

    def warning(self, message: str):

        self.logger.warning(message)

    def error(self, message: str):

        self.logger.error(message)

    def critical(self, message: str):

        self.logger.critical(message)

    def exception(self, message: str):

        self.logger.exception(message)


# -------------------------------------------------------------
# Performance Decorator
# -------------------------------------------------------------

def profile(func):
    """
    Logs execution time of a function.
    """

    @wraps(func)

    def wrapper(*args, **kwargs):

        start = time.perf_counter()

        result = func(*args, **kwargs)

        elapsed = time.perf_counter() - start

        log.info(
            f"{func.__module__}.{func.__name__} "
            f"completed in {elapsed:.4f} sec"
        )

        return result

    return wrapper


# -------------------------------------------------------------
# Global Logger
# -------------------------------------------------------------

log = FaceitLogger()