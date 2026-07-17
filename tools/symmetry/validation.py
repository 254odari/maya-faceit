# -*- coding: utf-8 -*-
"""
tools/symmetry/validation.py

Symmetry validation.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Set
from .types import VertexPair, ControllerPair, ValidationResult


class SymmetryValidator:
    """
    Validates symmetry maps and meshes.
    """

    @staticmethod
    def validate_vertex_map(mesh: str, vertex_map: List[VertexPair]) -> ValidationResult:
        errors = []
        warnings = []
        if not mesh:
            errors.append("No mesh specified.")
        elif not cmds.objExists(mesh):
            errors.append(f"Mesh '{mesh}' does not exist.")
        else:
            vertex_count = cmds.polyEvaluate(mesh, vertex=True)
            if len(vertex_map) != vertex_count:
                warnings.append(f"Vertex map size ({len(vertex_map)}) does not match mesh vertex count ({vertex_count}).")

        seen = set()
        for pair in vertex_map:
            if pair.vertex1 in seen or pair.vertex2 in seen:
                errors.append(f"Duplicate vertex index found: {pair.vertex1} or {pair.vertex2}")
            seen.add(pair.vertex1)
            if pair.vertex2 != -1:
                seen.add(pair.vertex2)

        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_controller_map(controllers: List[str], controller_pairs: List[ControllerPair]) -> ValidationResult:
        errors = []
        warnings = []
        covered = set()
        for pair in controller_pairs:
            covered.add(pair.source)
            if pair.target:
                covered.add(pair.target)
        missing = [c for c in controllers if c not in covered]
        if missing:
            warnings.append(f"Controllers without mapping: {missing}")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)