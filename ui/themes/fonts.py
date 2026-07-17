# ui/themes/fonts.py

"""
ui/themes/fonts.py

Font manager for the UI.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from ..qt_imports import QtGui

logger = logging.getLogger(__name__)


class FontManager:
    """Centralized font management."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_default_font() -> Optional[QtGui.QFont]:
        """Return the default application font."""
        if QtGui:
            return QtGui.QFont("Segoe UI", 9)
        return None

    @staticmethod
    def get_header_font() -> Optional[QtGui.QFont]:
        """Return the header font (larger, bold)."""
        if QtGui:
            return QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold)
        return None

    @staticmethod
    def get_mono_font() -> Optional[QtGui.QFont]:
        """Return a monospace font for console/log."""
        if QtGui:
            return QtGui.QFont("Consolas", 9)
        return None

    @staticmethod
    def get_small_font() -> Optional[QtGui.QFont]:
        """Return a small font for status bars."""
        if QtGui:
            return QtGui.QFont("Segoe UI", 8)
        return None