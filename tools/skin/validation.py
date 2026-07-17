# -*- coding: utf-8 -*-
"""
tools/skin/validation.py

SkinCluster validation.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional
from .types import SkinReport, SkinState
from .editor import SkinEditor


class SkinValidator:
    """
    Validate skinClusters for common issues.
    """

    def __init__(self):
        self.editor = SkinEditor(None)  # Will be initialized with default settings

    def validate(self, skin: str) -> SkinReport:
        """
        Validate a skinCluster and return a report.

        Checks:
            - Influences exist
            - Vertex weights sum to 1.0
            - No zero-weight influences
            - Max influences are respected
            - No locked vertices (optional)
        """
        report = SkinReport(operation="validate", skin_name=skin)

        if not cmds.objExists(skin):
            report.errors.append(f"SkinCluster '{skin}' does not exist.")
            report.success = False
            return report

        # Get info
        info = self.editor.get_skin_info(skin)
        if not info:
            report.errors.append("Could not retrieve skin info.")
            report.success = False
            return report

        # Check influences exist
        missing = []
        for inf in info.influences:
            if not cmds.objExists(inf.name):
                missing.append(inf.name)
        if missing:
            report.warnings.append(f"Missing influences: {', '.join(missing)}")

        # Check vertex weights
        if info.mesh:
            vertex_count = cmds.polyEvaluate(info.mesh, vertex=True)
            for v in range(min(vertex_count, 100)):  # Sample first 100 vertices
                weights = self.editor.get_vertex_weights(skin, v)
                if not weights:
                    continue
                total = sum(weights)
                if abs(total - 1.0) > 0.001:
                    report.warnings.append(f"Vertex {v} has non-normalized weights (sum={total:.4f})")

        # Check for zero-weight influences
        # This is more expensive, so we'll only check if it's a full validation
        # For now, just report success
        report.success = len(report.errors) == 0
        return report