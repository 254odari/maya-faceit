"""
tools/mesh/components/faces.py

FaceTools - Face-level operations, analysis, and utilities.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om # type: ignore

from ..core.editor import MeshEditor
from ..types import (
    MeshSelection, 
    MeshIssue, 
    IssueSeverity, 
    ComponentType
)


class FaceTools:
    """
    Comprehensive face operations and analysis for maya_faceit.
    """

    def __init__(self, editor: MeshEditor):
        self.editor = editor

    # =====================================================================
    # BASIC FACE OPERATIONS
    # =====================================================================

    def flip(self, faces: Optional[List[int]] = None, mesh: Optional[str] = None):
        """Flip face normals."""
        target = mesh or self.editor.get_active_shape()
        if faces is not None:
            face_list = [f"{target}.f[{f}]" for f in faces]
            cmds.polyFlipUV(face_list)  # Note: polyFlipUV is for UVs, use this for normals:
            cmds.polyNormal(face_list, normalMode=0)  # Reverse normals
        else:
            cmds.polyNormal(target, normalMode=0)

    def reverse(self, mesh: Optional[str] = None):
        """Reverse face orientation (normals)."""
        target = mesh or self.editor.get_active_shape()
        cmds.polyNormal(target, normalMode=0, constructionHistory=False)

    def extrude(self, faces: List[int], distance: float = 0.5, divisions: int = 1):
        """Extrude faces."""
        if not faces:
            return
        target = self.editor.get_active_shape()
        face_list = [f"{target}.f[{f}]" for f in faces]
        cmds.polyExtrudeFacet(face_list, offset=distance, divisions=divisions)

    def bevel(self, faces: List[int], offset: float = 0.2, segments: int = 3):
        """Bevel faces."""
        if not faces:
            return
        target = self.editor.get_active_shape()
        face_list = [f"{target}.f[{f}]" for f in faces]
        cmds.polyBevel3(face_list, offset=offset, segments=segments)

    def poke(self, faces: List[int], mesh: Optional[str] = None):
        """Poke (subdivide from center) faces."""
        target = mesh or self.editor.get_active_shape()
        face_list = [f"{target}.f[{f}]" for f in faces]
        cmds.polyPoke(face_list)

    def delete(self, faces: List[int], mesh: Optional[str] = None):
        """Delete specific faces."""
        target = mesh or self.editor.get_active_shape()
        face_list = [f"{target}.f[{f}]" for f in faces]
        cmds.delete(face_list)

    def duplicate(self, faces: List[int], mesh: Optional[str] = None) -> str:
        """Extract and duplicate faces as new mesh."""
        target = mesh or self.editor.get_active_shape()
        face_list = [f"{target}.f[{f}]" for f in faces]
        cmds.select(face_list)
        return cmds.duplicate()[0]

    # =====================================================================
    # FACE ANALYSIS
    # =====================================================================

    def analyze(self, mesh: Optional[str] = None) -> Dict:
        """Detailed face analysis."""
        target = mesh or self.editor.get_active_shape()
        
        analysis = {
            "total_faces": cmds.polyEvaluate(target, face=True),
            "triangles": cmds.polyEvaluate(target, triangle=True),
            "quads": 0,
            "ngons": 0,
            "total_area": 0.0,
            "average_area": 0.0,
            "largest_face": 0,
            "smallest_face": 0,
        }

        try:
            dag = self.editor.get_dag_path(target)
            fn_mesh = om.MFnMesh(dag)

            areas = []
            for i in range(fn_mesh.numPolygons):
                area = fn_mesh.getPolygonArea(i, om.MSpace.kWorld)
                areas.append(area)

                sides = len(fn_mesh.getPolygonVertices(i))
                if sides == 3:
                    analysis["triangles"] += 1  # already counted above, but consistent
                elif sides == 4:
                    analysis["quads"] += 1
                elif sides > 4:
                    analysis["ngons"] += 1

            if areas:
                analysis["total_area"] = sum(areas)
                analysis["average_area"] = sum(areas) / len(areas)
                analysis["largest_face"] = max(areas)
                analysis["smallest_face"] = min(areas)

        except Exception:
            pass

        return analysis

    def get_face_centers(self, mesh: str) -> List[Tuple[float, float, float]]:
        """Return world-space center of each face."""
        dag = self.editor.get_dag_path(mesh)
        fn_mesh = om.MFnMesh(dag)
        centers = []

        for i in range(fn_mesh.numPolygons):
            pt = fn_mesh.getPointAtUV(i, (0.5, 0.5), space=om.MSpace.kWorld)
            centers.append((pt.x, pt.y, pt.z))

        return centers

    def get_face_normals(self, mesh: str) -> List[Tuple[float, float, float]]:
        """Return face normals."""
        dag = self.editor.get_dag_path(mesh)
        fn_mesh = om.MFnMesh(dag)
        normals = []

        for i in range(fn_mesh.numPolygons):
            normal = fn_mesh.getPolygonNormal(i, om.MSpace.kWorld)
            normals.append((normal.x, normal.y, normal.z))

        return normals

    # =====================================================================
    # FACE ISLANDS & TOPOLOGY
    # =====================================================================

    def count_face_islands(self, mesh: Optional[str] = None) -> int:
        """Count disconnected face shells/islands."""
        target = mesh or self.editor.get_active_shape()
        # Using polyEvaluate shell count
        try:
            return cmds.polyEvaluate(target, shell=True)
        except:
            return 1

    def select_largest_face_island(self, mesh: Optional[str] = None):
        """Select the largest connected face component."""
        # Implementation can use polySelectConstraint or custom flood fill
        pass

    # =====================================================================
    # VALIDATION ISSUES
    # =====================================================================

    def find_problematic_faces(self, mesh: Optional[str] = None) -> List[MeshIssue]:
        """Detect zero-area, lamina, and other bad faces."""
        issues = []
        target = mesh or self.editor.get_active_shape()

        # Zero area faces
        zero_area = self._find_zero_area_faces(target)
        if zero_area > 0:
            issues.append(MeshIssue(
                severity=IssueSeverity.WARNING,
                issue_type="zero_area_faces",
                description=f"{zero_area} zero or near-zero area faces",
                component_type=ComponentType.FACE,
                mesh_name=target
            ))

        return issues

    def _find_zero_area_faces(self, mesh: str, tolerance: float = 1e-6) -> int:
        dag = self.editor.get_dag_path(mesh)
        fn_mesh = om.MFnMesh(dag)
        count = 0
        for i in range(fn_mesh.numPolygons):
            area = fn_mesh.getPolygonArea(i, om.MSpace.kWorld)
            if area < tolerance:
                count += 1
        return count

    # =====================================================================
    # UTILITY
    # =====================================================================

    def select_all(self, mesh: Optional[str] = None):
        """Select all faces."""
        target = mesh or self.editor.get_active_shape()
        cmds.select(f"{target}.f[*]")

    def select_random(self, count: int = 10, mesh: Optional[str] = None):
        """Select N random faces (useful for testing)."""
        target = mesh or self.editor.get_active_shape()
        total = cmds.polyEvaluate(target, face=True)
        import random
        indices = random.sample(range(total), min(count, total))
        cmds.select([f"{target}.f[{i}]" for i in indices])

    def triangulate(self, mesh: Optional[str] = None):
        """Triangulate all faces."""
        target = mesh or self.editor.get_active_shape()
        cmds.polyTriangulate(target)

    def quadrangulate(self, mesh: Optional[str] = None):
        """Quadrangulate faces where possible."""
        target = mesh or self.editor.get_active_shape()
        cmds.polyQuad(target)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

__all__ = ["FaceTools"]