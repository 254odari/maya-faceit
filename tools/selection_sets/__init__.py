# -*- coding: utf-8 -*-
"""
tools/selection_sets
~~~~~~~~~~~~~~~~~~~~

Named selection set management for Maya FaceIT.

Provides:
- Creation, deletion, and editing of named sets
- Support for vertex, edge, face, and object sets
- Export/import to JSON
- Validation

Usage:
    from maya_faceit.tools.selection_sets import SelectionSetEngine
    sets = SelectionSetEngine()
    sets.create("eye_verts", ["pCube1.vtx[10:20]"])
    sets.get_selection("eye_verts")
"""

from .types import (
    SelectionSetType,
    SelectionSetState,
    SetMemberType,
    SetInfo,
)
from .settings import SelectionSetSettings, DEFAULT_SETTINGS
from .engine import SelectionSetEngine, selection_sets
from .editor import SelectionSetEditor
from .manager import SetManager
from .exporter import SelectionSetExporter
from .validation import SelectionSetValidator

__all__ = [
    # Types
    "SelectionSetType",
    "SelectionSetState",
    "SetMemberType",
    "SetInfo",
    # Settings
    "SelectionSetSettings",
    "DEFAULT_SETTINGS",
    # Main Engine
    "SelectionSetEngine",
    "selection_sets",
    # Subsystems
    "SelectionSetEditor",
    "SetManager",
    "SelectionSetExporter",
    "SelectionSetValidator",
]