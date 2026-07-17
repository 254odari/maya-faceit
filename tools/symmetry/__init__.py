# -*- coding: utf-8 -*-
"""
tools/symmetry
~~~~~~~~~~~~~~

Core symmetry analysis engine for Maya FaceIT.

Discover, validate, and maintain symmetry relationships across meshes,
controllers, joints, and blendshapes.

Usage:
    from maya_faceit.tools.symmetry import SymmetryAnalyzer
    analyzer = SymmetryAnalyzer()
    map_data = analyzer.build_map("pCube1")
"""

from .types import (
    SymmetryAxis,
    SymmetryStatus,
    MatchMethod,
    SymmetryScope,
    SymmetrySettings,
    SymmetryPlane,
    VertexPair,
    ControllerPair,
    JointPair,
    BlendshapePair,
    SymmetryMap,
    SymmetryReport,
    ValidationResult,
)
from .settings import DEFAULT_SYMMETRY_SETTINGS
from .engine import SymmetryAnalyzer, get_analyzer
from .api import (
    detect_plane,
    build_symmetry_map,
    analyze_symmetry,
    validate_symmetry,
    repair_symmetry,
    generate_symmetry_report,
    get_mirror_name,
)

__all__ = [
    # Types
    "SymmetryAxis",
    "SymmetryStatus",
    "MatchMethod",
    "SymmetryScope",
    "SymmetrySettings",
    "SymmetryPlane",
    "VertexPair",
    "ControllerPair",
    "JointPair",
    "BlendshapePair",
    "SymmetryMap",
    "SymmetryReport",
    "ValidationResult",
    # Settings
    "DEFAULT_SYMMETRY_SETTINGS",
    # Main class & singleton
    "SymmetryAnalyzer",
    "get_analyzer",
    # Convenience functions
    "detect_plane",
    "build_symmetry_map",
    "analyze_symmetry",
    "validate_symmetry",
    "repair_symmetry",
    "generate_symmetry_report",
    "get_mirror_name",
]