# -*- coding: utf-8 -*-
"""
tools/smooth/curve.py

Curve smoothing (NURBS curves and animation keyframes).
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import time
import math
from typing import List, Optional
from .types import SmoothSettings, SmoothReport, SmoothMode, SmoothStatistics


class CurveSmoother:
    """
    Smooth NURBS curves and animation keyframes.
    """

    def __init__(self, algorithm_engine, settings: SmoothSettings):
        self.engine = algorithm_engine
        self.settings = settings

    def smooth_curve(self, curve: str, settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """Smooth a NURBS curve."""
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.CURVE)
        start = time.time()

        if not cmds.objExists(curve):
            report.errors.append(f"Curve '{curve}' does not exist.")
            report.success = False
            return report

        # Get CV positions
        cvs = cmds.getAttr(f"{curve}.controlPoints[*]")
        if not cvs:
            report.errors.append("No control points found.")
            report.success = False
            return report

        num_cvs = len(cvs)
        points = [(cv[0], cv[1], cv[2]) for cv in cvs]

        # Build adjacency (linear)
        adj = {i: [] for i in range(num_cvs)}
        for i in range(num_cvs):
            if i > 0:
                adj[i].append(i-1)
            if i < num_cvs-1:
                adj[i].append(i+1)

        total_delta = 0.0
        max_delta = 0.0
        for _ in range(settings.iterations):
            smoothed = self.engine.smooth_points(points, adj, boundary=set())
            for i, (old, new) in enumerate(zip(points, smoothed)):
                dx = new[0] - old[0]
                dy = new[1] - old[1]
                dz = new[2] - old[2]
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                total_delta += dist
                if dist > max_delta:
                    max_delta = dist
            points = smoothed

        # Apply
        for i, p in enumerate(points):
            cmds.setAttr(f"{curve}.controlPoints[{i}]", p[0], p[1], p[2])

        stats = SmoothStatistics(
            processed_count=num_cvs,
            iterations=settings.iterations,
            average_delta=total_delta / (num_cvs * max(1, settings.iterations)) if num_cvs else 0.0,
            max_delta=max_delta,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report

    def smooth_keyframes(self, objects: List[str],
                         attributes: Optional[List[str]] = None,
                         settings: Optional[SmoothSettings] = None) -> SmoothReport:
        """Smooth animation keyframes."""
        if settings is None:
            settings = self.settings

        report = SmoothReport(mode=SmoothMode.CURVE)
        start = time.time()

        total_curves = 0
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            if attributes is None:
                attrs = cmds.listAttr(obj, keyable=True) or []
            else:
                attrs = [a for a in attributes if cmds.objExists(f"{obj}.{a}")]
            for attr in attrs:
                full = f"{obj}.{attr}"
                if not cmds.keyframe(full, q=True, keyframeCount=True):
                    continue
                times = cmds.keyframe(full, q=True, timeChange=True) or []
                values = cmds.keyframe(full, q=True, valueChange=True) or []
                if len(times) < 3:
                    continue
                # Smooth values
                smoothed = values[:]
                for _ in range(settings.iterations):
                    new_vals = smoothed[:]
                    for i in range(1, len(values)-1):
                        avg = (smoothed[i-1] + smoothed[i+1]) * 0.5
                        new_vals[i] = smoothed[i] + (avg - smoothed[i]) * settings.strength
                    smoothed = new_vals
                # Apply
                for t, v in zip(times, smoothed):
                    cmds.setKeyframe(full, t=t, value=v)
                total_curves += 1

        stats = SmoothStatistics(
            processed_count=total_curves,
            iterations=settings.iterations,
            time_ms=(time.time() - start) * 1000,
        )
        report.statistics = stats
        report.success = True
        return report