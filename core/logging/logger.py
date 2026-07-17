"""
core/logging/logger.py

Central logging system for Maya Faceit.

Supports:
- Maya Script Editor output
- File logging
- Console logging
- Exception logging
- Performance profiling
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Singleton pattern
"""

import logging
import sys
import time
import os
from functools import wraps
from pathlib import Path
from typing import Optional

try:
    import maya.cmds as cmds # type: ignore
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

# Logger name
LOGGER_NAME = "MayaFaceit"

# Default log format
DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"

# Log levels mapping
LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class FaceitLogger:
    """
    Singleton logger for the entire plugin.
    Provides consistent logging across modules.
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
        self._logger = logging.getLogger(LOGGER_NAME)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)

        # Console handler (Script Editor or stdout)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        self._logger.addHandler(console)

        # Maya Script Editor handler (if available)
        if MAYA_AVAILABLE:
            self._add_maya_handler(formatter)

        # File handler
        log_dir = self._get_log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "maya_faceit.log",
            mode="a",  # Append mode for persistence across sessions
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

        # Silence noisy third-party loggers
        self._silence_third_party_loggers()

        self._logger.debug("Maya Faceit logger initialized.")

    # ----------------------------------------------------------------------
    # Maya Integration
    # ----------------------------------------------------------------------

    def _add_maya_handler(self, formatter):
        """Add a handler that writes to Maya's Script Editor."""
        try:
            # Maya's script editor output can be accessed via cmds.scriptEditorInfo
            # but we can also use a custom handler that prints.
            # We'll just use a handler that writes to sys.stdout; Maya captures it.
            pass
        except:
            pass

    def _silence_third_party_loggers(self):
        """Reduce noise from third-party libraries."""
        for name in ["urllib3", "requests", "shiboken", "PySide"]:
            logging.getLogger(name).setLevel(logging.WARNING)

    # ----------------------------------------------------------------------
    # Path Utilities
    # ----------------------------------------------------------------------

    @staticmethod
    def _get_log_directory() -> Path:
        """Get the directory where log files should be stored."""
        if MAYA_AVAILABLE:
            prefs = cmds.internalVar(userPrefDir=True)
            return Path(prefs) / "maya_faceit" / "logs"
        return Path.home() / ".maya_faceit" / "logs"

    # ----------------------------------------------------------------------
    # Logging API
    # ----------------------------------------------------------------------

    def set_level(self, level: str):
        """Set the logging level for console."""
        level = level.upper()
        if level in LEVELS:
            self._logger.setLevel(LEVELS[level])
            self._logger.info(f"Log level set to {level}")
        else:
            self._logger.warning(f"Unknown log level: {level}")

    def debug(self, message: str):
        self._logger.debug(message)

    def info(self, message: str):
        self._logger.info(message)

    def warning(self, message: str):
        self._logger.warning(message)

    def error(self, message: str):
        self._logger.error(message)

    def critical(self, message: str):
        self._logger.critical(message)

    def exception(self, message: str):
        self._logger.exception(message)

    def log(self, level: str, message: str):
        """Generic log method with level as string."""
        level = level.upper()
        if level in LEVELS:
            self._logger.log(LEVELS[level], message)
        else:
            self._logger.info(message)

    # ----------------------------------------------------------------------
    # Context Manager / Decorator Helpers
    # ----------------------------------------------------------------------

    def timeit(self, func):
        """
        Decorator to log the execution time of a function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            self.info(
                f"{func.__module__}.{func.__name__} "
                f"completed in {elapsed:.4f} sec"
            )
            return result
        return wrapper

    # ----------------------------------------------------------------------
    # Maya Script Editor Output
    # ----------------------------------------------------------------------

    def to_script_editor(self, message: str, level: str = "info"):
        """Print a message directly to Maya's Script Editor."""
        if MAYA_AVAILABLE:
            try:
                # Maya's script editor prints to stdout, so it will appear.
                print(f"[Faceit] {message}")
            except:
                pass
        else:
            print(f"[Faceit] {message}")

    # ----------------------------------------------------------------------
    # Progress / Status
    # ----------------------------------------------------------------------

    def progress(self, current: int, total: int, message: str = ""):
        """Log a progress update."""
        percent = (current / total * 100) if total > 0 else 0
        if message:
            self.info(f"Progress: {percent:.1f}% - {message}")
        else:
            self.info(f"Progress: {percent:.1f}%")


# -----------------------------------------------------------------------------
# Global Logger Instance
# -----------------------------------------------------------------------------

log = FaceitLogger()


# -----------------------------------------------------------------------------
# Profile Decorator (Backward Compatibility)
# -----------------------------------------------------------------------------

def profile(func):
    """
    Decorator alias for logging execution time.

    Usage:
        @profile
        def my_function():
            ...
    """
    return log.timeit(func)


__all__ = [
    "FaceitLogger",
    "log",
    "profile",
]