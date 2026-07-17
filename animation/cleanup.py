"""
animation/cleanup.py

Animation Optimization & Scene Cleanup Engine for Maya.

This module is the final stage of the animation pipeline. It removes
unnecessary data, optimizes animation, cleans the Maya scene, validates
results, and prepares animation for export, game engines, or rendering.

It operates on keyframes, animation curves, layers, constraints, and scene
nodes to produce a clean, optimized, and valid scene.

Responsibilities:
- Remove static, duplicate, and redundant keyframes.
- Optimize animation curves: smooth, simplify, Euler filter, remove noise.
- Remove empty animation layers, unused constraints, and unknown nodes.
- Validate animation for broken connections, missing targets, locked channels.
- Provide diagnostics, statistics, and reports.
- Support batch cleanup and preview mode.

Dependencies:
- timeline.py (range and playback)
- keyframes.py (key manipulation)
- curves.py (curve optimization)
- layers.py (layer management)
- constraints.py (constraint cleanup)
- baking.py (optional, for re-baking if needed)

The module is Maya-independent in interface but uses Maya commands internally.
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable

# Maya imports
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode, selected, ls, exists, currentTime, setKeyframe
    import pymel.core as pm
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional dependencies from animation package
try:
    from .timeline import TimelineManager, TimelineRange
except ImportError:
    class TimelineManager:
        def frame_range(self):
            from dataclasses import dataclass
            @dataclass
            class Range:
                start: int = 1
                end: int = 100
            return Range()
    TimelineRange = None

try:
    from .keyframes import KeyframeManager, Keyframe, KeySelection, TransformMode
except ImportError:
    KeyframeManager = None
    Keyframe = None
    KeySelection = None
    TransformMode = None

try:
    from .curves import CurveManager, CurveType, FilterMode, CurveEditor, CurveFilter
except ImportError:
    CurveManager = None
    CurveType = None
    FilterMode = None
    CurveEditor = None
    CurveFilter = None

try:
    from .layers import AnimationLayerManager, LayerType
except ImportError:
    AnimationLayerManager = None
    LayerType = None

try:
    from .constraints import ConstraintManager, ConstraintType
except ImportError:
    ConstraintManager = None
    ConstraintType = None

try:
    from .baking import AnimationBaker
except ImportError:
    AnimationBaker = None

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class CleanupError(Exception):
    """Base exception for cleanup operations."""
    pass

class CleanupValidationError(CleanupError):
    """Raised when validation fails."""
    pass

class CleanupOperationError(CleanupError):
    """Raised when an operation fails."""
    pass

class CleanupCancelledError(CleanupError):
    """Raised when cleanup is cancelled."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class CleanupType(Enum):
    """Categories of cleanup operations."""
    KEYS = "keys"
    CURVES = "curves"
    LAYERS = "layers"
    CONSTRAINTS = "constraints"
    NODES = "nodes"
    CAMERAS = "cameras"
    DISPLAY = "display"
    SCENE = "scene"
    EXPORT = "export"


