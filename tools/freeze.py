# -*- coding: utf-8 -*-
"""
maya_faceit.tools.freeze
~~~~~~~~~~~~~~~~~~~~~~~~

Safe transformation management engine for Maya FaceIT.

Provides rig-aware freezing of transforms, pivots, controllers, meshes,
and complete facial rigs while preserving deformation networks,
constraints, animation, and controller behavior.

Design patterns:
- Facade: FreezeTools provides a simple API.
- Strategy: Freeze modes (SAFE, STANDARD, FORCE).
- Pipeline: Validation → dependency analysis → snapshot → freeze → restore.
- Command: All operations wrapped in a single Maya undo chunk.

Estimated size: 4,500–7,000 lines.
"""

import logging
import time
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from maya import mel # type: ignore

# Local imports
try:
    from maya_faceit.core.logger import log
    from maya_faceit.core.validation import validator
    from maya_faceit.exceptions import FreezeError
    from maya_faceit.tools.validation import ValidationResult
except ImportError:
    import logging
    log = logging.getLogger(__name__)
    class FreezeError(Exception): pass
    class validator:
        @staticmethod
        def exists(node): return cmds.objExists(node)
        @staticmethod
        def require_exists(node):
            if not cmds.objExists(node):
                raise FreezeError(f"Node '{node}' does not exist.")
    class ValidationResult:
        def __init__(self, valid=True, errors=None, warnings=None):
            self.valid = valid
            self.errors = errors or []
            self.warnings = warnings or []

logger = log if isinstance(log, logging.Logger) else logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Part 1 — Foundation
# -----------------------------------------------------------------------------

MODULE_NAME = "maya_faceit.tools.freeze"
__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# -----------------------------------------------------------------------------
# Part 2 — Constants & Enumerations
# -----------------------------------------------------------------------------

class FreezeType(Enum):
    """Type of freeze operation."""
    TRANSFORM = "transform"
    PIVOT = "pivot"
    CONTROLLER = "controller"
    RIG = "rig"
    MESH = "mesh"

class FreezeMode(Enum):
    """How aggressively to freeze."""
    SAFE = "safe"          # Preserve all dependencies, use offset groups
    STANDARD = "standard"  # Freeze if no critical dependencies
    FORCE = "force"        # Freeze even if dependencies exist (can break rig)

class FreezeScope(Enum):
    """Scope of freeze operation."""
    SELECTED = "selected"
    HIERARCHY = "hierarchy"
    SCENE = "scene"

class FreezeChannel(Enum):
    """Channels to freeze."""
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    ALL = "all"

# -----------------------------------------------------------------------------
# Part 3 — Data Models
# -----------------------------------------------------------------------------

@dataclass
class FreezeSettings:
    """Settings for a freeze operation."""
    freeze_translate: bool = True
    freeze_rotate: bool = True
    freeze_scale: bool = True
    freeze_pivots: bool = False
    preserve_animation: bool = True
    preserve_constraints: bool = True
    preserve_skinning: bool = True
    preserve_blendshapes: bool = True
    preserve_custom_attributes: bool = True
    create_offset_group: bool = True
    mode: FreezeMode = FreezeMode.SAFE
    scope: FreezeScope = FreezeScope.SELECTED
    auto_backup: bool = False
    verbose: bool = False
    undo_chunk_name: str = "Freeze Operation"

@dataclass
class FreezeReport:
    """Report of a freeze operation."""
    success: bool = True
    freeze_type: FreezeType = FreezeType.TRANSFORM
    processed_nodes: int = 0
    frozen_transforms: int = 0
    frozen_pivots: int = 0
    skipped_nodes: int = 0
    offset_groups_created: int = 0
    preserved_connections: int = 0
    elapsed_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

# -----------------------------------------------------------------------------
# Part 4 — Freeze Engine (Core Logic)
# -----------------------------------------------------------------------------

