# -*- coding: utf-8 -*-
"""
validation/symmetry.py

Symmetry validation for meshes, controllers, and joints.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Optional, Tuple, Dict, Set
from .naming import ValidationResult, IssueSeverity


class SymmetryValidator:
    """
    Validate left-right symmetry of meshes, controllers, and joints.
    """

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    # =========================================================================
    # GENERAL SYMMETRY CHECKS
    # =========================================================================

    def validate_mesh_symmetry(self, mesh: str, axis: str = "x",
                               tolerance: float = 0.001) -> ValidationResult:
        """
        Validate that a mesh is symmetric across a given axis.

        Args:
            mesh: Mesh name.
            axis: "x", "y", or "z" – the symmetry axis.
            tolerance: Maximum distance tolerance.

        Returns:
            ValidationResult with issues found.
        """
        result = ValidationResult()
        if not cmds.objExists(mesh):
            result.add_error(f"Mesh '{mesh}' does not exist.")
            return result

        # Get vertex positions
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if not verts:
            result.add_error(f"Mesh '{mesh}' has no vertices.")
            return result

        positions = cmds.xform(verts, q=True, ws=True, t=True)
        # positions is a flat list: [x0,y0,z0, x1,y1,z1, ...]
        count = len(positions) // 3
        if count == 0:
            result.add_error("No vertex positions found.")
            return result

        # Build point list
        pts = [(positions[i], positions[i+1], positions[i+2]) for i in range(0, len(positions), 3)]

        # Check each vertex against its mirror
        axis_idx = {"x": 0, "y": 1, "z": 2}[axis]
        asymmetric_vertices = 0
        max_dist = 0.0
        for i, p in enumerate(pts):
            # Reflect point across symmetry plane (assumes plane at 0)
            reflected = list(p)
            reflected[axis_idx] = -p[axis_idx]
            # Find nearest neighbor
            min_dist = float('inf')
            for j, q in enumerate(pts):
                if j == i:
                    continue
                dx = reflected[0] - q[0]
                dy = reflected[1] - q[1]
                dz = reflected[2] - q[2]
                dist = dx*dx + dy*dy + dz*dz
                if dist < min_dist:
                    min_dist = dist
            min_dist = min_dist ** 0.5
            if min_dist > tolerance:
                asymmetric_vertices += 1
                if min_dist > max_dist:
                    max_dist = min_dist

        if asymmetric_vertices > 0:
            result.add_warning(
                f"Mesh '{mesh}' has {asymmetric_vertices} asymmetric vertices "
                f"(max distance: {max_dist:.4f})."
            )
        else:
            result.add_info(f"Mesh '{mesh}' is perfectly symmetric within {tolerance} tolerance.")

        return result

    # =========================================================================
    # CONTROLLER SYMMETRY
    # =========================================================================

    def validate_controller_symmetry(self, controllers: List[str],
                                     naming_rules: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate that controllers have symmetric counterparts.

        Args:
            controllers: List of controller names to check.
            naming_rules: List of naming patterns (e.g., "L_", "R_").

        Returns:
            ValidationResult with missing pairs.
        """
        result = ValidationResult()
        if not controllers:
            result.add_warning("No controllers provided for symmetry validation.")
            return result

        # Build side mapping
        side_map = {}
        for ctrl in controllers:
            side = self._detect_side(ctrl, naming_rules)
            if side:
                side_map[ctrl] = side

        # Group by base name (remove side prefix)
        groups: Dict[str, Dict[str, List[str]]] = {}
        for ctrl, side in side_map.items():
            base = self._get_base_name(ctrl, side)
            if base not in groups:
                groups[base] = {'L': [], 'R': [], 'C': []}
            groups[base][side].append(ctrl)

        # Check for missing pairs
        for base, sides in groups.items():
            if sides['L'] and not sides['R']:
                result.add_warning(f"Left controller for '{base}' has no right counterpart.")
            if sides['R'] and not sides['L']:
                result.add_warning(f"Right controller for '{base}' has no left counterpart.")
            # Also check for multiple controllers of the same side
            if len(sides['L']) > 1:
                result.add_warning(f"Multiple left controllers for '{base}': {sides['L']}")
            if len(sides['R']) > 1:
                result.add_warning(f"Multiple right controllers for '{base}': {sides['R']}")

        return result

    def _detect_side(self, name: str, naming_rules: Optional[List[str]] = None) -> Optional[str]:
        """Detect left/right side from naming conventions."""
        # Default patterns
        patterns = {
            'L': ['L_', 'Left', 'left', '_l', '.L', 'LF'],
            'R': ['R_', 'Right', 'right', '_r', '.R', 'RT'],
            'C': ['C_', 'Center', 'center', '_c', '.C', 'M_'],
        }
        # Apply user rules if provided
        if naming_rules:
            # Assume rules are lists of patterns for L and R
            pass

        for side, pats in patterns.items():
            for pat in pats:
                if pat in name:
                    return side
        return None

    def _get_base_name(self, name: str, side: str) -> str:
        """Remove side prefix/suffix to get base name."""
        # Remove common side indicators
        patterns = {
            'L': ['L_', 'Left', 'left', '_l', '.L', 'LF'],
            'R': ['R_', 'Right', 'right', '_r', '.R', 'RT'],
            'C': ['C_', 'Center', 'center', '_c', '.C', 'M_'],
        }
        for pat in patterns.get(side, []):
            if name.startswith(pat):
                return name[len(pat):]
            if name.endswith(pat):
                return name[:-len(pat)]
        return name