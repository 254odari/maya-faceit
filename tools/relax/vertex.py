# -*- coding: utf-8 -*-
"""
tools/relax/vertex.py

Vertex relaxation (selected vertices).
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional
from .types import RelaxReport, RelaxMode
from .mesh import MeshRelaxer


class VertexRelaxer:
    """
    Relax selected vertices.
    """

    def __init__(self, engine):
        self.engine = engine
        self.mesh_relaxer = MeshRelaxer(engine)

    def relax_selected(self) -> RelaxReport:
        """Relax currently selected vertices."""
        selection = cmds.ls(selection=True, flatten=True)
        verts = [v for v in selection if '.vtx' in v]
        if not verts:
            report = RelaxReport(mode=RelaxMode.VERTEX, success=False)
            report.errors.append("No vertices selected.")
            return report

        mesh = verts[0].split('.')[0]
        indices = []
        for v in verts:
            try:
                idx = int(v.split('[')[1].split(']')[0])
                indices.append(idx)
            except ValueError:
                pass

        if not indices:
            report = RelaxReport(mode=RelaxMode.VERTEX, success=False)
            report.errors.append("Could not parse vertex indices.")
            return report

        return self.mesh_relaxer.relax(mesh, indices)