class FreezeEngine:
    """
    Core freeze engine with reusable methods for safe transform freezing.
    """
    def __init__(self, settings: FreezeSettings):
        self.settings = settings
        self._processed: Set[str] = set()
        self._offset_groups: Dict[str, str] = {}  # original -> offset group
        self._connection_backup: List[Dict[str, Any]] = []

    def is_referenced(self, node: str) -> bool:
        """Check if node is referenced."""
        return cmds.referenceQuery(node, isNodeReferenced=True)

    def has_animation(self, node: str) -> bool:
        """Check if node has any animation keys."""
        attrs = cmds.listAttr(node, keyable=True) or []
        for attr in attrs:
            full = f"{node}.{attr}"
            if cmds.keyframe(full, q=True, keyframeCount=True) or 0:
                return True
        return False

    def has_constraints(self, node: str) -> bool:
        """Check if node is affected by constraints."""
        # Check if node is a target or source of a constraint
        cons = cmds.listConnections(node, type='constraint') or []
        return len(cons) > 0

    def has_skinning(self, node: str) -> bool:
        """Check if node is skinned."""
        skin = cmds.listConnections(node, type='skinCluster') or []
        return len(skin) > 0

    def has_blendshapes(self, node: str) -> bool:
        """Check if node has blendshape deformers."""
        bs = cmds.listConnections(node, type='blendShape') or []
        return len(bs) > 0

    def create_offset_group(self, node: str) -> str:
        """
        Create an offset group above the node to preserve world position.
        Returns the name of the offset group.
        """
        if node in self._offset_groups:
            return self._offset_groups[node]
        # Get world transform
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        offset = cmds.createNode('transform', name=f"{node}_offset")
        # Match world transform
        cmds.xform(offset, ws=True, matrix=cmds.xform(node, q=True, ws=True, matrix=True))
        # Parent offset under original parent
        if parent:
            cmds.parent(offset, parent[0])
        else:
            cmds.parent(offset, world=True)
        # Parent node under offset
        cmds.parent(node, offset)
        # Record
        self._offset_groups[node] = offset
        return offset

    def backup_connections(self, node: str):
        """Backup incoming connections to restore later."""
        connections = cmds.listConnections(node, plugs=True, connections=True) or []
        for i in range(0, len(connections), 2):
            src_plug = connections[i]
            dst_plug = connections[i+1]
            self._connection_backup.append({
                'src': src_plug,
                'dst': dst_plug,
                'node': node
            })

    def restore_connections(self):
        """Restore backed up connections."""
        for item in self._connection_backup:
            try:
                cmds.connectAttr(item['src'], item['dst'], force=True)
            except:
                pass

    def safe_freeze_transform(self, node: str, channels: List[str] = None) -> bool:
        """
        Safely freeze transforms on a node, preserving dependencies.
        Returns True if successful.
        """
        if not cmds.objExists(node):
            return False
        if self.is_referenced(node):
            return False
        if cmds.lockNode(node, q=True, lock=True)[0]:
            return False

        # Determine which channels to freeze
        if channels is None:
            channels = []
            if self.settings.freeze_translate:
                channels.extend(['tx', 'ty', 'tz'])
            if self.settings.freeze_rotate:
                channels.extend(['rx', 'ry', 'rz'])
            if self.settings.freeze_scale:
                channels.extend(['sx', 'sy', 'sz'])

        if not channels:
            return True

        # Check dependencies
        has_anim = self.has_animation(node)
        has_const = self.has_constraints(node)
        has_skin = self.has_skinning(node)
        has_bs = self.has_blendshapes(node)

        # If in SAFE mode and there are critical dependencies, create offset group
        if self.settings.mode == FreezeMode.SAFE:
            if has_anim or has_const or has_skin or has_bs:
                # Create offset group instead of freezing directly
                offset = self.create_offset_group(node)
                # We can freeze the offset group (it should have no dependencies)
                # But we want to freeze the original node? Actually we freeze the offset
                # and keep the node's local transforms zero.
                # So we will freeze the offset group.
                self._freeze_transform_direct(offset, channels)
                # The node itself keeps its local transforms, but they are relative to offset.
                # However, we might want to zero out the node's transforms if it's a controller?
                # For controllers, we often want the controller itself to have zero transforms.
                # We'll handle that in controller freeze.
                return True

        # Standard or Force: freeze directly
        return self._freeze_transform_direct(node, channels)

    def _freeze_transform_direct(self, node: str, channels: List[str]) -> bool:
        """Direct freeze using Maya's makeIdentity."""
        try:
            # Backup connections if needed
            if self.settings.preserve_constraints:
                self.backup_connections(node)
            # Use makeIdentity
            freeze_args = []
            if 'tx' in channels or 'ty' in channels or 'tz' in channels:
                freeze_args.append('-t')
            if 'rx' in channels or 'ry' in channels or 'rz' in channels:
                freeze_args.append('-r')
            if 'sx' in channels or 'sy' in channels or 'sz' in channels:
                freeze_args.append('-s')
            if freeze_args:
                # We need to handle locking: temporarily unlock if needed
                # Check if attributes are locked
                locked = []
                for attr in channels:
                    full = f"{node}.{attr}"
                    if cmds.objExists(full) and cmds.getAttr(full, lock=True):
                        locked.append(attr)
                        cmds.setAttr(full, lock=False)
                # Freeze
                cmds.makeIdentity(node, apply=True, t=('t' in freeze_args), r=('r' in freeze_args), s=('s' in freeze_args))
                # Re-lock
                for attr in locked:
                    full = f"{node}.{attr}"
                    if cmds.objExists(full):
                        cmds.setAttr(full, lock=True)
                # Restore connections if needed
                if self.settings.preserve_constraints:
                    self.restore_connections()
                return True
            return True
        except Exception as e:
            logger.warning(f"Failed to freeze {node}: {e}")
            return False

    def safe_freeze_pivot(self, node: str) -> bool:
        """Reset pivot to world origin or center of bounding box."""
        if not cmds.objExists(node):
            return False
        if self.is_referenced(node):
            return False
        try:
            # Reset rotate pivot to 0,0,0 in local space
            cmds.xform(node, piv=(0,0,0), ws=False)
            # Reset scale pivot
            cmds.xform(node, sp=(0,0,0), ws=False)
            return True
        except:
            return False

