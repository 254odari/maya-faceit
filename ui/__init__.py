# -*- coding: utf-8 -*-
"""
maya_faceit.ui

User Interface package.

Only lightweight imports should live here.
Avoid importing pages, widgets or windows to prevent circular imports.
"""

from __future__ import annotations

from .qt_imports import (
    QT_BINDING,
    QtCore,
    QtGui,
    QtWidgets,
    Qt,
    Signal,
    Slot,
    Property,
    QApplication,
    wrapInstance,
    get_maya_main_window,
)

__version__ = "1.0.0"

__all__ = [
    "QT_BINDING",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Qt",
    "Signal",
    "Slot",
    "Property",
    "QApplication",
    "wrapInstance",
    "get_maya_main_window",
]