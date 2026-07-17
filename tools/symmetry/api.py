# -*- coding: utf-8 -*-
"""
tools/symmetry/api.py

Convenience functions for symmetry operations.
"""

from typing import Optional, Dict, Any, List
from .types import SymmetryAxis, SymmetryPlane, SymmetryMap, SymmetryReport, ValidationResult, SymmetrySettings
from .engine import get_analyzer
from .controller import ControllerMapper


def detect_plane(mesh: str, axis: SymmetryAxis = SymmetryAxis.X) -> Optional[SymmetryPlane]:
    """Quick detect symmetry plane."""
    analyzer = get_analyzer()
    analyzer.settings.axis = axis
    return analyzer.detect_plane(mesh)


def build_symmetry_map(mesh: str) -> Optional[SymmetryMap]:
    """Quick build symmetry map."""
    analyzer = get_analyzer()
    return analyzer.build_map(mesh)


def analyze_symmetry(mesh: str) -> Dict[str, Any]:
    """Quick mesh symmetry analysis."""
    analyzer = get_analyzer()
    return analyzer.analyze_mesh(mesh)


def validate_symmetry(mesh: str) -> ValidationResult:
    """Quick symmetry validation."""
    analyzer = get_analyzer()
    return analyzer.validate(mesh)


def repair_symmetry(mesh: str) -> int:
    """Quick symmetry repair."""
    analyzer = get_analyzer()
    return analyzer.repair(mesh)


def generate_symmetry_report(mesh: str) -> Optional[SymmetryReport]:
    """Quick symmetry report."""
    analyzer = get_analyzer()
    return analyzer.report(mesh)


def get_mirror_name(node: str) -> Optional[str]:
    """Get mirror counterpart name using symmetry naming rules."""
    mapper = ControllerMapper(SymmetrySettings())
    pairs = mapper._fallback_mapping([node])
    if pairs and pairs[0].target:
        return pairs[0].target
    return None