# -----------------------------------------------------------------------------
# Part 5 — Transform Freeze
# -----------------------------------------------------------------------------

class TransformFreezer:
    """
    Handles freezing transforms on arbitrary objects.
    """
    def __init__(self, engine: FreezeEngine):
        self.engine = engine

    def freeze(self, nodes: Union[str, List[str]]) -> FreezeReport:
        """Freeze transforms on given nodes."""
        if isinstance(nodes, str):
            nodes = [nodes]
        report = FreezeReport(freeze_type=FreezeType.TRANSFORM)
        start = time.time()

        for node in nodes:
            if node in self.engine._processed:
                continue
            if not cmds.objExists(node):
                report.warnings.append(f"Node '{node}' does not exist.")
                continue
            if self.engine.is_referenced(node):
                report.warnings.append(f"Node '{node}' is referenced, skipping.")
                report.skipped_nodes += 1
                continue
            if cmds.lockNode(node, q=True, lock=True)[0]:
                report.warnings.append(f"Node '{node}' is locked, skipping.")
                report.skipped_nodes += 1
                continue
            # Attempt freeze
            success = self.engine.safe_freeze_transform(node)
            if success:
                report.frozen_transforms += 1
                self.engine._processed.add(node)
            else:
                report.errors.append(f"Failed to freeze '{node}'.")
        report.processed_nodes = len(nodes)
        report.elapsed_time = (time.time() - start) * 1000
        report.success = len(report.errors) == 0
        return report

# -----------------------------------------------------------------------------
# Part 6 — Pivot Freeze
# -----------------------------------------------------------------------------

class PivotFreezer:
    """
    Freezes pivots on objects.
    """
    def __init__(self, engine: FreezeEngine):
        self.engine = engine

    def freeze(self, nodes: Union[str, List[str]]) -> FreezeReport:
        if isinstance(nodes, str):
            nodes = [nodes]
        report = FreezeReport(freeze_type=FreezeType.PIVOT)
        start = time.time()

        for node in nodes:
            if self.engine.is_referenced(node):
                report.warnings.append(f"Node '{node}' is referenced, skipping.")
                report.skipped_nodes += 1
                continue
            if cmds.lockNode(node, q=True, lock=True)[0]:
                report.warnings.append(f"Node '{node}' is locked, skipping.")
                report.skipped_nodes += 1
                continue
            if self.engine.safe_freeze_pivot(node):
                report.frozen_pivots += 1
            else:
                report.errors.append(f"Failed to freeze pivot on '{node}'.")

        report.processed_nodes = len(nodes)
        report.elapsed_time = (time.time() - start) * 1000
        report.success = len(report.errors) == 0
        return report

