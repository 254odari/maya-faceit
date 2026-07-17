# -*- coding: utf-8 -*-
"""
maya_faceit.ui.launcher

Launches the Maya FaceIT UI.
"""

from __future__ import annotations

import logging

from .qt_imports import get_maya_main_window

logger = logging.getLogger("maya_faceit.ui")

_window = None


def show():
    """
    Create or raise the main window.
    """

    global _window

    if _window is None:

        from .application.main_window import MainWindow

        _window = MainWindow(
            parent=get_maya_main_window()
        )

    _window.show()

    _window.raise_()

    _window.activateWindow()

    logger.info("Maya FaceIT UI launched.")

    return _window


def close():
    """
    Close the UI.
    """

    global _window

    if _window is None:
        return

    _window.close()

    _window.deleteLater()

    _window = None

    logger.info("Maya FaceIT UI closed.")


def instance():
    """
    Return the current window instance.
    """

    return _window


def is_running():

    return _window is not None