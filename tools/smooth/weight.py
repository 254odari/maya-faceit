# -*- coding: utf-8 -*-
"""
tools/smooth/weight.py

Weight smoothing (skin weights, blendshape weights).
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import math
from typing import List, Optional, Dict
from .types import SmoothSettings, SmoothReport, SmoothMode, SmoothStatistics


class WeightSmoother:
    """
    Smooth skin weights and blendshape weights.
    """

    def __init__(self, algorithm_engine, settings: SmoothSettings):
        self.engine = algorithm_engine
        self.settings = settings

    def smooth_skin(self, skin: str, settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """Smooth skin weights."""
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.WEIGHT)
        start = time.time()

        if not cmds.objExists(skin):
            report.errors.append(f"SkinCluster '{skin}' does not exist.")
            report.success = False
            return report

        # Get mesh and influences
        geom = cmds.skinCluster(skin, q=True, geometry=True) or []
        if not geom:
            report.errors.append("No geometry found on skinCluster.")
            report.success = False
            return report
        mesh = geom[0]
        influences = cmds.skinCluster(skin, q=True, influence=True) or []
        if not influences:
            report.errors.append("No influences found.")
            report.success = False
            return report

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        if vertex_count == 0:
            report.errors.append("Mesh has no vertices.")
            report.success = False
            return report

        # Get adjacency
        adj = self._build_adjacency(mesh)

        # Read weights as matrix
        weights = []
        for v in range(vertex_count):
            w = cmds.skinPercent(skin, f"{mesh}.vtx[{v}]", q=True, value=True) or [0.0]*len(influences)
            weights.append(w)

        # Smooth weights using adjacency
        # We'll smooth each vertex's weights by averaging neighboring weights
        total_delta = 0.0
        for _ in range(settings.iterations):
            new_weights = [list(w) for w in weights]
            for v in range(vertex_count):
                neighbors = adj.get(v, [])
                if not neighbors:
                    continue
                avg = [0.0] * len(influences)
                for n in neighbors:
                    for i in range(len(influences)):
                        avg[i] += weights[n][i]
                for i in range(len(influences)):
                    avg[i] /= len(neighbors)
                # Blend with current
                strength = settings.strength
                for i in range(len(influences)):
                    new_val = weights[v][i] + (avg[i] - weights[v][i]) * strength
                    # Track delta
                    total_delta += abs(new_val - weights[v][i])
                    new_weights[v][i] = new_val
            weights = new_weights

        # Normalize each vertex
        for v in range(vertex_count):
            w_sum = sum(weights[v])
            if w_sum > 0:
                weights[v] = [w / w_sum for w in weights[v]]

        # Apply weights
        for v in range(vertex_count):
            for i, inf in enumerate(influences):
                cmds.skinPercent(skin, f"{mesh}.vtx[{v}]", transformValue=[(inf, weights[v][i])])

        stats = SmoothStatistics(
            processed_count=vertex_count,
            iterations=settings.iterations,
            average_delta=total_delta / (vertex_count * max(1, settings.iterations)) if vertex_count else 0.0,
            max_delta=0.0,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report

    def smooth_blendshape(self, blendshape_node: str,
                          settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """Smooth blendshape weights across targets."""
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.WEIGHT)
        start = time.time()

        if not cmds.objExists(blendshape_node):
            report.errors.append(f"Blendshape node '{blendshape_node}' does not exist.")
            report.success = False
            return report

        targets = cmds.listAttr(blendshape_node, m=True, string='weight') or []
        if not targets:
            report.warnings.append("No weight targets found.")
            report.success = True
            return report

        # Get current weights
        weights = [cmds.getAttr(f"{blendshape_node}.{t}") for t in targets]
        total_delta = 0.0

        for _ in range(settings.iterations):
            new_weights = weights[:]
            for i in range(1, len(weights)-1):
                avg = (weights[i-1] + weights[i+1]) * 0.5
                new_val = weights[i] + (avg - weights[i]) * settings.strength
                total_delta += abs(new_val - weights[i])
                new_weights[i] = new_val
            weights = new_weights

        # Apply
        for t, w in zip(targets, weights):
            cmds.setAttr(f"{blendshape_node}.{t}", w)

        stats = SmoothStatistics(
            processed_count=len(targets),
            iterations=settings.iterations,
            average_delta=total_delta / (len(targets) * max(1, settings.iterations)) if targets else 0.0,
            max_delta=0.0,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report

    def _build_adjacency(self, mesh: str) -> Dict[int, List[int]]:
        """Build vertex adjacency map."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        num_vertices = fn_mesh.numVertices()
        adj = {i: [] for i in range(num_vertices)}
        for i in range(num_vertices):
            connected = fn_mesh.getConnectedVertices(i)
            adj[i] = list(set(connected))
        return adj