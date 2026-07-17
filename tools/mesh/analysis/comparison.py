# -*- coding: utf-8 -*-
"""
tools.mesh.analysis.comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare two meshes for topology, UVs, normals, vertex positions, etc.
"""

import math
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Dict, List, Tuple, Optional, Any
from .analyzer import MeshAnalyzer
from .statistics import MeshStatistics
from ..types import MeshStats


class MeshComparison:
    """
    Compare two meshes to determine if they are similar or identical.
    """

    def __init__(self):
        self.analyzer = MeshAnalyzer()
        self.statistics = MeshStatistics()

    # =====================================================================
    # COMPARISON METHODS
    # =====================================================================

    def compare_vertex_count(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """Compare vertex counts."""
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        v1 = cmds.polyEvaluate(mesh1, vertex=True)
        v2 = cmds.polyEvaluate(mesh2, vertex=True)
        return {
            'mesh1': v1,
            'mesh2': v2,
            'match': v1 == v2,
            'difference': v2 - v1
        }

    def compare_face_count(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """Compare face counts."""
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        f1 = cmds.polyEvaluate(mesh1, face=True)
        f2 = cmds.polyEvaluate(mesh2, face=True)
        return {
            'mesh1': f1,
            'mesh2': f2,
            'match': f1 == f2,
            'difference': f2 - f1
        }

    def compare_edge_count(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """Compare edge counts."""
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        e1 = cmds.polyEvaluate(mesh1, edge=True)
        e2 = cmds.polyEvaluate(mesh2, edge=True)
        return {
            'mesh1': e1,
            'mesh2': e2,
            'match': e1 == e2,
            'difference': e2 - e1
        }

    def compare_uv_count(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """Compare UV counts (using current UV set)."""
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        # Get shapes
        shape1 = cmds.listRelatives(mesh1, shapes=True)[0]
        shape2 = cmds.listRelatives(mesh2, shapes=True)[0]
        uv1 = cmds.polyEvaluate(shape1, uvCoord=True)
        uv2 = cmds.polyEvaluate(shape2, uvCoord=True)
        return {
            'mesh1': uv1,
            'mesh2': uv2,
            'match': uv1 == uv2,
            'difference': uv2 - uv1
        }

    def compare_vertex_positions(self, mesh1: str, mesh2: str, tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Compare vertex positions within a tolerance.
        Returns dict with match status and statistics.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        # Get vertex positions
        verts1 = cmds.ls(f"{mesh1}.vtx[*]", flatten=True)
        verts2 = cmds.ls(f"{mesh2}.vtx[*]", flatten=True)
        if len(verts1) != len(verts2):
            return {
                'match': False,
                'reason': 'Vertex count mismatch',
                'mesh1_count': len(verts1),
                'mesh2_count': len(verts2)
            }
        pos1 = cmds.xform(verts1, q=True, ws=True, t=True)
        pos2 = cmds.xform(verts2, q=True, ws=True, t=True)
        # pos1 and pos2 are flat lists: [x0,y0,z0, x1,y1,z1, ...]
        max_diff = 0.0
        avg_diff = 0.0
        count = len(pos1) // 3
        for i in range(count):
            dx = pos1[3*i] - pos2[3*i]
            dy = pos1[3*i+1] - pos2[3*i+1]
            dz = pos1[3*i+2] - pos2[3*i+2]
            diff = math.sqrt(dx*dx + dy*dy + dz*dz)
            max_diff = max(max_diff, diff)
            avg_diff += diff
        avg_diff /= count if count > 0 else 1
        return {
            'match': max_diff <= tolerance,
            'max_difference': max_diff,
            'average_difference': avg_diff,
            'tolerance': tolerance,
            'vertex_count': count
        }

    def compare_topology(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """
        Compare topology by checking vertex count, face count, and face vertex counts.
        Returns a detailed match result.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        vc = self.compare_vertex_count(mesh1, mesh2)
        fc = self.compare_face_count(mesh1, mesh2)
        ec = self.compare_edge_count(mesh1, mesh2)
        match = vc['match'] and fc['match'] and ec['match']
        # Additional topology check: face vertex counts
        if match:
            # Get face vertex counts for each mesh
            sel1 = om2.MSelectionList()
            sel1.add(mesh1)
            dag1 = sel1.getDagPath(0)
            fn_mesh1 = om2.MFnMesh(dag1)
            sel2 = om2.MSelectionList()
            sel2.add(mesh2)
            dag2 = sel2.getDagPath(0)
            fn_mesh2 = om2.MFnMesh(dag2)
            # Compare face vertex counts
            face_vc1 = [len(fn_mesh1.getPolygonVertices(i)) for i in range(fn_mesh1.numPolygons())]
            face_vc2 = [len(fn_mesh2.getPolygonVertices(i)) for i in range(fn_mesh2.numPolygons())]
            if face_vc1 != face_vc2:
                match = False
        return {
            'match': match,
            'vertex_count': vc,
            'face_count': fc,
            'edge_count': ec
        }

    def compare_uv_sets(self, mesh1: str, mesh2: str) -> Dict[str, Any]:
        """
        Compare UV set names and count.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        shape1 = cmds.listRelatives(mesh1, shapes=True)[0]
        shape2 = cmds.listRelatives(mesh2, shapes=True)[0]
        sets1 = set(cmds.polyUVSet(shape1, q=True, allUVSets=True) or [])
        sets2 = set(cmds.polyUVSet(shape2, q=True, allUVSets=True) or [])
        return {
            'match': sets1 == sets2,
            'mesh1_sets': sorted(sets1),
            'mesh2_sets': sorted(sets2),
            'common_sets': sorted(sets1 & sets2),
            'only_in_mesh1': sorted(sets1 - sets2),
            'only_in_mesh2': sorted(sets2 - sets1)
        }

    def compare_uv_values(self, mesh1: str, mesh2: str, uv_set: Optional[str] = None, tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Compare UV coordinates for a specific UV set (or current).
        Requires identical vertex count.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        shape1 = cmds.listRelatives(mesh1, shapes=True)[0]
        shape2 = cmds.listRelatives(mesh2, shapes=True)[0]
        if uv_set is None:
            uv_set = cmds.polyUVSet(shape1, q=True, currentUVSet=True)[0]
        # Get UVs
        uvs1 = cmds.polyEditUV(shape1, q=True, u=True, v=True, uvSet=uv_set) or []
        uvs2 = cmds.polyEditUV(shape2, q=True, u=True, v=True, uvSet=uv_set) or []
        if not uvs1 or not uvs2:
            return {'match': False, 'reason': 'No UVs in one or both meshes'}
        if len(uvs1) != len(uvs2):
            return {'match': False, 'reason': f'UV count mismatch: {len(uvs1)//2} vs {len(uvs2)//2}'}
        # Compare U and V separately
        u1 = uvs1[0::2]
        v1 = uvs1[1::2]
        u2 = uvs2[0::2]
        v2 = uvs2[1::2]
        max_u_diff = max(abs(u1[i]-u2[i]) for i in range(len(u1))) if u1 else 0.0
        max_v_diff = max(abs(v1[i]-v2[i]) for i in range(len(v1))) if v1 else 0.0
        avg_u_diff = sum(abs(u1[i]-u2[i]) for i in range(len(u1))) / len(u1) if u1 else 0.0
        avg_v_diff = sum(abs(v1[i]-v2[i]) for i in range(len(v1))) / len(v1) if v1 else 0.0
        return {
            'match': max_u_diff <= tolerance and max_v_diff <= tolerance,
            'max_u_difference': max_u_diff,
            'max_v_difference': max_v_diff,
            'avg_u_difference': avg_u_diff,
            'avg_v_difference': avg_v_diff,
            'uv_count': len(u1),
            'tolerance': tolerance
        }

    def compare_normals(self, mesh1: str, mesh2: str, tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Compare vertex normals.
        Requires identical vertex count.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        # Get normals (assuming per‑vertex normals in world space)
        normals1 = cmds.polyNormalPerVertex(f"{mesh1}.vtx[*]", q=True, normal=True, ws=True) or []
        normals2 = cmds.polyNormalPerVertex(f"{mesh2}.vtx[*]", q=True, normal=True, ws=True) or []
        if len(normals1) != len(normals2):
            return {'match': False, 'reason': 'Normal count mismatch'}
        # normals are flat: [nx0,ny0,nz0, nx1,ny1,nz1, ...]
        count = len(normals1) // 3
        max_diff = 0.0
        avg_diff = 0.0
        for i in range(count):
            dx = normals1[3*i] - normals2[3*i]
            dy = normals1[3*i+1] - normals2[3*i+1]
            dz = normals1[3*i+2] - normals2[3*i+2]
            diff = math.sqrt(dx*dx + dy*dy + dz*dz)
            max_diff = max(max_diff, diff)
            avg_diff += diff
        avg_diff /= count if count > 0 else 1
        return {
            'match': max_diff <= tolerance,
            'max_difference': max_diff,
            'average_difference': avg_diff,
            'tolerance': tolerance
        }

    def compare_bbox(self, mesh1: str, mesh2: str, tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Compare bounding boxes.
        """
        if not cmds.objExists(mesh1) or not cmds.objExists(mesh2):
            return {'match': False, 'reason': 'Mesh does not exist'}
        bbox1 = cmds.exactWorldBoundingBox(mesh1)
        bbox2 = cmds.exactWorldBoundingBox(mesh2)
        if not bbox1 or not bbox2:
            return {'match': False, 'reason': 'Could not compute bounding box'}
        # bbox is [minX, minY, minZ, maxX, maxY, maxZ]
        max_diff = 0.0
        for i in range(6):
            diff = abs(bbox1[i] - bbox2[i])
            if diff > max_diff:
                max_diff = diff
        return {
            'match': max_diff <= tolerance,
            'max_difference': max_diff,
            'mesh1_bbox': bbox1,
            'mesh2_bbox': bbox2,
            'tolerance': tolerance
        }

    def compare_all(self, mesh1: str, mesh2: str, tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Run all comparisons and return a comprehensive result.
        """
        result = {
            'mesh1': mesh1,
            'mesh2': mesh2,
            'tolerance': tolerance,
            'matches': {},
            'overall_match': True
        }
        # Run each comparison
        result['matches']['vertex_count'] = self.compare_vertex_count(mesh1, mesh2)
        result['matches']['face_count'] = self.compare_face_count(mesh1, mesh2)
        result['matches']['edge_count'] = self.compare_edge_count(mesh1, mesh2)
        result['matches']['uv_count'] = self.compare_uv_count(mesh1, mesh2)
        result['matches']['topology'] = self.compare_topology(mesh1, mesh2)
        result['matches']['uv_sets'] = self.compare_uv_sets(mesh1, mesh2)
        result['matches']['vertex_positions'] = self.compare_vertex_positions(mesh1, mesh2, tolerance)
        result['matches']['normals'] = self.compare_normals(mesh1, mesh2, tolerance)
        result['matches']['bbox'] = self.compare_bbox(mesh1, mesh2, tolerance)
        # Determine overall match
        critical = ['topology', 'vertex_positions']
        result['overall_match'] = all(
            result['matches'][c].get('match', False) for c in critical
        )
        return result


# -----------------------------------------------------------------------------
# Convenience function
# -----------------------------------------------------------------------------

def compare_meshes(mesh1: str, mesh2: str, tolerance: float = 0.001) -> Dict[str, Any]:
    """Quick comparison of two meshes."""
    comparator = MeshComparison()
    return comparator.compare_all(mesh1, mesh2, tolerance)


__all__ = ["MeshComparison", "compare_meshes"]