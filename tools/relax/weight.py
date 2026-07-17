# -*- coding: utf-8 -*-
"""
tools/relax/weight.py

Weight relaxation (skin weights, blendshape weights).
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List
from .types import RelaxReport, RelaxMode, WeightType


class WeightRelaxer:
    """
    Relax skin weights or blendshape weights.
    """

    def __init__(self, engine):
        self.engine = engine

    def relax_skin_weights(self, mesh: str) -> RelaxReport:
        """Relax skin weights by smoothing per-vertex influences."""
        report = RelaxReport(mode=RelaxMode.WEIGHT)
        skin = cmds.listConnections(mesh, type='skinCluster')
        if not skin:
            report.errors.append(f"No skinCluster found on {mesh}.")
            report.success = False
            return report
        skin = skin[0]
        influences = cmds.skinCluster(skin, q=True, influence=True)
        if not influences:
            report.errors.append("No influences found.")
            return report

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = [f"{mesh}.vtx[{i}]" for i in range(vertex_count)]

        sel = om2.MSelectionList()
        sel.add(mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag_path)
        adj = self._build_vertex_adjacency(fn_mesh)

        weight_matrix = []
        for v in vertices:
            weights = cmds.skinPercent(skin, v, query=True, value=True) or [0.0]*len(influences)
            weight_matrix.append(weights)

        smoothed = self._smooth_weights(weight_matrix, adj)

        for i, v in enumerate(vertices):
            for j, inf in enumerate(influences):
                cmds.skinPercent(skin, v, transformValue=[(inf, smoothed[i][j])])

        report.processed_vertices = vertex_count
        report.iterations = self.engine.settings.iterations
        report.success = True
        return report

    def relax_blendshape_weights(self, blendshape_node: str) -> RelaxReport:
        """Relax blendshape weights across targets."""
        report = RelaxReport(mode=RelaxMode.WEIGHT)
        if not cmds.objExists(blendshape_node):
            report.errors.append(f"Blendshape node '{blendshape_node}' does not exist.")
            report.success = False
            return report

        targets = cmds.listAttr(blendshape_node, m=True, string='weight') or []
        if not targets:
            report.warnings.append("No weight attributes found.")
            report.success = True
            return report

        weights = [cmds.getAttr(f"{blendshape_node}.{t}") for t in targets]
        smoothed = weights[:]
        for _ in range(self.engine.settings.iterations):
            new_weights = smoothed[:]
            for i in range(1, len(weights)-1):
                avg = (smoothed[i-1] + smoothed[i+1]) * 0.5
                new_weights[i] = smoothed[i] + (avg - smoothed[i]) * self.engine.settings.strength
            smoothed = new_weights

        for t, w in zip(targets, smoothed):
            cmds.setAttr(f"{blendshape_node}.{t}", w)

        report.processed_vertices = len(targets)
        report.iterations = self.engine.settings.iterations
        report.success = True
        return report

    def _build_vertex_adjacency(self, fn_mesh: om2.MFnMesh):
        num_vertices = fn_mesh.numVertices()
        adj = {i: [] for i in range(num_vertices)}
        for i in range(num_vertices):
            connected = fn_mesh.getConnectedVertices(i)
            adj[i] = list(set(connected))
        return adj

    def _smooth_weights(self, weights: List[List[float]], adj):
        if not weights:
            return weights
        smoothed = [list(w) for w in weights]
        for _ in range(self.engine.settings.iterations):
            new_weights = [list(w) for w in smoothed]
            for i in range(len(weights)):
                neighbors = adj.get(i, [])
                if not neighbors:
                    continue
                avg = [0.0] * len(weights[i])
                for n in neighbors:
                    for j in range(len(weights[i])):
                        avg[j] += smoothed[n][j]
                for j in range(len(avg)):
                    avg[j] /= len(neighbors)
                strength = self.engine.settings.strength
                for j in range(len(avg)):
                    new_weights[i][j] = smoothed[i][j] + (avg[j] - smoothed[i][j]) * strength
            smoothed = new_weights
        return smoothed