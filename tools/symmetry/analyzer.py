# -*- coding: utf-8 -*-
"""
tools/symmetry/analyzer.py

Mesh analysis for symmetry.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, Any, List
from .types import VertexPair, SymmetrySettings


class MeshAnalyzer:
    """
    Analyzes mesh topology, symmetry, and geometry.
    """

    def __init__(self, settings: SymmetrySettings):
        self.settings = settings

    def analyze(self, mesh: str, vertex_map: List[VertexPair]) -> Dict[str, Any]:
        result = {
            "vertex_count": 0,
            "symmetric_vertices": 0,
            "asymmetric_vertices": 0,
            "symmetric_percentage": 0.0,
            "has_non_manifold": False,
            "has_open_borders": False,
            "warnings": [],
        }
        if not cmds.objExists(mesh):
            result["warnings"].append(f"Mesh {mesh} does not exist.")
            return result

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        result["vertex_count"] = vertex_count
        if vertex_map:
            symmetric = sum(1 for p in vertex_map if p.vertex2 != -1)
            asymmetric = len(vertex_map) - symmetric
            result["symmetric_vertices"] = symmetric
            result["asymmetric_vertices"] = asymmetric
            result["symmetric_percentage"] = symmetric / vertex_count * 100 if vertex_count else 0.0

        non_manifold = cmds.polyInfo(mesh, nonManifoldEdges=True) or []
        if non_manifold:
            result["has_non_manifold"] = True
            result["warnings"].append("Non-manifold geometry detected.")

        borders = cmds.polyInfo(mesh, borderEdges=True) or []
        if borders:
            result["has_open_borders"] = True
            result["warnings"].append("Open borders detected.")

        return result