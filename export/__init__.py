# -*- coding: utf-8 -*-
"""
maya_faceit.export
~~~~~~~~~~~~~~~~~~

Unified export system for Maya FaceIT.

Supports multiple formats (FBX, USD, Alembic, JSON, Maya ASCII) and
game engine integration (Unreal, Unity, MetaHuman) with packaging.

Usage:
    from maya_faceit.export import ExportEngine
    exporter = ExportEngine()
    exporter.export("fbx", scene_objects=["pCube1"], filepath="output.fbx")
"""

from .types import (
    ExportFormat,
    ExportMode,
    EngineType,
    PackageType,
    ExportSettings,
    ExportResult,
    ExportReport,
)
from .settings import DEFAULT_EXPORT_SETTINGS
from .engine import ExportEngine, get_exporter

# Format submodules are imported dynamically in engine
__all__ = [
    "ExportFormat",
    "ExportMode",
    "EngineType",
    "PackageType",
    "ExportSettings",
    "ExportResult",
    "ExportReport",
    "DEFAULT_EXPORT_SETTINGS",
    "ExportEngine",
    "get_exporter",
]