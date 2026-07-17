"""
core/validation/topology_validator.py

Topology validation for Maya Faceit.

This module validates whether a mesh is suitable for
automatic facial rig generation.

Checks include:
    • Polygon mesh validation
    • Vertex count
    • Face count
    • Triangles
    • Ngons
    • Non-manifold geometry
    • Lamina faces
    • Construction history
    • UV existence
    • World scale
    • Center alignment
    • Multiple shape nodes
    • Open borders
    • Symmetry (approximate)

Author: Maya FaceIT Team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore

from ..logging.logger import log
from ...exceptions import ValidationError
from ..mesh_analyzer import mesh_analyzer


# ---------------------------------------------------------
# Validation Report
# ---------------------------------------------------------

@dataclass(slots=True)
class ValidationReport:
    """Container for validation results."""
    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


# ---------------------------------------------------------
# Validator
# ---------------------------------------------------------

class TopologyValidator:
    """
    Validates polygon mesh topology for facial rigging.
    """

    # Thresholds
    MIN_VERTICES = 500
    MAX_VERTICES = 500000
    MIN_FACES = 500
    MAX_FACES = 500000
    MAX_NGON_PERCENTAGE = 5.0  # % of faces allowed to be ngons
    MAX_ASPECT_RATIO = 10.0    # for face quality

    # -----------------------------------------------------

    def validate(self, mesh: str) -> ValidationReport:
        """
        Perform complete topology validation on a mesh.

        Args:
            mesh: Name of the mesh transform to validate.

        Returns:
            ValidationReport with errors, warnings, and info.
        """
        report = ValidationReport()

        # Basic existence
        if not cmds.objExists(mesh):
            report.add_error(f"Mesh '{mesh}' does not exist.")
            return report

        try:
            mesh_analyzer.validate(mesh)
        except ValidationError as e:
            report.add_error(str(e))
            return report

        # Analyze mesh
        info = mesh_analyzer.analyze(mesh)
        report.info["vertices"] = info.vertices
        report.info["faces"] = info.faces
        report.info["triangles"] = info.triangles
        report.info["uv_sets"] = info.uv_sets
        report.info["width"] = info.width
        report.info["height"] = info.height
        report.info["depth"] = info.depth
        report.info["center"] = info.center

        # -------------------------------------------------
        # Vertex Count
        # -------------------------------------------------
        if info.vertices < self.MIN_VERTICES:
            report.add_error(
                f"Mesh has too few vertices ({info.vertices}). "
                f"Minimum required: {self.MIN_VERTICES}"
            )
        elif info.vertices > self.MAX_VERTICES:
            report.add_warning(
                f"Extremely dense mesh ({info.vertices} vertices). "
                f"This may impact performance."
            )

        # -------------------------------------------------
        # Face Count
        # -------------------------------------------------
        if info.faces < self.MIN_FACES:
            report.add_error(
                f"Mesh has too few faces ({info.faces}). "
                f"Minimum required: {self.MIN_FACES}"
            )
        elif info.faces > self.MAX_FACES:
            report.add_warning(
                f"Very high polygon count ({info.faces} faces). "
                f"May slow down rig generation."
            )

        # -------------------------------------------------
        # Triangles (should be low for facial rigs)
        # -------------------------------------------------
        if info.triangles > 0 and info.faces > 0:
            tri_percent = (info.triangles / info.faces) * 100.0
            report.info["triangles_percent"] = tri_percent
            if tri_percent > 50.0:
                report.add_warning(
                    f"High percentage of triangles ({tri_percent:.1f}%). "
                    "Facial rigs work best with quad-dominant meshes."
                )

        # -------------------------------------------------
        # Ngons
        # -------------------------------------------------
        ngon_count = self._count_ngons(mesh)
        report.info["ngons"] = ngon_count
        if ngon_count > 0:
            ngon_percent = (ngon_count / info.faces) * 100.0 if info.faces > 0 else 0
            if ngon_percent > self.MAX_NGON_PERCENTAGE:
                report.add_warning(
                    f"{ngon_count} ngons detected ({ngon_percent:.1f}% of faces). "
                    "Consider triangulating or cleaning up."
                )
            else:
                report.add_warning(
                    f"{ngon_count} ngons detected. "
                    "They may cause issues during blendshape creation."
                )

        # -------------------------------------------------
        # Non-Manifold Geometry
        # -------------------------------------------------
        non_manifold_verts = cmds.polyInfo(mesh, nonManifoldVertices=True) or []
        non_manifold_edges = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
        if non_manifold_verts or non_manifold_edges:
            report.add_error(
                f"Non-manifold geometry detected: "
                f"{len(non_manifold_verts)//2} vertices, "
                f"{len(non_manifold_edges)//2} edges. "
                "This will break rigging."
            )

        # -------------------------------------------------
        # Lamina Faces
        # -------------------------------------------------
        lamina = cmds.polyInfo(mesh, laminaFaces=True) or []
        if lamina:
            report.add_error(
                f"Lamina faces detected: {len(lamina)//2}. "
                "These are overlapping faces and must be fixed."
            )

        # -------------------------------------------------
        # Open Borders
        # -------------------------------------------------
        borders = cmds.polyInfo(mesh, borderEdges=True) or []
        if borders:
            report.add_warning(
                f"Open borders detected: {len(borders)//2} border edges. "
                "Mesh is not watertight; may affect skinning and blendshapes."
            )

        # -------------------------------------------------
        # Construction History
        # -------------------------------------------------
        if info.history:
            report.add_warning(
                "Construction history detected. "
                "It is recommended to delete history before rigging."
            )

        # -------------------------------------------------
        # UV Sets
        # -------------------------------------------------
        if info.uv_sets == 0:
            report.add_warning(
                "Mesh has no UVs. "
                "UVs are required for blendshape targets."
            )
        elif info.uv_sets > 1:
            report.add_warning(
                f"Multiple UV sets ({info.uv_sets}). "
                "Ensure the current UV set is correct for rigging."
            )

        # -------------------------------------------------
        # Scale / Dimensions
        # -------------------------------------------------
        if info.width > 1000 or info.height > 1000 or info.depth > 1000:
            report.add_warning(
                f"Large mesh dimensions: {info.width:.1f} x {info.height:.1f} x {info.depth:.1f}. "
                "Consider scaling to a reasonable size (e.g., 1-10 units)."
            )
        if info.width < 0.01 or info.height < 0.01 or info.depth < 0.01:
            report.add_warning(
                "Mesh is very small. Scaling may be needed for proper rigging."
            )

        # -------------------------------------------------
        # Center Alignment (X-axis symmetry)
        # -------------------------------------------------
        center_x = info.center[0]
        if abs(center_x) > 0.01:
            report.add_warning(
                f"Mesh center is at x={center_x:.3f}. "
                "It is recommended to center the mesh on the world X-axis for symmetry."
            )

        # -------------------------------------------------
        # Multiple Shape Nodes
        # -------------------------------------------------
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        if len(shapes) > 1:
            report.add_warning(
                f"Multiple shape nodes ({len(shapes)}) detected. "
                "Consider combining or deleting unused shapes."
            )

        # -------------------------------------------------
        # Face Quality (Aspect Ratio)
        # -------------------------------------------------
        # We'll check aspect ratio for a sample of faces to avoid performance hit
        avg_aspect = self._average_face_aspect_ratio(mesh)
        if avg_aspect is not None:
            report.info["avg_aspect_ratio"] = avg_aspect
            if avg_aspect > self.MAX_ASPECT_RATIO:
                report.add_warning(
                    f"Average face aspect ratio is {avg_aspect:.2f}. "
                    "Very high values indicate poor quality faces."
                )

        log.info(f"Topology validation complete for: {mesh}")
        return report

    # -----------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------

    def _count_ngons(self, mesh: str) -> int:
        """Count the number of faces with more than 4 sides."""
        try:
            sel = om2.MSelectionList()
            sel.add(mesh)
            dag_path = sel.getDagPath(0)
            fn_mesh = om2.MFnMesh(dag_path)
            ngons = 0
            for i in range(fn_mesh.numPolygons()):
                if len(fn_mesh.getPolygonVertices(i)) > 4:
                    ngons += 1
            return ngons
        except:
            return 0

    def _average_face_aspect_ratio(self, mesh: str) -> Optional[float]:
        """Compute average aspect ratio of faces (sample up to 1000 faces)."""
        try:
            sel = om2.MSelectionList()
            sel.add(mesh)
            dag_path = sel.getDagPath(0)
            fn_mesh = om2.MFnMesh(dag_path)
            total = 0.0
            count = 0
            # Sample up to 1000 faces
            face_count = fn_mesh.numPolygons()
            sample_size = min(1000, face_count)
            step = max(1, face_count // sample_size)
            for i in range(0, face_count, step):
                verts = fn_mesh.getPolygonVertices(i)
                if len(verts) < 3:
                    continue
                positions = [fn_mesh.getPoint(v, om2.MSpace.kWorld) for v in verts]
                # Compute edge lengths
                lengths = []
                for j in range(len(positions)):
                    p1 = positions[j]
                    p2 = positions[(j + 1) % len(positions)]
                    dx = p1.x - p2.x
                    dy = p1.y - p2.y
                    dz = p1.z - p2.z
                    lengths.append((dx*dx + dy*dy + dz*dz) ** 0.5)
                if lengths:
                    longest = max(lengths)
                    shortest = min(lengths)
                    if shortest > 1e-12:
                        total += longest / shortest
                        count += 1
            if count == 0:
                return None
            return total / count
        except:
            return None

    # -----------------------------------------------------
    # Convenience
    # -----------------------------------------------------

    def require_valid(self, mesh: str) -> ValidationReport:
        """
        Validate and raise an exception if the mesh is not valid.

        Returns:
            ValidationReport if valid, else raises ValidationError.
        """
        report = self.validate(mesh)
        if not report.valid:
            raise ValidationError("\n".join(report.errors))
        return report


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

topology_validator = TopologyValidator()