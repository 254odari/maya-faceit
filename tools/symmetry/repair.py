# -*- coding: utf-8 -*-
"""
tools/symmetry/repair.py

Symmetry repair tools.
"""

import math
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Optional, List
from .types import SymmetrySettings, VertexPair, SymmetryAxis


class SymmetryRepair:
    """
    Repair tools for symmetry issues.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings

    def snap_asymmetric_vertices(self, mesh: str, vertex_map: List[VertexPair],
                                 tolerance: Optional[float] = None) -> int:
        if not cmds.objExists(mesh):
            return 0
        if tolerance is None:
            tolerance = self.settings.tolerance

        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)

        repaired = 0
        for pair in vertex_map:
            if pair.vertex2 != -1:
                continue
            min_dist = float('inf')
            best_idx = -1
            for other in vertex_map:
                if other.vertex2 == -1 or other.vertex1 == pair.vertex1:
                    continue
                p1 = points[pair.vertex1]
                p2 = points[other.vertex1]
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                if dist < min_dist:
                    min_dist = dist
                    best_idx = other.vertex1
            if best_idx != -1:
                axis = self.settings.axis
                p = points[best_idx]
                if axis == SymmetryAxis.X:
                    new_p = om2.MPoint(-p.x, p.y, p.z)
                elif axis == SymmetryAxis.Y:
                    new_p = om2.MPoint(p.x, -p.y, p.z)
                else:
                    new_p = om2.MPoint(p.x, p.y, -p.z)
                points[pair.vertex1] = new_p
                repaired += 1

        if repaired > 0:
            fn_mesh.setPoints(points, om2.MSpace.kWorld)

        return repaired