"""
core/symmetry/symmetry.py

Symmetry engine for Maya Faceit.

Provides utilities for:

    • Detecting the symmetry plane
    • Mirroring transforms
    • Mirroring vertex positions
    • Finding mirrored objects
    • Left/Right naming
    • Symmetry validation

Author: Maya FaceIT Team
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import maya.cmds as cmds # type: ignore

from ..logging.logger import log
from ...exceptions import ValidationError


# -------------------------------------------------------------
# Constants
# -------------------------------------------------------------

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_Z = "Z"

VALID_AXES = {AXIS_X, AXIS_Y, AXIS_Z}


# -------------------------------------------------------------
# Dataclass
# -------------------------------------------------------------

@dataclass(slots=True)
class SymmetrySettings:
    """Settings for symmetry operations."""
    axis: str = AXIS_X
    tolerance: float = 0.0001
    positive_prefix: str = "L_"
    negative_prefix: str = "R_"


# -------------------------------------------------------------
# Symmetry Engine
# -------------------------------------------------------------

class SymmetryEngine:
    """
    Core symmetry engine for Maya Faceit.

    Handles naming, mirroring, and side detection for symmetric rigs.
    """

    def __init__(self):
        self.settings = SymmetrySettings()

    # ---------------------------------------------------------
    # Naming
    # ---------------------------------------------------------

    def mirror_name(self, node: str) -> str:
        """
        Mirror a node name.

        Examples:
            L_eye_ctrl -> R_eye_ctrl
            R_eye_ctrl -> L_eye_ctrl

        Returns:
            Mirrored name (or original if no side prefix found).
        """
        if node.startswith(self.settings.positive_prefix):
            return node.replace(
                self.settings.positive_prefix,
                self.settings.negative_prefix,
                1,
            )
        if node.startswith(self.settings.negative_prefix):
            return node.replace(
                self.settings.negative_prefix,
                self.settings.positive_prefix,
                1,
            )
        return node

    def side(self, node: str) -> str:
        """Return side of a node: 'L', 'R', or 'C' (center)."""
        if node.startswith("L_"):
            return "L"
        if node.startswith("R_"):
            return "R"
        return "C"

    # ---------------------------------------------------------
    # Queries
    # ---------------------------------------------------------

    def exists(self, node: str) -> bool:
        """Check if a node exists in the scene."""
        return cmds.objExists(node)

    def mirrored_node(self, node: str) -> Optional[str]:
        """Get the mirrored counterpart of a node if it exists."""
        mirror = self.mirror_name(node)
        if cmds.objExists(mirror):
            return mirror
        return None

    # ---------------------------------------------------------
    # Mirror Transforms
    # ---------------------------------------------------------

    def mirror_translation(self, node: str) -> None:
        """Mirror the translation of a node to its counterpart."""
        if not cmds.objExists(node):
            raise ValidationError(f"Node '{node}' does not exist.")

        pos = cmds.xform(node, q=True, ws=True, t=True)
        mirror = self.mirrored_node(node)
        if mirror is None:
            return

        cmds.xform(mirror, ws=True, t=(-pos[0], pos[1], pos[2]))

    def mirror_rotation(self, node: str) -> None:
        """Mirror the rotation of a node to its counterpart."""
        if not cmds.objExists(node):
            raise ValidationError(f"Node '{node}' does not exist.")

        rot = cmds.xform(node, q=True, ws=True, rotation=True)
        mirror = self.mirrored_node(node)
        if mirror is None:
            return

        cmds.xform(mirror, ws=True, rotation=(rot[0], -rot[1], -rot[2]))

    def mirror_transform(self, node: str) -> None:
        """Mirror both translation and rotation of a node."""
        self.mirror_translation(node)
        self.mirror_rotation(node)

    # ---------------------------------------------------------
    # Side Detection by Position
    # ---------------------------------------------------------

    def is_center(self, node: str) -> bool:
        """Check if a node is on the center axis (within tolerance)."""
        x = cmds.xform(node, q=True, ws=True, t=True)[0]
        return abs(x) <= self.settings.tolerance

    def is_left(self, node: str) -> bool:
        """Check if a node is on the left side (positive X)."""
        x = cmds.xform(node, q=True, ws=True, t=True)[0]
        return x > self.settings.tolerance

    def is_right(self, node: str) -> bool:
        """Check if a node is on the right side (negative X)."""
        x = cmds.xform(node, q=True, ws=True, t=True)[0]
        return x < -self.settings.tolerance

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    def validate_axis(self) -> None:
        """Validate that the current axis setting is valid."""
        if self.settings.axis not in VALID_AXES:
            raise ValidationError(
                f"Invalid symmetry axis: {self.settings.axis}"
            )

    def set_axis(self, axis: str) -> None:
        """Set the symmetry axis."""
        axis = axis.upper()
        if axis not in VALID_AXES:
            raise ValidationError(f"Invalid axis: {axis}")
        self.settings.axis = axis
        log.info(f"Symmetry axis set to {axis}")

    def set_tolerance(self, tolerance: float) -> None:
        """Set the tolerance for center detection."""
        self.settings.tolerance = abs(tolerance)

    def reset(self) -> None:
        """Reset symmetry settings to defaults."""
        self.settings = SymmetrySettings()
        log.info("Symmetry settings reset.")


# -------------------------------------------------------------
# Singleton
# -------------------------------------------------------------

symmetry = SymmetryEngine()