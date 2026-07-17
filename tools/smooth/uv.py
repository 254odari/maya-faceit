# -*- coding: utf-8 -*-
"""
tools/smooth/uv.py

UV smoothing.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import math
from typing import List, Optional, Dict
from .types import SmoothSettings, SmoothReport, SmoothMode, SmoothStatistics


class UVSmoother:
    """
    Smooth UV coordinates.
    """

    def __init__(self, algorithm_engine, settings: SmoothSettings):
        self.engine = algorithm_engine
        self.settings = settings

    def smooth_uvs(self, mesh: str, uv_set: Optional[str] = None,
                   settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """Smooth UVs."""
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.UV)
        start = time.time()

        if not cmds.objExists(mesh):
            report.errors.append(f"Mesh '{mesh}' does not exist.")
            report.success = False
            return report

        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if not shape:
            report.errors.append("No shape found.")
            report.success = False
            return report

        if uv_set is None:
            uv_set = cmds.polyUVSet(shape, q=True, currentUVSet=True)[0]

        # Get UVs
        uvs = cmds.polyEditUV(shape, q=True, u=True, v=True, uvSet=uv_set)
        if not uvs:
            report.warnings.append("No UVs found.")
            report.success = True
            return report

        uv_points = [(uvs[i], uvs[i+1]) for i in range(0, len(uvs), 2)]
        num_uvs = len(uv_points)

        # Build UV adjacency via vertex-UV mapping
        sel = om2.MSelectionList()
        sel.add(shape)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        adj = self._build_uv_adjacency(fn_mesh, uv_set)

        total_delta = 0.0
        max_delta = 0.0
        for _ in range(settings.iterations):
            smoothed = uv_points[:]
            for i, uv in enumerate(uv_points):
                neighbors = adj.get(i, [])
                if not neighbors:
                    continue
                avg_u = sum(uv_points[n][0] for n in neighbors) / len(neighbors)
                avg_v = sum(uv_points[n][1] for n in neighbors) / len(neighbors)
                new_u = uv[0] + (avg_u - uv[0]) * settings.strength
                new_v = uv[1] + (avg_v - uv[1]) * settings.strength
                du = new_u - uv[0]
                dv = new_v - uv[1]
                total_delta += math.sqrt(du*du + dv*dv)
                if math.sqrt(du*du + dv*dv) > max_delta:
                    max_delta = math.sqrt(du*du + dv*dv)
                smoothed[i] = (new_u, new_v)
            uv_points = smoothed

        # Apply UVs
        new_uvs = []
        for u, v in uv_points:
            new_uvs.extend([u, v])
        cmds.polyEditUV(shape, u=new_uvs, v=None, uvSet=uv_set)

        stats = SmoothStatistics(
            processed_count=num_uvs,
            iterations=settings.iterations,
            average_delta=total_delta / (num_uvs * max(1, settings.iterations)) if num_uvs else 0.0,
            max_delta=max_delta,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report

    def _build_uv_adjacency(self, fn_mesh: om2.MFnMesh, uv_set: str) -> Dict[int, List[int]]:
        """Build adjacency between UVs that share vertices."""
        uv_ids = fn_mesh.getUVIndices(uv_set)
        num_uvs = len(fn_mesh.getUVs()[0])
        adj = {i: [] for i in range(num_uvs)}
        for v_id in range(fn_mesh.numVertices()):
            uv_id = uv_ids[v_id]
            connected_verts = fn_mesh.getConnectedVertices(v_id)
            for cv in connected_verts:
                cv_uv = uv_ids[cv]
                if cv_uv != uv_id and cv_uv not in adj[uv_id]:
                    adj[uv_id].append(cv_uv)
        return adj