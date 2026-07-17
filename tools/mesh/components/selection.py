"""
tools/mesh/components/selection.py

Component selection utilities - Smart, topology-aware selection helpers.
One of the most useful modules in a production mesh pipeline.
"""

from __future__ import annotations

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Union, Dict

from ..core.editor import MeshEditor
from ..types import MeshSelection


class MeshSelectionTools:
    """
    Advanced component selection utilities for mesh topology work.
    """

    def __init__(self, editor: MeshEditor):
        self.editor = editor

    # =====================================================================
    # BORDER & BOUNDARY SELECTION
    # =====================================================================

    def select_border_edges(self, mesh: Optional[str] = None):
        """Select all open border edges."""
        target = mesh or self.editor.get_active_shape()
        borders = cmds.polyInfo(target, borderEdges=True) or []
        if borders:
            edge_ids = [int(x.split()[-1]) for x in borders if x.startswith("EDGE")]
            cmds.select([f"{target}.e[{eid}]" for eid in edge_ids])

    def select_border_vertices(self, mesh: Optional[str] = None):
        """Select vertices on mesh borders."""
        target = mesh or self.editor.get_active_shape()
        self.select_border_edges(target)
        cmds.polyListComponentConversion(fromEdge=True, toVertex=True)

    def select_holes(self, mesh: Optional[str] = None):
        """Select faces that are part of holes (border loops)."""
        target = mesh or self.editor.get_active_shape()
        self.select_border_edges(target)
        cmds.polyListComponentConversion(fromEdge=True, toFace=True)

    # =====================================================================
    # EDGE LOOPS & RINGS
    # =====================================================================

    def select_edge_loop(self, start_edge: int, mesh: Optional[str] = None):
        """Select a full edge loop starting from one edge."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(f"{target}.e[{start_edge}]")
        cmds.polySelectSp(loop=True, edgeRing=False)

    def select_edge_ring(self, start_edge: int, mesh: Optional[str] = None):
        """Select a full edge ring."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(f"{target}.e[{start_edge}]")
        cmds.polySelectSp(loop=False, edgeRing=True)

    def select_parallel_loops(self, count: int = 3, mesh: Optional[str] = None):
        """Select multiple parallel edge loops (useful for facial loops)."""
        pass  # Can be expanded

    # =====================================================================
    # FACE ISLANDS & SHELLS
    # =====================================================================

    def select_largest_face_island(self, mesh: Optional[str] = None):
        """Select the largest connected group of faces."""
        target = mesh or self.editor.get_active_shape()
        # Maya has no built-in, but we can use this trick:
        cmds.polySelectConstraint(shell=True, largest=True)
        cmds.polySelectConstraint(disable=True)  # Turn off constraint

    def select_all_face_islands(self, mesh: Optional[str] = None):
        """Select one face from each island/shell."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(target)
        cmds.polySelectConstraint(mode=2, type=0x0008, shell=True)  # Shell mode

    # =====================================================================
    # TOPOLOGY-AWARE SELECTION
    # =====================================================================

    def select_non_manifold(self, mesh: Optional[str] = None):
        """Select all non-manifold components."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(clear=True)
        
        # Non-manifold vertices
        nm_verts = cmds.polyInfo(target, nonManifoldVertices=True) or []
        if nm_verts:
            vert_ids = [int(x.split()[-1]) for x in nm_verts if "VERTEX" in x]
            cmds.select([f"{target}.vtx[{v}]" for v in vert_ids], add=True)

        # Non-manifold edges
        nm_edges = cmds.polyInfo(target, nonManifoldEdges=True) or []
        if nm_edges:
            edge_ids = [int(x.split()[-1]) for x in nm_edges if "EDGE" in x]
            cmds.select([f"{target}.e[{e}]" for e in edge_ids], add=True)

    def select_lamina_faces(self, mesh: Optional[str] = None):
        """Select lamina (overlapping) faces."""
        target = mesh or self.editor.get_active_shape()
        lamina = cmds.polyInfo(target, laminaFaces=True) or []
        if lamina:
            face_ids = [int(x.split()[-1]) for x in lamina if "FACE" in x]
            cmds.select([f"{target}.f[{f}]" for f in face_ids])

    def select_ngons(self, min_sides: int = 5, mesh: Optional[str] = None):
        """Select faces with more than N sides."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(clear=True)
        face_count = cmds.polyEvaluate(target, face=True)

        for i in range(face_count):
            if cmds.polyEvaluate(target, faceVertexCount=i) >= min_sides:
                cmds.select(f"{target}.f[{i}]", add=True)

    # =====================================================================
    # UV & TEXTURE SELECTION
    # =====================================================================

    def select_uv_shells(self, mesh: Optional[str] = None):
        """Select one face per UV shell."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(target)
        cmds.polySelectConstraint(mode=2, type=0x0010, uvShell=True)  # UV Shell

    def select_overlapping_uvs(self, mesh: Optional[str] = None):
        """Select faces with overlapping UVs (requires UV checker)."""
        # Advanced - usually done via UV editor tools or custom script
        pass

    # =====================================================================
    # UTILITY FUNCTIONS
    # =====================================================================

    def convert_selection(self, from_type: str, to_type: str):
        """Convert between component types (vtx, edge, face, uv)."""
        conversion_map = {
            ("edge", "vertex"): "toVertex",
            ("edge", "face"): "toFace",
            ("face", "edge"): "toEdge",
            ("vertex", "edge"): "toEdge",
            # Add more as needed
        }
        key = (from_type.lower(), to_type.lower())
        if key in conversion_map:
            cmds.polyListComponentConversion(**{conversion_map[key]: True})

    def grow_selection(self, iterations: int = 1):
        """Grow current component selection."""
        for _ in range(iterations):
            cmds.polySelectConstraint(mode=1, relative=True, expand=True)

    def shrink_selection(self, iterations: int = 1):
        """Shrink current component selection."""
        for _ in range(iterations):
            cmds.polySelectConstraint(mode=1, relative=True, shrink=True)

    def get_selected_components(self) -> Dict[str, List[int]]:
        """Return currently selected components by type."""
        selection = cmds.ls(selection=True, flatten=True)
        result = {"vertices": [], "edges": [], "faces": []}

        for item in selection:
            if '.vtx[' in item:
                result["vertices"].append(int(item.split('[')[-1].strip(']')))
            elif '.e[' in item:
                result["edges"].append(int(item.split('[')[-1].strip(']')))
            elif '.f[' in item:
                result["faces"].append(int(item.split('[')[-1].strip(']')))
        
        return result


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

__all__ = ["MeshSelectionTools"]