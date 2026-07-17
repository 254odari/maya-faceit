# -*- coding: utf-8 -*-
"""
tools.mesh.analysis.statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive statistical analysis for polygon meshes.

Provides both per‑mesh and scene‑wide statistics using Maya's API.
"""

import math
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Dict, Any, List, Optional, Tuple
from .analyzer import MeshAnalyzer
from ..types import MeshStats


class MeshStatistics:
    """
    Gathers and aggregates statistics for one or more meshes.
    """

    def __init__(self):
        self.analyzer = MeshAnalyzer()

    # =====================================================================
    # SINGLE MESH STATISTICS
    # =====================================================================

    def get_stats(self, mesh: str) -> MeshStats:
        """
        Get detailed statistics for a single mesh.
        Uses MeshAnalyzer for most data.
        """
        if not cmds.objExists(mesh):
            raise ValueError(f"Mesh '{mesh}' does not exist.")
        return self.analyzer.analyze(mesh)

    def get_area(self, mesh: str) -> float:
        """
        Calculate the total surface area of the mesh.
        """
        if not cmds.objExists(mesh):
            return 0.0
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        area = 0.0
        for i in range(fn_mesh.numPolygons()):
            area += fn_mesh.getPolygonArea(i, om2.MSpace.kWorld)
        return area

    def get_volume(self, mesh: str) -> float:
        """
        Calculate the volume of a closed mesh.
        Returns 0 if the mesh is open (non‑watertight).
        """
        if not cmds.objExists(mesh):
            return 0.0
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        # Use Maya's built-in volume calculation
        # MFnMesh::getVolume() is not available in Python API directly
        # We'll use polyInfo as a fallback.
        info = cmds.polyInfo(mesh, volume=True)
        if info:
            # Line format: "Volume: 12.345"
            try:
                vol_str = info[0].split(':')[-1].strip()
                return float(vol_str)
            except:
                pass
        return 0.0

    def get_bbox(self, mesh: str) -> Tuple[float, float, float, float, float, float]:
        """
        Return the bounding box as (minX, minY, minZ, maxX, maxY, maxZ).
        """
        if not cmds.objExists(mesh):
            return (0,0,0,0,0,0)
        bbox = cmds.exactWorldBoundingBox(mesh)
        return tuple(bbox)

    def get_face_aspect_ratios(self, mesh: str) -> List[float]:
        """
        Compute the aspect ratio (longest edge / shortest edge) for each face.
        Useful for detecting poorly shaped faces.
        """
        if not cmds.objExists(mesh):
            return []
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        ratios = []
        for i in range(fn_mesh.numPolygons()):
            verts = fn_mesh.getPolygonVertices(i)
            if len(verts) < 3:
                continue
            positions = [fn_mesh.getPoint(v, om2.MSpace.kWorld) for v in verts]
            # Compute edge lengths
            edge_lengths = []
            for j in range(len(positions)):
                p1 = positions[j]
                p2 = positions[(j + 1) % len(positions)]
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dz = p1.z - p2.z
                edge_lengths.append(math.sqrt(dx*dx + dy*dy + dz*dz))
            if edge_lengths:
                longest = max(edge_lengths)
                shortest = min(edge_lengths)
                ratios.append(longest / shortest if shortest > 1e-12 else 0.0)
        return ratios

    # =====================================================================
    # SCENE‑WIDE STATISTICS
    # =====================================================================

    def get_all_stats(self) -> Dict[str, MeshStats]:
        """
        Collect statistics for every mesh in the scene.
        Returns a dict mapping mesh transform names to MeshStats.
        """
        all_stats = {}
        meshes = cmds.ls(type='mesh')
        for m in meshes:
            # Get the transform parent
            parents = cmds.listRelatives(m, parent=True, fullPath=True)
            if parents:
                mesh_name = parents[0]
                try:
                    all_stats[mesh_name] = self.get_stats(mesh_name)
                except Exception as e:
                    print(f"Error analyzing {mesh_name}: {e}")
        return all_stats

    def get_scene_summary(self) -> Dict[str, Any]:
        """
        Aggregate statistics across all meshes in the scene.
        """
        all_stats = self.get_all_stats()
        total_meshes = len(all_stats)
        total_verts = sum(s.vertex_count for s in all_stats.values())
        total_edges = sum(s.edge_count for s in all_stats.values())
        total_faces = sum(s.face_count for s in all_stats.values())
        total_ngons = sum(s.ngon_count for s in all_stats.values())
        total_non_manifold = sum(s.non_manifold_edges for s in all_stats.values())
        total_lamina = sum(s.lamina_faces for s in all_stats.values())
        total_open_borders = sum(s.open_borders for s in all_stats.values())

        return {
            'total_meshes': total_meshes,
            'total_vertices': total_verts,
            'total_edges': total_edges,
            'total_faces': total_faces,
            'total_ngons': total_ngons,
            'total_non_manifold_edges': total_non_manifold,
            'total_lamina_faces': total_lamina,
            'total_open_borders': total_open_borders,
            'average_vertices_per_mesh': total_verts / total_meshes if total_meshes else 0,
            'average_faces_per_mesh': total_faces / total_meshes if total_meshes else 0,
        }

    def get_histogram(self, mesh: str, attribute: str = 'face_area', bins: int = 10) -> List[Tuple[float, float, int]]:
        """
        Build a histogram for a given attribute across faces or vertices.
        Supported attributes: 'face_area', 'edge_length', 'vertex_valence'.
        """
        if not cmds.objExists(mesh):
            return []
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)

        values = []
        if attribute == 'face_area':
            for i in range(fn_mesh.numPolygons()):
                values.append(fn_mesh.getPolygonArea(i, om2.MSpace.kWorld))
        elif attribute == 'vertex_valence':
            for i in range(fn_mesh.numVertices()):
                values.append(len(fn_mesh.getConnectedVertices(i)))
        elif attribute == 'edge_length':
            # Get all edge vertices and compute lengths
            edge_vertices = fn_mesh.getEdges()
            for e in range(len(edge_vertices)//2):
                v1 = edge_vertices[2*e]
                v2 = edge_vertices[2*e+1]
                p1 = fn_mesh.getPoint(v1, om2.MSpace.kWorld)
                p2 = fn_mesh.getPoint(v2, om2.MSpace.kWorld)
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dz = p1.z - p2.z
                values.append(math.sqrt(dx*dx + dy*dy + dz*dz))
        else:
            raise ValueError(f"Unsupported histogram attribute: {attribute}")

        if not values:
            return []
        min_val = min(values)
        max_val = max(values)
        if min_val == max_val:
            return [(min_val, max_val, len(values))]
        bin_width = (max_val - min_val) / bins
        bins_data = []
        for i in range(bins):
            low = min_val + i * bin_width
            high = low + bin_width
            count = sum(1 for v in values if low <= v < high)
            bins_data.append((low, high, count))
        # Include values exactly at max
        bins_data[-1] = (bins_data[-1][0], max_val, bins_data[-1][2] + sum(1 for v in values if v == max_val))
        return bins_data

    # =====================================================================
    # REPORTING
    # =====================================================================

    def print_report(self, mesh: Optional[str] = None):
        """
        Print a formatted report for a specific mesh or all meshes.
        """
        if mesh:
            stats = self.get_stats(mesh)
            area = self.get_area(mesh)
            volume = self.get_volume(mesh)
            bbox = self.get_bbox(mesh)
            print(f"\n=== Mesh Statistics: {mesh} ===")
            print(f"  Vertices: {stats.vertex_count}")
            print(f"  Edges: {stats.edge_count}")
            print(f"  Faces: {stats.face_count}")
            print(f"  UVs: {stats.uv_count}")
            print(f"  Non‑manifold edges: {stats.non_manifold_edges}")
            print(f"  Lamina faces: {stats.lamina_faces}")
            print(f"  Ngons: {stats.ngon_count}")
            print(f"  Open borders: {stats.open_borders}")
            print(f"  Surface area: {area:.3f}")
            print(f"  Volume: {volume:.3f}")
            print(f"  Bounding box: {bbox}")
        else:
            summary = self.get_scene_summary()
            print("\n=== Scene Summary ===")
            for key, value in summary.items():
                print(f"  {key}: {value}")


# -----------------------------------------------------------------------------
# Global instance
# -----------------------------------------------------------------------------

statistics = MeshStatistics()

__all__ = ["MeshStatistics", "statistics"]