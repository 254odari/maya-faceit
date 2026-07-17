# -*- coding: utf-8 -*-
"""
tools/mesh/mapping/normals
~~~~~~~~~~~~~~~~~~~~~~~~~~

Normal operations: recalculation, smoothing, hardening, locking, transfer.
"""

import math
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Optional, Tuple, Union, Dict, Any
from ..core.undo import UndoChunk


class NormalTools:
    """
    Comprehensive normal manipulation toolkit.

    Provides methods for:
    - Recalculation (smooth, hard, uniform)
    - Smoothing / softening
    - Hardening
    - Locking / unlocking
    - Averaging
    - Transfer
    - Getting / setting vertex normals
    """

    def __init__(self, editor):
        self.editor = editor

    # =====================================================================
    # BASIC NORMAL ACCESS
    # =====================================================================

    def get_vertex_normals(self, mesh: str, world_space: bool = True) -> List[Tuple[float, float, float]]:
        """
        Get vertex normals.

        Args:
            mesh: Mesh name.
            world_space: If True, return normals in world space.

        Returns:
            List of (nx, ny, nz) for each vertex.
        """
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if not verts:
            return []
        normals = cmds.polyNormalPerVertex(verts, q=True, normal=True, ws=world_space)
        # normals is a flat list: [nx0,ny0,nz0, nx1,ny1,nz1, ...]
        if not normals:
            return []
        return [(normals[i], normals[i+1], normals[i+2]) for i in range(0, len(normals), 3)]

    def get_face_normals(self, mesh: str, world_space: bool = True) -> List[Tuple[float, float, float]]:
        """Get face normals."""
        faces = cmds.ls(f"{mesh}.f[*]", flatten=True)
        if not faces:
            return []
        normals = cmds.polyNormalPerVertex(faces, q=True, normal=True, ws=world_space)
        if not normals:
            return []
        # For faces, we need to average per face? Better to use polyInfo.
        # We'll use polyInfo for face normals.
        info = cmds.polyInfo(mesh, faceNormals=True)
        if not info:
            return []
        # Parse: "FACE_NORMAL   0: 0.123 0.456 0.789"
        result = []
        for line in info:
            parts = line.split(':')
            if len(parts) == 2:
                nums = parts[1].strip().split()
                if len(nums) == 3:
                    result.append((float(nums[0]), float(nums[1]), float(nums[2])))
        return result

    def set_vertex_normals(self, mesh: str, normals: List[Tuple[float, float, float]],
                           world_space: bool = True) -> bool:
        """
        Set vertex normals (requires unlocked normals).

        Args:
            mesh: Mesh name.
            normals: List of (nx, ny, nz) for each vertex.
            world_space: If True, normals are in world space.

        Returns:
            True if successful.
        """
        verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        if len(verts) != len(normals):
            raise ValueError("Number of normals does not match vertex count.")

        # Build flat list
        flat = []
        for n in normals:
            flat.extend(n)
        try:
            cmds.polyNormalPerVertex(verts, normalXYZ=flat, ws=world_space)
            return True
        except:
            return False

    # =====================================================================
    # RECALCULATION
    # =====================================================================

    def recalculate(self, mesh: str, angle: float = 30.0, uniform: bool = True,
                    user_normal_mode: int = 0, **kwargs) -> bool:
        """
        Recalculate normals.

        Args:
            mesh: Mesh name.
            angle: Angle threshold for smoothing (0-180).
            uniform: If True, use uniform normals.
            user_normal_mode: 0=conform, 1=set to face, 2=set to vertex.
            **kwargs: Additional arguments to polyNormal.

        Returns:
            True if successful.
        """
        with UndoChunk("Recalculate Normals"):
            cmds.polyNormal(mesh, normalMode=user_normal_mode, angle=angle,
                            uniform=uniform, ch=False, **kwargs)
        return True

    def smooth(self, mesh: str, angle: float = 30.0, **kwargs) -> bool:
        """Smooth normals (soften) using an angle threshold."""
        with UndoChunk("Smooth Normals"):
            cmds.polySoftNormals(mesh, angle=angle, ch=False, **kwargs)
        return True

    def harden(self, mesh: str) -> bool:
        """Harden normals (set to face normals)."""
        with UndoChunk("Harden Normals"):
            cmds.polyNormal(mesh, normalMode=1, ch=False)  # 1 = set to face
        return True

    def soften(self, mesh: str, angle: float = 180.0, **kwargs) -> bool:
        """Soften all normals (set to vertex normals)."""
        with UndoChunk("Soften Normals"):
            cmds.polyNormal(mesh, normalMode=2, ch=False, **kwargs)
        return True

    # =====================================================================
    # LOCK / UNLOCK
    # =====================================================================

    def unlock(self, mesh: str) -> bool:
        """Unfreeze normals to allow editing."""
        try:
            cmds.polyNormalPerVertex(mesh, unFreezeNormals=True)
            return True
        except:
            return False

    def unlock_normals(self, mesh: str) -> bool:
        """Alias for unlock()."""
        return self.unlock(mesh)

    def lock(self, mesh: str) -> bool:
        """Freeze normals to lock them."""
        try:
            cmds.polyNormalPerVertex(mesh, freezeNormals=True)
            return True
        except:
            return False

    def lock_normals(self, mesh: str) -> bool:
        """Alias for lock()."""
        return self.lock(mesh)

    # =====================================================================
    # AVERAGE / SMOOTH SELECTED
    # =====================================================================

    def average_selected(self, mesh: str, vertices: Optional[List[int]] = None) -> bool:
        """
        Average normals of selected vertices (or all vertices) using adjacent faces.

        This is a simplified version; for complex operations, use relax or smooth.
        """
        if vertices is None:
            verts = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        else:
            verts = [f"{mesh}.vtx[{i}]" for i in vertices]
        if not verts:
            return False
        # Unlock first
        self.unlock(mesh)
        # Use polyNormalPerVertex to set averaged normals
        # For each vertex, get connected faces, average their normals.
        # We'll use a simple approach: use Maya's polyNormal with -normalMode 2?
        # Actually, we'll use polySoftNormals on a selection to average.
        with UndoChunk("Average Normals"):
            cmds.select(verts, replace=True)
            cmds.polySoftNormals(mesh, angle=180, ch=False)
        return True

    def relax_normals(self, mesh: str, iterations: int = 5) -> bool:
        """Relax normals by averaging adjacent normals (smoothing)."""
        # This is essentially smoothing; we'll just call smooth with a high angle.
        return self.smooth(mesh, angle=180)

    # =====================================================================
    # TRANSFER
    # =====================================================================

    def transfer(self, source_mesh: str, target_mesh: str) -> bool:
        """
        Transfer normals from source to target using closest point mapping.

        Args:
            source_mesh: Source mesh.
            target_mesh: Target mesh.

        Returns:
            True if successful.
        """
        try:
            # Use polyTransfer with normals flag
            src_shape = cmds.listRelatives(source_mesh, shapes=True)[0]
            tgt_shape = cmds.listRelatives(target_mesh, shapes=True)[0]
            cmds.polyTransfer(src_shape, tgt_shape, normal=True)
            return True
        except:
            return False

    def transfer_normals(self, source_mesh: str, target_mesh: str) -> bool:
        """Alias for transfer()."""
        return self.transfer(source_mesh, target_mesh)

    # =====================================================================
    # UTILITY
    # =====================================================================

    def _get_active_mesh(self) -> Optional[str]:
        """Get the currently selected mesh transform."""
        selection = cmds.ls(selection=True, long=True)
        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True) or []
            if shapes and cmds.nodeType(shapes[0]) == "mesh":
                return obj
        return None


# =============================================================================
# PUBLIC API EXPORTS
# =============================================================================

__all__ = [
    "NormalTools",
]