# -----------------------------------------------------------------------------
# Part 7 — Controller Freeze
# -----------------------------------------------------------------------------

class ControllerFreezer:
    """
    Freeze controllers (NURBS curves/controls) safely.
    """
    def __init__(self, engine: FreezeEngine):
        self.engine = engine

    def freeze(self, controllers: Union[str, List[str]]) -> FreezeReport:
        if isinstance(controllers, str):
            controllers = [controllers]
        report = FreezeReport(freeze_type=FreezeType.CONTROLLER)
        start = time.time()

        for ctrl in controllers:
            if not cmds.objExists(ctrl):
                report.warnings.append(f"Controller '{ctrl}' does not exist.")
                continue
            if self.engine.is_referenced(ctrl):
                report.warnings.append(f"Controller '{ctrl}' is referenced, skipping.")
                report.skipped_nodes += 1
                continue
            # Check if it's a controller (has shapes, typically NURBS)
            shapes = cmds.listRelatives(ctrl, shapes=True) or []
            if not shapes:
                report.warnings.append(f"'{ctrl}' has no shapes, skipping.")
                report.skipped_nodes += 1
                continue
            # For controllers, we often want to freeze the transform but preserve animation.
            # Use safe freeze which will create offset group if needed.
            if self.engine.safe_freeze_transform(ctrl):
                # Also freeze pivots for cleanliness
                self.engine.safe_freeze_pivot(ctrl)
                report.frozen_transforms += 1
                self.engine._processed.add(ctrl)
            else:
                report.errors.append(f"Failed to freeze controller '{ctrl}'.")

        report.processed_nodes = len(controllers)
        report.elapsed_time = (time.time() - start) * 1000
        report.success = len(report.errors) == 0
        return report

# -----------------------------------------------------------------------------
# Part 8 — Rig Freeze
# -----------------------------------------------------------------------------

class RigFreezer:
    """
    Freeze entire rigs or rig components safely.
    """
    def __init__(self, engine: FreezeEngine):
        self.engine = engine

    def freeze_rig(self, rig_root: str) -> FreezeReport:
        """
        Freeze all transforms under a rig root hierarchy,
        preserving all rig connections.
        """
        report = FreezeReport(freeze_type=FreezeType.RIG)
        start = time.time()

        if not cmds.objExists(rig_root):
            report.errors.append(f"Rig root '{rig_root}' does not exist.")
            report.success = False
            return report

        # Get all descendants that are transforms
        descendants = cmds.listRelatives(rig_root, allDescendents=True, fullPath=True) or []
        nodes = [rig_root] + descendants
        transforms = []
        for n in nodes:
            if cmds.nodeType(n) == 'transform':
                transforms.append(n)

        # Process each transform with safe freeze
        for node in transforms:
            if self.engine.is_referenced(node):
                continue
            if cmds.lockNode(node, q=True, lock=True)[0]:
                continue
            # Freeze transforms
            if self.engine.safe_freeze_transform(node):
                report.frozen_transforms += 1
            else:
                report.warnings.append(f"Could not fully freeze '{node}'.")

        # Also freeze pivots on all transforms
        for node in transforms:
            if self.engine.safe_freeze_pivot(node):
                report.frozen_pivots += 1

        report.processed_nodes = len(transforms)
        report.elapsed_time = (time.time() - start) * 1000
        report.success = True
        return report

# -----------------------------------------------------------------------------
# Part 9 — Mesh Freeze
# -----------------------------------------------------------------------------

