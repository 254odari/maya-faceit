# -*- coding: utf-8 -*-
"""
tools/mesh/operations/retopology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retopology operations: polygon reduction, remeshing, quad draw helpers.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, List, Union
from ..core.undo import UndoChunk


class RetopologyTools:
    """
    High-level retopology and mesh optimization operations.

    Provides methods for:
    - Polygon reduction (polyReduce)
    - Remeshing (polyRemesh)
    - Automatic retopology
    - Quad Draw target setup
    """

    def __init__(self, editor):
        self.editor = editor

    # =====================================================================
    # POLY REDUCTION
    # =====================================================================

    def poly_reduce(self, mesh: str, percentage: float = 50.0,
                    keep_border: bool = True, keep_uvs: bool = True,
                    keep_normals: bool = True) -> str:
        """
        Reduce polygon count using polyReduce.

        Args:
            mesh: Mesh name.
            percentage: Reduction percentage (0-100). Higher = more reduction.
            keep_border: Preserve border edges.
            keep_uvs: Preserve UVs.
            keep_normals: Preserve normals.

        Returns:
            Name of the reduced mesh (new mesh created by polyReduce).
        """
        with UndoChunk("Poly Reduce"):
            # polyReduce creates a new mesh
            result = cmds.polyReduce(
                mesh,
                reduction=percentage,
                keepBorder=keep_border,
                keepUVs=keep_uvs,
                keepNormals=keep_normals,
                ch=False
            )
            return result[0] if result else mesh

    def reduce_selected(self, percentage: float = 50.0, **kwargs) -> str:
        """Apply polyReduce to the currently selected mesh."""
        mesh = self._get_active_mesh()
        if not mesh:
            raise RuntimeError("No mesh selected.")
        return self.poly_reduce(mesh, percentage, **kwargs)

    # =====================================================================
    # REMESH
    # =====================================================================

    def remesh(self, mesh: str, target_edge_length: Optional[float] = None,
               target_face_count: Optional[int] = None,
               adaptivity: float = 0.5, preserve_features: bool = True) -> str:
        """
        Remesh using polyRemesh.

        Args:
            mesh: Mesh name.
            target_edge_length: Desired edge length (if None, uses target_face_count).
            target_face_count: Desired face count (used if target_edge_length is None).
            adaptivity: Adaptivity factor (0-1).
            preserve_features: Preserve hard edges and features.

        Returns:
            Name of the remeshed mesh (new mesh created by polyRemesh).
        """
        with UndoChunk("Remesh"):
            if target_edge_length is not None:
                result = cmds.polyRemesh(
                    mesh,
                    edgeLength=target_edge_length,
                    adaptivity=adaptivity,
                    preserveFeatures=preserve_features,
                    ch=False
                )
            elif target_face_count is not None:
                result = cmds.polyRemesh(
                    mesh,
                    targetCount=target_face_count,
                    adaptivity=adaptivity,
                    preserveFeatures=preserve_features,
                    ch=False
                )
            else:
                # Default: use face count 5000
                result = cmds.polyRemesh(
                    mesh,
                    targetCount=5000,
                    adaptivity=adaptivity,
                    preserveFeatures=preserve_features,
                    ch=False
                )
            return result[0] if result else mesh

    def remesh_selected(self, **kwargs) -> str:
        """Apply remesh to the currently selected mesh."""
        mesh = self._get_active_mesh()
        if not mesh:
            raise RuntimeError("No mesh selected.")
        return self.remesh(mesh, **kwargs)

    # =====================================================================
    # AUTO RETOPOLOGY
    # =====================================================================

    def auto_retopo(self, mesh: str, target_face_count: int = 5000) -> str:
        """
        Automatic retopology (polyRemesh with uniform quad target).

        This is essentially a remesh with quad target.

        Args:
            mesh: Mesh name.
            target_face_count: Target number of faces.

        Returns:
            Name of the retopologized mesh.
        """
        with UndoChunk("Auto Retopology"):
            result = cmds.polyRemesh(
                mesh,
                targetCount=target_face_count,
                adaptivity=0.5,
                preserveFeatures=True,
                ch=False
            )
            return result[0] if result else mesh

    # =====================================================================
    # QUAD DRAW HELPERS
    # =====================================================================

    def set_quad_draw_target(self, target_mesh: str) -> bool:
        """
        Set a mesh as the target for Quad Draw (live surface).

        This enables Quad Draw in the viewport to snap to this mesh.

        Args:
            target_mesh: Mesh to use as the Quad Draw target.

        Returns:
            True if successful.
        """
        try:
            # In Maya, the Quad Draw tool uses a "live surface" object.
            # We can set the target mesh as the live surface for Quad Draw.
            cmds.liveSurface(target_mesh, enable=True)
            return True
        except Exception as e:
            print(f"Failed to set Quad Draw target: {e}")
            return False

    def clear_quad_draw_target(self) -> bool:
        """Clear the current Quad Draw target (disable live surface)."""
        try:
            # Disable live surface on all objects
            all_meshes = cmds.ls(type='mesh')
            for m in all_meshes:
                cmds.liveSurface(m, enable=False)
            return True
        except:
            return False

    # =====================================================================
    # MESH CLEANUP (Lightweight)
    # =====================================================================

    def cleanup_mesh(self, mesh: str) -> bool:
        """
        Lightweight cleanup: merge duplicates, delete history, remove isolated.

        This is a minimal version for retopology pipeline.

        Args:
            mesh: Mesh name.

        Returns:
            True if successful.
        """
        with UndoChunk("Retopology Cleanup"):
            try:
                # Merge duplicate vertices
                cmds.polyMergeVertex(mesh, d=0.001, am=True, ch=False)
                # Delete non-deformer history
                cmds.delete(mesh, ch=True, nonDeformerHistory=True)
                # Remove isolated vertices
                isolated = cmds.polyInfo(mesh, isolatedVertices=True) or []
                if isolated:
                    vert_indices = []
                    for line in isolated:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0] == "Vertex":
                            try:
                                vert_indices.append(int(parts[1]))
                            except:
                                pass
                    if vert_indices:
                        cmds.select([f"{mesh}.vtx[{i}]" for i in vert_indices], replace=True)
                        cmds.delete()
                return True
            except:
                return False

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
    "RetopologyTools",
]