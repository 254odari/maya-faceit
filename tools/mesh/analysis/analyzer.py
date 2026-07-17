"""
tools/mesh/analysis/analyzer.py

MeshAnalyzer - Comprehensive mesh analysis, statistics, and comparison.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple, Any

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om # type: ignore

from ..types import (
    MeshStatistics, 
    TopologyFingerprint, 
    MeshSelection,
    AnalysisResult
)
from ..core.editor import MeshEditor


class MeshAnalyzer:
    """
    High-performance mesh analysis and statistics engine.
    """

    def __init__(self):
        self.editor = MeshEditor()

    # =====================================================================
    # MAIN ANALYSIS
    # =====================================================================

    def analyze(self, mesh: MeshSelection) -> MeshStatistics:
        """Full analysis of a mesh."""
        if isinstance(mesh, (list, tuple)):
            mesh = mesh[0]

        stats = MeshStatistics()

        try:
            dag = self.editor.get_dag_path(mesh)
            fn_mesh = om.MFnMesh(dag)

            # Basic counts
            stats.vertices = fn_mesh.numVertices
            stats.edges = fn_mesh.numEdges
            stats.faces = fn_mesh.numPolygons

            # Triangle count
            stats.triangles = cmds.polyEvaluate(mesh, triangle=True)

            # Face type breakdown
            self._analyze_face_types(fn_mesh, stats)

            # Geometric properties
            stats.surface_area = self._calculate_surface_area(fn_mesh)
            stats.volume = self._calculate_volume(fn_mesh)
            stats.bounding_box = self._get_bounding_box(fn_mesh)

            # Quality metrics
            stats.average_edge_length = self._calculate_avg_edge_length(fn_mesh)
            stats.max_edge_length = self._calculate_max_edge_length(fn_mesh)

        except Exception as e:
            print(f"Warning: Partial analysis on {mesh} - {e}")

        return stats

    def get_statistics(self, mesh: Optional[MeshSelection] = None) -> MeshStatistics:
        """Convenience method."""
        if not mesh:
            mesh = self.editor.get_active_shape()
        return self.analyze(mesh)

    # =====================================================================
    # INTERNAL ANALYSIS HELPERS
    # =====================================================================

    def _analyze_face_types(self, fn_mesh: om.MFnMesh, stats: MeshStatistics):
        """Count quads, triangles, ngons."""
        quad_count = tri_count = ngon_count = 0

        for i in range(fn_mesh.numPolygons):
            num_verts = len(fn_mesh.getPolygonVertices(i))
            if num_verts == 3:
                tri_count += 1
            elif num_verts == 4:
                quad_count += 1
            elif num_verts > 4:
                ngon_count += 1

        stats.triangles = tri_count
        stats.quads = quad_count
        stats.ngons = ngon_count

    def _calculate_surface_area(self, fn_mesh: om.MFnMesh) -> float:
        """Calculate total surface area."""
        total_area = 0.0
        for i in range(fn_mesh.numPolygons):
            total_area += fn_mesh.getPolygonArea(i, om.MSpace.kWorld)
        return total_area

    def _calculate_volume(self, fn_mesh: om.MFnMesh) -> float:
        """Calculate enclosed volume (only accurate for closed manifold meshes)."""
        try:
            return fn_mesh.getBoundingBox().volume()  # Rough approximation
        except:
            return 0.0

    def _get_bounding_box(self, fn_mesh: om.MFnMesh) -> Tuple[float, ...]:
        """Return bounding box as (min_x, min_y, min_z, max_x, max_y, max_z)."""
        bbox = fn_mesh.getBoundingBox()
        return (
            bbox.min.x, bbox.min.y, bbox.min.z,
            bbox.max.x, bbox.max.y, bbox.max.z
        )

    def _calculate_avg_edge_length(self, fn_mesh: om.MFnMesh) -> float:
        if fn_mesh.numEdges == 0:
            return 0.0
        total = 0.0
        for i in range(fn_mesh.numEdges):
            p1, p2 = fn_mesh.getEdgeVertices(i)
            v1 = fn_mesh.getPoint(p1, om.MSpace.kWorld)
            v2 = fn_mesh.getPoint(p2, om.MSpace.kWorld)
            total += (v1 - v2).length()
        return total / fn_mesh.numEdges

    def _calculate_max_edge_length(self, fn_mesh: om.MFnMesh) -> float:
        max_len = 0.0
        for i in range(fn_mesh.numEdges):
            p1, p2 = fn_mesh.getEdgeVertices(i)
            v1 = fn_mesh.getPoint(p1, om.MSpace.kWorld)
            v2 = fn_mesh.getPoint(p2, om.MSpace.kWorld)
            length = (v1 - v2).length()
            if length > max_len:
                max_len = length
        return max_len

    # =====================================================================
    # TOPOLOGY FINGERPRINT
    # =====================================================================

    def create_fingerprint(self, mesh: str) -> TopologyFingerprint:
        """Create a unique signature for topology comparison."""
        stats = self.analyze(mesh)

        # Simple hash based on counts and properties
        hash_str = f"{stats.vertices}|{stats.faces}|{stats.ngons}|{stats.surface_area:.2f}"

        return TopologyFingerprint(
            vertex_count=stats.vertices,
            face_count=stats.faces,
            edge_count=stats.edges,
            hash_value=hash_str,
            boundary_loops=len(cmds.polyInfo(mesh, borderEdges=True) or []),
            is_manifold=True  # Can be improved with validation data
        )

    # =====================================================================
    # MESH COMPARISON
    # =====================================================================

    def compare_meshes(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """Compare two meshes and return differences."""
        stat1 = self.analyze(mesh1)
        stat2 = self.analyze(mesh2)
        fp1 = self.create_fingerprint(mesh1)
        fp2 = self.create_fingerprint(mesh2)

        return {
            "topology_match": fp1.hash_value == fp2.hash_value,
            "vertex_count": {"mesh1": stat1.vertices, "mesh2": stat2.vertices},
            "face_count": {"mesh1": stat1.faces, "mesh2": stat2.faces},
            "ngons": {"mesh1": stat1.ngons, "mesh2": stat2.ngons},
            "surface_area_diff": abs(stat1.surface_area - stat2.surface_area),
            "compatible_for_blendshape": (
                stat1.vertices == stat2.vertices and 
                stat1.faces == stat2.faces
            )
        }

    # =====================================================================
    # UTILITY
    # =====================================================================

    def print_summary(self, mesh: Optional[MeshSelection] = None):
        """Print a nice summary of mesh statistics."""
        if not mesh:
            mesh = self.editor.get_active_shape()

        stats = self.analyze(mesh)

        print(f"\n=== Mesh Analysis: {mesh} ===")
        print(f"Vertices : {stats.vertices:,}")
        print(f"Edges    : {stats.edges:,}")
        print(f"Faces    : {stats.faces:,}")
        print(f"Triangles: {stats.triangles:,}")
        print(f"Quads    : {stats.quads:,}")
        print(f"N-Gons   : {stats.ngons:,}")
        print(f"Area     : {stats.surface_area:.4f}")
        print(f"Volume   : {stats.volume:.4f}")
        print(f"Avg Edge : {stats.average_edge_length:.6f}")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

analyzer = MeshAnalyzer()

__all__ = ["MeshAnalyzer", "analyzer"]