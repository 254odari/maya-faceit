# -*- coding: utf-8 -*-
"""
tools/optimizer/engine.py

Main facade for optimization operations.
"""

import time
import maya.cmds as cmds # type: ignore
from typing import Optional, List, Dict, Any
from .types import (
    OptimizationType, OptimizationLevel, EvaluationMode,
    OptimizationReport, SceneOptimization, MeshOptimization,
    RigOptimization, BlendshapeOptimization, SkinOptimization,
    DeformerOptimization, AnimationOptimization, EvaluationOptimization
)
from .settings import DEFAULT_OPTIMIZATION_SETTINGS
from .scene import SceneOptimizer
from .mesh import MeshOptimizer
from .rig import RigOptimizer
from .blendshape import BlendshapeOptimizer
from .skin import SkinOptimizer
from .deformer import DeformerOptimizer
from .animation import AnimationOptimizer
from .evaluation import EvaluationOptimizer
from .reporter import OptimizationReporter


class OptimizerEngine:
    """
    Main facade for all optimization operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_OPTIMIZATION_SETTINGS
        self.scene_optimizer = SceneOptimizer(self.settings)
        self.mesh_optimizer = MeshOptimizer(self.settings)
        self.rig_optimizer = RigOptimizer(self.settings)
        self.blendshape_optimizer = BlendshapeOptimizer(self.settings)
        self.skin_optimizer = SkinOptimizer(self.settings)
        self.deformer_optimizer = DeformerOptimizer(self.settings)
        self.animation_optimizer = AnimationOptimizer(self.settings)
        self.evaluation_optimizer = EvaluationOptimizer(self.settings)
        self.reporter = OptimizationReporter()

    # =========================================================================
    # FULL OPTIMIZATION
    # =========================================================================

    def optimize_all(self, level: Optional[OptimizationLevel] = None) -> OptimizationReport:
        """
        Run all optimizations in sequence.

        Args:
            level: Override optimization level.

        Returns:
            OptimizationReport with combined results.
        """
        if level is not None:
            self.settings.level = level

        start = time.time()
        report = OptimizationReport(
            type=OptimizationType.SCENE,
            level=self.settings.level
        )

        # Run each optimizer
        if self.settings.optimize_scene:
            report.scene = self.scene_optimizer.optimize()

        if self.settings.optimize_mesh:
            report.mesh = self.mesh_optimizer.optimize()

        if self.settings.optimize_rig:
            report.rig = self.rig_optimizer.optimize()

        if self.settings.optimize_blendshape:
            report.blendshape = self.blendshape_optimizer.optimize()

        if self.settings.optimize_skin:
            report.skin = self.skin_optimizer.optimize()

        if self.settings.optimize_deformer:
            report.deformer = self.deformer_optimizer.optimize()

        if self.settings.optimize_animation:
            report.animation = self.animation_optimizer.optimize()

        if self.settings.optimize_evaluation:
            report.evaluation = self.evaluation_optimizer.optimize()

        # Collect warnings/errors
        report.warnings = self._collect_warnings(report)
        report.errors = self._collect_errors(report)
        report.success = len(report.errors) == 0

        # Benchmark if enabled
        if self.settings.auto_benchmark:
            report.fps_before = self._get_fps()
            # After optimization, get FPS
            report.fps_after = self._get_fps()

        report.elapsed_time_ms = (time.time() - start) * 1000

        return report

    # =========================================================================
    # INDIVIDUAL OPTIMIZATIONS
    # =========================================================================

    def optimize_scene(self) -> SceneOptimization:
        """Optimize scene-level elements."""
        return self.scene_optimizer.optimize()

    def optimize_mesh(self) -> MeshOptimization:
        """Optimize meshes."""
        return self.mesh_optimizer.optimize()

    def optimize_rig(self) -> RigOptimization:
        """Optimize rig controllers."""
        return self.rig_optimizer.optimize()

    def optimize_blendshapes(self) -> BlendshapeOptimization:
        """Optimize blendshapes."""
        return self.blendshape_optimizer.optimize()

    def optimize_skin(self) -> SkinOptimization:
        """Optimize skinClusters."""
        return self.skin_optimizer.optimize()

    def optimize_deformers(self) -> DeformerOptimization:
        """Optimize deformer stack."""
        return self.deformer_optimizer.optimize()

    def optimize_animation(self) -> AnimationOptimization:
        """Optimize animation curves."""
        return self.animation_optimizer.optimize()

    def optimize_evaluation(self) -> EvaluationOptimization:
        """Optimize evaluation settings."""
        return self.evaluation_optimizer.optimize()

    # =========================================================================
    # BENCHMARKING
    # =========================================================================

    def benchmark(self) -> Dict[str, float]:
        """
        Benchmark current scene performance.

        Returns:
            Dict with 'fps' and 'memory_mb' keys.
        """
        return {
            'fps': self._get_fps(),
            'memory_mb': self._get_memory_usage(),
        }

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_report(self, report: Optional[OptimizationReport] = None):
        """Print a formatted optimization report."""
        if report is None:
            report = self.optimize_all()
        print(report.summary())

    def save_report(self, report: OptimizationReport, filepath: str, format: str = "json") -> bool:
        """Save a report to a file."""
        return self.reporter.save_report(report, filepath, format)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _collect_warnings(self, report: OptimizationReport) -> List[str]:
        """Collect warnings from all sections."""
        warnings = []
        if report.scene:
            warnings.extend([f"Scene: {w}" for w in report.scene.__dict__.get('warnings', [])])
        if report.mesh:
            warnings.extend([f"Mesh: {w}" for w in report.mesh.__dict__.get('warnings', [])])
        if report.rig:
            warnings.extend([f"Rig: {w}" for w in report.rig.__dict__.get('warnings', [])])
        if report.blendshape:
            warnings.extend([f"Blendshape: {w}" for w in report.blendshape.__dict__.get('warnings', [])])
        if report.skin:
            warnings.extend([f"Skin: {w}" for w in report.skin.__dict__.get('warnings', [])])
        if report.deformer:
            warnings.extend([f"Deformer: {w}" for w in report.deformer.__dict__.get('warnings', [])])
        if report.animation:
            warnings.extend([f"Animation: {w}" for w in report.animation.__dict__.get('warnings', [])])
        return warnings

    def _collect_errors(self, report: OptimizationReport) -> List[str]:
        """Collect errors from all sections."""
        errors = []
        if report.scene:
            errors.extend([f"Scene: {e}" for e in report.scene.__dict__.get('errors', [])])
        if report.mesh:
            errors.extend([f"Mesh: {e}" for e in report.mesh.__dict__.get('errors', [])])
        if report.rig:
            errors.extend([f"Rig: {e}" for e in report.rig.__dict__.get('errors', [])])
        if report.blendshape:
            errors.extend([f"Blendshape: {e}" for e in report.blendshape.__dict__.get('errors', [])])
        if report.skin:
            errors.extend([f"Skin: {e}" for e in report.skin.__dict__.get('errors', [])])
        if report.deformer:
            errors.extend([f"Deformer: {e}" for e in report.deformer.__dict__.get('errors', [])])
        if report.animation:
            errors.extend([f"Animation: {e}" for e in report.animation.__dict__.get('errors', [])])
        return errors

    def _get_fps(self) -> float:
        """Measure current FPS by evaluating 10 frames."""
        try:
            start = time.time()
            frames = 10
            for _ in range(frames):
                cmds.currentTime(cmds.currentTime(q=True) + 1, update=True)
            elapsed = time.time() - start
            if elapsed > 0:
                return frames / elapsed
        except:
            pass
        return 0.0

    def _get_memory_usage(self) -> float:
        """Get approximate memory usage."""
        try:
            import maya.mel as mel # type: ignore
            mem = mel.eval('memory -q -size -units MB')
            return float(mem)
        except:
            return 0.0

    def set_settings(self, settings):
        self.settings = settings

    def get_settings(self):
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

optimizer = OptimizerEngine()

__all__ = ["OptimizerEngine", "optimizer"]