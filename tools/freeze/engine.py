# -*- coding: utf-8 -*-
"""
tools/freeze/engine.py

Main facade for freeze operations.
"""

import time
import maya.cmds as cmds # type: ignore
from typing import Optional, List, Union, Dict, Any
from .types import (
    FreezeType, FreezeMode, FreezeScope, FreezeReport,
    TransformFreeze, PivotFreeze, ControllerFreeze,
    RigFreeze, MeshFreeze
)
from .settings import DEFAULT_FREEZE_SETTINGS
from .transforms import TransformFreezer
from .pivots import PivotFreezer
from .controllers import ControllerFreezer
from .rig import RigFreezer
from .mesh import MeshFreezer
from .validation import FreezeValidator
from .reporter import FreezeReporter


class FreezeEngine:
    """
    Main facade for all freeze operations.
    """

    def __init__(self, settings=None):
        self.settings = settings or DEFAULT_FREEZE_SETTINGS
        self.transform_freezer = TransformFreezer(self.settings)
        self.pivot_freezer = PivotFreezer(self.settings)
        self.controller_freezer = ControllerFreezer(self.settings)
        self.rig_freezer = RigFreezer(self.settings)
        self.mesh_freezer = MeshFreezer(self.settings)
        self.validator = FreezeValidator()
        self.reporter = FreezeReporter()

    # =========================================================================
    # FREEZE OPERATIONS
    # =========================================================================

    def freeze_transforms(self, nodes: Optional[Union[str, List[str]]] = None,
                          mode: Optional[FreezeMode] = None) -> FreezeReport:
        """
        Freeze transforms on given nodes.

        Args:
            nodes: Node or list of nodes. If None, uses selection.
            mode: Override freeze mode.

        Returns:
            FreezeReport.
        """
        if mode is not None:
            self.settings.mode = mode

        if nodes is None:
            nodes = self._get_selected_transforms()
            if not nodes:
                report = FreezeReport(type=FreezeType.TRANSFORM, success=False)
                report.errors.append("No nodes specified or selected.")
                return report
        elif isinstance(nodes, str):
            nodes = [nodes]

        # Convert to long names
        nodes = cmds.ls(nodes, long=True)

        start = time.time()
        result = self.transform_freezer.freeze(nodes)

        report = FreezeReport(
            type=FreezeType.TRANSFORM,
            mode=self.settings.mode,
            scope=self.settings.scope,
            transform=result,
            elapsed_time_ms=(time.time() - start) * 1000,
        )

        # Collect warnings and errors
        report.warnings = self._collect_warnings()
        report.errors = self._collect_errors()
        report.success = len(report.errors) == 0

        return report

    def freeze_pivots(self, nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze pivots on given nodes or selection."""
        if nodes is None:
            nodes = self._get_selected_transforms()
            if not nodes:
                report = FreezeReport(type=FreezeType.PIVOT, success=False)
                report.errors.append("No nodes specified or selected.")
                return report
        elif isinstance(nodes, str):
            nodes = [nodes]

        nodes = cmds.ls(nodes, long=True)

        start = time.time()
        result = self.pivot_freezer.freeze(nodes)

        report = FreezeReport(
            type=FreezeType.PIVOT,
            mode=self.settings.mode,
            scope=self.settings.scope,
            pivot=result,
            elapsed_time_ms=(time.time() - start) * 1000,
        )
        report.success = True
        return report

    def freeze_controllers(self, controllers: Optional[Union[str, List[str]]] = None,
                           mode: Optional[FreezeMode] = None) -> FreezeReport:
        """Freeze controllers (NURBS controls)."""
        if mode is not None:
            self.settings.mode = mode

        if controllers is None:
            controllers = self._get_selected_controllers()
            if not controllers:
                report = FreezeReport(type=FreezeType.CONTROLLER, success=False)
                report.errors.append("No controllers specified or selected.")
                return report
        elif isinstance(controllers, str):
            controllers = [controllers]

        controllers = cmds.ls(controllers, long=True)

        start = time.time()
        result = self.controller_freezer.freeze(controllers)

        report = FreezeReport(
            type=FreezeType.CONTROLLER,
            mode=self.settings.mode,
            scope=self.settings.scope,
            controller=result,
            elapsed_time_ms=(time.time() - start) * 1000,
        )
        report.success = True
        return report

    def freeze_rig(self, rig_root: str, mode: Optional[FreezeMode] = None) -> FreezeReport:
        """Freeze an entire rig hierarchy."""
        if mode is not None:
            self.settings.mode = mode

        if not cmds.objExists(rig_root):
            report = FreezeReport(type=FreezeType.RIG, success=False)
            report.errors.append(f"Rig root '{rig_root}' does not exist.")
            return report

        start = time.time()
        result = self.rig_freezer.freeze(rig_root)

        report = FreezeReport(
            type=FreezeType.RIG,
            mode=self.settings.mode,
            scope=self.settings.scope,
            rig=result,
            elapsed_time_ms=(time.time() - start) * 1000,
        )
        report.success = True
        return report

    def freeze_mesh(self, meshes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze mesh transforms."""
        if meshes is None:
            meshes = self._get_selected_meshes()
            if not meshes:
                report = FreezeReport(type=FreezeType.MESH, success=False)
                report.errors.append("No meshes specified or selected.")
                return report
        elif isinstance(meshes, str):
            meshes = [meshes]

        meshes = cmds.ls(meshes, long=True)

        start = time.time()
        result = self.mesh_freezer.freeze(meshes)

        report = FreezeReport(
            type=FreezeType.MESH,
            mode=self.settings.mode,
            scope=self.settings.scope,
            mesh=result,
            elapsed_time_ms=(time.time() - start) * 1000,
        )
        report.success = True
        return report

    def freeze_selected(self, mode: Optional[FreezeMode] = None) -> FreezeReport:
        """
        Freeze the current selection (auto-detect types).

        Args:
            mode: Override freeze mode.

        Returns:
            FreezeReport.
        """
        if mode is not None:
            self.settings.mode = mode

        start = time.time()
        report = FreezeReport(
            type=FreezeType.TRANSFORM,
            mode=self.settings.mode,
            scope=FreezeScope.SELECTED,
        )

        # Get selection
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            report.errors.append("No objects selected.")
            report.success = False
            return report

        # Separate by type
        controllers = []
        meshes = []
        generic = []

        for node in selection:
            if self._is_controller(node):
                controllers.append(node)
            elif self._is_mesh(node):
                meshes.append(node)
            else:
                generic.append(node)

        # Freeze each group
        if controllers:
            r = self.controller_freezer.freeze(controllers)
            report.controller.frozen_controllers = r.frozen_controllers
            report.controller.total_controllers = r.total_controllers
            report.controller.skipped_controllers = r.skipped_controllers
            report.controller.offset_groups = r.offset_groups

        if meshes:
            r = self.mesh_freezer.freeze(meshes)
            report.mesh.frozen_meshes = r.frozen_meshes
            report.mesh.total_meshes = r.total_meshes
            report.mesh.skipped_meshes = r.skipped_meshes

        if generic:
            r = self.transform_freezer.freeze(generic)
            report.transform.frozen_nodes = r.frozen_nodes
            report.transform.total_nodes = r.total_nodes
            report.transform.skipped_nodes = r.skipped_nodes
            report.transform.offset_groups = r.offset_groups
            report.transform.preserved_connections = r.preserved_connections

        report.elapsed_time_ms = (time.time() - start) * 1000
        report.success = True
        return report

    # =========================================================================
    # PREVIEW / VALIDATION
    # =========================================================================

    def preview(self, nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """
        Preview what would be frozen without modifying.

        Returns:
            FreezeReport with preview data.
        """
        if nodes is None:
            nodes = self._get_selected_transforms()
        if isinstance(nodes, str):
            nodes = [nodes]

        report = FreezeReport(type=FreezeType.TRANSFORM, mode=self.settings.mode)
        for node in nodes:
            if not cmds.objExists(node):
                report.warnings.append(f"Node '{node}' does not exist.")
                continue
            if self._is_referenced(node):
                report.warnings.append(f"Node '{node}' is referenced (would skip).")
                continue
            if cmds.lockNode(node, q=True, lock=True)[0]:
                report.warnings.append(f"Node '{node}' is locked (would skip).")
                continue
            report.transform.frozen_nodes += 1
            report.transform.total_nodes += 1

        report.warnings.append("Preview mode: no changes were made.")
        return report

    def validate(self, nodes: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Validate nodes for freezing.

        Returns:
            Dict with validation results.
        """
        if isinstance(nodes, str):
            nodes = [nodes]
        results = {}
        for node in nodes:
            results[node] = self.validator.validate(node)
        return results

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_report(self, report: Optional[FreezeReport] = None):
        """Print a formatted freeze report."""
        if report is None:
            report = self.freeze_selected()
        print(report.summary())

    def save_report(self, report: FreezeReport, filepath: str, format: str = "json") -> bool:
        """Save a report to a file."""
        return self.reporter.save_report(report, filepath, format)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _get_selected_transforms(self) -> List[str]:
        """Get selected transforms."""
        return cmds.ls(selection=True, type='transform', long=True)

    def _get_selected_controllers(self) -> List[str]:
        """Get selected controllers (NURBS controls)."""
        selection = cmds.ls(selection=True, long=True)
        controllers = []
        for node in selection:
            if self._is_controller(node):
                controllers.append(node)
        return controllers

    def _get_selected_meshes(self) -> List[str]:
        """Get selected meshes."""
        selection = cmds.ls(selection=True, long=True)
        meshes = []
        for node in selection:
            if self._is_mesh(node):
                meshes.append(node)
        return meshes

    def _is_controller(self, node: str) -> bool:
        """Check if node is a controller (NURBS shape)."""
        shapes = cmds.listRelatives(node, shapes=True) or []
        return any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes)

    def _is_mesh(self, node: str) -> bool:
        """Check if node is a mesh."""
        shapes = cmds.listRelatives(node, shapes=True) or []
        return any(cmds.nodeType(s) == 'mesh' for s in shapes)

    def _is_referenced(self, node: str) -> bool:
        """Check if node is referenced."""
        return cmds.referenceQuery(node, isNodeReferenced=True)

    def _collect_warnings(self) -> List[str]:
        """Collect warnings from the freeze operation."""
        # This would be populated by the individual freezers
        return []

    def _collect_errors(self) -> List[str]:
        """Collect errors from the freeze operation."""
        return []

    def set_settings(self, settings):
        self.settings = settings

    def get_settings(self):
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

freeze = FreezeEngine()

__all__ = ["FreezeEngine", "freeze"]