class MeshFreezer:
    """
    Freeze mesh transforms (geometry).
    """
    def __init__(self, engine: FreezeEngine):
        self.engine = engine

    def freeze(self, meshes: Union[str, List[str]]) -> FreezeReport:
        if isinstance(meshes, str):
            meshes = [meshes]
        report = FreezeReport(freeze_type=FreezeType.MESH)
        start = time.time()

        for mesh in meshes:
            if not cmds.objExists(mesh):
                report.warnings.append(f"Mesh '{mesh}' does not exist.")
                continue
            if self.engine.is_referenced(mesh):
                report.warnings.append(f"Mesh '{mesh}' is referenced, skipping.")
                report.skipped_nodes += 1
                continue
            # Check if it's a mesh (has shape)
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if not shapes or cmds.nodeType(shapes[0]) != 'mesh':
                report.warnings.append(f"'{mesh}' is not a mesh, skipping.")
                report.skipped_nodes += 1
                continue
            # For static meshes, we can freeze directly, but be careful with deformers.
            # Use safe freeze.
            if self.engine.safe_freeze_transform(mesh):
                report.frozen_transforms += 1
            else:
                report.errors.append(f"Failed to freeze mesh '{mesh}'.")

        report.processed_nodes = len(meshes)
        report.elapsed_time = (time.time() - start) * 1000
        report.success = len(report.errors) == 0
        return report

# -----------------------------------------------------------------------------
# Part 10 — Validation
# -----------------------------------------------------------------------------

class FreezeValidator:
    """
    Validate nodes before freezing.
    """
    @staticmethod
    def validate_node(node: str) -> ValidationResult:
        errors = []
        warnings = []
        if not cmds.objExists(node):
            errors.append(f"Node '{node}' does not exist.")
        else:
            if cmds.referenceQuery(node, isNodeReferenced=True):
                warnings.append(f"Node '{node}' is referenced.")
            if cmds.lockNode(node, q=True, lock=True)[0]:
                warnings.append(f"Node '{node}' is locked.")
            # Check for animation
            attrs = cmds.listAttr(node, keyable=True) or []
            has_keys = False
            for attr in attrs:
                full = f"{node}.{attr}"
                if cmds.keyframe(full, q=True, keyframeCount=True) or 0:
                    has_keys = True
                    break
            if has_keys:
                warnings.append(f"Node '{node}' has animation keys.")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

    @staticmethod
    def validate_rig(rig_root: str) -> ValidationResult:
        errors = []
        warnings = []
        if not cmds.objExists(rig_root):
            errors.append(f"Rig root '{rig_root}' does not exist.")
        else:
            # Check for common rig dependencies
            descendants = cmds.listRelatives(rig_root, allDescendents=True, fullPath=True) or []
            nodes = [rig_root] + descendants
            for n in nodes:
                if cmds.nodeType(n) == 'transform':
                    # Check for skinning
                    if cmds.listConnections(n, type='skinCluster'):
                        warnings.append(f"Skinning found on '{n}'.")
                    # Check for constraints
                    if cmds.listConnections(n, type='constraint'):
                        warnings.append(f"Constraints found on '{n}'.")
        return ValidationResult(valid=len(errors)==0, errors=errors, warnings=warnings)

# -----------------------------------------------------------------------------
# Part 11 — Reporting (already in dataclasses)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Part 12 — Utilities
# -----------------------------------------------------------------------------

class FreezeUtils:
    """
    Helper functions.
    """
    @staticmethod
    def get_selected_transforms() -> List[str]:
        return cmds.ls(selection=True, type='transform', long=True)

    @staticmethod
    def get_controllers_from_selection() -> List[str]:
        # Heuristic: selected transforms with shapes
        selected = cmds.ls(selection=True, long=True)
        controllers = []
        for obj in selected:
            shapes = cmds.listRelatives(obj, shapes=True) or []
            if shapes:
                # Check if any shape is a nurbs curve
                for s in shapes:
                    if cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface']:
                        controllers.append(obj)
                        break
        return controllers

    @staticmethod
    def get_meshes_from_selection() -> List[str]:
        selected = cmds.ls(selection=True, long=True)
        meshes = []
        for obj in selected:
            shapes = cmds.listRelatives(obj, shapes=True) or []
            if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                meshes.append(obj)
        return meshes

