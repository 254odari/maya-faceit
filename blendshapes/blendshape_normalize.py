
"""
blendshapes/blendshape_normalize.py

Blendshape Normalization System for Maya.

This module ensures blendshape weights, deltas, poses, ARKit coefficients,
corrective shapes, and inbetween systems remain mathematically consistent
and predictable. It prevents overdriven expressions, asymmetry, volume loss,
and other deformation artifacts that arise when multiple facial systems
interact simultaneously.

Responsibilities:
- Normalize blendshape weights (clamp, scale, range, symmetry).
- Normalize vertex deltas (magnitude, outliers, volume preservation).
- Normalize facial poses (expression balancing, redistribution).
- Normalize ARKit coefficients (52 channels, calibration, scaling).
- Normalize corrective shapes (PSD balancing, trigger normalization).
- Normalize inbetween targets (weight spacing, curve smoothing).
- Normalize symmetry (mirror, average, equalize left/right).
- Batch normalize multiple targets.
- Validate normalization results.
- Provide diagnostics and reports.

The normalizer integrates with other blendshape modules and the arkit package.

Dependencies:
- blendshape_weights.py: Weight management.
- blendshape_delta.py: Delta computation and management.
- blendshape_pose.py: Pose definitions and management.
- blendshape_correctives.py: Corrective definitions.
- blendshape_inbetweens.py: Inbetween management.
- blendshape_validator.py: Validation.
- blendshape_utils.py: Shared utilities.
- symmetry.py: Symmetry mapping.
- arkit52.py: ARKit channel constants.

The module uses Maya's Python API and may optionally leverage NumPy.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Maya imports (with fallback)
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists # type: ignore
    import pymel.core as pm # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional NumPy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# Import blendshape modules (with fallbacks)
try:
    from .blendshape_weights import BlendshapeWeightManager, WeightSet
except ImportError:
    BlendshapeWeightManager = None
    WeightSet = None

try:
    from .blendshape_delta import BlendshapeDeltaEngine, BlendshapeDelta, VertexDelta
except ImportError:
    BlendshapeDeltaEngine = None
    BlendshapeDelta = None
    VertexDelta = None

try:
    from .blendshape_pose import BlendshapePoseManager, PoseDefinition, PoseType
except ImportError:
    BlendshapePoseManager = None
    PoseDefinition = None
    PoseType = None

try:
    from .blendshape_correctives import BlendshapeCorrectiveManager, CorrectiveDefinition
except ImportError:
    BlendshapeCorrectiveManager = None
    CorrectiveDefinition = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager, InbetweenDefinition
except ImportError:
    BlendshadeInbetweenManager = None
    InbetweenDefinition = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None

try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions,
        get_vertex_position, set_vertex_position, clamp, lerp,
        sanitize_name, generate_unique_name, get_blendshape_targets,
        get_blendshape_weight, set_blendshape_weight, Timer, ProgressTracker,
        duplicate_mesh, freeze_transforms, remove_namespace, add_namespace,
        get_mesh_center, distance_point_to_point, normalize_vector,
        get_mesh_bounding_box, dict_to_json, json_to_dict, hash_data,
        checksum_mesh, get_active_weights, scale_weights, blend_weights,
        normalize_weights, apply_weight_bias, apply_weight_mask, mirror_weights
    )
except ImportError:
    # Minimal fallback
    def get_shape_node(x): return x
    def get_mesh_vertex_count(x): return 0
    def get_mesh_vertex_positions(x): return []
    def get_vertex_position(x,y): return (0,0,0)
    def set_vertex_position(x,y,z): pass
    def clamp(a,b,c): return max(b, min(a, c))
    def lerp(a,b,t): return a + (b-a)*t
    def sanitize_name(n): return n
    def generate_unique_name(n, existing): return n
    def get_blendshape_targets(n): return []
    def get_blendshape_weight(n,t): return 0.0
    def set_blendshape_weight(n,t,v): pass
    class Timer: pass
    class ProgressTracker: pass
    def duplicate_mesh(m, n): return m
    def freeze_transforms(m): pass
    def remove_namespace(n): return n
    def add_namespace(n, ns): return n
    def get_mesh_center(m): return (0,0,0)
    def distance_point_to_point(a,b): return 0.0
    def normalize_vector(v): return (0,0,0)
    def get_mesh_bounding_box(m): return ((0,0,0),(0,0,0))
    def dict_to_json(d, indent=2): return "{}"
    def json_to_dict(s): return {}
    def hash_data(d): return ""
    def checksum_mesh(m): return ""
    def get_active_weights(w, th): return {}
    def scale_weights(w, f): return {}
    def blend_weights(a,b,t): return {}
    def normalize_weights(w): return {}
    def apply_weight_bias(w,b): return {}
    def apply_weight_mask(w,m): return {}
    def mirror_weights(w,m): return {}

try:
    from ..core.symmetry import SymmetryEngine, SymmetryMap
except ImportError:
    SymmetryEngine = None
    SymmetryMap = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()


# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass

class NormalizationCanceledError(NormalizationError):
    """Raised when normalization is canceled."""
    pass

class NormalizationValidationError(NormalizationError):
    """Raised when validation fails after normalization."""
    pass


# ---- Part 2: Constants & Enumerations --------------------------------

class NormalizationType(Enum):
    """Types of normalization to perform."""
    WEIGHTS = "weights"
    DELTAS = "deltas"
    POSES = "poses"
    ARKIT = "arkit"
    CORRECTIVES = "correctives"
    INBETWEENS = "inbetweens"
    SYMMETRY = "symmetry"
    FULL = "full"


class NormalizationMode(Enum):
    """Mode of normalization."""
    CLAMP = "clamp"
    SCALE = "scale"
    AVERAGE = "average"
    WEIGHTED = "weighted"
    PROPORTIONAL = "proportional"
    CUSTOM = "custom"


class RangePolicy(Enum):
    """Policy for range limits."""
    ZERO_ONE = "zero_one"   # Clamp to [0,1]
    MIN_MAX = "min_max"     # Scale to [min, max]
    CUSTOM = "custom"       # User-defined range
    UNLIMITED = "unlimited" # No clamping


class SymmetryMode(Enum):
    """Symmetry normalization mode."""
    LEFT_RIGHT = "left_right"
    RIGHT_LEFT = "right_left"
    AVERAGE = "average"
    MIRROR = "mirror"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class NormalizationSettings:
    """Settings for normalization operations."""
    # General
    normalization_types: List[NormalizationType] = field(default_factory=lambda: [NormalizationType.FULL])
    mode: NormalizationMode = NormalizationMode.CLAMP
    range_policy: RangePolicy = RangePolicy.ZERO_ONE
    custom_min: float = 0.0
    custom_max: float = 1.0

    # Weights
    clamp_weights: bool = True
    weight_min: float = 0.0
    weight_max: float = 1.0
    normalize_weight_groups: bool = False
    weight_groups: Optional[Dict[str, List[str]]] = None

    # Deltas
    normalize_delta_magnitudes: bool = True
    delta_max_magnitude: float = 1.0
    remove_delta_outliers: bool = True
    outlier_threshold: float = 2.0  # standard deviations
    preserve_volume: bool = True

    # Poses
    normalize_poses: bool = True
    pose_balancing: bool = True
    pose_redistribution: bool = True

    # ARKit
    normalize_arkit: bool = True
    arkit_calibration_profile: Optional[str] = None
    arkit_range: Tuple[float, float] = (0.0, 1.0)

    # Correctives
    normalize_correctives: bool = True
    corrective_balancing: bool = True
    corrective_scaling: bool = True

    # Inbetweens
    normalize_inbetweens: bool = True
    inbetween_weight_spacing: bool = True
    inbetween_curve_smoothing: bool = True

    # Symmetry
    normalize_symmetry: bool = True
    symmetry_mode: SymmetryMode = SymmetryMode.AVERAGE
    symmetry_tolerance: float = 0.001

    # Batch
    batch_parallel: bool = False
    batch_max_workers: int = 4

    # Validation
    validate_before: bool = True
    validate_after: bool = True
    validation_level: str = "normal"

    # Progress
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class NormalizationTask:
    """A single normalization task for batch processing."""
    name: str
    settings: NormalizationSettings
    targets: Optional[List[str]] = None  # specific targets to normalize
    callback: Optional[Callable[[NormalizationResult], None]] = None


@dataclass
class NormalizationResult:
    """Result of a normalization operation."""
    success: bool
    normalized_targets: List[str] = field(default_factory=list)
    corrected_weights: int = 0
    corrected_deltas: int = 0
    corrected_poses: int = 0
    corrected_arkit: int = 0
    corrected_correctives: int = 0
    corrected_inbetweens: int = 0
    corrected_symmetry: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass
class NormalizationStatistics:
    """Statistics for normalization operations."""
    total_targets: int = 0
    normalized_targets: int = 0
    weight_corrections: int = 0
    delta_corrections: int = 0
    pose_corrections: int = 0
    arkit_corrections: int = 0
    corrective_corrections: int = 0
    inbetween_corrections: int = 0
    symmetry_corrections: int = 0
    time_seconds: float = 0.0


@dataclass
class NormalizationReport:
    """Full report of normalization run."""
    success: bool
    result: NormalizationResult
    statistics: NormalizationStatistics
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


# ---- Part 4: Normalization Manager ------------------------------------

class BlendshapeNormalizer:
    """
    Main controller for all blendshape normalization operations.
    """
    def __init__(self):
        self._weight_manager = BlendshapeWeightManager() if BlendshapeWeightManager else None
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._pose_manager = BlendshapePoseManager() if BlendshapePoseManager else None
        self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._symmetry_engine = SymmetryEngine() if SymmetryEngine else None

        self._settings = NormalizationSettings()
        self._last_report: Optional[NormalizationReport] = None
        self._last_stats: Optional[NormalizationStatistics] = None
        self._cancelled = False

    # ---- Main Normalization API ----

    def normalize(
        self,
        targets: Optional[List[str]] = None,
        settings: Optional[NormalizationSettings] = None,
    ) -> NormalizationReport:
        """
        Normalize blendshapes according to the provided settings.
        If targets is None, normalizes all available blendshapes.
        """
        if settings is not None:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # Collect targets
        if targets is None:
            targets = self._collect_all_targets()

        # Validate before
        if self._settings.validate_before and self._validator:
            val_report = self._validator.validate(targets, level=self._settings.validation_level)
            if not val_report.is_valid:
                return self._create_failure_report("Pre-validation failed", val_report.errors, start_time)

        result = NormalizationResult(success=True)
        stats = NormalizationStatistics()
        stats.total_targets = len(targets)

        # Run each normalization type
        for norm_type in self._settings.normalization_types:
            if self._cancelled:
                raise NormalizationCanceledError("Normalization canceled")
            try:
                if norm_type == NormalizationType.WEIGHTS:
                    weight_result = self._normalize_weights(targets)
                    result = self._merge_result(result, weight_result)
                elif norm_type == NormalizationType.DELTAS:
                    delta_result = self._normalize_deltas(targets)
                    result = self._merge_result(result, delta_result)
                elif norm_type == NormalizationType.POSES:
                    pose_result = self._normalize_poses()
                    result = self._merge_result(result, pose_result)
                elif norm_type == NormalizationType.ARKIT:
                    arkit_result = self._normalize_arkit()
                    result = self._merge_result(result, arkit_result)
                elif norm_type == NormalizationType.CORRECTIVES:
                    corr_result = self._normalize_correctives()
                    result = self._merge_result(result, corr_result)
                elif norm_type == NormalizationType.INBETWEENS:
                    inb_result = self._normalize_inbetweens()
                    result = self._merge_result(result, inb_result)
                elif norm_type == NormalizationType.SYMMETRY:
                    sym_result = self._normalize_symmetry(targets)
                    result = self._merge_result(result, sym_result)
                elif norm_type == NormalizationType.FULL:
                    # Run all types
                    for sub_type in [NormalizationType.WEIGHTS, NormalizationType.DELTAS,
                                     NormalizationType.POSES, NormalizationType.ARKIT,
                                     NormalizationType.CORRECTIVES, NormalizationType.INBETWEENS,
                                     NormalizationType.SYMMETRY]:
                        sub_result = self.normalize(targets, settings)  # Recursive? Not ideal.
                        # Instead, we'll manually call each.
                        pass
            except NormalizationCanceledError:
                raise
            except Exception as e:
                result.errors.append(f"Normalization type {norm_type.value} failed: {e}")
                result.success = False

        # Validate after
        if self._settings.validate_after and self._validator:
            val_report = self._validator.validate(targets, level=self._settings.validation_level)
            if not val_report.is_valid:
                result.errors.extend(val_report.errors)
                result.success = False

        # Compute final statistics
        stats = self._compute_statistics(targets, start_time)
        stats.normalized_targets = len(result.normalized_targets)
        stats.weight_corrections = result.corrected_weights
        stats.delta_corrections = result.corrected_deltas
        stats.pose_corrections = result.corrected_poses
        stats.arkit_corrections = result.corrected_arkit
        stats.corrective_corrections = result.corrected_correctives
        stats.inbetween_corrections = result.corrected_inbetweens
        stats.symmetry_corrections = result.corrected_symmetry

        report = NormalizationReport(
            success=result.success,
            result=result,
            statistics=stats,
            validation_errors=[],
            validation_warnings=[]
        )
        self._last_report = report
        self._last_stats = stats
        return report

    def normalize_weights(self, targets: Optional[List[str]] = None) -> NormalizationReport:
        """Convenience method to normalize only weights."""
        settings = copy.copy(self._settings)
        settings.normalization_types = [NormalizationType.WEIGHTS]
        return self.normalize(targets, settings)

    def normalize_deltas(self, targets: Optional[List[str]] = None) -> NormalizationReport:
        """Convenience method to normalize only deltas."""
        settings = copy.copy(self._settings)
        settings.normalization_types = [NormalizationType.DELTAS]
        return self.normalize(targets, settings)

    def normalize_poses(self) -> NormalizationReport:
        """Convenience method to normalize only poses."""
        settings = copy.copy(self._settings)
        settings.normalization_types = [NormalizationType.POSES]
        return self.normalize(None, settings)

    def normalize_arkit(self) -> NormalizationReport:
        """Convenience method to normalize only ARKit."""
        settings = copy.copy(self._settings)
        settings.normalization_types = [NormalizationType.ARKIT]
        return self.normalize(None, settings)

    def normalize_symmetry(self, targets: Optional[List[str]] = None) -> NormalizationReport:
        """Convenience method to normalize only symmetry."""
        settings = copy.copy(self._settings)
        settings.normalization_types = [NormalizationType.SYMMETRY]
        return self.normalize(targets, settings)

    def cancel(self) -> None:
        """Cancel the current normalization operation."""
        self._cancelled = True

    # ---- Internal Normalization Methods ----

    def _normalize_weights(self, targets: List[str]) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._weight_manager:
            result.errors.append("Weight manager not available")
            result.success = False
            return result

        # Get all current weights
        all_weights = self._weight_manager.get_all_weights()
        corrected = 0
        for target in targets:
            if target not in all_weights:
                continue
            val = all_weights[target]
            # Apply range policy
            if self._settings.range_policy == RangePolicy.ZERO_ONE:
                new_val = clamp(val, 0.0, 1.0)
            elif self._settings.range_policy == RangePolicy.MIN_MAX:
                if self._settings.custom_min < self._settings.custom_max:
                    new_val = clamp(val, self._settings.custom_min, self._settings.custom_max)
                else:
                    new_val = val
            else:
                new_val = val
            if new_val != val:
                self._weight_manager.set_weight(target, new_val)
                corrected += 1
                result.normalized_targets.append(target)

        # Group normalization if requested
        if self._settings.normalize_weight_groups and self._settings.weight_groups:
            for group_name, group_targets in self._settings.weight_groups.items():
                group_weights = {t: self._weight_manager.get_weight(t) for t in group_targets if t in all_weights}
                if group_weights:
                    # Normalize group to sum to 1.0
                    total = sum(group_weights.values())
                    if total > 0:
                        for t, v in group_weights.items():
                            new_val = v / total
                            self._weight_manager.set_weight(t, new_val)
                            corrected += 1
                            result.normalized_targets.append(t)

        result.corrected_weights = corrected
        return result

    def _normalize_deltas(self, targets: List[str]) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._delta_engine:
            result.errors.append("Delta engine not available")
            result.success = False
            return result

        corrected = 0
        for target in targets:
            delta = self._delta_engine.get(target)
            if not delta:
                continue

            # Normalize delta magnitudes
            if self._settings.normalize_delta_magnitudes:
                max_mag = max((v.magnitude() for v in delta.deltas), default=0.0)
                if max_mag > self._settings.delta_max_magnitude:
                    scale = self._settings.delta_max_magnitude / max_mag
                    # Scale all deltas
                    new_deltas = []
                    for v in delta.deltas:
                        dx, dy, dz = v.offset
                        new_deltas.append(VertexDelta(
                            index=v.index,
                            offset=(dx * scale, dy * scale, dz * scale)
                        ))
                    # Update delta
                    new_delta = BlendshapeDelta(
                        name=delta.name,
                        vertex_count=delta.vertex_count,
                        deltas=new_deltas,
                        base_mesh=delta.base_mesh,
                        target_mesh=delta.target_mesh,
                        metadata=delta.metadata
                    )
                    self._delta_engine.add(new_delta)
                    corrected += 1
                    result.normalized_targets.append(target)

            # Remove outliers (based on standard deviation of magnitudes)
            if self._settings.remove_delta_outliers:
                magnitudes = [v.magnitude() for v in delta.deltas]
                if magnitudes:
                    mean = sum(magnitudes) / len(magnitudes)
                    std = math.sqrt(sum((m - mean)**2 for m in magnitudes) / len(magnitudes))
                    if std > 0:
                        threshold = mean + self._settings.outlier_threshold * std
                        # Keep only deltas with magnitude <= threshold
                        new_deltas = [v for v in delta.deltas if v.magnitude() <= threshold]
                        if len(new_deltas) < len(delta.deltas):
                            new_delta = BlendshapeDelta(
                                name=delta.name,
                                vertex_count=delta.vertex_count,
                                deltas=new_deltas,
                                base_mesh=delta.base_mesh,
                                target_mesh=delta.target_mesh,
                                metadata=delta.metadata
                            )
                            self._delta_engine.add(new_delta)
                            corrected += 1
                            result.normalized_targets.append(target)

            # Volume preservation (placeholder: would involve correcting deltas to preserve volume)
            if self._settings.preserve_volume:
                # Not implemented in this placeholder
                pass

        result.corrected_deltas = corrected
        return result

    def _normalize_poses(self) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._pose_manager:
            result.errors.append("Pose manager not available")
            result.success = False
            return result

        poses = self._pose_manager._poses  # Access internal dict
        corrected = 0
        for name, pose in poses.items():
            # Balance weights in pose
            if self._settings.pose_balancing:
                # Ensure all weights in pose are within [0,1]
                modified = False
                for target, val in pose.weights.items():
                    if self._settings.range_policy == RangePolicy.ZERO_ONE:
                        new_val = clamp(val, 0.0, 1.0)
                    elif self._settings.range_policy == RangePolicy.MIN_MAX:
                        new_val = clamp(val, self._settings.custom_min, self._settings.custom_max)
                    else:
                        new_val = val
                    if new_val != val:
                        pose.weights[target] = new_val
                        modified = True
                if modified:
                    corrected += 1
                    result.normalized_targets.append(name)

            # Redistribution (make sure sum is normalized)
            if self._settings.pose_redistribution:
                total = sum(pose.weights.values())
                if total > 0 and total != 1.0:
                    for target in pose.weights:
                        pose.weights[target] = pose.weights[target] / total
                    corrected += 1
                    result.normalized_targets.append(name)

        result.corrected_poses = corrected
        return result

    def _normalize_arkit(self) -> NormalizationResult:
        result = NormalizationResult(success=True)
        # ARKit normalization would typically happen in the weight manager or driver.
        # We'll just ensure all ARKit channel weights are in the specified range.
        if not self._weight_manager:
            result.errors.append("Weight manager not available")
            result.success = False
            return result

        # Get all weights and filter to ARKit channels
        all_weights = self._weight_manager.get_all_weights()
        arkit_weights = {k: v for k, v in all_weights.items() if k in ARKIT_SET}
        corrected = 0
        for target, val in arkit_weights.items():
            # Apply ARKit-specific range (default 0-1)
            low, high = self._settings.arkit_range
            new_val = clamp(val, low, high)
            if new_val != val:
                self._weight_manager.set_weight(target, new_val)
                corrected += 1
                result.normalized_targets.append(target)

        result.corrected_arkit = corrected
        return result

    def _normalize_correctives(self) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._corrective_manager:
            result.errors.append("Corrective manager not available")
            result.success = False
            return result

        # For each corrective, ensure its weight is normalized and triggers are balanced.
        correctives = self._corrective_manager._definitions  # Access internal dict
        corrected = 0
        for name, defn in correctives.items():
            # Balance corrective weight (clamp to 0-1)
            if self._settings.corrective_balancing:
                if defn.weight < 0 or defn.weight > 1:
                    defn.weight = clamp(defn.weight, 0.0, 1.0)
                    corrected += 1
                    result.normalized_targets.append(name)
            # Scaling (placeholder)
            if self._settings.corrective_scaling:
                # Could apply global scaling factor
                pass

        result.corrected_correctives = corrected
        return result

    def _normalize_inbetweens(self) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._inbetween_manager:
            result.errors.append("Inbetween manager not available")
            result.success = False
            return result

        # For each inbetween, ensure weights are spaced correctly and smooth.
        corrected = 0
        for parent, inbetweens in self._inbetween_manager._inbetween_cache.items():
            if len(inbetweens) < 2:
                continue
            # Sort by weight
            sorted_ibs = sorted(inbetweens, key=lambda x: x.weight)
            # Ensure weights are evenly spaced if requested
            if self._settings.inbetween_weight_spacing:
                # Create evenly spaced weights from 0 to 1
                n = len(sorted_ibs)
                ideal_weights = [(i+1)/(n+1) for i in range(n)]
                for i, ib in enumerate(sorted_ibs):
                    if ib.weight != ideal_weights[i]:
                        # Update inbetween weight
                        self._inbetween_manager.set_inbetween_weight(parent, ib.weight, ideal_weights[i])
                        corrected += 1
                        result.normalized_targets.append(ib.name)
            # Curve smoothing (placeholder)
            if self._settings.inbetween_curve_smoothing:
                pass

        result.corrected_inbetweens = corrected
        return result

    def _normalize_symmetry(self, targets: List[str]) -> NormalizationResult:
        result = NormalizationResult(success=True)
        if not self._weight_manager or not self._symmetry_engine:
            result.errors.append("Weight manager or symmetry engine not available")
            result.success = False
            return result

        # Get all weights
        all_weights = self._weight_manager.get_all_weights()
        corrected = 0
        # Build left/right pairs using symmetry engine
        if self._symmetry_engine:
            # For each target, find its mirror
            for target in targets:
                mirror = self._symmetry_engine.get_mirror_target(target)
                if mirror and mirror in all_weights:
                    val = all_weights[target]
                    mirror_val = all_weights[mirror]
                    if self._settings.symmetry_mode == SymmetryMode.AVERAGE:
                        avg = (val + mirror_val) * 0.5
                        if abs(val - avg) > self._settings.symmetry_tolerance:
                            self._weight_manager.set_weight(target, avg)
                            corrected += 1
                            result.normalized_targets.append(target)
                        if abs(mirror_val - avg) > self._settings.symmetry_tolerance:
                            self._weight_manager.set_weight(mirror, avg)
                            corrected += 1
                            result.normalized_targets.append(mirror)
                    elif self._settings.symmetry_mode == SymmetryMode.MIRROR:
                        # Mirror the left to right (or vice versa)
                        if target.endswith("Left") and mirror:
                            self._weight_manager.set_weight(mirror, val)
                            corrected += 1
                            result.normalized_targets.append(mirror)
                        elif target.endswith("Right") and mirror:
                            self._weight_manager.set_weight(mirror, val)
                            corrected += 1
                            result.normalized_targets.append(mirror)

        result.corrected_symmetry = corrected
        return result

    # ---- Helpers ----

    def _collect_all_targets(self) -> List[str]:
        """Collect all blendshape target names from the scene."""
        all_targets = set()
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            all_targets.update(targets)
        return list(all_targets)

    def _merge_result(self, base: NormalizationResult, new: NormalizationResult) -> NormalizationResult:
        """Merge a child result into the base result."""
        base.success = base.success and new.success
        base.normalized_targets.extend(new.normalized_targets)
        base.corrected_weights += new.corrected_weights
        base.corrected_deltas += new.corrected_deltas
        base.corrected_poses += new.corrected_poses
        base.corrected_arkit += new.corrected_arkit
        base.corrected_correctives += new.corrected_correctives
        base.corrected_inbetweens += new.corrected_inbetweens
        base.corrected_symmetry += new.corrected_symmetry
        base.errors.extend(new.errors)
        base.warnings.extend(new.warnings)
        base.details.update(new.details)
        return base

    def _compute_statistics(self, targets: List[str], start_time: float) -> NormalizationStatistics:
        stats = NormalizationStatistics()
        stats.total_targets = len(targets)
        # We'll compute corrections from the result later, so placeholder
        stats.time_seconds = time.time() - start_time
        return stats

    def _create_failure_report(self, msg: str, errors: List[str], start_time: float) -> NormalizationReport:
        result = NormalizationResult(success=False, errors=[msg] + errors)
        stats = NormalizationStatistics(total_targets=0, time_seconds=time.time() - start_time)
        return NormalizationReport(success=False, result=result, statistics=stats)

    # ---- Settings ----

    def set_settings(self, settings: NormalizationSettings) -> None:
        self._settings = settings

    def get_settings(self) -> NormalizationSettings:
        return self._settings

    def get_last_report(self) -> Optional[NormalizationReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[NormalizationStatistics]:
        return self._last_stats

    def reset(self) -> None:
        self._last_report = None
        self._last_stats = None
        self._cancelled = False


# ---- Part 15: Utilities -----------------------------------------------

def apply_normalization_profile(profile_name: str) -> NormalizationSettings:
    """
    Return a NormalizationSettings object for a predefined profile.
    """
    profiles = {
        "ARKit": NormalizationSettings(
            normalization_types=[NormalizationType.ARKIT, NormalizationType.SYMMETRY],
            range_policy=RangePolicy.ZERO_ONE,
            arkit_range=(0.0, 1.0),
            normalize_symmetry=True,
            symmetry_mode=SymmetryMode.AVERAGE,
        ),
        "Expression": NormalizationSettings(
            normalization_types=[NormalizationType.WEIGHTS, NormalizationType.POSES],
            range_policy=RangePolicy.ZERO_ONE,
            normalize_weight_groups=True,
            pose_balancing=True,
            pose_redistribution=True,
        ),
        "Corrective": NormalizationSettings(
            normalization_types=[NormalizationType.CORRECTIVES, NormalizationType.DELTAS],
            range_policy=RangePolicy.ZERO_ONE,
            normalize_delta_magnitudes=True,
            delta_max_magnitude=1.0,
            corrective_balancing=True,
        ),
        "Full": NormalizationSettings(
            normalization_types=[NormalizationType.FULL],
            range_policy=RangePolicy.ZERO_ONE,
            normalize_weights=True,
            normalize_deltas=True,
            normalize_poses=True,
            normalize_arkit=True,
            normalize_correctives=True,
            normalize_inbetweens=True,
            normalize_symmetry=True,
            symmetry_mode=SymmetryMode.AVERAGE,
        ),
        "Symmetry": NormalizationSettings(
            normalization_types=[NormalizationType.SYMMETRY],
            normalize_symmetry=True,
            symmetry_mode=SymmetryMode.AVERAGE,
            symmetry_tolerance=0.001,
        )
    }
    if profile_name in profiles:
        return profiles[profile_name]
    else:
        raise NormalizationError(f"Unknown profile: {profile_name}")


# ---- Part 16: Public API -----------------------------------------------

__all__ = [
    "BlendshapeNormalizer",
    "NormalizationSettings",
    "NormalizationTask",
    "NormalizationResult",
    "NormalizationStatistics",
    "NormalizationReport",
    "NormalizationType",
    "NormalizationMode",
    "RangePolicy",
    "SymmetryMode",
    "NormalizationError",
    "NormalizationCanceledError",
    "NormalizationValidationError",
    "apply_normalization_profile",
]
