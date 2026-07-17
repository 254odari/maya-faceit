# -*- coding: utf-8 -*-
"""
tools/mesh/operations/batch
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Batch processing for multiple meshes.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Callable, Dict, Any, Optional, Union
from ..core.engine import MeshEngine
from ..core.undo import UndoChunk
from ..operations.editing import MeshEditingTools
from ..operations.retopology import RetopologyTools


class BatchProcessor:
    """
    Batch processing for meshes.

    Provides methods to apply operations to multiple meshes sequentially
    or in parallel (where possible), with progress reporting and error handling.
    """

    def __init__(self):
        self.engine = MeshEngine()
        self.editing = MeshEditingTools(self.engine.editor)
        self.retopology = RetopologyTools(self.engine.editor)

    # =====================================================================
    # CORE BATCH PROCESSING
    # =====================================================================

    def process_meshes(self, meshes: List[str], func: Callable,
                       progress_callback: Optional[Callable[[int, int, str], None]] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Apply a function to each mesh, returning results.

        Args:
            meshes: List of mesh names.
            func: Function to apply to each mesh. Should accept mesh name and kwargs.
            progress_callback: Optional callback(completed, total, mesh_name).
            **kwargs: Additional arguments to pass to func.

        Returns:
            Dictionary mapping mesh names to results (or errors).
        """
        results = {}
        total = len(meshes)
        for idx, mesh in enumerate(meshes):
            if not cmds.objExists(mesh):
                results[mesh] = {'error': f"Mesh '{mesh}' does not exist."}
                if progress_callback:
                    progress_callback(idx + 1, total, mesh)
                continue
            try:
                result = func(mesh, **kwargs)
                results[mesh] = result
            except Exception as e:
                results[mesh] = {'error': str(e)}
            if progress_callback:
                progress_callback(idx + 1, total, mesh)
        return results

    # =====================================================================
    # BATCH MERGING
    # =====================================================================

    def merge_all(self, meshes: List[str], keep_original: bool = False) -> str:
        """
        Merge all meshes into one.

        Args:
            meshes: List of mesh names to merge.
            keep_original: If True, keep original meshes after merge.

        Returns:
            Name of the merged mesh.
        """
        with UndoChunk("Batch Merge Meshes"):
            # Use MeshEditingTools.merge
            merged = self.editing.merge(meshes, keep_original)
            return merged

    # =====================================================================
    # BATCH POLY REDUCTION
    # =====================================================================

    def reduce_all(self, meshes: List[str], percentage: float = 50.0,
                   keep_border: bool = True) -> Dict[str, str]:
        """
        Reduce polygon count for all meshes.

        Args:
            meshes: List of mesh names.
            percentage: Target polygon reduction percentage (0-100).
            keep_border: Preserve border edges.

        Returns:
            Dictionary mapping original mesh to reduced mesh name.
        """
        results = {}
        with UndoChunk("Batch Reduce Meshes"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = f"ERROR: Mesh '{mesh}' does not exist."
                    continue
                try:
                    reduced = self.retopology.poly_reduce(mesh, percentage, keep_border)
                    results[mesh] = reduced
                except Exception as e:
                    results[mesh] = f"ERROR: {str(e)}"
        return results

    # =====================================================================
    # BATCH REMESH
    # =====================================================================

    def remesh_all(self, meshes: List[str], target_edge_length: Optional[float] = None,
                   target_face_count: int = 5000) -> Dict[str, str]:
        """
        Remesh all meshes.

        Args:
            meshes: List of mesh names.
            target_edge_length: Target edge length for remesh.
            target_face_count: Target face count (used if target_edge_length is None).

        Returns:
            Dictionary mapping original mesh to remeshed mesh name.
        """
        results = {}
        with UndoChunk("Batch Remesh Meshes"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = f"ERROR: Mesh '{mesh}' does not exist."
                    continue
                try:
                    remeshed = self.retopology.remesh(mesh, target_edge_length, target_face_count)
                    results[mesh] = remeshed
                except Exception as e:
                    results[mesh] = f"ERROR: {str(e)}"
        return results

    # =====================================================================
    # BATCH CLEANUP
    # =====================================================================

    def cleanup_all(self, meshes: List[str]) -> Dict[str, bool]:
        """
        Run cleanup on all meshes.

        Args:
            meshes: List of mesh names.

        Returns:
            Dictionary mapping mesh to success boolean.
        """
        results = {}
        with UndoChunk("Batch Cleanup Meshes"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = False
                    continue
                try:
                    self.engine.cleanup(mesh)
                    results[mesh] = True
                except Exception:
                    results[mesh] = False
        return results

    # =====================================================================
    # BATCH REPAIR
    # =====================================================================

    def repair_all(self, meshes: List[str]) -> Dict[str, int]:
        """
        Run full repair on all meshes.

        Args:
            meshes: List of mesh names.

        Returns:
            Dictionary mapping mesh to number of repairs applied.
        """
        results = {}
        with UndoChunk("Batch Repair Meshes"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = -1
                    continue
                try:
                    count = self.engine.repair(mesh).repaired_count
                    results[mesh] = count
                except Exception:
                    results[mesh] = -1
        return results

    # =====================================================================
    # BATCH SYMMETRY SNAP
    # =====================================================================

    def snap_symmetry_all(self, meshes: List[str], axis: str = "x", plane_x: float = 0.0) -> Dict[str, int]:
        """
        Snap vertices to symmetry on all meshes.

        Args:
            meshes: List of mesh names.
            axis: Axis of symmetry plane ("x", "y", or "z").
            plane_x: Position of the symmetry plane.

        Returns:
            Dictionary mapping mesh to number of vertices snapped.
        """
        results = {}
        with UndoChunk("Batch Symmetry Snap"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = -1
                    continue
                try:
                    snapped = self.engine.symmetry.snap_vertices(mesh, plane_x=plane_x)
                    results[mesh] = snapped
                except Exception:
                    results[mesh] = -1
        return results

    # =====================================================================
    # BATCH UV OPERATIONS
    # =====================================================================

    def auto_uv_all(self, meshes: List[str], projection_type: str = "automatic") -> Dict[str, bool]:
        """
        Run auto UV projection on all meshes.

        Args:
            meshes: List of mesh names.
            projection_type: "automatic", "planar", "cylindrical", "spherical".

        Returns:
            Dictionary mapping mesh to success boolean.
        """
        results = {}
        with UndoChunk("Batch Auto UV"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = False
                    continue
                try:
                    self.engine.auto_uv(mesh, projection_type)
                    results[mesh] = True
                except Exception:
                    results[mesh] = False
        return results

    def unfold_all(self, meshes: List[str], iterations: int = 10) -> Dict[str, bool]:
        """Unfold UVs on all meshes."""
        results = {}
        with UndoChunk("Batch Unfold UVs"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = False
                    continue
                try:
                    self.engine.unfold_uvs(mesh, iterations)
                    results[mesh] = True
                except Exception:
                    results[mesh] = False
        return results

    def layout_all(self, meshes: List[str], resolution: int = 1024) -> Dict[str, bool]:
        """Layout UVs on all meshes."""
        results = {}
        with UndoChunk("Batch Layout UVs"):
            for mesh in meshes:
                if not cmds.objExists(mesh):
                    results[mesh] = False
                    continue
                try:
                    self.engine.layout_uvs(mesh, resolution=resolution)
                    results[mesh] = True
                except Exception:
                    results[mesh] = False
        return results

    # =====================================================================
    # BATCH EXPORT
    # =====================================================================

    def export_all(self, meshes: List[str], directory: str, format: str = "obj") -> Dict[str, str]:
        """
        Export all meshes to files.

        Args:
            meshes: List of mesh names.
            directory: Directory to save files.
            format: Export format ("obj", "fbx", etc.).

        Returns:
            Dictionary mapping mesh to exported file path (or error).
        """
        results = {}
        import os
        for mesh in meshes:
            if not cmds.objExists(mesh):
                results[mesh] = f"ERROR: Mesh '{mesh}' does not exist."
                continue
            filename = f"{mesh}.{format}"
            filepath = os.path.join(directory, filename)
            try:
                cmds.select(mesh, replace=True)
                cmds.file(filepath, force=True, options="", type=format.upper(), exportSelected=True)
                results[mesh] = filepath
            except Exception as e:
                results[mesh] = f"ERROR: {str(e)}"
        return results


# =============================================================================
# CONVENIENCE SINGLETON
# =============================================================================

batch_processor = BatchProcessor()

__all__ = ["BatchProcessor", "batch_processor"]