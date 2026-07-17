# -*- coding: utf-8 -*-
"""
tools/mesh/mapping/uvs
~~~~~~~~~~~~~~~~~~~~~~

UV operations: projection, unfolding, layout, optimization, and editing.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Optional, Tuple, Union, Dict, Any
from ..types import UVCoordinate
from ..core.undo import UndoChunk


class UVTools:
    """
    Comprehensive UV manipulation toolkit.

    Provides methods for:
    - Projection (automatic, planar, cylindrical, spherical)
    - Unfolding
    - Layout (packing shells)
    - Optimization (reduce distortion)
    - Sewing, moving, and basic UV editing
    - UV set management
    """

    def __init__(self, editor):
        self.editor = editor

    # =====================================================================
    # UV SET MANAGEMENT
    # =====================================================================

    def get_current_uv_set(self, mesh: str) -> str:
        """Get the name of the currently active UV set."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        return cmds.polyUVSet(shape, q=True, currentUVSet=True)[0]

    def list_uv_sets(self, mesh: str) -> List[str]:
        """List all UV sets on the mesh."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        return cmds.polyUVSet(shape, q=True, allUVSets=True) or []

    def create_uv_set(self, mesh: str, name: str) -> bool:
        """Create a new empty UV set."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        try:
            cmds.polyUVSet(shape, create=True, uvSet=name)
            return True
        except:
            return False

    def delete_uv_set(self, mesh: str, name: str) -> bool:
        """Delete a UV set (cannot delete the current one)."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        try:
            cmds.polyUVSet(shape, delete=True, uvSet=name)
            return True
        except:
            return False

    def set_current_uv_set(self, mesh: str, name: str) -> bool:
        """Set the active UV set."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        try:
            cmds.polyUVSet(shape, currentUVSet=True, uvSet=name)
            return True
        except:
            return False

    # =====================================================================
    # UV DATA ACCESS
    # =====================================================================

    def get_uvs(self, mesh: str, uv_set: Optional[str] = None) -> List[UVCoordinate]:
        """Get UV coordinates for all vertices in a UV set."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        uvs = cmds.polyEditUV(shape, q=True, u=True, v=True, uvSet=uv_set)
        if not uvs:
            return []
        return [UVCoordinate(uvs[i], uvs[i+1]) for i in range(0, len(uvs), 2)]

    def set_uvs(self, mesh: str, uvs: List[UVCoordinate], uv_set: Optional[str] = None) -> bool:
        """Set UV coordinates for all vertices."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        flat = []
        for uv in uvs:
            flat.extend([uv.u, uv.v])
        try:
            cmds.polyEditUV(shape, u=flat, v=None, uvSet=uv_set)
            return True
        except:
            return False

    def get_uv_shells(self, mesh: str, uv_set: Optional[str] = None) -> List[List[int]]:
        """
        Get UV shells (connected groups of UVs).

        Returns a list of lists, each containing UV indices belonging to a shell.
        """
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        # Use polyEvaluate to get shell info
        shells = cmds.polyEvaluate(shape, uvShell=True)
        # Not directly available; we'll use a simpler approach:
        # We'll use polySelect to select shells and get their UV indices.
        result = []
        # For each shell, select it and get the UV indices
        # This is complex; we'll implement a basic version using API.
        # Placeholder: return an empty list.
        return []

    # =====================================================================
    # UV PROJECTION
    # =====================================================================

    def auto_project(self, mesh: str, **kwargs) -> bool:
        """
        Automatically project UVs using Maya's best method.

        Args:
            mesh: Mesh name.
            **kwargs: Additional arguments to polyProjection.

        Returns:
            True if successful.
        """
        with UndoChunk("Auto Project UVs"):
            cmds.polyProjection(mesh, type="automatic", ch=False, **kwargs)
        return True

    def planar_project(self, mesh: str, axis: str = "x", **kwargs) -> bool:
        """
        Project UVs from a single planar direction.

        Args:
            mesh: Mesh name.
            axis: "x", "y", or "z" - projection direction.
            **kwargs: Additional arguments to polyProjection.

        Returns:
            True if successful.
        """
        with UndoChunk("Planar UV Projection"):
            cmds.polyProjection(mesh, type="planar", axis=axis, ch=False, **kwargs)
        return True

    def cylindrical_project(self, mesh: str, axis: str = "y", **kwargs) -> bool:
        """Project UVs cylindrically around an axis."""
        with UndoChunk("Cylindrical UV Projection"):
            cmds.polyProjection(mesh, type="cylindrical", axis=axis, ch=False, **kwargs)
        return True

    def spherical_project(self, mesh: str, axis: str = "z", **kwargs) -> bool:
        """Project UVs spherically around an axis."""
        with UndoChunk("Spherical UV Projection"):
            cmds.polyProjection(mesh, type="spherical", axis=axis, ch=False, **kwargs)
        return True

    def auto_uv(self, mesh: str, projection_type: str = "automatic", **kwargs) -> bool:
        """
        Generic UV projection with type selection.

        Args:
            mesh: Mesh name.
            projection_type: "automatic", "planar", "cylindrical", "spherical"
            **kwargs: Additional arguments to polyProjection.

        Returns:
            True if successful.
        """
        if projection_type == "planar":
            return self.planar_project(mesh, **kwargs)
        elif projection_type == "cylindrical":
            return self.cylindrical_project(mesh, **kwargs)
        elif projection_type == "spherical":
            return self.spherical_project(mesh, **kwargs)
        else:
            return self.auto_project(mesh, **kwargs)

    # =====================================================================
    # UNFOLD
    # =====================================================================

    def unfold(self, mesh: str, iterations: int = 10, pin_selected: bool = False, **kwargs) -> bool:
        """
        Unfold UVs to reduce stretching.

        Args:
            mesh: Mesh name.
            iterations: Number of iterations.
            pin_selected: If True, pin currently selected UVs.
            **kwargs: Additional arguments to polyUnfold.

        Returns:
            True if successful.
        """
        with UndoChunk("Unfold UVs"):
            cmds.polyUnfold(mesh, iterations=iterations, pin=pin_selected, ch=False, **kwargs)
        return True

    # =====================================================================
    # LAYOUT / PACKING
    # =====================================================================

    def layout(self, mesh: str, resolution: int = 1024, scale: float = 1.0,
               rotate_for_best_fit: bool = True, **kwargs) -> bool:
        """
        Layout UV shells within the 0-1 space.

        Args:
            mesh: Mesh name.
            resolution: Layout grid resolution.
            scale: Scale factor for shells.
            rotate_for_best_fit: Auto-rotate shells.
            **kwargs: Additional arguments to polyLayoutUV.

        Returns:
            True if successful.
        """
        with UndoChunk("Layout UVs"):
            cmds.polyLayoutUV(mesh,
                              resolution=resolution,
                              scale=scale,
                              rotateForBestFit=rotate_for_best_fit,
                              ch=False, **kwargs)
        return True

    def layout_uvs(self, mesh: str, **kwargs) -> bool:
        """Alias for layout()."""
        return self.layout(mesh, **kwargs)

    # =====================================================================
    # OPTIMIZATION
    # =====================================================================

    def optimize(self, mesh: str, iterations: int = 5, **kwargs) -> bool:
        """
        Optimize UVs by reducing distortion.

        Args:
            mesh: Mesh name.
            iterations: Number of optimization iterations.
            **kwargs: Additional arguments to polyOptimizeUV.

        Returns:
            True if successful.
        """
        with UndoChunk("Optimize UVs"):
            cmds.polyOptimizeUV(mesh, iterations=iterations, ch=False, **kwargs)
        return True

    def optimize_uvs(self, mesh: str, **kwargs) -> bool:
        """Alias for optimize()."""
        return self.optimize(mesh, **kwargs)

    # =====================================================================
    # SEW / MOVE / ALIGN / TRANSFORM
    # =====================================================================

    def sew(self, mesh: str) -> bool:
        """Sew overlapping UV edges (merge seams)."""
        with UndoChunk("Sew UVs"):
            cmds.polyMapSewMove(mesh, ch=False)
        return True

    def sew_uvs(self, mesh: str) -> bool:
        """Alias for sew()."""
        return self.sew(mesh)

    def move(self, mesh: str, u_offset: float = 0.0, v_offset: float = 0.0,
             uv_set: Optional[str] = None) -> bool:
        """Move all UVs by an offset."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        with UndoChunk("Move UVs"):
            cmds.polyEditUV(shape, u=u_offset, v=v_offset, relative=True, uvSet=uv_set)
        return True

    def move_uvs(self, mesh: str, u_offset: float = 0.0, v_offset: float = 0.0,
                 uv_set: Optional[str] = None) -> bool:
        """Alias for move()."""
        return self.move(mesh, u_offset, v_offset, uv_set)

    def scale(self, mesh: str, u_scale: float = 1.0, v_scale: float = 1.0,
              uv_set: Optional[str] = None) -> bool:
        """Scale UVs."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        with UndoChunk("Scale UVs"):
            cmds.polyEditUV(shape, su=u_scale, sv=v_scale, uvSet=uv_set)
        return True

    def scale_uvs(self, mesh: str, **kwargs) -> bool:
        """Alias for scale()."""
        return self.scale(mesh, **kwargs)

    def rotate(self, mesh: str, angle: float = 0.0, uv_set: Optional[str] = None) -> bool:
        """Rotate UVs around their center."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        if uv_set is None:
            uv_set = self.get_current_uv_set(mesh)
        with UndoChunk("Rotate UVs"):
            cmds.polyEditUV(shape, rotation=angle, uvSet=uv_set)
        return True

    def rotate_uvs(self, mesh: str, **kwargs) -> bool:
        """Alias for rotate()."""
        return self.rotate(mesh, **kwargs)

    # =====================================================================
    # COPY / TRANSFER
    # =====================================================================

    def copy(self, source_mesh: str, target_mesh: str, uv_set: Optional[str] = None) -> bool:
        """Copy UVs from source to target using closest point mapping."""
        src_shape = cmds.listRelatives(source_mesh, shapes=True)[0]
        tgt_shape = cmds.listRelatives(target_mesh, shapes=True)[0]
        try:
            cmds.polyTransfer(src_shape, tgt_shape, uv=True)
            return True
        except:
            return False

    def copy_uvs(self, source_mesh: str, target_mesh: str, uv_set: Optional[str] = None) -> bool:
        """Alias for copy()."""
        return self.copy(source_mesh, target_mesh, uv_set)

    # =====================================================================
    # CLEANUP
    # =====================================================================

    def cleanup(self, mesh: str, remove_unused: bool = True) -> bool:
        """Clean up UVs: remove unused, fix overlaps."""
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        try:
            if remove_unused:
                cmds.polyUVSet(shape, removeUnused=True)
            cmds.polyMapSewMove(shape, ch=False)
            return True
        except:
            return False

    def cleanup_uvs(self, mesh: str, **kwargs) -> bool:
        """Alias for cleanup()."""
        return self.cleanup(mesh, **kwargs)

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
    "UVTools",
]