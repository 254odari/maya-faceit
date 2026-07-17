# -*- coding: utf-8 -*-
"""
tools/relax/surface.py

Surface relaxation (NURBS surfaces/curves and polygon meshes).
"""

import maya.cmds as cmds # type: ignore
from .types import RelaxReport, RelaxMode
from .mesh import MeshRelaxer


class SurfaceRelaxer:
    """
    Relax surfaces (NURBS or polygon) using surface methods.
    """

    def __init__(self, engine):
        self.engine = engine
        self.mesh_relaxer = MeshRelaxer(engine)

    def relax_surface(self, surface: str) -> RelaxReport:
        """Relax a NURBS surface or polygon mesh."""
        if cmds.nodeType(surface) == 'mesh':
            return self.mesh_relaxer.relax(surface)
        elif cmds.nodeType(surface) in ['nurbsSurface', 'nurbsCurve']:
            return self._relax_nurbs_surface(surface)
        else:
            report = RelaxReport(mode=RelaxMode.SURFACE, success=False)
            report.errors.append(f"Unsupported surface type: {cmds.nodeType(surface)}")
            return report

    def _relax_nurbs_surface(self, surface: str) -> RelaxReport:
        """Relax NURBS surface control vertices."""
        report = RelaxReport(mode=RelaxMode.SURFACE)
        if not cmds.objExists(surface):
            report.errors.append(f"Surface '{surface}' does not exist.")
            report.success = False
            return report

        cvs = cmds.getAttr(f"{surface}.controlPoints[*]")
        if not cvs:
            report.errors.append("No control points found.")
            return report

        spans_u = cmds.getAttr(f"{surface}.spansU")
        spans_v = cmds.getAttr(f"{surface}.spansV")
        degree_u = cmds.getAttr(f"{surface}.degreeU")
        degree_v = cmds.getAttr(f"{surface}.degreeV")
        num_u = spans_u + degree_u
        num_v = spans_v + degree_v
        num_cvs = num_u * num_v

        adj = {}
        for i in range(num_cvs):
            u = i % num_u
            v = i // num_u
            neighbors = []
            if u > 0: neighbors.append(i - 1)
            if u < num_u - 1: neighbors.append(i + 1)
            if v > 0: neighbors.append(i - num_u)
            if v < num_v - 1: neighbors.append(i + num_u)
            adj[i] = neighbors

        points = [(cv[0], cv[1], cv[2]) for cv in cvs]
        relaxed = self.engine.relax_points(points, adj, boundary=set())

        for i, p in enumerate(relaxed):
            cmds.setAttr(f"{surface}.controlPoints[{i}]", p[0], p[1], p[2])

        report.processed_vertices = num_cvs
        report.iterations = self.engine.settings.iterations
        report.success = True
        return report