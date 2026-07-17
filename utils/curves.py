# -*- coding: utf-8 -*-
"""
maya_faceit.utils.curves
~~~~~~~~~~~~~~~~~~~~~~~~

NURBS curve utilities.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Tuple, Optional


class CurveUtils:
    """Utilities for working with NURBS curves."""

    @staticmethod
    def get_curve_points(curve: str) -> List[Tuple[float, float, float]]:
        """Get control point positions of a NURBS curve."""
        if not cmds.objExists(curve):
            return []
        cvs = cmds.getAttr(f"{curve}.controlPoints[*]")
        if not cvs:
            return []
        return [(cv[0], cv[1], cv[2]) for cv in cvs]

    @staticmethod
    def set_curve_points(curve: str, points: List[Tuple[float, float, float]]) -> bool:
        """Set control point positions of a NURBS curve."""
        if not cmds.objExists(curve):
            return False
        if len(points) != cmds.getAttr(f"{curve}.controlPoints", size=True):
            return False
        for i, p in enumerate(points):
            cmds.setAttr(f"{curve}.controlPoints[{i}]", p[0], p[1], p[2])
        return True

    @staticmethod
    def create_circle(radius: float = 1.0, center: Tuple[float, float, float] = (0, 0, 0),
                      axis: str = "y", name: str = "circle") -> str:
        """Create a NURBS circle."""
        result = cmds.circle(r=radius, nr=(axis == "x", axis == "y", axis == "z"), name=name)
        if result:
            cmds.move(center[0], center[1], center[2], result[0])
            return result[0]
        return ""

    @staticmethod
    def create_square(size: float = 1.0, center: Tuple[float, float, float] = (0, 0, 0),
                      name: str = "square") -> str:
        """Create a NURBS square (closed curve)."""
        # Create a square using curve points
        half = size / 2
        pts = [
            (-half, 0, -half),
            (-half, 0, half),
            (half, 0, half),
            (half, 0, -half),
            (-half, 0, -half),
        ]
        curve = cmds.curve(d=1, p=pts, name=name)
        cmds.move(center[0], center[1], center[2], curve)
        return curve

    @staticmethod
    def create_arrow(length: float = 1.0, head_length: float = 0.3,
                     head_width: float = 0.2, name: str = "arrow") -> str:
        """Create an arrow NURBS curve."""
        pts = [
            (0, 0, 0),
            (length - head_length, 0, 0),
            (length - head_length, 0, -head_width/2),
            (length, 0, 0),
            (length - head_length, 0, head_width/2),
            (length - head_length, 0, 0),
            (0, 0, 0),
        ]
        return cmds.curve(d=1, p=pts, name=name)

    @staticmethod
    def create_controller_shape(shape_type: str, size: float = 1.0,
                                name: str = "") -> str:
        """Create a controller shape (circle, square, arrow)."""
        shapes = {
            "circle": CurveUtils.create_circle,
            "square": CurveUtils.create_square,
            "arrow": CurveUtils.create_arrow,
        }
        if shape_type in shapes:
            return shapes[shape_type](size, name=name)
        return ""