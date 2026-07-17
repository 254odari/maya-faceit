# -*- coding: utf-8 -*-
"""
tools/mesh/operations/editing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mesh editing operations: merge, separate, bridge, extrude, bevel,
duplicate, split, delete, fill hole, insert edge loop, and more.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Union, Tuple
from ..core.undo import UndoChunk


class MeshEditingTools:
    """
    High-level mesh editing operations.

    Provides Maya's core mesh editing functionality with consistent
    undo support and automatic selection handling.
    """

    def __init__(self, editor):
        self.editor = editor

    # =====================================================================
    # MERGE / COMBINE
    # =====================================================================

    def merge(self, meshes: List[str], keep_original: bool = False,
              merge_uvs: bool = True, center_pivot: bool = True) -> str:
        """
        Merge multiple meshes into one using polyUnite.

        Args:
            meshes: List of mesh names to merge.
            keep_original: If True, keep original meshes.
            merge_uvs: Merge UV sets together.
            center_pivot: Center pivot of the new mesh.

        Returns:
            Name of the merged mesh.
        """
        with UndoChunk("Merge Meshes"):
            flags = []
            if merge_uvs:
                flags.append('mergeUVSets')
            if center_pivot:
                flags.append('centerPivot')
            result = cmds.polyUnite(meshes, ch=False, **{f: True for f in flags})
            if not keep_original:
                for m in meshes:
                    if cmds.objExists(m):
                        cmds.delete(m)
            return result[0]

    def combine(self, meshes: List[str], **kwargs) -> str:
        """Alias for merge()."""
        return self.merge(meshes, **kwargs)

    # =====================================================================
    # SEPARATE
    # =====================================================================

    def separate(self, mesh: str) -> List[str]:
        """
        Separate a mesh into individual shells (polySeparate).

        Args:
            mesh: Mesh name.

        Returns:
            List of separated mesh names.
        """
        with UndoChunk("Separate Mesh"):
            cmds.select(mesh, replace=True)
            result = cmds.polySeparate(mesh, ch=False)
            return cmds.ls(selection=True) or []

    # =====================================================================
    # BRIDGE
    # =====================================================================

    def bridge(self, mesh: str, edge1: int, edge2: int,
               divisions: int = 1, taper: float = 1.0) -> bool:
        """
        Bridge two edges (polyBridgeEdge).

        Args:
            mesh: Mesh name.
            edge1: First edge index.
            edge2: Second edge index.
            divisions: Number of bridge segments.
            taper: Taper factor (0-1).

        Returns:
            True if successful.
        """
        with UndoChunk("Bridge Edges"):
            try:
                cmds.select(f"{mesh}.e[{edge1}]", f"{mesh}.e[{edge2}]", replace=True)
                cmds.polyBridgeEdge(mesh, divisions=divisions, taper=taper, ch=False)
                return True
            except:
                return False

    def bridge_edges(self, mesh: str, edge1: int, edge2: int, **kwargs) -> bool:
        """Alias for bridge()."""
        return self.bridge(mesh, edge1, edge2, **kwargs)

    # =====================================================================
    # EXTRUDE
    # =====================================================================

    def extrude_face(self, mesh: str, face: Union[int, List[int]],
                     distance: float = 0.5, keep_faces_together: bool = False) -> bool:
        """
        Extrude a face or faces (polyExtrudeFacet).

        Args:
            mesh: Mesh name.
            face: Face index or list of face indices.
            distance: Extrusion distance.
            keep_faces_together: Keep extruded faces together.

        Returns:
            True if successful.
        """
        if isinstance(face, int):
            face = [face]
        with UndoChunk("Extrude Faces"):
            try:
                cmds.select([f"{mesh}.f[{i}]" for i in face], replace=True)
                cmds.polyExtrudeFacet(mesh, ltz=distance, kft=keep_faces_together, ch=False)
                return True
            except:
                return False

    def extrude_edge(self, mesh: str, edge: Union[int, List[int]],
                     distance: float = 0.5) -> bool:
        """Extrude an edge (polyExtrudeEdge)."""
        if isinstance(edge, int):
            edge = [edge]
        with UndoChunk("Extrude Edges"):
            try:
                cmds.select([f"{mesh}.e[{i}]" for i in edge], replace=True)
                cmds.polyExtrudeEdge(mesh, ltz=distance, ch=False)
                return True
            except:
                return False

    # =====================================================================
    # BEVEL
    # =====================================================================

    def bevel(self, mesh: str, edge: Union[int, List[int]] = None,
              offset: float = 0.2, segments: int = 1) -> bool:
        """
        Bevel edges (polyBevel).

        Args:
            mesh: Mesh name.
            edge: Edge index or list of edge indices. If None, uses selection.
            offset: Bevel offset.
            segments: Number of bevel segments.

        Returns:
            True if successful.
        """
        if edge is None:
            # Use current selection
            sel = cmds.ls(selection=True, flatten=True)
            if not sel:
                return False
            with UndoChunk("Bevel Edges"):
                try:
                    cmds.polyBevel(mesh, offset=offset, segments=segments, ch=False)
                    return True
                except:
                    return False
        else:
            if isinstance(edge, int):
                edge = [edge]
            with UndoChunk("Bevel Edges"):
                try:
                    cmds.select([f"{mesh}.e[{i}]" for i in edge], replace=True)
                    cmds.polyBevel(mesh, offset=offset, segments=segments, ch=False)
                    return True
                except:
                    return False

    # =====================================================================
    # DUPLICATE
    # =====================================================================

    def duplicate(self, mesh: str, new_name: Optional[str] = None,
                  smart_transform: bool = True) -> Optional[str]:
        """
        Duplicate a mesh (polyDuplicate).

        Args:
            mesh: Mesh name.
            new_name: Optional new name for the duplicate.
            smart_transform: Apply smart translate/rotate/scale.

        Returns:
            Name of the duplicated mesh, or None on failure.
        """
        with UndoChunk("Duplicate Mesh"):
            try:
                result = cmds.duplicate(mesh, returnRootsOnly=True, rr=True)
                if result:
                    dup = result[0]
                    if new_name:
                        dup = cmds.rename(dup, new_name)
                    # Optionally apply smart transform?
                    return dup
            except:
                pass
        return None

    # =====================================================================
    # DELETE COMPONENTS
    # =====================================================================

    def delete_vertices(self, mesh: str, vertices: List[int]) -> bool:
        """Delete vertices (and their adjacent faces)."""
        with UndoChunk("Delete Vertices"):
            try:
                cmds.select([f"{mesh}.vtx[{i}]" for i in vertices], replace=True)
                cmds.delete()
                return True
            except:
                return False

    def delete_edges(self, mesh: str, edges: List[int]) -> bool:
        """Delete edges (and their adjacent faces)."""
        with UndoChunk("Delete Edges"):
            try:
                cmds.select([f"{mesh}.e[{i}]" for i in edges], replace=True)
                cmds.delete()
                return True
            except:
                return False

    def delete_faces(self, mesh: str, faces: List[int]) -> bool:
        """Delete faces (and their adjacent edges/vertices)."""
        with UndoChunk("Delete Faces"):
            try:
                cmds.select([f"{mesh}.f[{i}]" for i in faces], replace=True)
                cmds.delete()
                return True
            except:
                return False

    # =====================================================================
    # FILL HOLE
    # =====================================================================

    def fill_hole(self, mesh: str, edge: Union[int, List[int]] = None) -> bool:
        """
        Fill a hole by bridging border edges.

        Args:
            mesh: Mesh name.
            edge: Edge index or list of edge indices (on the border). If None, uses selection.

        Returns:
            True if successful.
        """
        with UndoChunk("Fill Hole"):
            try:
                if edge is None:
                    # Use current selection
                    cmds.polyCloseBorder(mesh, ch=False)
                else:
                    if isinstance(edge, int):
                        edge = [edge]
                    cmds.select([f"{mesh}.e[{i}]" for i in edge], replace=True)
                    cmds.polyCloseBorder(mesh, ch=False)
                return True
            except:
                return False

    def fill_holes(self, mesh: str) -> bool:
        """Fill all holes in the mesh."""
        with UndoChunk("Fill All Holes"):
            try:
                cmds.select(mesh, replace=True)
                cmds.polyCloseBorder(mesh, ch=False)
                return True
            except:
                return False

    # =====================================================================
    # INSERT EDGE LOOP
    # =====================================================================

    def insert_edge_loop(self, mesh: str, edge: int, position: float = 0.5,
                         relative: bool = True) -> bool:
        """
        Insert an edge loop along an edge ring.

        Args:
            mesh: Mesh name.
            edge: Edge index to start the loop.
            position: Position along the edge (0-1).
            relative: If True, position is relative to edge; else world.

        Returns:
            True if successful.
        """
        with UndoChunk("Insert Edge Loop"):
            try:
                cmds.select(f"{mesh}.e[{edge}]", replace=True)
                cmds.polyInsertEdgeLoop(mesh, position=position, relative=relative, ch=False)
                return True
            except:
                return False

    # =====================================================================
    # SPLIT / CUT
    # =====================================================================

    def split_edges(self, mesh: str, edges: List[int]) -> bool:
        """Split edges (polySplit)."""
        with UndoChunk("Split Edges"):
            try:
                cmds.select([f"{mesh}.e[{i}]" for i in edges], replace=True)
                cmds.polySplit(mesh, ch=False)
                return True
            except:
                return False

    # =====================================================================
    # DETACH / EXTRACT
    # =====================================================================

    def detach_faces(self, mesh: str, faces: List[int]) -> bool:
        """Detach faces from the mesh (polyChipOff)."""
        with UndoChunk("Detach Faces"):
            try:
                cmds.select([f"{mesh}.f[{i}]" for i in faces], replace=True)
                cmds.polyChipOff(mesh, ch=False)
                return True
            except:
                return False

    # =====================================================================
    # SELECTION HELPERS
    # =====================================================================

    def select_by_type(self, mesh: str, component_type: str,
                       indices: Optional[List[int]] = None) -> bool:
        """Select mesh components by type."""
        if indices is None:
            # Select all components of that type
            cmds.select(f"{mesh}.{component_type}[*]", replace=True)
        else:
            cmds.select([f"{mesh}.{component_type}[{i}]" for i in indices], replace=True)
        return True

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
    "MeshEditingTools",
]