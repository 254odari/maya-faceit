# -*- coding: utf-8 -*-
"""
tools/smooth/normal.py

Normal smoothing.
"""

import maya.cmds as cmds # type: ignore
import time
from .types import SmoothSettings, SmoothReport, SmoothMode, SmoothStatistics


class NormalSmoother:
    """
    Smooth normals (soften/harden).
    """

    def __init__(self, algorithm_engine, settings: SmoothSettings):
        self.engine = algorithm_engine
        self.settings = settings

    def smooth_normals(self, mesh: str, angle: float = 30.0) -> SmoothReport:
        """Smooth normals by softening."""
        report = SmoothReport(mode=SmoothMode.NORMAL)
        start = time.time()

        if not cmds.objExists(mesh):
            report.errors.append(f"Mesh '{mesh}' does not exist.")
            report.success = False
            return report

        try:
            cmds.polySoftNormals(mesh, angle=angle)
            stats = SmoothStatistics(
                processed_count=1,
                iterations=1,
                time_ms=(time.time() - start) * 1000,
            )
            report.statistics = stats
            report.success = True
        except Exception as e:
            report.errors.append(str(e))
            report.success = False

        return report