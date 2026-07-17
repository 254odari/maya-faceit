# -*- coding: utf-8 -*-
"""
tools/mesh/utils/math.py

Mesh_specific math utilities (vertices, edges, faces).
"""

import math
from typing import List, Tuple


class MeshMath:
    """Math utilities for mesh geometry."""

    @staticmethod
    def face_area(verts: List[Tuple[float, float, float]]) -> float:
        """Compute area of a polygon (assumes planar)."""
        if len(verts) < 3:
            return 0.0
        # Use triangle fan
        total = 0.0
        for i in range(1, len(verts) - 1):
            v1 = verts[i]
            v2 = verts[i + 1]
            # Triangle (verts[0], v1, v2)
            u = (v1[0] - verts[0][0], v1[1] - verts[0][1], v1[2] - verts[0][2])
            v = (v2[0] - verts[0][0], v2[1] - verts[0][1], v2[2] - verts[0][2])
            cross = (u[1] * v[2] - u[2] * v[1],
                     u[2] * v[0] - u[0] * v[2],
                     u[0] * v[1] - u[1] * v[0])
            total += 0.5 * math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
        return total

    @staticmethod
    def face_center(verts: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """Compute centroid of a polygon."""
        if not verts:
            return (0.0, 0.0, 0.0)
        n = len(verts)
        sx = sum(p[0] for p in verts)
        sy = sum(p[1] for p in verts)
        sz = sum(p[2] for p in verts)
        return (sx / n, sy / n, sz / n)

    @staticmethod
    def edge_length(p1: Tuple[float, float, float],
                    p2: Tuple[float, float, float]) -> float:
        """Compute Euclidean distance between two points."""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @staticmethod
    def vertex_valence(vertex_index: int, face_vertex_lists: List[List[int]]) -> int:
        """Compute valence (number of edges) of a vertex."""
        count = 0
        for fv in face_vertex_lists:
            if vertex_index in fv:
                count += 1
        return count