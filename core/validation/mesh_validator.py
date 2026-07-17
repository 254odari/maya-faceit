"""
core/validation/mesh_validator.py

Mesh validation for rigging compatibility.

Extends topology_validator with rig-specific checks.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, List, Optional

from ..logging.logger import log
from .topology_validator import TopologyValidator
from .validation import Validator


class MeshValidator:
    """
    Validate mesh for facial rigging.
    """

    @staticmethod
    def validate_for_rigging(mesh: str) -> Dict[str, List[str]]:
        """
        Run comprehensive mesh validation specific to rigging.

        Checks:
            - Basic topology (using TopologyValidator)
            - UV existence
            - Vertex count within range
            - No overlapping vertices (optional)
            - Material assignments (optional)

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []

        # Basic validation
        if not cmds.objExists(mesh):
            errors.append(f"Mesh '{mesh}' does not exist.")
            return {'errors': errors, 'warnings': warnings}

        try:
            Validator.mesh(mesh)
        except Exception as e:
            errors.append(str(e))
            return {'errors': errors, 'warnings': warnings}

        # Topology validation
        topo_report = TopologyValidator.validate(mesh)
        if not topo_report.valid:
            errors.extend(topo_report.errors)
        warnings.extend(topo_report.warnings)

        # Rig-specific checks
        vtx_count = cmds.polyEvaluate(mesh, vertex=True)
        if vtx_count < 500:
            warnings.append("Mesh has very few vertices (<500) - may be insufficient for facial rigging.")
        if vtx_count > 100000:
            warnings.append("Mesh has very many vertices (>100000) - performance may be impacted.")

        # Check for UVs
        shapes = cmds.listRelatives(mesh, shapes=True) or []
        if shapes:
            uv_sets = cmds.polyUVSet(shapes[0], q=True, allUVSets=True) or []
            if not uv_sets:
                warnings.append("Mesh has no UV sets - blendshape targets may be affected.")
        else:
            errors.append("Mesh has no shape node.")

        # Check for symmetry (heuristic)
        bbox = cmds.exactWorldBoundingBox(mesh)
        if bbox:
            width = bbox[3] - bbox[0]
            if abs(bbox[0] + bbox[3]) > 0.01:
                warnings.append("Mesh may not be centered on X-axis. Symmetry may be affected.")

        # Check for non-manifold (again)
        nm = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
        if nm:
            errors.append(f"Non-manifold edges detected: {len(nm)//2} edges.")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def require_valid_for_rigging(mesh: str) -> None:
        """
        Require that the mesh passes all rigging validation.

        Raises:
            ValidationError if any errors found.
        """
        result = MeshValidator.validate_for_rigging(mesh)
        if result['errors']:
            from ...exceptions import ValidationError
            raise ValidationError("\n".join(result['errors']))
        if result['warnings']:
            log.warning("Mesh validation warnings:\n" + "\n".join(result['warnings']))


# Singleton
mesh_validator = MeshValidator()