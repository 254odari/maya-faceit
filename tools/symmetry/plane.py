# -*- coding: utf-8 -*-
"""
tools/symmetry/plane.py

Symmetry plane detection.
"""

import math
import numpy as np
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Tuple, Optional
from .types import SymmetryAxis, SymmetryPlane


class SymmetryPlaneDetector:
    """
    Detects the symmetry plane of a mesh or selection.
    """

    @staticmethod
    def detect_from_mesh(mesh: str, axis: SymmetryAxis = SymmetryAxis.X,
                         method: str = "bounding_box") -> Optional[SymmetryPlane]:
        """
        Detect symmetry plane from a mesh.
        Methods: 'bounding_box', 'centroid', 'pca', 'world_origin'.
        """
        if not cmds.objExists(mesh):
            return None

        points = SymmetryPlaneDetector._get_mesh_points(mesh)
        if not points:
            return None

        if method == "world_origin":
            center = (0.0, 0.0, 0.0)
        elif method == "centroid":
            center = SymmetryPlaneDetector._compute_centroid(points)
        elif method == "bounding_box":
            center = SymmetryPlaneDetector._compute_bounding_box_center(points)
        elif method == "pca":
            center, normal = SymmetryPlaneDetector._compute_pca_plane(points)
            axis = SymmetryPlaneDetector._closest_axis(normal)
            return SymmetryPlane(axis=axis, center=center, normal=normal, confidence=0.8, method="pca")
        else:
            return None

        if axis == SymmetryAxis.X:
            normal = (1.0, 0.0, 0.0)
        elif axis == SymmetryAxis.Y:
            normal = (0.0, 1.0, 0.0)
        else:
            normal = (0.0, 0.0, 1.0)

        confidence = SymmetryPlaneDetector._compute_symmetry_confidence(points, center, normal, axis)
        return SymmetryPlane(axis=axis, center=center, normal=normal, confidence=confidence, method=method)

    @staticmethod
    def _get_mesh_points(mesh: str) -> List[Tuple[float, float, float]]:
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        return [(p.x, p.y, p.z) for p in points]

    @staticmethod
    def _compute_centroid(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not points:
            return (0.0, 0.0, 0.0)
        n = len(points)
        sx = sum(p[0] for p in points)
        sy = sum(p[1] for p in points)
        sz = sum(p[2] for p in points)
        return (sx/n, sy/n, sz/n)

    @staticmethod
    def _compute_bounding_box_center(points: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        if not points:
            return (0.0, 0.0, 0.0)
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        min_z = min(p[2] for p in points)
        max_z = max(p[2] for p in points)
        return ((min_x+max_x)/2, (min_y+max_y)/2, (min_z+max_z)/2)

    @staticmethod
    def _compute_pca_plane(points: List[Tuple[float, float, float]]):
        if np is None:
            raise ImportError("numpy required for PCA method.")
        pts = np.array(points)
        centroid = pts.mean(axis=0)
        pts_centered = pts - centroid
        cov = np.cov(pts_centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        idx = np.argmin(eigenvalues)
        normal = eigenvectors[:, idx]
        if normal[0] < 0:
            normal = -normal
        return (centroid[0], centroid[1], centroid[2]), (normal[0], normal[1], normal[2])

    @staticmethod
    def _closest_axis(normal: Tuple[float, float, float]) -> SymmetryAxis:
        abs_n = [abs(normal[0]), abs(normal[1]), abs(normal[2])]
        idx = abs_n.index(max(abs_n))
        if idx == 0:
            return SymmetryAxis.X
        elif idx == 1:
            return SymmetryAxis.Y
        else:
            return SymmetryAxis.Z

    @staticmethod
    def _compute_symmetry_confidence(points: List[Tuple[float, float, float]],
                                     center: Tuple[float, float, float],
                                     normal: Tuple[float, float, float],
                                     axis: SymmetryAxis) -> float:
        if not points:
            return 0.0
        sample_size = min(500, len(points))
        sample_indices = range(0, len(points), max(1, len(points)//sample_size))
        total = 0
        within_tolerance = 0
        tolerance = 0.1
        for i in sample_indices:
            p = points[i]
            reflected = SymmetryPlaneDetector._reflect_point(p, center, normal)
            min_dist = float('inf')
            for j, q in enumerate(points):
                if j == i:
                    continue
                dist = math.sqrt((reflected[0]-q[0])**2 + (reflected[1]-q[1])**2 + (reflected[2]-q[2])**2)
                if dist < min_dist:
                    min_dist = dist
            total += 1
            if min_dist < tolerance:
                within_tolerance += 1
        return within_tolerance / total if total > 0 else 0.0

    @staticmethod
    def _reflect_point(point: Tuple[float, float, float],
                       center: Tuple[float, float, float],
                       normal: Tuple[float, float, float]) -> Tuple[float, float, float]:
        p = np.array(point)
        c = np.array(center)
        n = np.array(normal)
        n = n / np.linalg.norm(n)
        d = np.dot(p - c, n)
        reflected = p - 2 * d * n
        return (reflected[0], reflected[1], reflected[2])