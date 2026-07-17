# -*- coding: utf-8 -*-
"""
tools/mesh/utils/symmetry.py

Symmetry detection and enforcement for meshes.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Tuple
from ...symmetry import SymmetryAnalyzer, SymmetryAxis


class MeshSymmetry:
    """Symmetry utilities for meshes."""

    def __init__(self):
        self.analyzer = SymmetryAnalyzer()

    def detect_plane(self, mesh: str, axis: SymmetryAxis = SymmetryAxis.X) -> Optional[Tuple[float, float, float]]:
        """
        Detect symmetry plane center along the given axis.
        Returns (cx, cy, cz) of the plane.
        """
        plane = self.analyzer.detect_plane(mesh, axis)
        if plane:
            return plane.center
        return None

    def build_vertex_map(self, mesh: str) -> List[Tuple[int, int]]:
        """
        Build vertex pairs (source, target) for symmetry.
        Returns list of (vertex1, vertex2) pairs.
        """
        map_data = self.analyzer.build_map(mesh)
        if map_data:
            return [(v.vertex1, v.vertex2) for v in map_data.vertices if v.vertex2 != -1]
        return []

    def snap_vertices(self, mesh: str, vertices: Optional[List[int]] = None) -> int:
        """
        Snap vertices to their mirror positions to enforce symmetry.
        Returns number of vertices snapped.
        """
        if vertices is None:
            vtx_count = cmds.polyEvaluate(mesh, vertex=True)
            vertices = list(range(vtx_count))

        plane_center = self.detect_plane(mesh)
        if not plane_center:
            return 0

        axis_idx = 0  # X axis
        pairs = self.build_vertex_map(mesh)
        mirror_map = {}
        for v1, v2 in pairs:
            mirror_map[v1] = v2
            mirror_map[v2] = v1

        snapped = 0
        for vidx in vertices:
            if vidx not in mirror_map:
                continue
            m = mirror_map[vidx]
            pos1 = cmds.xform(f"{mesh}.vtx[{vidx}]", q=True, ws=True, t=True)
            pos2 = cmds.xform(f"{mesh}.vtx[{m}]", q=True, ws=True, t=True)
            avg = list(pos1)
            avg[axis_idx] = (pos1[axis_idx] + pos2[axis_idx]) * 0.5
            cmds.xform(f"{mesh}.vtx[{vidx}]", ws=True, t=avg)
            cmds.xform(f"{mesh}.vtx[{m}]", ws=True, t=avg)
            snapped += 1
        return snapped