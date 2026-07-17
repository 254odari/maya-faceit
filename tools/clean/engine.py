# -*- coding: utf-8 -*-
"""
tools/clean/engine.py

Main facade for cleanup operations.
"""

import time
import maya.cmds as cmds # type: ignore
from typing import Optional, List, Dict, Any
from .types import (
    CleanupType, CleanupMode, CleanupReport,
    SceneCleanup, MeshCleanup, MaterialCleanup,
    AnimationCleanup, RigCleanup, BlendshapeCleanup,
    NamespaceCleanup
)
from .settings import DEFAULT_CLEANUP_SETTINGS
from .scene import SceneCleaner
from .mesh import MeshCleaner
from .materials import MaterialCleaner
from .animation import AnimationCleaner
from .rig import RigCleaner
from .blendshape import BlendshapeCleaner
from .namespace import NamespaceCleaner
from .reporter import CleanupReporter


class CleanEngine:
    """
    Main facade for all cleanup operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_CLEANUP_SETTINGS
        self.scene_cleaner = SceneCleaner(self.settings)
        self.mesh_cleaner = MeshCleaner(self.settings)
        self.material_cleaner = MaterialCleaner(self.settings)
        self.animation_cleaner = AnimationCleaner(self.settings)
        self.rig_cleaner = RigCleaner(self.settings)
        self.blendshape_cleaner = BlendshapeCleaner(self.settings)
        self.namespace_cleaner = NamespaceCleaner(self.settings)
        self.reporter = CleanupReporter()

    # =========================================================================
    # FULL CLEANUP
    # =========================================================================

    def cleanup_all(self, mode: Optional[CleanupMode] = None) -> CleanupReport:
        """
        Run all cleanup operations in sequence.

        Args:
            mode: Override cleanup mode.

        Returns:
            CleanupReport with combined results.
        """
        if mode is not None:
            self.settings.mode = mode

        start = time.time()
        report = CleanupReport(
            type=CleanupType.SCENE,
            mode=self.settings.mode
        )

        # Run each cleaner
        if self.settings.clean_scene:
            report.scene = self.scene_cleaner.cleanup()

        if self.settings.clean_mesh:
            report.mesh = self.mesh_cleaner.cleanup()

        if self.settings.clean_materials:
            report.material = self.material_cleaner.cleanup()

        if self.settings.clean_animation:
            report.animation = self.animation_cleaner.cleanup()

        if self.settings.clean_rig:
            report.rig = self.rig_cleaner.cleanup()

        if self.settings.clean_blendshape:
            report.blendshape = self.blendshape_cleaner.cleanup()

        if self.settings.clean_namespace:
            report.namespace = self.namespace_cleaner.cleanup()

        # Collect warnings/errors
        report.warnings = self._collect_warnings(report)
        report.errors = self._collect_errors(report)
        report.success = len(report.errors) == 0

        report.elapsed_time_ms = (time.time() - start) * 1000

        return report

    # =========================================================================
    # INDIVIDUAL CLEANUP OPERATIONS
    # =========================================================================

    def cleanup_scene(self) -> SceneCleanup:
        """Clean up scene-level elements."""
        return self.scene_cleaner.cleanup()

    def cleanup_mesh(self) -> MeshCleanup:
        """Clean up meshes."""
        return self.mesh_cleaner.cleanup()

    def cleanup_materials(self) -> MaterialCleanup:
        """Clean up materials and textures."""
        return self.material_cleaner.cleanup()

    def cleanup_animation(self) -> AnimationCleanup:
        """Clean up animation data."""
        return self.animation_cleaner.cleanup()

    def cleanup_rig(self) -> RigCleanup:
        """Clean up rig components."""
        return self.rig_cleaner.cleanup()

    def cleanup_blendshapes(self) -> BlendshapeCleanup:
        """Clean up blendshapes."""
        return self.blendshape_cleaner.cleanup()

    def cleanup_namespaces(self) -> NamespaceCleanup:
        """Clean up namespaces."""
        return self.namespace_cleaner.cleanup()

    # =========================================================================
    # PREVIEW
    # =========================================================================

    def preview(self) -> CleanupReport:
        """
        Preview what would be cleaned without modifying the scene.

        Returns:
            CleanupReport with preview data.
        """
        # For preview, we can analyze but not delete
        # We'll temporarily set a dry-run flag
        # This is a placeholder; real implementation would scan without deleting
        report = CleanupReport(
            type=CleanupType.SCENE,
            mode=self.settings.mode
        )
        report.warnings.append("Preview mode: no changes were made.")
        return report

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_report(self, report: Optional[CleanupReport] = None):
        """Print a formatted cleanup report."""
        if report is None:
            report = self.cleanup_all()
        print(report.summary())

    def save_report(self, report: CleanupReport, filepath: str, format: str = "json") -> bool:
        """Save a report to a file."""
        return self.reporter.save_report(report, filepath, format)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _collect_warnings(self, report: CleanupReport) -> List[str]:
        warnings = []
        if report.scene:
            warnings.extend(report.scene.__dict__.get('warnings', []))
        if report.mesh:
            warnings.extend(report.mesh.__dict__.get('warnings', []))
        if report.material:
            warnings.extend(report.material.__dict__.get('warnings', []))
        if report.animation:
            warnings.extend(report.animation.__dict__.get('warnings', []))
        if report.rig:
            warnings.extend(report.rig.__dict__.get('warnings', []))
        if report.blendshape:
            warnings.extend(report.blendshape.__dict__.get('warnings', []))
        if report.namespace:
            warnings.extend(report.namespace.__dict__.get('warnings', []))
        return warnings

    def _collect_errors(self, report: CleanupReport) -> List[str]:
        errors = []
        if report.scene:
            errors.extend(report.scene.__dict__.get('errors', []))
        if report.mesh:
            errors.extend(report.mesh.__dict__.get('errors', []))
        if report.material:
            errors.extend(report.material.__dict__.get('errors', []))
        if report.animation:
            errors.extend(report.animation.__dict__.get('errors', []))
        if report.rig:
            errors.extend(report.rig.__dict__.get('errors', []))
        if report.blendshape:
            errors.extend(report.blendshape.__dict__.get('errors', []))
        if report.namespace:
            errors.extend(report.namespace.__dict__.get('errors', []))
        return errors

    def set_settings(self, settings):
        self.settings = settings

    def get_settings(self):
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

clean = CleanEngine()

__all__ = ["CleanEngine", "clean"]