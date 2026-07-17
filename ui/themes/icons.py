# ui/themes/icons.py

"""
ui/themes/icons.py

Icon manager for the UI.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from ..qt_imports import QtGui

logger = logging.getLogger(__name__)


class IconManager:
    """Manages icons for the application."""
    _instance = None
    _icon_cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_icon(name: str, size: int = 16) -> Optional[QtGui.QIcon]:
        """
        Get an icon by name. Searches in resources/icons/.
        """
        if not QtGui:
            return None

        # Check cache
        cache_key = f"{name}_{size}"
        if cache_key in IconManager._icon_cache:
            return IconManager._icon_cache[cache_key]

        # Try to find icon in various locations
        icon_paths = [
            f":/icons/{name}.png",
            f":/icons/{name}.svg",
            f"resources/icons/{name}.png",
            f"resources/icons/{name}.svg",
            os.path.join(os.path.dirname(__file__), "..", "resources", "icons", f"{name}.png"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "icons", f"{name}.svg"),
        ]

        for path in icon_paths:
            if os.path.exists(path) or path.startswith(":"):
                icon = QtGui.QIcon(path)
                if not icon.isNull():
                    # Optionally scale to size
                    if size != 16:
                        pixmap = icon.pixmap(size, size)
                        icon = QtGui.QIcon(pixmap)
                    IconManager._icon_cache[cache_key] = icon
                    return icon

        # Fallback: create a colored square for missing icons
        try:
            pixmap = QtGui.QPixmap(size, size)
            pixmap.fill(QtGui.QColor("#4a90d9"))
            icon = QtGui.QIcon(pixmap)
            IconManager._icon_cache[cache_key] = icon
            return icon
        except Exception as e:
            logger.debug(f"Failed to create fallback icon: {e}")
            return None

    @staticmethod
    def get_pixmap(name: str, size: int = 16) -> Optional[QtGui.QPixmap]:
        """Get a pixmap directly."""
        icon = IconManager.get_icon(name, size)
        if icon:
            return icon.pixmap(size, size)
        return None