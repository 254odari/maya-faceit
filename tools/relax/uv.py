# -*- coding: utf-8 -*-
"""
tools/relax/uv.py

UV relaxation.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
from typing import List, Tuple, Dict, Optional
from .types import RelaxReport, RelaxMode


class UVRelaxer:
    """
    Relax UVs (reduce distortion, smooth UV shells).
    """

    def __init__(self, engine):
        self.engine = engine

    def relax_uvs(self, mesh: str, uv_set: Optional[str] = None) -> RelaxReport:
        """Relax UV coordinates using Laplacian smoothing on UV space."""
        report = RelaxReport(mode=RelaxMode.UV)
        if not cmds.objExists(mesh):
            report.errors.append(f"Mesh '{mesh}' does not exist.")
            report.success = False
            return report

        shapes = cmds.listRelatives(mesh, shapes=True) or []
        if not shapes:
            report.errors.append("Mesh has no shape.")
            return report
        shape = shapes[0]

        if uv_set is None:
            uv_set = cmds.polyUVSet(shape, q=True, currentUVSet=True)[0]

        uvs = cmds.polyEditUV(shape, q=True, u=True, v=True)
        if not uvs:
            report.errors.append("No UVs found.")
            return report

        uv_points = [(uvs[i], uvs[i+1]) for i in range(0, len(uvs), 2)]
        num_uvs = len(uv_points)

        sel = om2.MSelectionList()
        sel.add(shape)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)

        adj = self._build_uv_adjacency(fn_mesh, uv_set)
        relaxed = self._relax_uv_points(uv_points, adj)

        new_uvs = []
        for u, v in relaxed:
            new_uvs.extend([u, v])
        cmds.polyEditUV(shape, u=new_uvs, v=None)

        report.processed_vertices = num_uvs
        report.iterations = self.engine.settings.iterations
        report.success = True
        return report

    def _build_uv_adjacency(self, fn_mesh: om2.MFnMesh, uv_set: str) -> Dict[int, List[int]]:
        u_array, v_array = fn_mesh.getUVs(uv_set)
        num_uvs = len(u_array)
        adj = {i: [] for i in range(num_uvs)}
        uv_ids = fn_mesh.getUVIndices(uv_set)
        num_vertices = fn_mesh.numVertices()
        for v_id in range(num_vertices):
            uv_id = uv_ids[v_id]
            connected_verts = fn_mesh.getConnectedVertices(v_id)
            for cv in connected_verts:
                cv_uv = uv_ids[cv]
                if cv_uv != uv_id:
                    if cv_uv not in adj[uv_id]:
                        adj[uv_id].append(cv_uv)
        return adj

    def _relax_uv_points(self, uvs: List[Tuple[float, float]], adj: Dict[int, List[int]]) -> List[Tuple[float, float]]:
        if not uvs:
            return uvs
        strength = self.engine.settings.strength
        new_uvs = uvs[:]
        for _ in range(self.engine.settings.iterations):
            current = new_uvs[:]
            for i, uv in enumerate(current):
                neighbors = adj.get(i, [])
                if not neighbors:
                    continue
                avg_u = sum(current[n][0] for n in neighbors) / len(neighbors)
                avg_v = sum(current[n][1] for n in neighbors) / len(neighbors)
                new_uvs[i] = (
                    uv[0] + (avg_u - uv[0]) * strength,
                    uv[1] + (avg_v - uv[1]) * strength,
                )
        return new_uvs