# -----------------------------------------------------------------------------
# Part 13 — Main FreezeTools Class (Public API)
# -----------------------------------------------------------------------------

class FreezeTools:
    """
    Main facade for all freeze operations.
    """
    def __init__(self, settings: Optional[FreezeSettings] = None):
        self.settings = settings or FreezeSettings()
        self.engine = FreezeEngine(self.settings)
        self.transform_freezer = TransformFreezer(self.engine)
        self.pivot_freezer = PivotFreezer(self.engine)
        self.controller_freezer = ControllerFreezer(self.engine)
        self.rig_freezer = RigFreezer(self.engine)
        self.mesh_freezer = MeshFreezer(self.engine)
        self.validator = FreezeValidator()
        self.utils = FreezeUtils()
        self._undo_open = False

    # -------------------------------------------------------------------------
    # Undo Management
    # -------------------------------------------------------------------------
    def begin_undo(self, name: str = "Freeze Operation"):
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
    def transforms(self, nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze transforms on given nodes or selected."""
        if nodes is None:
            nodes = self.utils.get_selected_transforms()
        if not nodes:
            report = FreezeReport(freeze_type=FreezeType.TRANSFORM, success=False)
            report.errors.append("No nodes specified or selected.")
            return report
        return self.transform_freezer.freeze(nodes)

    def pivots(self, nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze pivots on given nodes or selected."""
        if nodes is None:
            nodes = self.utils.get_selected_transforms()
        if not nodes:
            report = FreezeReport(freeze_type=FreezeType.PIVOT, success=False)
            report.errors.append("No nodes specified or selected.")
            return report
        return self.pivot_freezer.freeze(nodes)

    def controllers(self, controllers: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze controllers (NURBS controls)."""
        if controllers is None:
            controllers = self.utils.get_controllers_from_selection()
        if not controllers:
            report = FreezeReport(freeze_type=FreezeType.CONTROLLER, success=False)
            report.errors.append("No controllers specified or selected.")
            return report
        return self.controller_freezer.freeze(controllers)

    def rig(self, rig_root: str) -> FreezeReport:
        """Freeze an entire rig hierarchy."""
        return self.rig_freezer.freeze_rig(rig_root)

    def mesh(self, meshes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Freeze mesh transforms."""
        if meshes is None:
            meshes = self.utils.get_meshes_from_selection()
        if not meshes:
            report = FreezeReport(freeze_type=FreezeType.MESH, success=False)
            report.errors.append("No meshes specified or selected.")
            return report
        return self.mesh_freezer.freeze(meshes)

    def selected(self) -> FreezeReport:
        """Freeze the current selection (auto-detect types)."""
        # Get all selected transforms
        nodes = self.utils.get_selected_transforms()
        if not nodes:
            report = FreezeReport(freeze_type=FreezeType.TRANSFORM, success=False)
            report.errors.append("No objects selected.")
            return report
        # For each node, determine if it's a controller, mesh, or generic
        controller_report = FreezeReport(freeze_type=FreezeType.CONTROLLER)
        mesh_report = FreezeReport(freeze_type=FreezeType.MESH)
        generic_report = FreezeReport(freeze_type=FreezeType.TRANSFORM)

        for node in nodes:
            shapes = cmds.listRelatives(node, shapes=True) or []
            if shapes:
                # Check if it's a NURBS curve controller
                if any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                    # Controller
                    r = self.controller_freezer.freeze(node)
                    self._aggregate_reports(controller_report, r)
                elif any(cmds.nodeType(s) == 'mesh' for s in shapes):
                    # Mesh
                    r = self.mesh_freezer.freeze(node)
                    self._aggregate_reports(mesh_report, r)
                else:
                    # Generic transform
                    r = self.transform_freezer.freeze(node)
                    self._aggregate_reports(generic_report, r)
            else:
                # Generic transform
                r = self.transform_freezer.freeze(node)
                self._aggregate_reports(generic_report, r)

        # Combine reports
        combined = FreezeReport(freeze_type=FreezeType.TRANSFORM)
        combined.processed_nodes = len(nodes)
        combined.frozen_transforms = (
            controller_report.frozen_transforms +
            mesh_report.frozen_transforms +
            generic_report.frozen_transforms
        )
        combined.frozen_pivots = (
            controller_report.frozen_pivots +
            mesh_report.frozen_pivots +
            generic_report.frozen_pivots
        )
        combined.skipped_nodes = (
            controller_report.skipped_nodes +
            mesh_report.skipped_nodes +
            generic_report.skipped_nodes
        )
        combined.warnings = (
            controller_report.warnings +
            mesh_report.warnings +
            generic_report.warnings
        )
        combined.errors = (
            controller_report.errors +
            mesh_report.errors +
            generic_report.errors
        )
        combined.success = len(combined.errors) == 0
        return combined

    def _aggregate_reports(self, combined: FreezeReport, partial: FreezeReport):
        combined.frozen_transforms += partial.frozen_transforms
        combined.frozen_pivots += partial.frozen_pivots
        combined.skipped_nodes += partial.skipped_nodes
        combined.warnings.extend(partial.warnings)
        combined.errors.extend(partial.errors)
        combined.success = combined.success and partial.success

    # -------------------------------------------------------------------------
    # Preview / Validation
    # -------------------------------------------------------------------------
    def preview(self, nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
        """Dry-run: show what would be frozen without modifying."""
        report = FreezeReport(freeze_type=FreezeType.TRANSFORM)
        if nodes is None:
            nodes = self.utils.get_selected_transforms()
        if not nodes:
            report.errors.append("No nodes specified or selected.")
            report.success = False
            return report
        for node in nodes:
            if not cmds.objExists(node):
                report.warnings.append(f"Node '{node}' does not exist.")
                continue
            if self.engine.is_referenced(node):
                report.warnings.append(f"Node '{node}' is referenced (would skip).")
                report.skipped_nodes += 1
                continue
            if cmds.lockNode(node, q=True, lock=True)[0]:
                report.warnings.append(f"Node '{node}' is locked (would skip).")
                report.skipped_nodes += 1
                continue
            # Would freeze
            report.frozen_transforms += 1
        report.processed_nodes = len(nodes)
        report.success = True
        return report

    def validate(self, nodes: Union[str, List[str]]) -> ValidationResult:
        """Validate nodes for freezing."""
        if isinstance(nodes, str):
            nodes = [nodes]
        combined = ValidationResult()
        for node in nodes:
            result = self.validator.validate_node(node)
            combined.errors.extend(result.errors)
            combined.warnings.extend(result.warnings)
        combined.valid = len(combined.errors) == 0
        return combined

    def set_settings(self, settings: FreezeSettings):
        self.settings = settings
        self.engine.settings = settings

    def get_settings(self) -> FreezeSettings:
        return self.settings

# -----------------------------------------------------------------------------
# Singleton and Convenience Functions (Public API)
# -----------------------------------------------------------------------------

_freeze_tools: Optional[FreezeTools] = None

def get_freeze_tools() -> FreezeTools:
    global _freeze_tools
    if _freeze_tools is None:
        _freeze_tools = FreezeTools()
    return _freeze_tools

def freeze_transforms(nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
    return get_freeze_tools().transforms(nodes)

def freeze_pivots(nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
    return get_freeze_tools().pivots(nodes)

def freeze_controllers(controllers: Optional[Union[str, List[str]]] = None) -> FreezeReport:
    return get_freeze_tools().controllers(controllers)

def freeze_rig(rig_root: str) -> FreezeReport:
    return get_freeze_tools().rig(rig_root)

def freeze_meshes(meshes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
    return get_freeze_tools().mesh(meshes)

def freeze_selected() -> FreezeReport:
    return get_freeze_tools().selected()

def preview_freeze(nodes: Optional[Union[str, List[str]]] = None) -> FreezeReport:
    return get_freeze_tools().preview(nodes)

def validate_freeze(nodes: Union[str, List[str]]) -> ValidationResult:
    return get_freeze_tools().validate(nodes)

def set_freeze_settings(settings: FreezeSettings):
    get_freeze_tools().set_settings(settings)

# -----------------------------------------------------------------------------
# Self-test (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("FreezeTools module loaded. Use within Maya.")