# -*- coding: utf-8 -*-
"""
tools/symmetry/vertex.py

Vertex mapping for symmetry.
"""

import math
import numpy as np
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Dict, Tuple, Optional
from .types import SymmetrySettings, SymmetryPlane, VertexPair
from .plane import SymmetryPlaneDetector


class VertexMapper:
    """
    Builds vertex correspondence maps for symmetric meshes.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings
        self._vertex_cache: Dict[str, List[VertexPair]] = {}

    def build_map(self, mesh: str, plane: Optional[SymmetryPlane] = None) -> List[VertexPair]:
        if not cmds.objExists(mesh):
            return []

        cache_key = f"{mesh}_{self.settings.axis.value}_{self.settings.tolerance}"
        if cache_key in self._vertex_cache:
            return self._vertex_cache[cache_key]

        if plane is None:
            plane = SymmetryPlaneDetector.detect_from_mesh(mesh, self.settings.axis)
            if plane is None:
                return []

        points = self._get_vertex_positions(mesh)
        if not points:
            return []

        pairs = []
        used = set()
        for i, p in enumerate(points):
            if i in used:
                continue
            reflected = self._reflect_point(p, plane)
            best_idx = -1
            best_dist = float('inf')
            for j, q in enumerate(points):
                if j == i or j in used:
                    continue
                dist = math.sqrt((reflected[0]-q[0])**2 + (reflected[1]-q[1])**2 + (reflected[2]-q[2])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = j
            if best_idx != -1 and best_dist <= self.settings.tolerance:
                pairs.append(VertexPair(vertex1=i, vertex2=best_idx, distance=best_dist, confidence=1.0))
                used.add(i)
                used.add(best_idx)
            else:
                pairs.append(VertexPair(vertex1=i, vertex2=-1, distance=0.0, confidence=0.0))

        self._vertex_cache[cache_key] = pairs
        return pairs

    def _get_vertex_positions(self, mesh: str) -> List[Tuple[float, float, float]]:
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        return [(p.x, p.y, p.z) for p in points]

    def _reflect_point(self, point: Tuple[float, float, float], plane: SymmetryPlane) -> Tuple[float, float, float]:
        p = np.array(point)
        c = np.array(plane.center)
        n = np.array(plane.normal)
        n = n / np.linalg.norm(n)
        d = np.dot(p - c, n)
        reflected = p - 2 * d * n
        return (reflected[0], reflected[1], reflected[2])

    def clear_cache(self):
        self._vertex_cache.clear()