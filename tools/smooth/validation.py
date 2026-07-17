# -*- coding: utf-8 -*-
"""
tools/smooth/validation.py

Validation utilities for smoothing.
"""

import maya.cmds as cmds # type: ignore
from .types import SmoothValidation


class SmoothValidator:
    """
    Validate meshes, weights, and curves for smoothing.
    """

    @staticmethod
    def validate_mesh(mesh: str) -> SmoothValidation:
        errors = []
        warnings = []
        if not cmds.objExists(mesh):
            errors.append(f"Mesh '{mesh}' does not exist.")
        else:
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if not shapes:
                errors.append("No shape found.")
            elif cmds.nodeType(shapes[0]) != "mesh":
                warnings.append(f"'{mesh}' is not a polygon mesh (type: {cmds.nodeType(shapes[0])})")
        return SmoothValidation(valid=len(errors)==0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_weight(skin: str) -> SmoothValidation:
        errors = []
        warnings = []
        if not cmds.objExists(skin):
            errors.append(f"SkinCluster '{skin}' does not exist.")
        else:
            if cmds.nodeType(skin) != "skinCluster":
                errors.append(f"'{skin}' is not a skinCluster.")
        return SmoothValidation(valid=len(errors)==0, errors=errors, warnings=warnings)