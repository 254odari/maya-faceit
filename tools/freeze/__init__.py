# -*- coding: utf-8 -*-
"""
tools/freeze
~~~~~~~~~~~~

Safe transformation management engine for Maya FaceIT.

Provides rig-aware freezing of transforms, pivots, controllers, meshes,
and complete facial rigs while preserving deformation networks,
constraints, animation, and controller behavior.

Usage:
    from maya_faceit.tools.freeze import FreezeEngine
    freeze = FreezeEngine()
    report = freeze.freeze_selected()
    print(report.summary())
"""

from .types import (
    FreezeType,
    FreezeMode,
    FreezeScope,
    FreezeChannel,
    FreezeResult,
    TransformFreeze,
    PivotFreeze,
    ControllerFreeze,
    RigFreeze,
    MeshFreeze,
    FreezeReport,
)
from .settings import FreezeSettings, DEFAULT_FREEZE_SETTINGS
from .engine import FreezeEngine, freeze
from .transforms import TransformFreezer
from .pivots import PivotFreezer
from .controllers import ControllerFreezer
from .rig import RigFreezer
from .mesh import MeshFreezer
from .validation import FreezeValidator
from .reporter import FreezeReporter

__all__ = [
    # Types
    "FreezeType",
    "FreezeMode",
    "FreezeScope",
    "FreezeChannel",
    "FreezeResult",
    "TransformFreeze",
    "PivotFreeze",
    "ControllerFreeze",
    "RigFreeze",
    "MeshFreeze",
    "FreezeReport",
    # Settings
    "FreezeSettings",
    "DEFAULT_FREEZE_SETTINGS",
    # Engine
    "FreezeEngine",
    "freeze",
    # Subsystems
    "TransformFreezer",
    "PivotFreezer",
    "ControllerFreezer",
    "RigFreezer",
    "MeshFreezer",
    "FreezeValidator",
    "FreezeReporter",
]