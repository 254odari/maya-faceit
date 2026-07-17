# -*- coding: utf-8 -*-
"""
tools.mesh.core.editor
~~~~~~~~~~~~~~~~~~~~~~

Low_level Maya command wrappers with undo support.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from ..types import VertexPair, List, Tuple
from .undo import UndoChunk

class MeshEditor:
    """Low_level mesh editing operations."""
    @staticmethod
    def merge_vertices(mesh: str, distance: float = 0.001, always_merge: bool = True):
        """Merge duplicate vertices within tolerance."""
        cmds.polyMergeVertex(mesh, d=distance, am=always_merge, ch=False)

    @staticmethod
    def delete_history(mesh: str, non_deformer: bool = True):
        """Delete construction history."""
        cmds.delete(mesh, ch=True, nonDeformerHistory=non_deformer)

    @staticmethod
    def freeze_transforms(mesh: str):
        """Freeze mesh transforms (makeIdentity)."""
        cmds.makeIdentity(mesh, apply=True, t=1, r=1, s=1, n=0)

    @staticmethod
    def get_vertex_positions(mesh: str, world_space: bool = True) -> List[Tuple[float, float, float]]:
        """Get vertex positions as list of (x,y,z)."""
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if not verts:
            return []
        if world_space:
            positions = cmds.xform(verts, q=True, ws=True, t=True)
        else:
            positions = cmds.xform(verts, q=True, t=True)
        # positions is a flat list: [x0,y0,z0, x1,y1,z1, ...]
        return [(positions[i], positions[i+1], positions[i+2]) for i in range(0, len(positions), 3)]

    @staticmethod
    def set_vertex_positions(mesh: str, positions: List[Tuple[float, float, float]], world_space: bool = True):
        """Set vertex positions from list of (x,y,z)."""
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if len(verts) != len(positions):
            raise ValueError("Number of vertices does not match.")
        flat = []
        for p in positions:
            flat.extend(p)
        if world_space:
            cmds.xform(verts, ws=True, t=flat)
        else:
            cmds.xform(verts, t=flat)