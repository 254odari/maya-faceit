# -*- coding: utf-8 -*-
"""
tools/clean
~~~~~~~~~~~

Scene cleanup and optimization engine for Maya FaceIT.

Safely removes unnecessary data, repairs common scene issues,
optimizes performance, and prepares assets for rigging, animation,
export, or publishing.

Usage:
    from maya_faceit.tools.clean import CleanEngine
    clean = CleanEngine()
    report = clean.cleanup_all()
    print(report.summary())
"""

from .types import (
    CleanupType,
    CleanupMode,
    HistoryMode,
    ReferenceMode,
    CleanupResult,
    SceneCleanup,
    MeshCleanup,
    MaterialCleanup,
    AnimationCleanup,
    RigCleanup,
    BlendshapeCleanup,
    NamespaceCleanup,
    CleanupReport,
)
from .settings import CleanupSettings, DEFAULT_CLEANUP_SETTINGS
from .engine import CleanEngine, clean
from .scene import SceneCleaner
from .mesh import MeshCleaner
from .materials import MaterialCleaner
from .animation import AnimationCleaner
from .rig import RigCleaner
from .blendshape import BlendshapeCleaner
from .namespace import NamespaceCleaner
from .reporter import CleanupReporter

__all__ = [
    # Types
    "CleanupType",
    "CleanupMode",
    "HistoryMode",
    "ReferenceMode",
    "CleanupResult",
    "SceneCleanup",
    "MeshCleanup",
    "MaterialCleanup",
    "AnimationCleanup",
    "RigCleanup",
    "BlendshapeCleanup",
    "NamespaceCleanup",
    "CleanupReport",
    # Settings
    "CleanupSettings",
    "DEFAULT_CLEANUP_SETTINGS",
    # Engine
    "CleanEngine",
    "clean",
    # Subsystems
    "SceneCleaner",
    "MeshCleaner",
    "MaterialCleaner",
    "AnimationCleaner",
    "RigCleaner",
    "BlendshapeCleaner",
    "NamespaceCleaner",
    "CleanupReporter",
]