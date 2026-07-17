"""
tools/mesh/core/engine.py

MeshEngine - Central controller and facade for all mesh operations.
Orchestrates the full pipeline: Validation → Analysis → Operation → Repair → Statistics → Report.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from enum import Enum, auto
import maya.cmds as cmds # type: ignore

from ..types import (
    MeshSettings, MeshStatistics, MeshReport, MeshIssue,
    MeshOperation, MeshSelection, UVCoordinate
)
from ..settings import get_settings_for_operation, DEFAULT_MESH_SETTINGS

# Import subsystems (will be initialized in __post_init__)
from .editor import MeshEditor
from ..validation.validator import MeshValidator
from ..analysis.analyzer import MeshAnalyzer
from ..repair.repair import MeshRepair
from ..components.vertices import VertexTools
from ..components.edges import EdgeTools
from ..components.faces import FaceTools
from ..mapping.uvs import UVTools
from ..mapping.normals import NormalTools
from ..operations.editing import MeshEditingTools
from ..operations.retopology import RetopologyTools
from ..utils.symmetry import SymmetryTools

# =============================================================================
# ENUMS (until they are moved to types.py)
# =============================================================================

class UVProjection(Enum):
    """UV projection methods."""
    AUTOMATIC = auto()
    PLANAR = auto()
    CYLINDRICAL = auto()
    SPHERICAL = auto()
    CUSTOM = auto()


class NormalMode(Enum):
    """Normal recalculation modes."""
    RECALCULATE = auto()
    SMOOTH = auto()
    HARD = auto()
    CUSTOM = auto()


# =============================================================================
# MESH ENGINE
# =============================================================================

class MeshEngine:
    """
    Main mesh processing engine for maya_faceit.
    Acts as a Facade + Pipeline Controller.
    """

    def __init__(self):
        self.settings: MeshSettings = DEFAULT_MESH_SETTINGS

        # Subsystem initialization
        self.editor = MeshEditor()
        self.validator = MeshValidator()
        self.analyzer = MeshAnalyzer()
        self.repair = MeshRepair()

        # Component tools
        self.vertices = VertexTools(self.editor)
        self.edges = EdgeTools(self.editor)
        self.faces = FaceTools(self.editor)

        # Mapping tools
        self.uvs = UVTools(self.editor)
        self.normals = NormalTools(self.editor)

        # Operations
        self.editing = MeshEditingTools(self.editor)
        self.retopology = RetopologyTools(self.editor)

        # Utilities
        self.symmetry = SymmetryTools()

    # =========================================================================
    # PIPELINE MANAGEMENT
    # =========================================================================

    @contextmanager
    def operation(self, name: str, settings: Optional[MeshSettings] = None):
        """Context manager for safe operation execution with undo and reporting."""
        start_time = time.time()
        report = MeshReport(operation=name, success=False)

        if settings:
            self.settings = settings
        else:
            self.settings = get_settings_for_operation(name)

        try:
            if self.settings.use_undo_chunk:
                with self.editor.undo_chunk(name):
                    yield report
            else:
                yield report

            report.success = True
            report.elapsed_time = time.time() - start_time
            report.meshes_processed = 1  # Can be updated in batch mode

        except Exception as e:
            report.warnings.append(f"Operation failed: {str(e)}")
            raise
        finally:
            # Always generate final statistics
            try:
                report.statistics = self.analyzer.get_statistics()
            except:
                pass

    # =========================================================================
    # PUBLIC HIGH-LEVEL API
    # =========================================================================

    def validate(self, mesh: Optional[MeshSelection] = None) -> MeshReport:
        """Full mesh validation."""
        with self.operation("validate") as report:
            issues = self.validator.validate(mesh or self.get_active_mesh())
            report.issues = issues
            report.success = len([i for i in issues if i.severity == "ERROR"]) == 0
        return report

    def repair(self, mesh: Optional[MeshSelection] = None) -> MeshReport:
        """Run full automated repair."""
        with self.operation("repair") as report:
            repaired = self.repair.run_full_repair(mesh or self.get_active_mesh())
            report.repaired_count = repaired
        return report

    def cleanup(self, mesh: Optional[MeshSelection] = None) -> MeshReport:
        """Standard cleanup pipeline."""
        with self.operation("cleanup") as report:
            self.repair.cleanup(mesh)
            self.validator.validate(mesh)
        return report

    def optimize(self, mesh: Optional[MeshSelection] = None) -> MeshReport:
        """Optimize mesh for performance / rendering."""
        with self.operation("optimize") as report:
            self.repair.optimize(mesh)
        return report

    # =========================================================================
    # DELEGATED OPERATIONS
    # =========================================================================

    def merge_vertices(self, distance: float = 0.001, **kwargs):
        return self.vertices.merge(distance=distance, **kwargs)

    def relax_vertices(self, iterations: int = 10, **kwargs):
        return self.vertices.relax(iterations=iterations, **kwargs)

    def recalculate_normals(self, mode: NormalMode = NormalMode.RECALCULATE, **kwargs):
        return self.normals.recalculate(mode=mode, **kwargs)

    def poly_reduce(self, percent: float = 50.0, **kwargs):
        return self.retopology.poly_reduce(percent=percent, **kwargs)

    def remesh(self, target_edge_length: Optional[float] = None, **kwargs):
        return self.retopology.remesh(target_edge_length=target_edge_length, **kwargs)

    # =========================================================================
    # UV OPERATIONS (Delegated to UVTools)
    # =========================================================================

    def auto_uv(self, mesh: Optional[str] = None, projection_type: str = "automatic", **kwargs) -> bool:
        """
        Automatically project UVs.

        Args:
            mesh: Mesh name. If None, uses active selection.
            projection_type: "automatic", "planar", "cylindrical", "spherical"
            **kwargs: Additional arguments to polyProjection.

        Returns:
            True if successful.
        """
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.auto_uv(mesh, projection_type, **kwargs)

    def planar_uv(self, mesh: Optional[str] = None, axis: str = "x", **kwargs) -> bool:
        """Planar UV projection."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.planar_project(mesh, axis, **kwargs)

    def cylindrical_uv(self, mesh: Optional[str] = None, axis: str = "y", **kwargs) -> bool:
        """Cylindrical UV projection."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.cylindrical_project(mesh, axis, **kwargs)

    def spherical_uv(self, mesh: Optional[str] = None, axis: str = "z", **kwargs) -> bool:
        """Spherical UV projection."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.spherical_project(mesh, axis, **kwargs)

    def unfold_uvs(self, mesh: Optional[str] = None, iterations: int = 10,
                   pin_selected: bool = False, **kwargs) -> bool:
        """Unfold UVs to reduce stretching."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.unfold(mesh, iterations, pin_selected, **kwargs)

    def layout_uvs(self, mesh: Optional[str] = None, resolution: int = 1024,
                   scale: float = 1.0, rotate_for_best_fit: bool = True,
                   **kwargs) -> bool:
        """Layout UV shells in 0-1 space."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.layout(mesh, resolution, scale, rotate_for_best_fit, **kwargs)

    def optimize_uvs(self, mesh: Optional[str] = None, iterations: int = 5, **kwargs) -> bool:
        """Optimize UVs (reduce distortion)."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.optimize(mesh, iterations, **kwargs)

    def sew_uvs(self, mesh: Optional[str] = None) -> bool:
        """Sew overlapping UV edges (merge seams)."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.sew(mesh)

    def move_uvs(self, mesh: Optional[str] = None,
                 u_offset: float = 0.0, v_offset: float = 0.0,
                 uv_set: Optional[str] = None) -> bool:
        """Move all UVs by an offset."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.move(mesh, u_offset, v_offset, uv_set)

    def scale_uvs(self, mesh: Optional[str] = None,
                  u_scale: float = 1.0, v_scale: float = 1.0,
                  uv_set: Optional[str] = None) -> bool:
        """Scale UVs."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.scale(mesh, u_scale, v_scale, uv_set)

    def rotate_uvs(self, mesh: Optional[str] = None,
                   angle: float = 0.0,
                   uv_set: Optional[str] = None) -> bool:
        """Rotate UVs around their center."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.rotate(mesh, angle, uv_set)

    def copy_uvs(self, source: str, target: str, uv_set: Optional[str] = None) -> bool:
        """Copy UVs from source to target using closest point mapping."""
        return self.uvs.copy(source, target, uv_set)

    def cleanup_uvs(self, mesh: Optional[str] = None, remove_unused: bool = True) -> bool:
        """Clean up UVs: remove unused, fix overlaps."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.cleanup(mesh, remove_unused)

    def get_uvs(self, mesh: Optional[str] = None, uv_set: Optional[str] = None) -> List[UVCoordinate]:
        """Get UV coordinates for all vertices."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.get_uvs(mesh, uv_set)

    def set_uvs(self, mesh: Optional[str] = None, uvs: Optional[List[UVCoordinate]] = None,
                uv_set: Optional[str] = None) -> bool:
        """Set UV coordinates for all vertices."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.set_uvs(mesh, uvs, uv_set)

    # =========================================================================
    # UV SET MANAGEMENT
    # =========================================================================

    def list_uv_sets(self, mesh: Optional[str] = None) -> List[str]:
        """List all UV sets on the mesh."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.list_uv_sets(mesh)

    def get_current_uv_set(self, mesh: Optional[str] = None) -> str:
        """Get the currently active UV set name."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.get_current_uv_set(mesh)

    def create_uv_set(self, name: str = "uvSet", mesh: Optional[str] = None) -> bool:
        """Create a new empty UV set."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.create_uv_set(mesh, name)

    def delete_uv_set(self, name: str, mesh: Optional[str] = None) -> bool:
        """Delete a UV set (cannot delete the current one)."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.delete_uv_set(mesh, name)

    def set_current_uv_set(self, name: str, mesh: Optional[str] = None) -> bool:
        """Set the active UV set."""
        if mesh is None:
            mesh = self.get_active_mesh()
        return self.uvs.set_current_uv_set(mesh, name)

    # =========================================================================
    # ANALYSIS & UTILITIES
    # =========================================================================

    def analyze(self, mesh: Optional[MeshSelection] = None) -> MeshStatistics:
        """Return detailed mesh analysis."""
        return self.analyzer.analyze(mesh or self.get_active_mesh())

    def get_statistics(self) -> MeshStatistics:
        return self.analyzer.get_statistics()

    def check_nonmanifold(self, mesh: Optional[MeshSelection] = None) -> List[MeshIssue]:
        return self.validator.check_nonmanifold(mesh)

    def batch(self, operation: str, meshes: List[str], **kwargs) -> List[MeshReport]:
        """Process multiple meshes."""
        reports = []
        for m in meshes:
            cmds.select(m)
            report = getattr(self, operation)(**kwargs)
            reports.append(report)
        return reports

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_active_mesh(self) -> str:
        """Return the currently selected mesh or first in selection."""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            raise RuntimeError("No mesh selected.")

        # Return first mesh shape
        shapes = cmds.listRelatives(selection[0], shapes=True, fullPath=True) or [selection[0]]
        return shapes[0]

    def select(self, mesh: str):
        """Select a mesh."""
        cmds.select(mesh)

    def refresh(self):
        """Force viewport refresh."""
        cmds.refresh()


# =============================================================================
# GLOBAL CONVENIENCE INSTANCE
# =============================================================================

mesh = MeshEngine()
MeshTools = MeshEngine  # Alias for clarity


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["MeshEngine", "MeshTools", "mesh"]