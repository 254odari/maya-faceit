# -*- coding: utf-8 -*-
"""
tools/relax/relax_tools.py

Main facade for relaxation operations.
"""

import logging
import maya.cmds as cmds # type: ignore
from typing import Optional, List, Union
from .types import (
    RelaxMode, RelaxAlgorithm, RelaxSettings, RelaxReport,
    ValidationResult, WeightType
)
from .settings import DEFAULT_RELAX_SETTINGS
from .engine import RelaxEngine
from .mesh import MeshRelaxer
from .vertex import VertexRelaxer
from .surface import SurfaceRelaxer
from .weight import WeightRelaxer
from .uv import UVRelaxer
from .region import RegionRelaxer
from .validation import RelaxValidator
from .utils import RelaxUtils
from .reporter import RelaxReporter

logger = logging.getLogger(__name__)


class RelaxTools:
    """
    Main facade for all relaxation operations.
    """

    def __init__(self, settings: Optional[RelaxSettings] = None):
        self.settings = settings or DEFAULT_RELAX_SETTINGS
        self.engine = RelaxEngine(self.settings)
        self.mesh_relaxer = MeshRelaxer(self.engine)
        self.vertex_relaxer = VertexRelaxer(self.engine)
        self.surface_relaxer = SurfaceRelaxer(self.engine)
        self.weight_relaxer = WeightRelaxer(self.engine)
        self.uv_relaxer = UVRelaxer(self.engine)
        self.region_relaxer = RegionRelaxer(self.engine)
        self.validator = RelaxValidator()
        self.utils = RelaxUtils()
        self.reporter = RelaxReporter()
        self._undo_open = False

    # -------------------------------------------------------------------------
    # Undo Management
    # -------------------------------------------------------------------------
    def begin_undo(self, name: str = "Relax Operation"):
        if not self._undo_open:
            cmds.undoInfo(openChunk=True, chunkName=name)
            self._undo_open = True

    def end_undo(self):
        if self._undo_open:
            cmds.undoInfo(closeChunk=True)
            self._undo_open = False

    def __enter__(self):
        self.begin_undo(self.settings.undo_chunk_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_undo()

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------
    def mesh(self, mesh: Optional[str] = None) -> RelaxReport:
        """Relax entire mesh (or selected vertices if mesh is None)."""
        if mesh is None:
            mesh = self.utils.get_mesh_from_selection()
            if not mesh:
                report = RelaxReport(mode=RelaxMode.MESH, success=False)
                report.errors.append("No mesh selected.")
                return report
        return self.mesh_relaxer.relax(mesh)

    def vertices(self, mesh: Optional[str] = None, indices: Optional[List[int]] = None) -> RelaxReport:
        """Relax selected vertices (or specified indices)."""
        if mesh is None:
            mesh, indices = self.utils.get_selected_vertices()
            if not mesh or not indices:
                report = RelaxReport(mode=RelaxMode.VERTEX, success=False)
                report.errors.append("No vertices selected.")
                return report
        else:
            if indices is None:
                report = RelaxReport(mode=RelaxMode.VERTEX, success=False)
                report.errors.append("Indices required if mesh is specified.")
                return report
        validation = self.validator.validate_vertices(mesh, indices)
        if not validation.valid:
            report = RelaxReport(mode=RelaxMode.VERTEX, success=False)
            report.errors = validation.errors
            return report
        return self.mesh_relaxer.relax(mesh, indices)

    def surface(self, surface: str) -> RelaxReport:
        """Relax a NURBS surface or polygon mesh."""
        return self.surface_relaxer.relax_surface(surface)

    def weights(self, mesh: str, weight_type: WeightType = WeightType.SKIN) -> RelaxReport:
        """Relax skin weights or blendshape weights."""
        if weight_type == WeightType.SKIN:
            return self.weight_relaxer.relax_skin_weights(mesh)
        elif weight_type == WeightType.BLENDSHAPE:
            return self.weight_relaxer.relax_blendshape_weights(mesh)
        else:
            report = RelaxReport(mode=RelaxMode.WEIGHT, success=False)
            report.errors.append(f"Weight type {weight_type} not implemented.")
            return report

    def uvs(self, mesh: str, uv_set: Optional[str] = None) -> RelaxReport:
        """Relax UVs of a mesh."""
        return self.uv_relaxer.relax_uvs(mesh, uv_set)

    def region(self, mesh: str, region: str) -> RelaxReport:
        """Relax a specific facial region."""
        return self.region_relaxer.relax_region(mesh, region)

    def validate(self, mesh: str) -> ValidationResult:
        """Validate mesh for relaxation."""
        return self.validator.validate_mesh(mesh)

    def preview(self, mesh: str, iterations: int = 1) -> None:
        """Preview relaxation (placeholder)."""
        logger.warning("Preview not implemented.")

    def cancel(self) -> None:
        """Cancel current operation (placeholder)."""
        logger.warning("Cancel not implemented.")

    def set_settings(self, settings: RelaxSettings):
        self.settings = settings
        self.engine.settings = settings

    def get_settings(self) -> RelaxSettings:
        return self.settings


# =============================================================================
# Global instance and convenience functions
# =============================================================================

_relax_tools: Optional[RelaxTools] = None


def get_relax_tools() -> RelaxTools:
    """Get the global RelaxTools instance."""
    global _relax_tools
    if _relax_tools is None:
        _relax_tools = RelaxTools()
    return _relax_tools


def relax_mesh(mesh: Optional[str] = None) -> RelaxReport:
    return get_relax_tools().mesh(mesh)


def relax_vertices(mesh: Optional[str] = None, indices: Optional[List[int]] = None) -> RelaxReport:
    return get_relax_tools().vertices(mesh, indices)


def relax_surface(surface: str) -> RelaxReport:
    return get_relax_tools().surface(surface)


def relax_skin_weights(mesh: str) -> RelaxReport:
    return get_relax_tools().weights(mesh, WeightType.SKIN)


def relax_blendshape_weights(blendshape_node: str) -> RelaxReport:
    return get_relax_tools().weights(blendshape_node, WeightType.BLENDSHAPE)


def relax_uvs(mesh: str, uv_set: Optional[str] = None) -> RelaxReport:
    return get_relax_tools().uvs(mesh, uv_set)


def relax_region(mesh: str, region: str) -> RelaxReport:
    return get_relax_tools().region(mesh, region)


def set_relax_settings(settings: RelaxSettings):
    get_relax_tools().set_settings(settings)