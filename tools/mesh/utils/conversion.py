# -*- coding: utf-8 -*-
"""
tools/mesh/utils/conversion.py

Conversion utilities between Maya (OpenMaya) and Python/NumPy.
"""

import numpy as np
from typing import List, Tuple, Optional, Union
import maya.api.OpenMaya as om2 # type: ignore


class ConversionUtils:
    """Convert between Maya data structures and Python/NumPy."""

    @staticmethod
    def mpoint_to_tuple(p: om2.MPoint) -> Tuple[float, float, float]:
        """Convert MPoint to tuple."""
        return (p.x, p.y, p.z)

    @staticmethod
    def tuple_to_mpoint(t: Tuple[float, float, float]) -> om2.MPoint:
        """Convert tuple to MPoint."""
        return om2.MPoint(t[0], t[1], t[2])

    @staticmethod
    def mpoint_array_to_list(points: om2.MPointArray) -> List[Tuple[float, float, float]]:
        """Convert MPointArray to list of tuples."""
        return [(points[i].x, points[i].y, points[i].z) for i in range(points.length())]

    @staticmethod
    def list_to_mpoint_array(pts: List[Tuple[float, float, float]]) -> om2.MPointArray:
        """Convert list of tuples to MPointArray."""
        arr = om2.MPointArray()
        for p in pts:
            arr.append(om2.MPoint(p[0], p[1], p[2]))
        return arr

    @staticmethod
    def mpoint_array_to_numpy(points: om2.MPointArray) -> np.ndarray:
        """Convert MPointArray to numpy array (Nx3)."""
        arr = np.zeros((points.length(), 3))
        for i in range(points.length()):
            arr[i] = [points[i].x, points[i].y, points[i].z]
        return arr

    @staticmethod
    def numpy_to_mpoint_array(arr: np.ndarray) -> om2.MPointArray:
        """Convert numpy array to MPointArray."""
        pts = om2.MPointArray()
        for row in arr:
            pts.append(om2.MPoint(row[0], row[1], row[2]))
        return pts

    @staticmethod
    def mmatrix_to_list(m: om2.MMatrix) -> List[float]:
        """Convert MMatrix to flat list (row-major)."""
        return [m.getElement(i, j) for i in range(4) for j in range(4)]

    @staticmethod
    def list_to_mmatrix(data: List[float]) -> om2.MMatrix:
        """Convert flat list to MMatrix."""
        m = om2.MMatrix()
        for i in range(4):
            for j in range(4):
                m.setElement(i, j, data[i * 4 + j])
        return m