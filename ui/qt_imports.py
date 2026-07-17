# -*- coding: utf-8 -*-
"""
maya_faceit.ui.qt_imports

Central Qt compatibility layer.

Supports

    Maya 2026 (PySide6)
    Maya 2025/2024 (PySide2)
"""

from __future__ import annotations

import logging

logger = logging.getLogger("maya_faceit.ui")

QT_BINDING = None

QtCore = None
QtGui = None
QtWidgets = None

Qt = None
Signal = None
Slot = None
Property = None

wrapInstance = None


# ---------------------------------------------------------
# PySide6
# ---------------------------------------------------------

try:

    from PySide6 import QtCore
    from PySide6 import QtGui
    from PySide6 import QtWidgets

    from shiboken6 import wrapInstance

    QT_BINDING = "PySide6"

    Qt = QtCore.Qt
    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property

    logger.info("Using PySide6")

except Exception:

    try:

        from PySide2 import QtCore
        from PySide2 import QtGui
        from PySide2 import QtWidgets

        from shiboken2 import wrapInstance

        QT_BINDING = "PySide2"

        Qt = QtCore.Qt
        Signal = QtCore.Signal
        Slot = QtCore.Slot
        Property = QtCore.Property

        logger.info("Using PySide2")

    except Exception as exc:

        raise RuntimeError(
            "PySide6/PySide2 not available."
        ) from exc


QApplication = QtWidgets.QApplication


# ---------------------------------------------------------
# Maya Main Window
# ---------------------------------------------------------

def get_maya_main_window():

    from maya import OpenMayaUI

    ptr = OpenMayaUI.MQtUtil.mainWindow()

    if ptr is None:
        return None

    return wrapInstance(int(ptr), QtWidgets.QWidget)


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