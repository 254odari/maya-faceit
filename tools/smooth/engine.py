# -*- coding: utf-8 -*-
"""
tools/smooth/engine.py

Main facade for smoothing operations.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, List, Union, Dict, Any
from .types import (
    SmoothMode, SmoothAlgorithm, SmoothBoundary,
    SmoothFalloff, SmoothSettings, SmoothReport,
    SmoothStatistics, SmoothValidation
)
from .settings import DEFAULT_SMOOTH_SETTINGS
from .algorithms import SmoothAlgorithmEngine
from .mesh import MeshSmoother
from .weight import WeightSmoother
from .curve import CurveSmoother
from .uv import UVSmoother
from .normal import NormalSmoother
from .validation import SmoothValidator


class SmoothEngine:
    """
    Main facade for all smoothing operations.
    """

    def __init__(self, settings: Optional[SmoothSettings] = None):
        self.settings = settings or DEFAULT_SMOOTH_SETTINGS
        self.algorithm_engine = SmoothAlgorithmEngine(self.settings)
        self.mesh_smoother = MeshSmoother(self.algorithm_engine, self.settings)
        self.weight_smoother = WeightSmoother(self.algorithm_engine, self.settings)
        self.curve_smoother = CurveSmoother(self.algorithm_engine, self.settings)
        self.uv_smoother = UVSmoother(self.algorithm_engine, self.settings)
        self.normal_smoother = NormalSmoother(self.algorithm_engine, self.settings)
        self.validator = SmoothValidator()

    # =========================================================================
    # MESH SMOOTHING
    # =========================================================================

    def mesh(self, mesh: Optional[str] = None,
             iterations: Optional[int] = None,
             strength: Optional[float] = None,
             algorithm: Optional[SmoothAlgorithm] = None,
             preserve_border: Optional[bool] = None) -> SmoothReport:
        """
        Smooth a polygon mesh.

        Args:
            mesh: Mesh name. If None, uses active selection.
            iterations: Number of iterations (uses settings if None).
            strength: Smoothing strength (uses settings if None).
            algorithm: Smoothing algorithm (uses settings if None).
            preserve_border: Preserve border vertices (uses settings if None).

        Returns:
            SmoothReport.
        """
        # Apply overrides
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        if algorithm is not None:
            self.settings.algorithm = algorithm
        if preserve_border is not None:
            self.settings.preserve_border = preserve_border

        if mesh is None:
            mesh = self._get_active_mesh()
            if not mesh:
                report = SmoothReport(mode=SmoothMode.MESH, success=False)
                report.errors.append("No mesh selected.")
                return report

        return self.mesh_smoother.smooth(mesh, self.settings)

    # =========================================================================
    # WEIGHT SMOOTHING
    # =========================================================================

    def weights(self, skin: str, iterations: Optional[int] = None,
                strength: Optional[float] = None) -> SmoothReport:
        """
        Smooth skin weights.

        Args:
            skin: SkinCluster name.
            iterations: Number of iterations.
            strength: Smoothing strength.

        Returns:
            SmoothReport.
        """
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        return self.weight_smoother.smooth_skin(skin, self.settings)

    def blendshape_weights(self, blendshape_node: str,
                           iterations: Optional[int] = None,
                           strength: Optional[float] = None) -> SmoothReport:
        """Smooth blendshape weights across targets."""
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        return self.weight_smoother.smooth_blendshape(blendshape_node, self.settings)

    # =========================================================================
    # CURVE SMOOTHING
    # =========================================================================

    def curve(self, curve: str, iterations: Optional[int] = None,
              strength: Optional[float] = None) -> SmoothReport:
        """Smooth a NURBS curve."""
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        return self.curve_smoother.smooth_curve(curve, self.settings)

    def keyframes(self, objects: List[str], attributes: Optional[List[str]] = None,
                  iterations: Optional[int] = None,
                  strength: Optional[float] = None) -> SmoothReport:
        """Smooth animation keyframes."""
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        return self.curve_smoother.smooth_keyframes(objects, attributes, self.settings)

    # =========================================================================
    # UV SMOOTHING
    # =========================================================================

    def uvs(self, mesh: str, uv_set: Optional[str] = None,
            iterations: Optional[int] = None,
            strength: Optional[float] = None) -> SmoothReport:
        """Smooth UVs."""
        if iterations is not None:
            self.settings.iterations = iterations
        if strength is not None:
            self.settings.strength = strength
        return self.uv_smoother.smooth_uvs(mesh, uv_set, self.settings)

    # =========================================================================
    # NORMAL SMOOTHING
    # =========================================================================

    def normals(self, mesh: str, angle: float = 30.0) -> SmoothReport:
        """Smooth normals (soften)."""
        return self.normal_smoother.smooth_normals(mesh, angle)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_mesh(self, mesh: str) -> SmoothValidation:
        """Validate a mesh for smoothing."""
        return self.validator.validate_mesh(mesh)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def set_settings(self, settings: SmoothSettings):
        self.settings = settings
        self.algorithm_engine.settings = settings

    def get_settings(self) -> SmoothSettings:
        return self.settings

    def _get_active_mesh(self) -> Optional[str]:
        """Get the currently selected mesh transform."""
        selection = cmds.ls(selection=True, long=True)
        for obj in selection:
            shapes = cmds.listRelatives(obj, shapes=True) or []
            if shapes and cmds.nodeType(shapes[0]) == "mesh":
                return obj
        return None


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

smooth = SmoothEngine()

__all__ = ["SmoothEngine", "smooth"]