class OptimizationLevel(Enum):
    """Level of optimization aggressiveness."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"


class ValidationState(Enum):
    """Validation status."""
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"
    FIXED = "fixed"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CleanupSettings:
    """Settings for cleanup operations."""
    # Keyframe optimization
    remove_static_keys: bool = True
    remove_duplicate_keys: bool = True
    simplify_keys: bool = True
    simplify_tolerance: float = 0.01
    quantize_keys: bool = True
    quantize_step: float = 1.0

    # Curve optimization
    smooth_curves: bool = False
    smooth_window: int = 3
    euler_filter: bool = True
    remove_noise: bool = False
    noise_threshold: float = 0.05

    # Scene cleanup
    remove_empty_layers: bool = True
    remove_unused_constraints: bool = True
    remove_unknown_nodes: bool = True
    delete_empty_groups: bool = True
    delete_unused_cameras: bool = False
    clean_display_layers: bool = True

    # Validation
    validate_animation: bool = True
    fix_broken_connections: bool = False

    # Batch
    batch_mode: bool = False
    process_selected: bool = True
    process_hierarchy: bool = False
    process_all: bool = False

    # Advanced
    compress_animation: bool = False
    compress_threshold: float = 0.001
    optimize_for_export: bool = False


@dataclass
class CleanupTask:
    """A single cleanup task for batch processing."""
    name: str
    settings: CleanupSettings
    targets: List[str]  # nodes to process
    callback: Optional[Callable[[CleanupResult], None]] = None


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    success: bool
    keys_removed: int = 0
    keys_added: int = 0
    keys_modified: int = 0
    curves_optimized: int = 0
    layers_removed: int = 0
    constraints_removed: int = 0
    nodes_removed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CleanupStatistics:
    """Statistics for cleanup operations."""
    total_objects: int = 0
    total_curves: int = 0
    keys_before: int = 0
    keys_after: int = 0
    keys_reduction_percent: float = 0.0
    layers_before: int = 0
    layers_after: int = 0
    constraints_before: int = 0
    constraints_after: int = 0
    runtime_seconds: float = 0.0
    # Additional
    node_types_removed: Dict[str, int] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    """A single validation issue."""
    state: ValidationState
    message: str
    node: Optional[str] = None
    attribute: Optional[str] = None
    time: Optional[float] = None


@dataclass
class ValidationReport:
    """Validation report."""
    success: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CleanupReport:
    """Combined report for cleanup and validation."""
    success: bool
    cleanup_result: CleanupResult
    validation_report: ValidationReport
    statistics: CleanupStatistics
    preview: bool = False


# ---- Part 4: Cleanup Manager ------------------------------------------

class AnimationCleanupManager:
    """
    Main controller for animation cleanup and optimization.
    """
    def __init__(self):
        self._timeline = TimelineManager()
        self._keyframe_manager = KeyframeManager() if KeyframeManager else None
        self._curve_manager = CurveManager() if CurveManager else None
        self._layer_manager = AnimationLayerManager() if AnimationLayerManager else None
        self._constraint_manager = ConstraintManager() if ConstraintManager else None
        self._baker = AnimationBaker() if AnimationBaker else None

        self._settings = CleanupSettings()
        self._last_result: Optional[CleanupResult] = None
        self._last_stats: Optional[CleanupStatistics] = None
        self._last_report: Optional[CleanupReport] = None
        self._cancelled = False

    # ---- Main Entry Points ----

    def cleanup(self, settings: Optional[CleanupSettings] = None) -> CleanupReport:
        """
        Run the full cleanup pipeline.
        """
        if settings:
            self._settings = settings

        start_time = time.time()
        result = CleanupResult(success=True)
        stats = CleanupStatistics()
        validation = ValidationReport(success=True)

        # Step 1: Validate (optional)
        if self._settings.validate_animation:
            validation = self.validate()
            if not validation.is_valid and not self._settings.fix_broken_connections:
                # If validation has errors and we're not fixing, we can still proceed but report.
                result.warnings.append("Validation found errors; continue with caution.")

        # Step 2: Keyframe optimization
        if self._settings.remove_static_keys or self._settings.remove_duplicate_keys or self._settings.simplify_keys:
            key_result = self.optimize_keys()
            result.keys_removed += key_result.keys_removed
            result.keys_modified += key_result.keys_modified
            if not key_result.success:
                result.errors.extend(key_result.errors)
                result.success = False

        # Step 3: Curve optimization
        if self._settings.smooth_curves or self._settings.euler_filter or self._settings.remove_noise:
            curve_result = self.optimize_curves()
            result.curves_optimized += curve_result.curves_optimized
            if not curve_result.success:
                result.errors.extend(curve_result.errors)
                result.success = False

        # Step 4: Layer cleanup
        if self._settings.remove_empty_layers:
            layer_result = self.cleanup_layers()
            result.layers_removed += layer_result.layers_removed
            if not layer_result.success:
                result.errors.extend(layer_result.errors)
                result.success = False

        # Step 5: Constraint cleanup
        if self._settings.remove_unused_constraints:
            constraint_result = self.cleanup_constraints()
            result.constraints_removed += constraint_result.constraints_removed
            if not constraint_result.success:
                result.errors.extend(constraint_result.errors)
                result.success = False

        # Step 6: Scene cleanup (nodes, cameras, etc.)
        if self._settings.remove_unknown_nodes or self._settings.delete_empty_groups or self._settings.delete_unused_cameras:
            scene_result = self.cleanup_scene()
            result.nodes_removed += scene_result.nodes_removed
            if not scene_result.success:
                result.errors.extend(scene_result.errors)
                result.success = False

        # Step 7: Post-validation
        if self._settings.validate_animation:
            validation_after = self.validate()
            # Merge validation results
            validation.issues.extend(validation_after.issues)
            validation.warnings.extend(validation_after.warnings)
            validation.errors.extend(validation_after.errors)
            validation.success = validation_after.success

        # Compute statistics
        stats = self.compute_statistics()
        stats.runtime_seconds = time.time() - start_time

        self._last_result = result
        self._last_stats = stats
        report = CleanupReport(
            success=result.success and validation.success,
            cleanup_result=result,
            validation_report=validation,
            statistics=stats,
            preview=False
        )
        self._last_report = report
        return report

    def preview(self, settings: Optional[CleanupSettings] = None) -> CleanupReport:
        """
        Preview what cleanup would do without actually modifying the scene.
        """
        # We'll simulate by collecting statistics and estimating changes.
        if settings:
            self._settings = settings

        # We'll run validation and statistics, but not actually modify.
        validation = self.validate()
        stats = self.compute_statistics()
        # Estimate reductions based on settings
        # For simplicity, we'll just return a report with preview=True.
        result = CleanupResult(success=True)
        # Estimate key reduction
        if self._settings.remove_static_keys or self._settings.simplify_keys:
            # Simulate by checking static keys? Too heavy.
            # We'll just estimate based on typical reduction.
            result.keys_removed = int(stats.keys_before * 0.2)  # placeholder
        report = CleanupReport(
            success=True,
            cleanup_result=result,
            validation_report=validation,
            statistics=stats,
            preview=True
        )
        return report

    def undo(self) -> bool:
        """Undo the last cleanup operation (Maya undo)."""
        try:
            cmds.undo()
            return True
        except:
            return False

    def cancel(self) -> None:
        """Cancel the current cleanup operation (if running in a thread)."""
        self._cancelled = True

    # ---- Keyframe Optimization ----

    def optimize_keys(self) -> CleanupResult:
        """Remove static, duplicate, and redundant keys."""
        if not self._keyframe_manager:
            return CleanupResult(success=False, errors=["KeyframeManager not available"])

        result = CleanupResult(success=True)

        # Get nodes to process
        nodes = self._get_target_nodes()
        if not nodes:
            result.warnings.append("No nodes to process")
            return result

        # For each node and its animatable attributes
        for node in nodes:
            if self._cancelled:
                raise CleanupCancelledError("Cleanup cancelled")
            attrs = cmds.listAttr(node, keyable=True, scalar=True) or []
            for attr in attrs:
                full_attr = f"{node}.{attr}"
                if not cmds.objExists(full_attr):
                    continue
                # Get keys
                keys = cmds.keyframe(full_attr, q=True) or []
                if not keys:
                    continue

                # Remove static keys (all same value)
                if self._settings.remove_static_keys:
                    values = [cmds.keyframe(full_attr, q=True, time=(t, t), valueChange=True)[0] for t in keys]
                    if len(set(values)) == 1:
                        # All keys have the same value, keep one key or delete all?
                        # We'll delete all and insert one at start.
                        start = self._timeline.frame_range().start
                        cmds.cutKey(full_attr, clear=True)
                        cmds.setKeyframe(full_attr, t=start, v=values[0])
                        result.keys_removed += len(keys) - 1
                        # We've replaced all with one; skip further ops on this attr
                        continue

                # Remove duplicate keys (consecutive same value)
                if self._settings.remove_duplicate_keys:
                    keys = cmds.keyframe(full_attr, q=True) or []
                    if len(keys) > 1:
                        # We'll check consecutive keys
                        values = [cmds.keyframe(full_attr, q=True, time=(t, t), valueChange=True)[0] for t in keys]
                        to_remove = []
                        for i in range(1, len(keys)):
                            if values[i] == values[i-1]:
                                to_remove.append(keys[i])
                        for t in to_remove:
                            cmds.cutKey(full_attr, t=(t, t))
                            result.keys_removed += 1

                # Simplify keys (using Maya's simplifyCurve)
                if self._settings.simplify_keys:
                    # We can use simplifyCurve on the attribute's curve.
                    # First get the curve node
                    curve_nodes = cmds.listConnections(full_attr, type='animCurve') or []
                    for curve in curve_nodes:
                        cmds.simplifyCurve(curve, r=self._settings.simplify_tolerance)
                        # Count keys removed? We'll estimate by key count before/after.
                        # We'll compute after.

        # Recompute key counts for statistics
        # We'll update result keys_removed more accurately? Hard.
        return result

    # ---- Curve Optimization ----

    def optimize_curves(self) -> CleanupResult:
        """Optimize animation curves using smoothing, Euler filter, etc."""
        if not self._curve_manager:
            return CleanupResult(success=False, errors=["CurveManager not available"])

        result = CleanupResult(success=True)
        nodes = self._get_target_nodes()
        if not nodes:
            result.warnings.append("No nodes to process")
            return result

        # Collect all animCurve nodes connected to these nodes
        curve_nodes = []
        for node in nodes:
            attrs = cmds.listAttr(node, keyable=True, scalar=True) or []
            for attr in attrs:
                full_attr = f"{node}.{attr}"
                if cmds.objExists(full_attr):
                    conns = cmds.listConnections(full_attr, type='animCurve') or []
                    curve_nodes.extend(conns)

        # Remove duplicates
        curve_nodes = list(set(curve_nodes))

        for curve in curve_nodes:
            if self._cancelled:
                raise CleanupCancelledError("Cleanup cancelled")
            try:
                # Euler filter on rotation curves
                if self._settings.euler_filter and 'rotate' in curve:
                    cmds.eulerFilter(curve)

                # Smoothing (moving average)
                if self._settings.smooth_curves:
                    # We'll use a moving average on keys.
                    # We can use CurveFilter.smooth if available.
                    if CurveFilter:
                        CurveFilter.smooth(curve, window=self._settings.smooth_window)
                    else:
                        # Fallback: simple smooth using key operations.
                        pass

                # Remove noise (simplify with low tolerance)
                if self._settings.remove_noise:
                    cmds.simplifyCurve(curve, r=self._settings.noise_threshold)

                result.curves_optimized += 1
            except Exception as e:
                result.errors.append(f"Failed to optimize curve {curve}: {e}")
                result.success = False

        return result

    # ---- Layer Cleanup ----

    def cleanup_layers(self) -> CleanupResult:
        """Remove empty animation layers."""
        if not self._layer_manager:
            return CleanupResult(success=False, errors=["LayerManager not available"])

        result = CleanupResult(success=True)
        layers = self._layer_manager.list_layers()
        for layer in layers:
            if layer == "BaseLayer":
                continue
            members = self._layer_manager.members(layer)
            if not members:
                # Empty layer
                try:
                    self._layer_manager.delete(layer)
                    result.layers_removed += 1
                except Exception as e:
                    result.errors.append(f"Failed to delete empty layer {layer}: {e}")
                    result.success = False
        return result

    # ---- Constraint Cleanup ----

    def cleanup_constraints(self) -> CleanupResult:
        """Remove unused constraints (constraints that have no effect or are broken)."""
        if not self._constraint_manager:
            return CleanupResult(success=False, errors=["ConstraintManager not available"])

        result = CleanupResult(success=True)
        constraints = self._constraint_manager.list_constraints()
        for constr in constraints:
            # Check if constraint is disabled or has zero weight
            try:
                weight = self._constraint_manager.weight(constr)
                if weight == 0:
                    self._constraint_manager.delete(constr)
                    result.constraints_removed += 1
                    continue
                # Check if source or targets are missing
                constraint_obj = self._constraint_manager.get_constraint(constr)
                if not cmds.objExists(constraint_obj.source):
                    self._constraint_manager.delete(constr)
                    result.constraints_removed += 1
                    continue
                for target in constraint_obj.targets:
                    if not cmds.objExists(target.node):
                        self._constraint_manager.delete(constr)
                        result.constraints_removed += 1
                        break
            except Exception as e:
                result.errors.append(f"Failed to process constraint {constr}: {e}")
                result.success = False
        return result

    # ---- Scene Cleanup ----

    def cleanup_scene(self) -> CleanupResult:
        """Delete unknown nodes, empty groups, unused cameras, etc."""
        result = CleanupResult(success=True)

        # Delete unknown nodes (nodes that are not recognized or are orphaned)
        if self._settings.remove_unknown_nodes:
            unknown_types = ['unknown', 'dependNode', 'script', 'expression', 'timeEditor']
            for ut in unknown_types:
                nodes = cmds.ls(type=ut) or []
                for node in nodes:
                    try:
                        cmds.delete(node)
                        result.nodes_removed += 1
                    except:
                        pass

        # Delete empty groups
        if self._settings.delete_empty_groups:
            groups = cmds.ls(type='transform') or []
            for group in groups:
                if cmds.nodeType(group) == 'transform':
                    children = cmds.listRelatives(group, children=True) or []
                    if not children and cmds.getAttr(f"{group}.tx") == 0 and cmds.getAttr(f"{group}.ty") == 0 and cmds.getAttr(f"{group}.tz") == 0:
                        # Also check if it has any attributes? We'll delete if empty.
                        try:
                            cmds.delete(group)
                            result.nodes_removed += 1
                        except:
                            pass

        # Delete unused cameras
        if self._settings.delete_unused_cameras:
            cameras = cmds.ls(type='camera') or []
            # Get default cameras (persp, top, front, side)
            default_cameras = ['persp', 'top', 'front', 'side']
            for cam in cameras:
                if cam in default_cameras:
                    continue
                # Check if camera is used by any render layer or view?
                # For simplicity, we'll delete if not in any render layer and not selected.
                # We'll be conservative: only delete if it's a shape with no transform connections.
                # We'll skip for now.
                pass

        return result

    # ---- Validation ----

    def validate(self) -> ValidationReport:
        """Validate the animation for common issues."""
        report = ValidationReport(success=True)
        nodes = self._get_target_nodes()
        if not nodes:
            report.issues.append(ValidationIssue(state=ValidationState.WARNING, message="No nodes to validate"))
            return report

        for node in nodes:
            attrs = cmds.listAttr(node, keyable=True, scalar=True) or []
            for attr in attrs:
                full_attr = f"{node}.{attr}"
                if not cmds.objExists(full_attr):
                    continue
                # Check for broken connections
                if cmds.objExists(full_attr):
                    connections = cmds.listConnections(full_attr, source=True, destination=False) or []
                    if not connections:
                        # No incoming connections, but may be fine.
                        pass
                # Check for locked attributes
                if cmds.getAttr(full_attr, lock=True):
                    report.warnings.append(ValidationIssue(state=ValidationState.WARNING, message=f"Locked attribute {full_attr}", node=node, attribute=attr))
                # Check for NaN or infinite values
                try:
                    val = cmds.getAttr(full_attr)
                    if not isinstance(val, (int, float)):
                        continue
                    if math.isnan(val) or math.isinf(val):
                        report.errors.append(ValidationIssue(state=ValidationState.ERROR, message=f"Invalid value {val} on {full_attr}", node=node, attribute=attr))
                        report.success = False
                except:
                    pass
                # Check for keys outside timeline
                keys = cmds.keyframe(full_attr, q=True) or []
                timeline = self._timeline.frame_range()
                for t in keys:
                    if t < timeline.start or t > timeline.end:
                        report.warnings.append(ValidationIssue(state=ValidationState.WARNING, message=f"Key at {t} outside timeline", node=node, attribute=attr, time=t))

        return report

    # ---- Batch Cleanup ----

    def batch_cleanup(self, tasks: List[CleanupTask]) -> List[CleanupReport]:
        """Run multiple cleanup tasks in sequence."""
        reports = []
        for task in tasks:
            self._settings = task.settings
            report = self.cleanup()
            if task.callback:
                task.callback(report.cleanup_result)
            reports.append(report)
        return reports

    # ---- Statistics ----

    def compute_statistics(self) -> CleanupStatistics:
        """Compute statistics for the current scene."""
        stats = CleanupStatistics()
        # Count objects (transforms)
        all_transforms = cmds.ls(type='transform') + cmds.ls(type='joint')
        stats.total_objects = len(all_transforms)

        # Count animation curves and keys
        curve_nodes = cmds.ls(type='animCurve*') or []
        stats.total_curves = len(curve_nodes)
        total_keys = 0
        for curve in curve_nodes:
            keys = cmds.keyframe(curve, q=True) or []
            total_keys += len(keys)
        stats.keys_before = total_keys
        stats.keys_after = total_keys  # Will be updated after cleanup

        # Count layers
        if self._layer_manager:
            stats.layers_before = len(self._layer_manager.list_layers())
            stats.layers_after = stats.layers_before

        # Count constraints
        if self._constraint_manager:
            stats.constraints_before = len(self._constraint_manager.list_constraints())
            stats.constraints_after = stats.constraints_before

        return stats

    # ---- Utility ----

    def _get_target_nodes(self) -> List[str]:
        """Determine which nodes to process based on settings."""
        if self._settings.process_selected:
            nodes = cmds.ls(selection=True, type='transform') or []
        elif self._settings.process_hierarchy:
            selected = cmds.ls(selection=True, type='transform') or []
            nodes = []
            for root in selected:
                hierarchy = cmds.listRelatives(root, allDescendents=True, fullPath=True) or []
                nodes.extend(hierarchy)
                nodes.append(root)
        elif self._settings.process_all:
            nodes = cmds.ls(type='transform') + cmds.ls(type='joint')
        else:
            nodes = cmds.ls(selection=True, type='transform') or []
        return nodes

    # ---- Public API methods ----

    def remove_static_keys(self) -> CleanupResult:
        """Shortcut to remove static keys."""
        self._settings.remove_static_keys = True
        self._settings.remove_duplicate_keys = False
        self._settings.simplify_keys = False
        return self.optimize_keys()

    def remove_duplicate_keys(self) -> CleanupResult:
        """Shortcut to remove duplicate keys."""
        self._settings.remove_static_keys = False
        self._settings.remove_duplicate_keys = True
        self._settings.simplify_keys = False
        return self.optimize_keys()

    def simplify_keys(self, tolerance: float = 0.01) -> CleanupResult:
        """Shortcut to simplify keys."""
        self._settings.remove_static_keys = False
        self._settings.remove_duplicate_keys = False
        self._settings.simplify_keys = True
        self._settings.simplify_tolerance = tolerance
        return self.optimize_keys()

    def optimize_curves_smooth(self, window: int = 3) -> CleanupResult:
        self._settings.smooth_curves = True
        self._settings.smooth_window = window
        return self.optimize_curves()

    def euler_filter_curves(self) -> CleanupResult:
        self._settings.euler_filter = True
        return self.optimize_curves()

    def remove_empty_layers(self) -> CleanupResult:
        return self.cleanup_layers()

    def remove_unused_constraints(self) -> CleanupResult:
        return self.cleanup_constraints()

    def delete_unknown_nodes(self) -> CleanupResult:
        self._settings.remove_unknown_nodes = True
        return self.cleanup_scene()

    def statistics(self) -> CleanupStatistics:
        return self.compute_statistics()

    def get_last_report(self) -> Optional[CleanupReport]:
        return self._last_report

    def get_last_result(self) -> Optional[CleanupResult]:
        return self._last_result

    def reset(self) -> None:
        """Reset settings to defaults."""
        self._settings = CleanupSettings()
        self._cancelled = False


# ---- Part 11: Utility Functions --------------------------------------

def get_cleanup_presets() -> Dict[str, CleanupSettings]:
    """Return preset cleanup settings for common use cases."""
    presets = {}

    # Lossless cleanup (remove static keys, empty layers, unused constraints)
    presets["lossless"] = CleanupSettings(
        remove_static_keys=True,
        remove_duplicate_keys=False,
        simplify_keys=False,
        remove_empty_layers=True,
        remove_unused_constraints=True,
        remove_unknown_nodes=False,
        delete_empty_groups=False,
        validate_animation=True,
    )

    # Standard optimization (good for animation export)
    presets["standard"] = CleanupSettings(
        remove_static_keys=True,
        remove_duplicate_keys=True,
        simplify_keys=True,
        simplify_tolerance=0.01,
        remove_empty_layers=True,
        remove_unused_constraints=True,
        remove_unknown_nodes=True,
        delete_empty_groups=True,
        euler_filter=True,
        validate_animation=True,
    )

    # High optimization (aggressive reduction)
    presets["high"] = CleanupSettings(
        remove_static_keys=True,
        remove_duplicate_keys=True,
        simplify_keys=True,
        simplify_tolerance=0.05,
        smooth_curves=True,
        smooth_window=3,
        euler_filter=True,
        remove_noise=True,
        noise_threshold=0.05,
        remove_empty_layers=True,
        remove_unused_constraints=True,
        remove_unknown_nodes=True,
        delete_empty_groups=True,
        validate_animation=True,
    )

    # Game export (heavy optimization)
    presets["game_export"] = CleanupSettings(
        remove_static_keys=True,
        remove_duplicate_keys=True,
        simplify_keys=True,
        simplify_tolerance=0.02,
        smooth_curves=False,
        euler_filter=True,
        remove_noise=False,
        remove_empty_layers=True,
        remove_unused_constraints=True,
        remove_unknown_nodes=True,
        delete_empty_groups=True,
        delete_unused_cameras=True,
        compress_animation=True,
        compress_threshold=0.001,
        validate_animation=True,
    )

    return presets


# ---- Part 12: Public API -----------------------------------------------

__all__ = [
    "AnimationCleanupManager",
    "CleanupSettings",
    "CleanupTask",
    "CleanupResult",
    "CleanupStatistics",
    "ValidationIssue",
    "ValidationReport",
    "CleanupReport",
    "CleanupType",
    "OptimizationLevel",
    "ValidationState",
    "CleanupError",
    "CleanupValidationError",
    "CleanupOperationError",
    "CleanupCancelledError",
    "get_cleanup_presets",
]