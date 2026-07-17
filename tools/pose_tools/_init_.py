# -*- coding: utf-8 -*-
"""
tools/pose_tools
~~~~~~~~~~~~~~~~

Facial pose management for Maya FaceIT.

Provides:
- Creating and applying poses
- Pose library management (save/load/import/export)
- Pose blending and mirroring
- Validation

Usage:
    from maya_faceit.tools.pose_tools import PoseEngine
    poses = PoseEngine()
    poses.create("smile", controllers={"jaw_ctrl": 0.5})
    poses.apply("smile")
"""

from .types import (
    Pose,
    PoseCategory,
    PoseType,
    PoseState,
    PoseInfo,
    PoseAttribute,
    PoseBlendMode,
    PoseReport,
)
from .settings import PoseSettings, DEFAULT_POSE_SETTINGS
from .engine import PoseEngine, pose_tools
from .editor import PoseEditor
from .manager import PoseManager
from .blend import PoseBlender
from .mirror import PoseMirror
from .exporter import PoseExporter
from .validation import PoseValidator

__all__ = [
    # Types
    "Pose",
    "PoseCategory",
    "PoseType",
    "PoseState",
    "PoseInfo",
    "PoseAttribute",
    "PoseBlendMode",
    "PoseReport",
    # Settings
    "PoseSettings",
    "DEFAULT_POSE_SETTINGS",
    # Main Engine
    "PoseEngine",
    "pose_tools",
    # Subsystems
    "PoseEditor",
    "PoseManager",
    "PoseBlender",
    "PoseMirror",
    "PoseExporter",
    "PoseValidator",
]