# -*- coding: utf-8 -*-
"""
maya_faceit.utils.mesh
~~~~~~~~~~~~~~~~~~~~~~

Mesh utility functions.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Tuple, Optional, Set, Dict
from .math import MathUtils
from .api import MayaAPI


class MeshUtils:
    """Utilities for polygon meshes."""

    @staticmethod
    def get_vertex_positions(mesh: str, world_space: bool = True) -> List[Tuple[float, float, float]]:
        """Get all vertex positions."""
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if not verts:
            return []
        if world_space:
            pos = cmds.xform(verts, q=True, ws=True, t=True)
        else:
            pos = cmds.xform(verts, q=True, t=True)
        if not pos:
            return []
        return [(pos[i], pos[i+1], pos[i+2]) for i in range(0, len(pos), 3)]

    @staticmethod
    def set_vertex_positions(mesh: str, positions: List[Tuple[float, float, float]],
                             world_space: bool = True) -> bool:
        """Set vertex positions."""
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if len(verts) != len(positions):
            return False
        flat = []
        for p in positions:
            flat.extend(p)
        if world_space:
            cmds.xform(verts, ws=True, t=flat)
        else:
            cmds.xform(verts, t=flat)
        return True

    @staticmethod
    def get_vertex_neighbors(mesh: str, vertex_index: int) -> List[int]:
        """Get neighbor vertex indices."""
        fn_mesh = MayaAPI.get_mfn_mesh(mesh)
        if not fn_mesh:
            return []
        return fn_mesh.getConnectedVertices(vertex_index)

    @staticmethod
    def get_face_vertices(mesh: str, face_index: int) -> List[int]:
        """Get vertex indices of a face."""
        fn_mesh = MayaAPI.get_mfn_mesh(mesh)
        if not fn_mesh:
            return []
        return fn_mesh.getPolygonVertices(face_index)

    @staticmethod
    def get_vertex_count(mesh: str) -> int:
        """Get vertex count."""
        return cmds.polyEvaluate(mesh, vertex=True)

    @staticmethod
    def get_face_count(mesh: str) -> int:
        """Get face count."""
        return cmds.polyEvaluate(mesh, face=True)

    @staticmethod
    def get_edge_count(mesh: str) -> int:
        """Get edge count."""
        return cmds.polyEvaluate(mesh, edge=True)

    @staticmethod
    def get_bounding_box(mesh: str) -> Tuple[float, float, float, float, float, float]:
        """Get bounding box as (minX, minY, minZ, maxX, maxY, maxZ)."""
        bbox = cmds.exactWorldBoundingBox(mesh)
        if not bbox:
            return (0, 0, 0, 0, 0, 0)
        return tuple(bbox)

    @staticmethod
    def get_center(mesh: str) -> Tuple[float, float, float]:
        """Get the center of the mesh bounding box."""
        bbox = MeshUtils.get_bounding_box(mesh)
        return ((bbox[0] + bbox[3]) / 2,
                (bbox[1] + bbox[4]) / 2,
                (bbox[2] + bbox[5]) / 2)

    @staticmethod
    def is_closed(mesh: str) -> bool:
        """Check if the mesh is closed (no open borders)."""
        borders = cmds.polyInfo(mesh, borderEdges=True) or []
        return len(borders) == 0

    @staticmethod
    def get_surface_area(mesh: str) -> float:
        """Get total surface area."""
        fn_mesh = MayaAPI.get_mfn_mesh(mesh)
        if not fn_mesh:
            return 0.0
        area = 0.0
        for i in range(fn_mesh.numPolygons()):
            area += fn_mesh.getPolygonArea(i, om2.MSpace.kWorld)
        return area

    @staticmethod
    def get_volume(mesh: str) -> float:
        """Get enclosed volume (approximate)."""
        info = cmds.polyInfo(mesh, volume=True)
        if info:
            try:
                return float(info[0].split(':')[-1].strip())
            except:
                pass
        return 0.0

    @staticmethod
    def get_face_centers(mesh: str) -> List[Tuple[float, float, float]]:
        """Get centers of all faces in world space."""
        faces = cmds.ls(f"{mesh}.f[*]", flatten=True)
        if not faces:
            return []
        # Use xform to get position of face centers
        centers = []
        for f in faces:
            # Get the average of vertices of the face
            verts = cmds.polyListComponentConversion(f, toVertex=True)
            verts = cmds.ls(verts, flatten=True)
            if verts:
                pos = cmds.xform(verts, q=True, ws=True, t=True)
                cx = sum(pos[0::3]) / len(verts)
                cy = sum(pos[1::3]) / len(verts)
                cz = sum(pos[2::3]) / len(verts)
                centers.append((cx, cy, cz))
        return centers