# ui/widgets/buttons.py

"""
ui/widgets/buttons.py

Custom button widgets.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QPushButton, QToolButton, QIcon, QSize, QtGui


class IconButton(QPushButton):
    """Button with icon and optional text."""
    def __init__(self, icon_path: str = "", text: str = "", parent=None):
        super().__init__(text, parent)
        if icon_path:
            self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(16, 16))


class ToggleButton(QPushButton):
    """Toggle button with checked state."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)


class ActionButton(QPushButton):
    """Button with a specific action and tooltip."""
    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        if tooltip:
            self.setToolTip(tooltip)