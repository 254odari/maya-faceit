# -*- coding: utf-8 -*-
"""
tools/analysis/mesh.py

Mesh analysis.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Optional, Set
from .types import MeshStats, AnalysisScope, AnalysisLevel


class MeshAnalyzer:
    """
    Analyze mesh geometry and topology.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> MeshStats:
        """Analyze mesh statistics."""
        stats = MeshStats()

        # Get all meshes
        all_meshes = cmds.ls(type='mesh', long=True)
        mesh_transforms = set()
        for m in all_meshes:
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                mesh_transforms.add(parents[0])
        mesh_transforms = list(mesh_transforms)

        stats.total_meshes = len(mesh_transforms)
        if stats.total_meshes == 0:
            return stats

        total_vertices = 0
        total_edges = 0
        total_faces = 0
        total_triangles = 0
        total_ngons = 0
        total_non_manifold = 0
        total_lamina = 0
        total_borders = 0
        meshes_with_history = 0
        meshes_with_uvs = 0
        meshes_with_normals = 0
        max_vertices = 0
        max_faces = 0

        for mesh in mesh_transforms:
            try:
                v = cmds.polyEvaluate(mesh, vertex=True)
                e = cmds.polyEvaluate(mesh, edge=True)
                f = cmds.polyEvaluate(mesh, face=True)
                tri = cmds.polyEvaluate(mesh, triangle=True)

                total_vertices += v
                total_edges += e
                total_faces += f
                total_triangles += tri

                if v > max_vertices:
                    max_vertices = v
                if f > max_faces:
                    max_faces = f

                # Check for ngons (faces with >4 sides)
                ngons = 0
                sel = om2.MSelectionList()
                sel.add(mesh)
                dag = sel.getDagPath(0)
                fn_mesh = om2.MFnMesh(dag)
                for i in range(fn_mesh.numPolygons()):
                    if len(fn_mesh.getPolygonVertices(i)) > 4:
                        ngons += 1
                total_ngons += ngons

                # Non-manifold
                nm = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
                total_non_manifold += len(nm)

                # Lamina
                lamina = cmds.polyInfo(mesh, laminaFaces=True) or []
                total_lamina += len(lamina)

                # Borders
                borders = cmds.polyInfo(mesh, borderEdges=True) or []
                total_borders += len(borders)

                # History
                history = cmds.listHistory(mesh) or []
                if len(history) > 1:
                    meshes_with_history += 1

                # UVs
                shape = cmds.listRelatives(mesh, shapes=True)[0] if cmds.listRelatives(mesh, shapes=True) else None
                if shape:
                    uv_sets = cmds.polyUVSet(shape, q=True, allUVSets=True) or []
                    if uv_sets:
                        meshes_with_uvs += 1
                    # Normals
                    try:
                        cmds.getAttr(f"{shape}.normals")
                        meshes_with_normals += 1
                    except:
                        pass

            except:
                continue

        stats.total_vertices = total_vertices
        stats.total_edges = total_edges
        stats.total_faces = total_faces
        stats.total_triangles = total_triangles
        stats.total_ngons = total_ngons
        stats.non_manifold_edges = total_non_manifold
        stats.lamina_faces = total_lamina
        stats.open_borders = total_borders
        stats.average_vertex_count = total_vertices / stats.total_meshes if stats.total_meshes > 0 else 0
        stats.average_face_count = total_faces / stats.total_meshes if stats.total_meshes > 0 else 0
        stats.max_vertex_count = max_vertices
        stats.max_face_count = max_faces
        stats.meshes_with_history = meshes_with_history
        stats.meshes_with_uvs = meshes_with_uvs
        stats.meshes_with_normals = meshes_with_normals

        if level == AnalysisLevel.DEEP:
            stats.details['mesh_names'] = mesh_transforms[:10]  # First 10

        return stats