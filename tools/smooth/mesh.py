# -*- coding: utf-8 -*-
"""
tools/smooth/mesh.py

Mesh smoothing implementation.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import math
from typing import List, Tuple, Set, Dict, Optional
from .types import SmoothSettings, SmoothReport, SmoothMode, SmoothStatistics
from .algorithms import SmoothAlgorithmEngine


class MeshSmoother:
    """
    Smooth polygon meshes.
    """

    def __init__(self, algorithm_engine: SmoothAlgorithmEngine, settings: SmoothSettings):
        self.engine = algorithm_engine
        self.settings = settings

    def smooth(self, mesh: str, settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """
        Smooth a mesh.
        """
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.MESH)
        start = time.time()

        if not cmds.objExists(mesh):
            report.errors.append(f"Mesh '{mesh}' does not exist.")
            report.success = False
            return report

        # Get mesh data
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        num_vertices = len(points)

        # Build adjacency
        adj = self._build_adjacency(fn_mesh, num_vertices)

        # Detect boundary
        boundary = set()
        if settings.preserve_border:
            boundary = self._detect_boundary(fn_mesh)

        # Prepare point list
        current_points = [(p.x, p.y, p.z) for p in points]

        total_delta = 0.0
        max_delta = 0.0

        # Apply iterations
        for _ in range(settings.iterations):
            smoothed = self.engine.smooth_points(current_points, adj, boundary)
            # Compute deltas
            for i, (old, new) in enumerate(zip(current_points, smoothed)):
                dx = new[0] - old[0]
                dy = new[1] - old[1]
                dz = new[2] - old[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                total_delta += dist
                if dist > max_delta:
                    max_delta = dist
            current_points = smoothed

        # Apply to mesh
        new_points = om2.MPointArray()
        for p in current_points:
            new_points.append(om2.MPoint(p[0], p[1], p[2]))
        fn_mesh.setPoints(new_points, om2.MSpace.kWorld)

        # Build report
        stats = SmoothStatistics(
            processed_count=num_vertices,
            iterations=settings.iterations,
            average_delta=total_delta / (num_vertices * max(1, settings.iterations)) if num_vertices else 0.0,
            max_delta=max_delta,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report

    def _build_adjacency(self, fn_mesh: om2.MFnMesh, num_vertices: int) -> Dict[int, List[int]]:
        """Build vertex adjacency."""
        adj = {i: [] for i in range(num_vertices)}
        for i in range(num_vertices):
            connected = fn_mesh.getConnectedVertices(i)
            adj[i] = list(set(connected))
        return adj

    def _detect_boundary(self, fn_mesh: om2.MFnMesh) -> Set[int]:
        """Detect boundary vertices."""
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