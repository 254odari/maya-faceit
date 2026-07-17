# -*- coding: utf-8 -*-
"""
tools/relax/validation.py

Validation utilities for relaxation.
"""

import maya.cmds as cmds # type: ignore
from typing import List
from .types import ValidationResult


class RelaxValidator:
    """Validate inputs before relaxation."""

    @staticmethod
    def validate_mesh(mesh: str) -> ValidationResult:
        errors = []
        warnings = []
        if not cmds.objExists(mesh):
            errors.append(f"Mesh '{mesh}' does not exist.")
        else:
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if not shapes:
                errors.append(f"'{mesh}' has no shape.")
            elif cmds.nodeType(shapes[0]) != "mesh":
                warnings.append(f"'{mesh}' is not a polygon mesh (type: {cmds.nodeType(shapes[0])})")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_vertices(mesh: str, vertex_indices: List[int]) -> ValidationResult:
        result = RelaxValidator.validate_mesh(mesh)
        if result.valid:
            vertex_count = cmds.polyEvaluate(mesh, vertex=True)
            invalid = [i for i in vertex_indices if i < 0 or i >= vertex_count]
            if invalid:
                result.errors.append(f"Invalid vertex indices: {invalid}")
                result.valid = False
        return result

    @staticmethod
    def validate_weights(mesh: str) -> ValidationResult:
        errors = []
        warnings = []
        skin = cmds.listConnections(mesh, type='skinCluster')
        if not skin:
            warnings.append(f"No skinCluster found on '{mesh}'.")
        else:
            influences = cmds.skinCluster(skin[0], q=True, influence=True)
            if not influences:
                warnings.append("No influences found.")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)