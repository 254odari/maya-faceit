"""
blendshapes/blendshape_mirror.py

Blendshape Mirroring & Symmetry Engine for Maya.

This module provides a comprehensive system for mirroring blendshape targets,
vertex deltas, weights, poses, correctives, inbetweens, and ARKit expressions
across a configurable symmetry plane while preserving topology, naming
conventions, and deformation quality.

Responsibilities:
- Mirror blendshape targets, deltas, weights, poses, correctives, inbetweens.
- Detect symmetry and build vertex correspondence maps.
- Support left-to-right, right-to-left, and bidirectional mirroring.
- Convert naming conventions (Left<->Right, _L<->_R, etc.).
- Validate mirrored results and preserve centerline vertices.
- Provide batch mirroring, diagnostics, and statistics.

Dependencies:
- blendshape_delta.py: Delta operations and storage.
- blendshape_weights.py: Weight management.
- blendshape_pose.py: Pose definitions and management.
- blendshape_correctives.py: Corrective management.
- blendshape_inbetweens.py: Inbetween management.
- blendshape_validator.py: Validation.
- blendshape_utils.py: Shared utilities.
- blendshape_manager.py: Consumer of mirror services.
- symmetry.py: Symmetry detection and maps (if available).
- arkit52.py: ARKit left/right pairs.

The module uses Maya's Python API and may optionally leverage NumPy.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import time
import uuid
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
    from .blendshape_delta import BlendshapeDeltaEngine, BlendshapeDelta, VertexDelta
except ImportError:
    BlendshapeDeltaEngine = None
    BlendshapeDelta = None
    VertexDelta = None

try:
    from .blendshape_weights import BlendshapeWeightManager, WeightSet
except ImportError:
    BlendshapeWeightManager = None
    WeightSet = None

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
    from .blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None

try:
    from ..core.symmetry import SymmetryEngine, SymmetryMap
except ImportError:
    SymmetryEngine = None
    SymmetryMap = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}


# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class MirrorError(Exception):
    """Base exception for mirror operations."""
    pass

class MirrorCanceledError(MirrorError):
    """Raised when mirroring is canceled."""
    pass

class MirrorValidationError(MirrorError):
    """Raised when validation fails."""
    pass

class MirrorMappingError(MirrorError):
    """Raised when vertex mapping fails."""
    pass

class MirrorNotFoundError(MirrorError):
    """Raised when a target is not found."""
    pass


# ---- Part 2: Constants & Enumerations --------------------------------

class MirrorDirection(Enum):
    """Direction of mirroring."""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    BOTH = "both"
    CENTER_ONLY = "center_only"
    CUSTOM = "custom"


class MirrorPlane(Enum):
    """Symmetry plane for mirroring."""
    YZ = "yz"          # X is mirrored
    XZ = "xz"          # Y is mirrored
    XY = "xy"          # Z is mirrored
    CUSTOM = "custom"


class SymmetryMode(Enum):
    """How symmetry is determined."""
    TOPOLOGY = "topology"
    WORLD_SPACE = "world_space"
    OBJECT_SPACE = "object_space"
    UV_SPACE = "uv_space"
    CUSTOM = "custom"


class NamingConvention(Enum):
    """Naming convention for left/right pairs."""
    LEFT_RIGHT = "Left_Right"
    _L__R = "_L__R"
    Left_Right = "Left_Right"
    L_R = "L_R"
    CUSTOM = "custom"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class MirrorPair:
    """A pair of left/right target names."""
    left: str
    right: str

    def __post_init__(self):
        self.left = sanitize_name(self.left)
        self.right = sanitize_name(self.right)

    def get_mirror(self, name: str) -> Optional[str]:
        if name == self.left:
            return self.right
        elif name == self.right:
            return self.left
        return None


@dataclass
class VertexMap:
    """A mapping between source and target vertex indices."""
    source_to_target: Dict[int, int]  # source index -> target index
    target_to_source: Dict[int, int]  # target index -> source index
    center_vertices: List[int]        # vertices on the symmetry plane
    plane: MirrorPlane = MirrorPlane.YZ


@dataclass
class MirrorSettings:
    """Settings for mirroring operations."""
    # General
    direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT
    plane: MirrorPlane = MirrorPlane.YZ
    symmetry_mode: SymmetryMode = SymmetryMode.TOPOLOGY
    naming_convention: NamingConvention = NamingConvention.LEFT_RIGHT
    custom_name_func: Optional[Callable[[str], str]] = None

    # Delta mirroring
    mirror_deltas: bool = True
    flip_x: bool = True
    preserve_tangents: bool = False

    # Weight mirroring
    mirror_weights: bool = True
    average_weights: bool = False
    center_weights: bool = True

    # Target mirroring
    create_missing_targets: bool = True
    overwrite_existing: bool = False

    # Pose mirroring
    mirror_poses: bool = True
    mirror_pose_libraries: bool = True

    # Corrective mirroring
    mirror_correctives: bool = True
    remap_corrective_triggers: bool = True

    # Inbetween mirroring
    mirror_inbetweens: bool = True
    mirror_inbetween_curves: bool = True

    # ARKit mirroring
    mirror_arkit: bool = True
    use_arkit_pairs: bool = True

    # Topology
    topology_tolerance: float = 0.001
    centerline_tolerance: float = 0.01

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
class MirrorResult:
    """Result of a mirror operation."""
    success: bool
    mirrored_targets: List[str] = field(default_factory=list)
    skipped_targets: List[str] = field(default_factory=list)
    vertex_pairs_mapped: int = 0
    delta_mirrored: int = 0
    weights_mirrored: int = 0
    poses_mirrored: int = 0
    correctives_mirrored: int = 0
    inbetweens_mirrored: int = 0
    arkit_mirrored: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass
class MirrorStatistics:
    """Statistics for mirror operations."""
    total_targets: int = 0
    mirrored_targets: int = 0
    skipped_targets: int = 0
    vertex_pairs: int = 0
    center_vertices: int = 0
    deltas_mirrored: int = 0
    weights_mirrored: int = 0
    poses_mirrored: int = 0
    correctives_mirrored: int = 0
    inbetweens_mirrored: int = 0
    arkit_mirrored: int = 0
    time_seconds: float = 0.0


@dataclass
class MirrorReport:
    """Full report of mirror operation."""
    success: bool
    result: MirrorResult
    statistics: MirrorStatistics
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


# ---- Part 4: Mirror Manager ------------------------------------------

class BlendshapeMirrorManager:
    """
    Main controller for all blendshape mirroring and symmetry operations.
    """
    def __init__(self):
        self._weight_manager = BlendshapeWeightManager() if BlendshapeWeightManager else None
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._pose_manager = BlendshapePoseManager() if BlendshapePoseManager else None
        self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._symmetry_engine = SymmetryEngine() if SymmetryEngine else None

        self._settings = MirrorSettings()
        self._last_report: Optional[MirrorReport] = None
        self._last_stats: Optional[MirrorStatistics] = None
        self._cancelled = False

        # Cache for vertex maps
        self._vertex_map_cache: Dict[str, VertexMap] = {}

        # Default mirror pairs based on ARKit left/right mapping
        self._default_pairs = self._build_default_pairs()

    # ---- Main Mirroring API ----

    def mirror(
        self,
        targets: Optional[List[str]] = None,
        settings: Optional[MirrorSettings] = None,
    ) -> MirrorReport:
        """
        Mirror blendshapes according to the provided settings.
        If targets is None, mirrors all available blendshapes.
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

        # Prepare result and stats
        result = MirrorResult(success=True)
        stats = MirrorStatistics()
        stats.total_targets = len(targets)

        # Determine which targets to mirror and the direction mapping
        mirror_pairs = self._build_mirror_pairs(targets, self._settings)

        # For each pair, mirror the appropriate target
        for left, right in mirror_pairs.items():
            if self._cancelled:
                raise MirrorCanceledError("Mirroring canceled")
            # Mirror from left to right or right to left based on direction
            if self._settings.direction == MirrorDirection.LEFT_TO_RIGHT:
                source = left
                target = right
            elif self._settings.direction == MirrorDirection.RIGHT_TO_LEFT:
                source = right
                target = left
            elif self._settings.direction == MirrorDirection.BOTH:
                # Mirror both ways
                self._mirror_single(left, right, result, stats)
                self._mirror_single(right, left, result, stats)
                continue
            else:
                self._mirror_single(left, right, result, stats)

        # Validate after
        if self._settings.validate_after and self._validator:
            val_report = self._validator.validate(targets, level=self._settings.validation_level)
            if not val_report.is_valid:
                result.errors.extend(val_report.errors)
                result.success = False

        # Compute final statistics
        stats.time_seconds = time.time() - start_time
        stats.mirrored_targets = len(result.mirrored_targets)
        stats.skipped_targets = len(result.skipped_targets)

        report = MirrorReport(
            success=result.success,
            result=result,
            statistics=stats,
            validation_errors=[],
            validation_warnings=[]
        )
        self._last_report = report
        self._last_stats = stats
        return report

    def mirror_selected(self, settings: Optional[MirrorSettings] = None) -> MirrorReport:
        """Mirror the currently selected blendshape targets."""
        selected_targets = self._collect_selected_targets()
        return self.mirror(selected_targets, settings)

    def mirror_all(self, settings: Optional[MirrorSettings] = None) -> MirrorReport:
        """Mirror all available blendshape targets."""
        return self.mirror(None, settings)

    def mirror_pose(self, pose_name: str, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> MirrorResult:
        """
        Mirror a specific facial pose.
        """
        if not self._pose_manager:
            return MirrorResult(success=False, errors=["Pose manager not available"])
        pose = self._pose_manager.get_pose(pose_name)
        if not pose:
            return MirrorResult(success=False, errors=[f"Pose '{pose_name}' not found"])

        # Mirror the pose's weights
        mirrored_weights = self._mirror_weight_dict(pose.weights, direction)
        new_name = self._generate_mirror_name(pose_name)
        new_pose = PoseDefinition(
            name=new_name,
            weights=mirrored_weights,
            pose_type=pose.pose_type,
            metadata=pose.metadata,
            tags=pose.tags,
            category=pose.category
        )
        self._pose_manager._poses[new_name] = new_pose
        result = MirrorResult(success=True)
        result.mirrored_targets.append(new_name)
        result.poses_mirrored = 1
        return result

    def mirror_weights(self, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> MirrorResult:
        """Mirror blendshape weights (swap left/right values)."""
        if not self._weight_manager:
            return MirrorResult(success=False, errors=["Weight manager not available"])
        weights = self._weight_manager.get_all_weights()
        mirrored_weights = self._mirror_weight_dict(weights, direction)
        corrected = 0
        for target, val in mirrored_weights.items():
            if target in weights and abs(val - weights[target]) > 1e-6:
                self._weight_manager.set_weight(target, val)
                corrected += 1
        result = MirrorResult(success=True)
        result.weights_mirrored = corrected
        return result

    def mirror_delta(self, target: str, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> MirrorResult:
        """
        Mirror a specific blendshape delta.
        """
        if not self._delta_engine:
            return MirrorResult(success=False, errors=["Delta engine not available"])
        delta = self._delta_engine.get(target)
        if not delta:
            return MirrorResult(success=False, errors=[f"Delta for target '{target}' not found"])
        # Get vertex map for the base mesh of this delta
        base_mesh = delta.base_mesh
        if not base_mesh:
            return MirrorResult(success=False, errors=["Base mesh not available for delta"])
        vertex_map = self._get_vertex_map(base_mesh)
        if not vertex_map or not vertex_map.source_to_target:
            return MirrorResult(success=False, errors=["Failed to get vertex map"])
        # Mirror the delta vertices
        mirrored_deltas = []
        for v in delta.deltas:
            if v.index in vertex_map.source_to_target:
                target_idx = vertex_map.source_to_target[v.index]
                # Flip the appropriate axis based on plane
                dx, dy, dz = v.offset
                if self._settings.plane == MirrorPlane.YZ:
                    mirrored_vertex = VertexDelta(
                        index=target_idx,
                        offset=(-dx, dy, dz)
                    )
                elif self._settings.plane == MirrorPlane.XZ:
                    mirrored_vertex = VertexDelta(
                        index=target_idx,
                        offset=(dx, -dy, dz)
                    )
                elif self._settings.plane == MirrorPlane.XY:
                    mirrored_vertex = VertexDelta(
                        index=target_idx,
                        offset=(dx, dy, -dz)
                    )
                else:
                    mirrored_vertex = VertexDelta(
                        index=target_idx,
                        offset=(-dx, dy, dz)  # default
                    )
                mirrored_deltas.append(mirrored_vertex)
        if not mirrored_deltas:
            return MirrorResult(success=False, errors=["No vertices mirrored"])
        # Create a new delta with mirrored vertices
        new_name = self._generate_mirror_name(target)
        new_delta = BlendshapeDelta(
            name=new_name,
            vertex_count=delta.vertex_count,
            deltas=mirrored_deltas,
            base_mesh=delta.base_mesh,
            target_mesh=delta.target_mesh,
            metadata={"mirrored_from": target, "direction": direction.value}
        )
        self._delta_engine.add(new_delta)
        result = MirrorResult(success=True)
        result.mirrored_targets.append(new_name)
        result.delta_mirrored = len(mirrored_deltas)
        return result

    def cancel(self) -> None:
        """Cancel the current mirror operation."""
        self._cancelled = True

    # ---- Internal Mirroring Methods ----

    def _mirror_single(self, source: str, target: str, result: MirrorResult, stats: MirrorStatistics) -> None:
        """Mirror a single source target to a target target."""
        if not source or not target:
            result.skipped_targets.append(source or target)
            return

        # Mirror delta if source exists in delta engine
        if self._settings.mirror_deltas and self._delta_engine:
            delta_result = self.mirror_delta(source)
            if delta_result.success:
                result.delta_mirrored += delta_result.delta_mirrored
                result.mirrored_targets.extend(delta_result.mirrored_targets)
            else:
                result.errors.extend(delta_result.errors)

        # Mirror weight if target exists in weight manager
        if self._settings.mirror_weights and self._weight_manager:
            try:
                source_weight = self._weight_manager.get_weight(source)
                target_weight = self._weight_manager.get_weight(target)
                if self._settings.average_weights:
                    new_val = (source_weight + target_weight) * 0.5
                else:
                    new_val = source_weight
                self._weight_manager.set_weight(target, new_val)
                result.weights_mirrored += 1
                result.mirrored_targets.append(target)
            except Exception as e:
                result.errors.append(f"Failed to mirror weight: {e}")

        # Mirror pose if source exists in pose manager
        if self._settings.mirror_poses and self._pose_manager:
            pose_result = self.mirror_pose(source)
            if pose_result.success:
                result.poses_mirrored += pose_result.poses_mirrored
                result.mirrored_targets.extend(pose_result.mirrored_targets)
            else:
                result.errors.extend(pose_result.errors)

        # Mirror corrective if source exists in corrective manager
        if self._settings.mirror_correctives and self._corrective_manager:
            # Placeholder: would mirror corrective definitions
            pass

        # Mirror inbetween if source exists in inbetween manager
        if self._settings.mirror_inbetweens and self._inbetween_manager:
            # Placeholder: would mirror inbetween targets
            pass

        # Mirror ARKit if source is an ARKit target
        if self._settings.mirror_arkit and source in ARKIT_SET:
            # Mirror ARKit channel via default pairs
            for left, right in self._default_pairs.items():
                if source == left and target == right:
                    if self._weight_manager:
                        try:
                            lval = self._weight_manager.get_weight(left)
                            self._weight_manager.set_weight(right, lval)
                            result.arkit_mirrored += 1
                            result.mirrored_targets.append(right)
                        except:
                            pass
                    break

    def _mirror_weight_dict(self, weights: Dict[str, float], direction: MirrorDirection) -> Dict[str, float]:
        """Mirror a weight dictionary: swap left/right values."""
        mirrored = {}
        pairs = self._build_mirror_pairs(list(weights.keys()), self._settings)
        for left, right in pairs.items():
            if direction in (MirrorDirection.LEFT_TO_RIGHT, MirrorDirection.BOTH):
                if left in weights:
                    mirrored[right] = weights[left]
                else:
                    mirrored[right] = 0.0
            if direction in (MirrorDirection.RIGHT_TO_LEFT, MirrorDirection.BOTH):
                if right in weights:
                    mirrored[left] = weights[right]
                else:
                    mirrored[left] = 0.0
        # Handle center or unpaired targets
        for target in weights:
            if target not in mirrored:
                # Keep as is or set to center weight
                mirrored[target] = weights[target]
                if self._settings.center_weights:
                    # If this is a center target (by naming convention), keep its value
                    pass
        return mirrored

    def _build_mirror_pairs(self, targets: List[str], settings: MirrorSettings) -> Dict[str, str]:
        """Build a dictionary of left->right mirror pairs based on available targets."""
        pairs = {}
        # Use ARKit default pairs if requested
        if settings.use_arkit_pairs:
            for left, right in self._default_pairs.items():
                if left in targets and right in targets:
                    pairs[left] = right
        # Also try to detect pairs by naming convention
        for t in targets:
            mirror = self._find_mirror_by_name(t)
            if mirror and mirror in targets and mirror != t:
                if t not in pairs and mirror not in pairs:
                    # Determine which is left and which is right
                    if t.endswith('Left') or t.endswith('L') or '_L' in t:
                        pairs[t] = mirror
                    elif mirror.endswith('Left') or mirror.endswith('L') or '_L' in mirror:
                        pairs[mirror] = t
                    else:
                        # Default: if t < mirror by lexicographic, left is t
                        if t < mirror:
                            pairs[t] = mirror
                        else:
                            pairs[mirror] = t
        return pairs

    def _find_mirror_by_name(self, name: str) -> Optional[str]:
        """Find the mirror name by swapping left/right indicators."""
        patterns = [
            ('Left', 'Right'),
            ('Right', 'Left'),
            ('_L', '_R'),
            ('_R', '_L'),
            ('L_', 'R_'),
            ('R_', 'L_'),
            ('Left_', 'Right_'),
            ('Right_', 'Left_'),
            ('_left', '_right'),
            ('_right', '_left'),
        ]
        for a, b in patterns:
            if a in name:
                return name.replace(a, b)
            if b in name:
                return name.replace(b, a)
        return None

    def _build_default_pairs(self) -> Dict[str, str]:
        """Build default left/right pairs from ARKit or common facial targets."""
        pairs = {}
        # Use LEFT_RIGHT_PAIRS from arkit52 if available
        if LEFT_RIGHT_PAIRS:
            # LEFT_RIGHT_PAIRS is a dict with both directions; we need to build a consistent mapping.
            seen = set()
            for k, v in LEFT_RIGHT_PAIRS.items():
                if k in seen or v in seen:
                    continue
                if 'Left' in k or '_L' in k:
                    pairs[k] = v
                elif 'Left' in v or '_L' in v:
                    pairs[v] = k
                else:
                    if k < v:
                        pairs[k] = v
                    else:
                        pairs[v] = k
                seen.add(k)
                seen.add(v)
        # Add common facial pairs not in ARKit
        common_pairs = [
            ('mouthSmileLeft', 'mouthSmileRight'),
            ('mouthFrownLeft', 'mouthFrownRight'),
            ('mouthDimpleLeft', 'mouthDimpleRight'),
            ('mouthStretchLeft', 'mouthStretchRight'),
            ('mouthPressLeft', 'mouthPressRight'),
            ('mouthUpperUpLeft', 'mouthUpperUpRight'),
            ('mouthLowerDownLeft', 'mouthLowerDownRight'),
            ('eyeBlinkLeft', 'eyeBlinkRight'),
            ('eyeSquintLeft', 'eyeSquintRight'),
            ('eyeWideLeft', 'eyeWideRight'),
            ('browDownLeft', 'browDownRight'),
            ('browOuterUpLeft', 'browOuterUpRight'),
            ('cheekSquintLeft', 'cheekSquintRight'),
            ('noseSneerLeft', 'noseSneerRight'),
        ]
        for left, right in common_pairs:
            if left not in pairs and right not in pairs:
                pairs[left] = right
        return pairs

    def _generate_mirror_name(self, name: str) -> str:
        """Generate a mirror name based on naming convention."""
        if self._settings.naming_convention == NamingConvention.LEFT_RIGHT:
            if 'Left' in name:
                return name.replace('Left', 'Right')
            elif 'Right' in name:
                return name.replace('Right', 'Left')
            else:
                return name + "_mirrored"
        elif self._settings.naming_convention == NamingConvention._L__R:
            if '_L' in name:
                return name.replace('_L', '_R')
            elif '_R' in name:
                return name.replace('_R', '_L')
            else:
                return name + "_mirrored"
        elif self._settings.naming_convention == NamingConvention.L_R:
            if '.L' in name:
                return name.replace('.L', '.R')
            elif '.R' in name:
                return name.replace('.R', '.L')
            else:
                return name + "_mirrored"
        elif self._settings.naming_convention == NamingConvention.Left_Right:
            if 'Left_' in name:
                return name.replace('Left_', 'Right_')
            elif 'Right_' in name:
                return name.replace('Right_', 'Left_')
            else:
                return name + "_mirrored"
        elif self._settings.naming_convention == NamingConvention.CUSTOM and self._settings.custom_name_func:
            return self._settings.custom_name_func(name)
        else:
            return name + "_mirrored"

    # ---- Vertex Mapping ----

    def _get_vertex_map(self, mesh: str) -> Optional[VertexMap]:
        """Get a vertex map for a mesh (cached)."""
        if mesh in self._vertex_map_cache:
            return self._vertex_map_cache[mesh]

        # If symmetry engine available, use it
        if self._symmetry_engine:
            sym_map = self._symmetry_engine.get_symmetry_map(mesh)
            if sym_map:
                # Convert to VertexMap format
                source_to_target = {}
                target_to_source = {}
                center = []
                for k, v in sym_map.items():
                    if k == v:
                        center.append(k)
                    else:
                        source_to_target[k] = v
                        target_to_source[v] = k
                vertex_map = VertexMap(
                    source_to_target=source_to_target,
                    target_to_source=target_to_source,
                    center_vertices=center,
                    plane=self._settings.plane
                )
                self._vertex_map_cache[mesh] = vertex_map
                return vertex_map

        # Otherwise, build map by world position
        positions = get_mesh_vertex_positions(mesh)
        if not positions:
            raise MirrorMappingError(f"Failed to get vertex positions for mesh '{mesh}'")
        map_dict = {}
        used = set()
        for i, pos in enumerate(positions):
            if i in used:
                continue
            # Find mirror position based on plane
            if self._settings.plane == MirrorPlane.YZ:
                mirror_pos = (-pos[0], pos[1], pos[2])
            elif self._settings.plane == MirrorPlane.XZ:
                mirror_pos = (pos[0], -pos[1], pos[2])
            elif self._settings.plane == MirrorPlane.XY:
                mirror_pos = (pos[0], pos[1], -pos[2])
            else:
                mirror_pos = (-pos[0], pos[1], pos[2])  # default

            # Find nearest vertex to mirror_pos
            nearest_idx = -1
            min_dist = float('inf')
            for j, pos2 in enumerate(positions):
                if j == i or j in used:
                    continue
                dist = distance_point_to_point(mirror_pos, pos2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = j
            if nearest_idx != -1 and min_dist < self._settings.topology_tolerance:
                map_dict[i] = nearest_idx
                map_dict[nearest_idx] = i
                used.add(i)
                used.add(nearest_idx)
            else:
                # On centerline, map to itself (no offset)
                if self._settings.plane == MirrorPlane.YZ and abs(pos[0]) < self._settings.centerline_tolerance:
                    map_dict[i] = i
                    used.add(i)
                elif self._settings.plane == MirrorPlane.XZ and abs(pos[1]) < self._settings.centerline_tolerance:
                    map_dict[i] = i
                    used.add(i)
                elif self._settings.plane == MirrorPlane.XY and abs(pos[2]) < self._settings.centerline_tolerance:
                    map_dict[i] = i
                    used.add(i)

        # Build VertexMap
        source_to_target = {}
        target_to_source = {}
        center = []
        for k, v in map_dict.items():
            if k == v:
                if k not in center:
                    center.append(k)
            else:
                source_to_target[k] = v
                target_to_source[v] = k
        vertex_map = VertexMap(
            source_to_target=source_to_target,
            target_to_source=target_to_source,
            center_vertices=center,
            plane=self._settings.plane
        )
        self._vertex_map_cache[mesh] = vertex_map
        return vertex_map

    # ---- Collection Helpers ----

    def _collect_all_targets(self) -> List[str]:
        """Collect all blendshape target names from the scene."""
        all_targets = set()
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            all_targets.update(targets)
        return list(all_targets)

    def _collect_selected_targets(self) -> List[str]:
        """Collect targets from selected nodes."""
        selected_nodes = cmds.ls(selection=True, type='transform') or []
        targets = set()
        for node in selected_nodes:
            bs_nodes = cmds.listConnections(node, type='blendShape') or []
            for bs in bs_nodes:
                t = cmds.blendShape(bs, q=True, target=True) or []
                targets.update(t)
        return list(targets)

    # ---- Validation ----

    def _create_failure_report(self, msg: str, errors: List[str], start_time: float) -> MirrorReport:
        result = MirrorResult(success=False, errors=[msg] + errors)
        stats = MirrorStatistics(total_targets=0, time_seconds=time.time() - start_time)
        return MirrorReport(success=False, result=result, statistics=stats)

    # ---- Settings ----

    def set_settings(self, settings: MirrorSettings) -> None:
        self._settings = settings

    def get_settings(self) -> MirrorSettings:
        return self._settings

    def get_last_report(self) -> Optional[MirrorReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[MirrorStatistics]:
        return self._last_stats

    def reset(self) -> None:
        self._last_report = None
        self._last_stats = None
        self._cancelled = False


# ---- Part 18: Utilities -----------------------------------------------

def detect_mirror_pairs(targets: List[str]) -> Dict[str, str]:
    """
    Utility to detect left/right pairs from a list of target names.
    Returns dict of left->right pairs.
    """
    pairs = {}
    for t in targets:
        # Try common patterns
        if 'Left' in t:
            r = t.replace('Left', 'Right')
            if r in targets:
                pairs[t] = r
        elif 'Right' in t:
            l = t.replace('Right', 'Left')
            if l in targets:
                pairs[l] = t
        elif '_L' in t:
            r = t.replace('_L', '_R')
            if r in targets:
                pairs[t] = r
        elif '_R' in t:
            l = t.replace('_R', '_L')
            if l in targets:
                pairs[l] = t
    return pairs


def build_vertex_map_by_position(
    mesh: str,
    plane: MirrorPlane = MirrorPlane.YZ,
    tolerance: float = 0.001,
    center_tolerance: float = 0.01
) -> VertexMap:
    """
    Build a vertex map by comparing world positions.
    """
    positions = get_mesh_vertex_positions(mesh)
    if not positions:
        return VertexMap({}, {}, [], plane)
    map_dict = {}
    used = set()
    for i, pos in enumerate(positions):
        if i in used:
            continue
        # Determine mirror position
        if plane == MirrorPlane.YZ:
            mirror_pos = (-pos[0], pos[1], pos[2])
        elif plane == MirrorPlane.XZ:
            mirror_pos = (pos[0], -pos[1], pos[2])
        elif plane == MirrorPlane.XY:
            mirror_pos = (pos[0], pos[1], -pos[2])
        else:
            mirror_pos = (-pos[0], pos[1], pos[2])
        # Find nearest vertex
        nearest_idx = -1
        min_dist = float('inf')
        for j, pos2 in enumerate(positions):
            if j == i or j in used:
                continue
            dist = distance_point_to_point(mirror_pos, pos2)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = j
        if nearest_idx != -1 and min_dist < tolerance:
            map_dict[i] = nearest_idx
            map_dict[nearest_idx] = i
            used.add(i)
            used.add(nearest_idx)
        else:
            # On centerline, map to itself if close to center
            if plane == MirrorPlane.YZ and abs(pos[0]) < center_tolerance:
                map_dict[i] = i
                used.add(i)
            elif plane == MirrorPlane.XZ and abs(pos[1]) < center_tolerance:
                map_dict[i] = i
                used.add(i)
            elif plane == MirrorPlane.XY and abs(pos[2]) < center_tolerance:
                map_dict[i] = i
                used.add(i)
    source_to_target = {}
    target_to_source = {}
    center = []
    for k, v in map_dict.items():
        if k == v:
            if k not in center:
                center.append(k)
        else:
            source_to_target[k] = v
            target_to_source[v] = k
    return VertexMap(
        source_to_target=source_to_target,
        target_to_source=target_to_source,
        center_vertices=center,
        plane=plane
    )


# ---- Part 19: Public API -----------------------------------------------

__all__ = [
    "BlendshapeMirrorManager",
    "MirrorSettings",
    "MirrorPair",
    "VertexMap",
    "MirrorResult",
    "MirrorStatistics",
    "MirrorReport",
    "MirrorDirection",
    "MirrorPlane",
    "SymmetryMode",
    "NamingConvention",
    "MirrorError",
    "MirrorCanceledError",
    "MirrorValidationError",
    "MirrorMappingError",
    "MirrorNotFoundError",
    "detect_mirror_pairs",
    "build_vertex_map_by_position",
]