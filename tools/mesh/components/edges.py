"""
tools/mesh/components/edges.py

EdgeTools - Edge-level operations and advanced topology analysis.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om # type: ignore

from ..core.editor import MeshEditor
from ..types import MeshSelection, MeshIssue, IssueSeverity, ComponentType


class EdgeTools:
    """
    Edge manipulation and comprehensive topology analysis.
    """

    def __init__(self, editor: MeshEditor):
        self.editor = editor

    # =====================================================================
    # EDGE SELECTION HELPERS
    # =====================================================================

    def select_edge_loop(self, edge_id: int, mesh: Optional[str] = None):
        """Select full edge loop from a starting edge."""
        target = mesh or self.editor.get_active_shape()
        cmds.polySelectSp(loop=True, edgeRing=False)

    def select_edge_ring(self, edge_id: int, mesh: Optional[str] = None):
        """Select full edge ring."""
        target = mesh or self.editor.get_active_shape()
        cmds.polySelectSp(loop=False, edgeRing=True)

    def select_border_edges(self, mesh: Optional[str] = None):
        """Select all open border edges."""
        target = mesh or self.editor.get_active_shape()
        border = cmds.polyInfo(target, borderEdges=True) or []
        if border:
            edge_ids = [int(x.split()[-1]) for x in border if "EDGE" in x]
            cmds.select([f"{target}.e[{eid}]" for eid in edge_ids])

    # =====================================================================
    # TOPOLOGY ANALYSIS
    # =====================================================================

    def analyze_topology(self, mesh: Optional[str] = None) -> Dict:
        """Comprehensive edge topology analysis."""
        target = mesh or self.editor.get_active_shape()
        
        analysis = {
            "total_edges": cmds.polyEvaluate(target, edge=True),
            "border_edges": 0,
            "non_manifold_edges": 0,
            "hard_edges": 0,
            "soft_edges": 0,
            "edge_loops": 0,
            "edge_rings": 0,
            "average_edge_length": 0.0,
            "max_edge_length": 0.0,
        }

        # Border edges
        border = cmds.polyInfo(target, borderEdges=True) or []
        analysis["border_edges"] = len(border) // 2

        # Non-manifold edges
        nm_edges = cmds.polyInfo(target, nonManifoldEdges=True) or []
        analysis["non_manifold_edges"] = len(nm_edges) // 2

        # Hard vs Soft edges
        hard_edges = cmds.polySoftEdge(target, query=True, angle=0) or []
        analysis["hard_edges"] = len(hard_edges)

        return analysis

    def find_edge_flow_issues(self, mesh: Optional[str] = None) -> List[MeshIssue]:
        """Detect poor edge flow / topology problems."""
        issues = []
        target = mesh or self.editor.get_active_shape()

        # Non-manifold
        nm = cmds.polyInfo(target, nonManifoldEdges=True) or []
        if nm:
            issues.append(MeshIssue(
                severity=IssueSeverity.ERROR,
                issue_type="non_manifold_edge",
                description=f"{len(nm)//2} non-manifold edges",
                component_type=ComponentType.EDGE,
                mesh_name=target
            ))

        # Star vertices (5+ edges) - often bad for deformation
        # Can be expanded with custom logic

        return issues

    # =====================================================================
    # EDGE OPERATIONS
    # =====================================================================

    def harden(self, edges: Optional[List[int]] = None, mesh: Optional[str] = None):
        """Make edges hard (crease)."""
        target = mesh or self.editor.get_active_shape()
        if edges:
            edge_list = [f"{target}.e[{e}]" for e in edges]
            cmds.polySoftEdge(edge_list, angle=0)
        else:
            cmds.polySoftEdge(angle=0)

    def soften(self, edges: Optional[List[int]] = None, mesh: Optional[str] = None):
        """Make edges soft."""
        target = mesh or self.editor.get_active_shape()
        if edges:
            edge_list = [f"{target}.e[{e}]" for e in edges]
            cmds.polySoftEdge(edge_list, angle=180)
        else:
            cmds.polySoftEdge(angle=180)

    def chamfer(self, edges: List[int], width: float = 0.2, segments: int = 2):
        """Chamfer selected edges."""
        if not edges:
            return
        target = self.editor.get_active_shape()
        edge_list = [f"{target}.e[{e}]" for e in edges]
        cmds.polyChamfer(edge_list, offset=width, segments=segments)

    def bridge(self, edge1: int, edge2: int):
        """Bridge two edges."""
        cmds.polyBridgeEdge([edge1, edge2], divisions=1)

    def extrude(self, edges: List[int], length: float = 0.5):
        """Extrude edges."""
        if edges:
            cmds.polyExtrudeEdge(edges, length=length)

    # =====================================================================
    # OPENMAYA EDGE ANALYSIS
    # =====================================================================

    def get_edge_lengths(self, mesh: str) -> List[float]:
        """Return lengths of all edges using OpenMaya."""
        dag = self.editor.get_dag_path(mesh)
        fn_mesh = om.MFnMesh(dag)
        lengths = []

        for i in range(fn_mesh.numEdges):
            v1, v2 = fn_mesh.getEdgeVertices(i)
            p1 = fn_mesh.getPoint(v1, om.MSpace.kWorld)
            p2 = fn_mesh.getPoint(v2, om.MSpace.kWorld)
            lengths.append((p1 - p2).length())

        return lengths

    def get_longest_edge(self, mesh: str) -> Tuple[int, float]:
        """Return (edge_id, length) of the longest edge."""
        lengths = self.get_edge_lengths(mesh)
        if not lengths:
            return -1, 0.0
        max_idx = lengths.index(max(lengths))
        return max_idx, lengths[max_idx]

    def get_shortest_edge(self, mesh: str) -> Tuple[int, float]:
        lengths = self.get_edge_lengths(mesh)
        if not lengths:
            return -1, 0.0
        min_idx = lengths.index(min(lengths))
        return min_idx, lengths[min_idx]

    # =====================================================================
    # UTILITY
    # =====================================================================

    def select_all(self, mesh: Optional[str] = None):
        target = mesh or self.editor.get_active_shape()
        cmds.select(f"{target}.e[*]")

    def convert_to_vertices(self):
        """Convert current edge selection to vertices."""
        cmds.polyListComponentConversion(fromEdge=True, toVertex=True)

    def convert_to_faces(self):
        """Convert current edge selection to faces."""
        cmds.polyListComponentConversion(fromEdge=True, toFace=True)


# =============================================================================
# GLOBAL HELPER
# =============================================================================

__all__ = ["EdgeTools"]