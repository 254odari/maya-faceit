# -*- coding: utf-8 -*-
"""
maya_faceit.utils.math
~~~~~~~~~~~~~~~~~~~~~~

General math utilities.
"""

import math
from typing import Tuple, List, Optional, Union
import maya.api.OpenMaya as om2 # type: ignore


class MathUtils:
    """Collection of common math functions."""

    @staticmethod
    def distance(p1: Tuple[float, float, float],
                 p2: Tuple[float, float, float]) -> float:
        """Euclidean distance between two points."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def distance2d(p1: Tuple[float, float],
                   p2: Tuple[float, float]) -> float:
        """Euclidean distance in 2D."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def centroid(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """Compute the centroid of a list of points."""
        if not points:
            return (0.0, 0.0, 0.0)
        n = len(points)
        sx = sum(p[0] for p in points)
        sy = sum(p[1] for p in points)
        sz = sum(p[2] for p in points)
        return (sx / n, sy / n, sz / n)

    @staticmethod
    def lerp(a: float, b: float, t: float) -> float:
        """Linear interpolation."""
        return a + (b - a) * t

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp a value between min and max."""
        return max(min_val, min(max_val, value))

    @staticmethod
    def smoothstep(edge0: float, edge1: float, x: float) -> float:
        """Hermite interpolation (smooth step)."""
        t = MathUtils.clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
        return t * t * (3 - 2 * t)

    @staticmethod
    def gaussian(x: float, sigma: float = 0.5) -> float:
        """Gaussian function."""
        return math.exp(-(x * x) / (2 * sigma * sigma))

    @staticmethod
    def angle_between_vectors(v1: Tuple[float, float, float],
                              v2: Tuple[float, float, float]) -> float:
        """Angle between two vectors in radians."""
        dot = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
        len1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
        if len1 * len2 == 0:
            return 0.0
        cos_angle = dot / (len1 * len2)
        cos_angle = MathUtils.clamp(cos_angle, -1.0, 1.0)
        return math.acos(cos_angle)

    @staticmethod
    def normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Normalize a vector."""
        length = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
        if length < 1e-12:
            return (0.0, 0.0, 0.0)
        return (v[0] / length, v[1] / length, v[2] / length)

    @staticmethod
    def cross(a: Tuple[float, float, float],
              b: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Cross product of two vectors."""
        return (
            a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]
        )

    @staticmethod
    def dot(a: Tuple[float, float, float],
            b: Tuple[float, float, float]) -> float:
        """Dot product."""
        return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]