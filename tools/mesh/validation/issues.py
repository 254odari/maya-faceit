# -*- coding: utf-8 -*-
"""
tools.mesh.validation.issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specific mesh issue checks.
"""

import math
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Tuple, Optional


class MeshIssues:
    """Collection of static methods to detect common mesh issues."""

    @staticmethod
    def has_non_manifold_edges(mesh: str) -> bool:
        """Check if the mesh has non‑manifold edges (edges with >2 incident faces)."""
        info = cmds.polyInfo(mesh, nonManifoldEdges=True)
        return bool(info)

    @staticmethod
    def has_lamina_faces(mesh: str) -> bool:
        """Check if the mesh has lamina faces (faces sharing the same vertices)."""
        info = cmds.polyInfo(mesh, laminaFaces=True)
        return bool(info)

    @staticmethod
    def has_ngons(mesh: str) -> bool:
        """Check if any face has more than 4 vertices."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        for i in range(fn_mesh.numPolygons()):
            if len(fn_mesh.getPolygonVertices(i)) > 4:
                return True
        return False

    @staticmethod
    def has_open_borders(mesh: str) -> bool:
        """Check if the mesh has open border edges (edges with only one incident face)."""
        info = cmds.polyInfo(mesh, borderEdges=True)
        return bool(info)

    @staticmethod
    def has_duplicate_vertices(mesh: str, tolerance: float = 0.001) -> bool:
        """Check if there are duplicate vertices within the given tolerance."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        n = len(points)
        if n < 2:
            return False
        # Sort by x-coordinate for early exit
        sorted_indices = sorted(range(n), key=lambda i: points[i].x)
        for i in range(n):
            for j in range(i + 1, n):
                if points[sorted_indices[j]].x - points[sorted_indices[i]].x > tolerance:
                    break
                p1 = points[sorted_indices[i]]
                p2 = points[sorted_indices[j]]
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dz = p1.z - p2.z
                if dx * dx + dy * dy + dz * dz < tolerance * tolerance:
                    return True
        return False

    @staticmethod
    def has_zero_area_faces(mesh: str, tolerance: float = 1e-10) -> bool:
        """Check if there are faces with zero area (degenerate faces)."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        for i in range(fn_mesh.numPolygons()):
            if fn_mesh.getPolygonArea(i) < tolerance:
                return True
        return False

    @staticmethod
    def has_non_planar_faces(mesh: str, threshold: float = 0.01) -> bool:
        """Check for non‑planar faces (faces with vertices deviating from plane)."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        for i in range(fn_mesh.numPolygons()):
            verts = fn_mesh.getPolygonVertices(i)
            if len(verts) <= 3:
                continue
            # Get positions
            positions = [fn_mesh.getPoint(vid, om2.MSpace.kWorld) for vid in verts]
            p1 = positions[0]
            p2 = positions[1]
            p3 = positions[2]
            u = (p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
            v = (p3.x - p1.x, p3.y - p1.y, p3.z - p1.z)
            # Normal
            nx = u[1] * v[2] - u[2] * v[1]
            ny = u[2] * v[0] - u[0] * v[2]
            nz = u[0] * v[1] - u[1] * v[0]
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length < 1e-12:
                continue
            # Normalize
            nx /= length
            ny /= length
            nz /= length
            # Check distance of other vertices to plane
            for pt in positions[3:]:
                d = (pt.x - p1.x) * nx + (pt.y - p1.y) * ny + (pt.z - p1.z) * nz
                if abs(d) > threshold:
                    return True
        return False

    @staticmethod
    def has_invalid_uvs(mesh: str) -> bool:
        """Check for UVs with NaN, infinite, or out‑of‑range values."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        uvs = cmds.polyEditUV(shape, q=True, u=True, v=True)
        if not uvs:
            return False
        for val in uvs:
            if not math.isfinite(val):
                return True
            if val < -1000 or val > 1000:  # heuristic range
                return True
        return False

    @staticmethod
    def has_unused_uvs(mesh: str) -> bool:
        """Check if there are UVs that are not referenced by any vertex."""
        # Simplified check: compare UV count vs vertex count
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        uv_count = cmds.polyEvaluate(shape, uvCoord=True)
        if uv_count == 0:
            return False
        # Get UV indices for vertices
        sel = om2.MSelectionList()
        sel.add(shape)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        uv_ids = fn_mesh.getUVIndices()
        unique_uvs = set(uv_ids)
        # If there are UVs not used by any vertex, they won't appear in uv_ids
        # So if len(unique_uvs) < uv_count, there are unused UVs
        return len(unique_uvs) < uv_count

    @staticmethod
    def has_missing_normals(mesh: str) -> bool:
        """Check if any vertex normals are missing or uninitialized."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        # Get normals (per‑vertex)
        normals = fn_mesh.getVertexNormals(om2.MSpace.kWorld)
        for n in normals:
            if n.length() < 1e-10:
                return True
        return False