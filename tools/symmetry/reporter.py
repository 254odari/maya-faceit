# -*- coding: utf-8 -*-
"""
tools/symmetry/reporter.py

Symmetry report generation.
"""

from typing import Dict, Any, List
from .types import SymmetryMap, SymmetryReport


class SymmetryReporter:
    """
    Generates detailed symmetry reports.
    """

    @staticmethod
    def generate_report(mesh: str, map_data: SymmetryMap,
                        mesh_analysis: Dict[str, Any]) -> SymmetryReport:
        report = SymmetryReport()
        report.mesh = mesh
        report.plane = map_data.plane
        report.vertex_count = mesh_analysis.get("vertex_count", 0)
        report.symmetric_vertices = mesh_analysis.get("symmetric_vertices", 0)
        report.asymmetric_vertices = mesh_analysis.get("asymmetric_vertices", 0)
        report.symmetric_percentage = mesh_analysis.get("symmetric_percentage", 0.0)

        controllers = map_data.controllers
        report.controller_count = len(controllers)
        report.symmetric_controllers = sum(1 for c in controllers if c.target)
        report.asymmetric_controllers = report.controller_count - report.symmetric_controllers

        joints = map_data.joints
        report.joint_count = len(joints)
        report.symmetric_joints = sum(1 for j in joints if j.target)
        report.asymmetric_joints = report.joint_count - report.symmetric_joints

        blendshapes = map_data.blendshapes
        report.blendshape_count = len(blendshapes)
        report.symmetric_blendshapes = sum(1 for b in blendshapes if b.target)
        report.asymmetric_blendshapes = report.blendshape_count - report.symmetric_blendshapes

        confidences = []
        for v in map_data.vertices:
            if v.vertex2 != -1:
                confidences.append(v.confidence)
        for c in map_data.controllers:
            if c.target:
                confidences.append(c.confidence)
        for j in map_data.joints:
            if j.target:
                confidences.append(j.confidence)
        for b in map_data.blendshapes:
            if b.target:
                confidences.append(b.confidence)
        if confidences:
            report.confidence = sum(confidences) / len(confidences)
        else:
            report.confidence = 0.0

        report.warnings = mesh_analysis.get("warnings", [])
        report.details = mesh_analysis
        return report