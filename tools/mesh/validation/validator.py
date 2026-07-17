"""
tools/mesh/validation/validator.py

Enhanced MeshValidator with better performance using OpenMaya where appropriate.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om # type: ignore

from ..types import (
    MeshIssue, IssueSeverity, ComponentType,
    MeshSelection, ValidationResult
)
from ..core.editor import MeshEditor


class MeshValidator:
    """
    Comprehensive mesh validation system.
    Combines cmds and OpenMaya for best performance and accuracy.
    """

    def __init__(self):
        self.editor = MeshEditor()

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    def validate(self, mesh: Optional[MeshSelection] = None) -> List[MeshIssue]:
        """Run complete validation on a mesh."""
        if isinstance(mesh, (list, tuple)):
            mesh = mesh[0]
        if not mesh:
            mesh = self.editor.get_active_shape()

        issues: List[MeshIssue] = []

        # Core topology checks
        issues.extend(self.check_non_manifold(mesh))
        issues.extend(self.check_lamina_faces(mesh))
        issues.extend(self.check_ngons(mesh))
        issues.extend(self.check_zero_area_faces(mesh))
        issues.extend(self.check_zero_length_edges(mesh))
        issues.extend(self.check_isolated_vertices(mesh))
        issues.extend(self.check_duplicate_vertices(mesh))
        issues.extend(self.check_open_borders(mesh))

        # UV & Normal checks
        issues.extend(self.check_uv_issues(mesh))
        issues.extend(self.check_normal_issues(mesh))

        return issues

    def validate_full(self, mesh: Optional[MeshSelection] = None) -> ValidationResult:
        """Return (is_valid, issues) tuple."""
        issues = self.validate(mesh)
        has_critical_errors = any(i.severity == IssueSeverity.ERROR for i in issues)
        return not has_critical_errors, issues

    # =====================================================================
    # TOPOLOGY VALIDATION
    # =====================================================================

    def check_non_manifold(self, mesh: str) -> List[MeshIssue]:
        issues = []

        # Using polyInfo for simplicity and reliability
        nm_verts = cmds.polyInfo(mesh, nonManifoldVertices=True) or []
        nm_edges = cmds.polyInfo(mesh, nonManifoldEdges=True) or []

        if nm_verts:
            issues.append(MeshIssue(
                severity=IssueSeverity.ERROR,
                issue_type="non_manifold_vertex",
                description=f"{len(nm_verts)//2} non-manifold vertices detected",
                component_type=ComponentType.VERTEX,
                component_ids=[],  # Can be populated with proper parsing
                mesh_name=mesh,
                suggestion="Merge or manually connect vertices."
            ))

        if nm_edges:
            issues.append(MeshIssue(
                severity=IssueSeverity.ERROR,
                issue_type="non_manifold_edge",
                description=f"{len(nm_edges)//2} non-manifold edges detected",
                component_type=ComponentType.EDGE,
                mesh_name=mesh,
                suggestion="Fix topology to ensure manifold geometry."
            ))

        return issues

    def check_lamina_faces(self, mesh: str) -> List[MeshIssue]:
        lamina = cmds.polyInfo(mesh, laminaFaces=True) or []
        if lamina:
            return [MeshIssue(
                severity=IssueSeverity.ERROR,
                issue_type="lamina_faces",
                description=f"{len(lamina)//2} lamina (overlapping) faces found",
                component_type=ComponentType.FACE,
                mesh_name=mesh,
                suggestion="Remove duplicate/lamina faces."
            )]
        return []

    def check_ngons(self, mesh: str, max_sides: int = 4) -> List[MeshIssue]:
        try:
            face_count = cmds.polyEvaluate(mesh, face=True)
            ngon_count = 0

            for i in range(face_count):
                if cmds.polyEvaluate(mesh, faceVertexCount=i) > max_sides:
                    ngon_count += 1

            if ngon_count > 0:
                return [MeshIssue(
                    severity=IssueSeverity.WARNING,
                    issue_type="ngons",
                    description=f"{ngon_count} N-Gons detected (faces with > {max_sides} sides)",
                    component_type=ComponentType.FACE,
                    mesh_name=mesh,
                    suggestion="Consider triangulating or retopologizing."
                )]
        except:
            pass
        return []

    def check_zero_area_faces(self, mesh: str, tolerance: float = 1e-6) -> List[MeshIssue]:
        # More accurate using OpenMaya
        dag = self.editor.get_dag_path(mesh)
        fn_mesh = om.MFnMesh(dag)

        zero_count = 0
        for i in range(fn_mesh.numPolygons):
            area = fn_mesh.getPolygonArea(i, om.MSpace.kWorld)
            if area < tolerance:
                zero_count += 1

        if zero_count > 0:
            return [MeshIssue(
                severity=IssueSeverity.WARNING,
                issue_type="zero_area_faces",
                description=f"{zero_count} zero or near-zero area faces",
                component_type=ComponentType.FACE,
                mesh_name=mesh
            )]
        return []

    def check_zero_length_edges(self, mesh: str, tolerance: float = 1e-6) -> List[MeshIssue]:
        # Placeholder - can be expanded with full edge length calculation
        return []

    def check_isolated_vertices(self, mesh: str) -> List[MeshIssue]:
        isolated = cmds.polyInfo(mesh, isolatedVertices=True) or []
        if isolated:
            return [MeshIssue(
                severity=IssueSeverity.WARNING,
                issue_type="isolated_vertices",
                description=f"{len(isolated)//2} isolated vertices found",
                component_type=ComponentType.VERTEX,
                mesh_name=mesh,
                suggestion="Delete unused vertices."
            )]
        return []

    def check_duplicate_vertices(self, mesh: str, tolerance: float = 0.0001) -> List[MeshIssue]:
        # Can be implemented with vertex position comparison using OpenMaya
        return []

    def check_open_borders(self, mesh: str) -> List[MeshIssue]:
        borders = cmds.polyInfo(mesh, borderEdges=True) or []
        if borders:
            return [MeshIssue(
                severity=IssueSeverity.INFO,
                issue_type="open_borders",
                description=f"Mesh has open borders ({len(borders)//2} border edges)",
                component_type=ComponentType.EDGE,
                mesh_name=mesh,
                suggestion="Close holes if watertight mesh is required."
            )]
        return []

    # =====================================================================
    # UV & NORMAL VALIDATION
    # =====================================================================

    def check_uv_issues(self, mesh: str) -> List[MeshIssue]:
        issues = []

        if not cmds.polyEvaluate(mesh, uv=True):
            issues.append(MeshIssue(
                severity=IssueSeverity.WARNING,
                issue_type="missing_uvs",
                description="Mesh has no UV map",
                mesh_name=mesh
            ))
        return issues

    def check_normal_issues(self, mesh: str) -> List[MeshIssue]:
        # Can be expanded
        return []

    # =====================================================================
    # UTILITY METHODS
    # =====================================================================

    def is_valid(self, mesh: Optional[MeshSelection] = None) -> bool:
        """Quick check if mesh has no critical errors."""
        issues = self.validate(mesh)
        return all(issue.severity != IssueSeverity.ERROR for issue in issues)

    def print_report(self, mesh: Optional[MeshSelection] = None):
        """Print validation summary to script editor."""
        issues = self.validate(mesh)
        print(f"\n=== Validation Report: {mesh} ===")
        print(f"Total Issues: {len(issues)}")
        for issue in issues:
            print(f"[{issue.severity.name}] {issue.issue_type}: {issue.description}")


# Global instance
validator = MeshValidator()

__all__ = ["MeshValidator", "validator"]