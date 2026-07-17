# -*- coding: utf-8 -*-
"""
tools/relax/mesh.py

Mesh relaxation.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import math
from typing import List, Optional, Set, Dict, Tuple
from .types import RelaxReport, RelaxMode
from .engine import RelaxEngine


class MeshRelaxer:
    """
    Relax polygon meshes.
    """

    def __init__(self, engine: RelaxEngine):
        self.engine = engine
        self._adjacency_cache = {}

    def relax(self, mesh: str, vertices: Optional[List[int]] = None) -> RelaxReport:
        """
        Relax a mesh (or selected vertices).
        Returns report.
        """
        report = RelaxReport(mode=RelaxMode.MESH)
        if not cmds.objExists(mesh):
            report.errors.append(f"Mesh '{mesh}' does not exist.")
            report.success = False
            return report

        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)

        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        num_vertices = len(points)

        adj = self._build_adjacency(fn_mesh)

        if vertices:
            vertex_indices = [i for i in vertices if 0 <= i < num_vertices]
            if not vertex_indices:
                report.errors.append("No valid vertex indices provided.")
                report.success = False
                return report
            mask = set(vertex_indices)
        else:
            mask = None

        boundary = set()
        if self.engine.settings.preserve_border:
            boundary = self._detect_boundary(fn_mesh)

        start_time = time.time()
        current_points = [(p.x, p.y, p.z) for p in points]
        total_displacement = 0.0
        max_displacement = 0.0

        for _ in range(self.engine.settings.iterations):
            relaxed = self.engine.relax_points(current_points, adj, boundary)
            if mask:
                for i in mask:
                    dx = relaxed[i][0] - current_points[i][0]
                    dy = relaxed[i][1] - current_points[i][1]
                    dz = relaxed[i][2] - current_points[i][2]
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    total_displacement += dist
                    if dist > max_displacement:
                        max_displacement = dist
                for i in range(num_vertices):
                    if i not in mask:
                        relaxed[i] = current_points[i]
            else:
                for i, (old, new) in enumerate(zip(current_points, relaxed)):
                    dx = new[0] - old[0]
                    dy = new[1] - old[1]
                    dz = new[2] - old[2]
                    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    total_displacement += dist
                    if dist > max_displacement:
                        max_displacement = dist
            current_points = relaxed

        new_points = om2.MPointArray()
        for p in current_points:
            new_points.append(om2.MPoint(p[0], p[1], p[2]))
        fn_mesh.setPoints(new_points, om2.MSpace.kWorld)

        report.iterations = self.engine.settings.iterations
        report.processed_vertices = len(mask) if mask else num_vertices
        report.average_displacement = total_displacement / (report.processed_vertices * max(1, self.engine.settings.iterations)) if report.processed_vertices else 0.0
        report.max_displacement = max_displacement
        report.time_ms = (time.time() - start_time) * 1000
        report.success = True
        return report

    def _build_adjacency(self, fn_mesh: om2.MFnMesh) -> Dict[int, List[int]]:
        num_vertices = fn_mesh.numVertices()
        adj = {i: [] for i in range(num_vertices)}
        for i in range(num_vertices):
            connected = fn_mesh.getConnectedVertices(i)
            adj[i] = list(set(connected))
        return adj

    def _detect_boundary(self, fn_mesh: om2.MFnMesh) -> Set[int]:
        boundary = set()
        edge_vertices = fn_mesh.getEdges()
        num_edges = len(edge_vertices) // 2
        for e in range(num_edges):
            faces = fn_mesh.getFacesForEdge(e)
            if len(faces) == 1:
                v1 = edge_vertices[2*e]
                v2 = edge_vertices[2*e+1]
                boundary.add(v1)
                boundary.add(v2)
        return boundary