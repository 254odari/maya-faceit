# -*- coding: utf-8 -*-
"""
tools/analysis/engine.py

Main facade for analysis operations.
"""

import time
from typing import Optional, Dict, Any, List
from .types import (
    AnalysisScope, AnalysisLevel, AnalysisReport,
    SceneStats, MeshStats, RigStats, AnimationStats,
    PerformanceStats, DependencyStats
)
from .settings import DEFAULT_ANALYSIS_SETTINGS
from .scene import SceneAnalyzer
from .mesh import MeshAnalyzer
from .rig import RigAnalyzer
from .animation import AnimationAnalyzer
from .performance import PerformanceAnalyzer
from .dependencies import DependencyAnalyzer
from .reporter import AnalysisReporter


class AnalysisEngine:
    """
    Main facade for all analysis operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_ANALYSIS_SETTINGS
        self.scene_analyzer = SceneAnalyzer(self.settings)
        self.mesh_analyzer = MeshAnalyzer(self.settings)
        self.rig_analyzer = RigAnalyzer(self.settings)
        self.animation_analyzer = AnimationAnalyzer(self.settings)
        self.performance_analyzer = PerformanceAnalyzer(self.settings)
        self.dependency_analyzer = DependencyAnalyzer(self.settings)
        self.reporter = AnalysisReporter()

    # =========================================================================
    # COMPLETE ANALYSIS
    # =========================================================================

    def analyze_scene(self, scope: Optional[AnalysisScope] = None,
                      level: Optional[AnalysisLevel] = None) -> AnalysisReport:
        """
        Perform a complete scene analysis.

        Args:
            scope: Scope of analysis.
            level: Level of detail.

        Returns:
            AnalysisReport with all results.
        """
        start = time.time()
        scope = scope or self.settings.scope
        level = level or self.settings.level

        report = AnalysisReport(
            scope=scope,
            level=level,
            timestamp=time.ctime(),
        )

        # Run each analyzer
        if self.settings.analyze_scene:
            report.scene = self.scene_analyzer.analyze(scope, level)

        if self.settings.analyze_mesh:
            report.mesh = self.mesh_analyzer.analyze(scope, level)

        if self.settings.analyze_rig:
            report.rig = self.rig_analyzer.analyze(scope, level)

        if self.settings.analyze_animation:
            report.animation = self.animation_analyzer.analyze(scope, level)

        if self.settings.analyze_performance:
            report.performance = self.performance_analyzer.analyze(scope, level)

        if self.settings.analyze_dependencies:
            report.dependencies = self.dependency_analyzer.analyze(scope, level)

        # Collect warnings
        report.warnings = self._collect_warnings(report)
        report.duration_ms = (time.time() - start) * 1000

        return report

    # =========================================================================
    # INDIVIDUAL ANALYSES
    # =========================================================================

    def analyze_scene_only(self) -> SceneStats:
        """Analyze only scene statistics."""
        return self.scene_analyzer.analyze(self.settings.scope, self.settings.level)

    def analyze_mesh_only(self) -> MeshStats:
        """Analyze only mesh statistics."""
        return self.mesh_analyzer.analyze(self.settings.scope, self.settings.level)

    def analyze_rig_only(self) -> RigStats:
        """Analyze only rig statistics."""
        return self.rig_analyzer.analyze(self.settings.scope, self.settings.level)

    def analyze_animation_only(self) -> AnimationStats:
        """Analyze only animation statistics."""
        return self.animation_analyzer.analyze(self.settings.scope, self.settings.level)

    def analyze_performance_only(self) -> PerformanceStats:
        """Analyze only performance statistics."""
        return self.performance_analyzer.analyze(self.settings.scope, self.settings.level)

    def analyze_dependencies_only(self) -> DependencyStats:
        """Analyze only dependency statistics."""
        return self.dependency_analyzer.analyze(self.settings.scope, self.settings.level)

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_report(self, report: Optional[AnalysisReport] = None):
        """Print a formatted report."""
        if report is None:
            report = self.analyze_scene()
        print(report.summary())

    def save_report(self, report: AnalysisReport, filepath: str, format: str = "json") -> bool:
        """Save a report to a file."""
        return self.reporter.save_report(report, filepath, format)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _collect_warnings(self, report: AnalysisReport) -> List[str]:
        """Collect warnings from all sections."""
        warnings = []
        # Scene warnings
        if report.scene.unknown_nodes:
            warnings.append(f"Unknown nodes: {report.scene.unknown_nodes}")
        if report.scene.empty_groups:
            warnings.append(f"Empty groups: {report.scene.empty_groups}")

        # Mesh warnings
        if report.mesh.non_manifold_edges:
            warnings.append(f"Non-manifold edges: {report.mesh.non_manifold_edges}")
        if report.mesh.lamina_faces:
            warnings.append(f"Lamina faces: {report.mesh.lamina_faces}")
        if report.mesh.total_ngons:
            warnings.append(f"N-Gons: {report.mesh.total_ngons}")

        # Rig warnings
        if report.rig.orphan_joints:
            warnings.append(f"Orphan joints: {report.rig.orphan_joints}")
        if report.rig.orphan_controllers:
            warnings.append(f"Orphan controllers: {report.rig.orphan_controllers}")
        if report.rig.invalid_constraints:
            warnings.append(f"Invalid constraints: {report.rig.invalid_constraints}")

        # Animation warnings
        if report.animation.empty_curves:
            warnings.append(f"Empty curves: {report.animation.empty_curves}")
        if report.animation.static_channels:
            warnings.append(f"Static channels: {report.animation.static_channels}")

        # Performance warnings
        if not report.performance.gpu_compatible:
            warnings.append("GPU compatibility: partial or none")

        return warnings

    def set_settings(self, settings):
        self.settings = settings

    def get_settings(self):
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

analysis = AnalysisEngine()

__all__ = ["AnalysisEngine", "analysis"]