# -*- coding: utf-8 -*-
"""
tools/controllers
~~~~~~~~~~~~~~~~~

Controller management toolkit for Maya FaceIT.

Provides creation, editing, mirroring, attribute management, and
shape operations for facial controllers.

Public API:
    - ControllerEngine: Main facade for all controller operations.
    - ControllerTools: Alias for ControllerEngine.
    - ControllerEditor: Low-level controller editing.
    - ControllerTypes: Enums and dataclasses.
    - ControllerSettings: Configuration.
"""

from .types import (
    ControllerType,
    ControllerState,
    ControllerShape,
    ControllerAxis,
    ControllerAttribute,
    ControllerInfo,
    ControllerPair,
    ControllerStats,
)
from .settings import ControllerSettings, DEFAULT_CONTROLLER_SETTINGS
from .engine import ControllerEngine, controller

__all__ = [
    # Types
    "ControllerType",
    "ControllerState",
    "ControllerShape",
    "ControllerAxis",
    "ControllerAttribute",
    "ControllerInfo",
    "ControllerPair",
    "ControllerStats",
    # Settings
    "ControllerSettings",
    "DEFAULT_CONTROLLER_SETTINGS",
    # Engine
    "ControllerEngine",
    "controller",
]