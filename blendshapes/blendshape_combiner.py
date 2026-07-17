"""
blendshapes/blendshape_combiner.py

Blendshape Composition Engine for Maya.

This module creates new blendshapes by mathematically combining existing
blendshape targets. It reduces the need for manually sculpting every
expression by generating complex shapes from simpler components.

Responsibilities:
- Combine multiple blendshape deltas (additive, weighted, average, etc.).
- Blend weights from multiple sources.
- Generate corrective shapes for combined expressions.
- Create pose-space deformation (PSD) combinations.
- Compose ARKit expressions from individual shapes.
- Validate inputs and results.
- Batch process multiple combinations.
- Provide statistics and reports.

Dependencies:
- blendshape_delta.py: vertex delta operations.
- blendshape_creator.py: create new blendshape targets.
- blendshape_weights.py: weight management utilities.
- blendshape_validator.py: validation of meshes and deltas.
- blendshape_utils.py: shared utilities.
- blendshape_pose.py: pose-space combination (optional).
- blendshape_transfer.py: transfer combined targets to other meshes.
- blendshape_library.py: predefined combinations.
- blendshapes/arkit/: ARKit-specific constants and templates.

The module uses Maya's Python API and may optionally leverage NumPy
for performance in production environments.
"""

from __future__ import annotations

import copy
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Maya imports
try:
    import maya.cmds as cmds  # type: ignore
    import maya.mel as mel  # type: ignore
    from pymel.core import PyNode, selected, ls, exists, currentTime  # type: ignore
    import pymel.core as pm  # type: ignore
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

# Local imports (with fallbacks for testing)
try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions,
        get_vertex_position, set_vertex_position, clamp, lerp,
        normalize_vector, distance_point_to_point, get_mesh_center,
        sanitize_name, generate_unique_name, get_blendshape_targets,
        get_blendshape_weight, set_blendshape_weight, Timer, ProgressTracker,
        dict_to_json, json_to_dict, hash_data, checksum_mesh,
        get_active_weights, scale_weights, blend_weights, normalize_weights,
        apply_weight_bias, apply_weight_mask, mirror_weights
    )
except ImportError:
    # Dummy implementations
    def get_shape_node(x): return x
    def get_mesh_vertex_count(x): return 0
    def get_mesh_vertex_positions(x): return []
    def get_vertex_position(x, y): return (0, 0, 0)
    def set_vertex_position(x, y, z): pass
    def clamp(x, a, b): return max(a, min(b, x))
    def lerp(a, b, t): return a + (b - a) * t
    def normalize_vector(v): return (0, 0, 0)
    def distance_point_to_point(a, b): return 0.0
    def get_mesh_center(x): return (0, 0, 0)
    def sanitize_name(n): return n
    def generate_unique_name(n, existing): return n
    def get_blendshape_targets(n): return []
    def get_blendshape_weight(n, t): return 0.0
    def set_blendshape_weight(n, t, v): pass
    class Timer: pass
    class ProgressTracker: pass
    def dict_to_json(d): return ""
    def json_to_dict(s): return {}
    def hash_data(d): return ""
    def checksum_mesh(m): return ""
    def get_active_weights(w, th): return {}
    def scale_weights(w, f): return {}
    def blend_weights(a, b, t): return {}
    def normalize_weights(w): return {}
    def apply_weight_bias(w, b): return {}
    def apply_weight_mask(w, m): return {}
    def mirror_weights(w, m): return {}

try:
    from .blendshape_delta import (
        BlendshapeDeltaEngine, BlendshapeDelta, VertexDelta,
        DeltaFormat, CompressionMode, MirrorMode, BlendMode as DeltaBlendMode
    )
except ImportError:
    BlendshapeDeltaEngine = None
    BlendshapeDelta = None
    VertexDelta = None
    DeltaFormat = None
    CompressionMode = None
    MirrorMode = None
    DeltaBlendMode = None

try:
    from .blendshape_creator import (
        BlendShapeCreator, BlendShapeTarget, TargetType, CreationMode,
        WeightMode, NamingMode, CreationResult, CreationStatistics
    )
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None
    CreationMode = None
    WeightMode = None
    NamingMode = None
    CreationResult = None
    CreationStatistics = None

try:
    from .blendshape_weights import WeightManager
except ImportError:
    WeightManager = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel, ValidationReport
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None
    ValidationReport = None

try:
    from .blendshape_pose import PoseManager
except ImportError:
    PoseManager = None

try:
    from .blendshape_transfer import BlendshapeTransferEngine
except ImportError:
    BlendshapeTransferEngine = None

try:
    from .blendshape_library import BlendShapeLibrary
except ImportError:
    BlendShapeLibrary = None

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
class CombinationError(Exception):
    """Base exception for combination operations."""
    pass

class InvalidCombinationError(CombinationError):
    """Raised when a combination definition is invalid."""
    pass

class CombinationNotFoundError(CombinationError):
    """Raised when a referenced source delta or target is not found."""
    pass

class CombinationValidationError(CombinationError):
    """Raised when validation fails."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class CombinationMode(Enum):
    """How to combine deltas."""
    ADD = "add"                # Sum of all weighted deltas
    SUBTRACT = "subtract"      # First minus the rest
    AVERAGE = "average"        # Weighted average
    MAXIMUM = "max"            # Per-vertex maximum value
    MINIMUM = "min"            # Per-vertex minimum value
    MULTIPLY = "multiply"      # Per-vertex product (scaled)
    CUSTOM = "custom"          # User-defined operation


class BlendMode(Enum):
    """How to blend weight contributions."""
    LINEAR = "linear"          # Direct weighted sum
    NORMALIZED = "normalized"  # Normalize to sum=1
    WEIGHTED = "weighted"      # Weighted by influence
    PSD = "psd"                # Pose-space deformation blend


class CorrectiveMode(Enum):
    """Mode for generating corrective shapes."""
    NONE = "none"
    AUTOMATIC = "automatic"    # Automatically detect and generate
    MANUAL = "manual"          # User-defined corrective
    POSE_SPACE = "pose_space"  # Use pose-space blendshapes


class ConflictPolicy(Enum):
    """How to handle conflicts (e.g., duplicate target names)."""
    KEEP_FIRST = "keep_first"
    KEEP_SECOND = "keep_second"
    AVERAGE = "average"
    NORMALIZE = "normalize"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class BlendshapeCombination:
    """
    Definition of a blendshape combination.
    """
    name: str
    sources: List[str]  # names of source targets or deltas
    weights: List[float]  # weights for each source
    combination_mode: CombinationMode = CombinationMode.ADD
    blend_mode: BlendMode = BlendMode.LINEAR
    corrective_mode: CorrectiveMode = CorrectiveMode.NONE
    output_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if len(self.sources) != len(self.weights):
            raise ValueError("Number of sources and weights must match")
        if not self.sources:
            raise ValueError("At least one source is required")
        if self.output_name is None:
            # Auto-generate output name from source names
            base = "_".join(self.sources)
            self.output_name = sanitize_name(base)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sources": self.sources,
            "weights": self.weights,
            "combination_mode": self.combination_mode.value,
            "blend_mode": self.blend_mode.value,
            "corrective_mode": self.corrective_mode.value,
            "output_name": self.output_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlendshapeCombination:
        return cls(
            name=data["name"],
            sources=data["sources"],
            weights=data["weights"],
            combination_mode=CombinationMode(data.get("combination_mode", "add")),
            blend_mode=BlendMode(data.get("blend_mode", "linear")),
            corrective_mode=CorrectiveMode(data.get("corrective_mode", "none")),
            output_name=data.get("output_name"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CombinationSettings:
    """Settings for combination operations."""
    # Combination parameters
    combination_mode: CombinationMode = CombinationMode.ADD
    blend_mode: BlendMode = BlendMode.LINEAR
    corrective_mode: CorrectiveMode = CorrectiveMode.NONE
    # Output
    output_prefix: str = ""
    output_suffix: str = "_combined"
    overwrite_existing: bool = False
    # Validation
    validate: bool = True
    # Performance
    use_numpy: bool = True
    # Progress
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class CombinationTask:
    """A combination task for batch processing."""
    name: str
    combination: BlendshapeCombination
    settings: Optional[CombinationSettings] = None
    callback: Optional[Callable[[CombinationResult], None]] = None


@dataclass
class CombinationResult:
    """Result of a combination operation."""
    success: bool
    output_targets: List[str] = field(default_factory=list)
    skipped_sources: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass
class CombinationStatistics:
    """Statistics for combination operations."""
    total_combinations: int = 0
    successful: int = 0
    failed: int = 0
    vertices_processed: int = 0
    total_sources: int = 0
    total_outputs: int = 0
    elapsed_time: float = 0.0


# ---- Part 4: Combination Engine ----------------------------------------

class BlendshapeCombiner:
    """
    Main controller for blendshape combination operations.
    """
    def __init__(self):
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._weight_manager = WeightManager() if WeightManager else None
        self._pose_manager = PoseManager() if PoseManager else None
        self._transfer_engine = BlendshapeTransferEngine() if BlendshapeTransferEngine else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None

        self._settings = CombinationSettings()
        self._last_result: Optional[CombinationResult] = None
        self._last_stats: Optional[CombinationStatistics] = None

    # ---- Main Combination API ----

    def combine(
        self,
        combination: Union[BlendshapeCombination, Dict[str, Any]],
        base_mesh: str,
        settings: Optional[CombinationSettings] = None,
    ) -> CombinationResult:
        """
        Execute a single combination definition.

        Args:
            combination: BlendshapeCombination or dict definition.
            base_mesh: The mesh to apply the combined target to.
            settings: Override settings.

        Returns:
            CombinationResult
        """
        start_time = time.time()
        if settings is None:
            settings = self._settings
        else:
            self._settings = settings

        if isinstance(combination, dict):
            combination = BlendshapeCombination.from_dict(combination)

        result = CombinationResult(success=True)

        # Validate combination
        try:
            self._validate_combination(combination, base_mesh, settings)
        except CombinationValidationError as e:
            result.errors.append(str(e))
            result.success = False
            result.elapsed_time = time.time() - start_time
            self._last_result = result
            return result

        # Retrieve deltas for each source
        source_deltas = []
        source_weights = combination.weights
        for i, src_name in enumerate(combination.sources):
            if settings.cancel_check and settings.cancel_check():
                result.errors.append("Cancelled by user")
                result.success = False
                break
            if settings.progress_callback:
                settings.progress_callback(i / len(combination.sources), f"Loading {src_name}")

            # Try to get delta from delta engine
            if self._delta_engine:
                delta = self._delta_engine.get(src_name)
                if delta is not None:
                    source_deltas.append(delta)
                    continue

            # If not found, try to get from blendshape node
            # We need to find the blendshape node on base_mesh that has this target.
            bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
            found = False
            for bs in bs_nodes:
                if src_name in get_blendshape_targets(bs):
                    # Compute delta from base_mesh to target mesh
                    # We need the target mesh for this target
                    target_mesh = self._get_target_mesh_for_blendshape(bs, src_name)
                    if target_mesh:
                        if self._delta_engine:
                            # Compute delta on the fly
                            try:
                                delta = self._delta_engine.compute(base_mesh, target_mesh, src_name)
                                source_deltas.append(delta)
                                found = True
                            except Exception as e:
                                result.errors.append(f"Failed to compute delta for {src_name}: {e}")
                                result.success = False
                            break
            if not found:
                result.errors.append(f"Source '{src_name}' not found in delta cache or blendshape node")
                result.success = False
                break

        if not result.success:
            result.elapsed_time = time.time() - start_time
            self._last_result = result
            return result

        # Combine deltas
        combined_delta = self._combine_deltas(source_deltas, source_weights, combination.combination_mode, settings)
        if combined_delta is None:
            result.errors.append("Failed to combine deltas")
            result.success = False
            result.elapsed_time = time.time() - start_time
            self._last_result = result
            return result

        # Generate corrective shape if requested
        if combination.corrective_mode != CorrectiveMode.NONE:
            corrective_delta = self._generate_corrective(combined_delta, source_deltas, combination.corrective_mode, settings)
            if corrective_delta is not None:
                # Add corrective to combined
                combined_delta = self._add_deltas([combined_delta, corrective_delta], [1.0, 1.0], CombinationMode.ADD, settings)

        # Apply combined delta to base_mesh to create a new target mesh
        if self._delta_engine:
            output_name = combination.output_name
            # Apply prefix/suffix
            if settings.output_prefix:
                output_name = settings.output_prefix + output_name
            if settings.output_suffix:
                output_name = output_name + settings.output_suffix
            output_mesh = self._delta_engine.apply(base_mesh, combined_delta, output_mesh=output_name)
            if output_mesh:
                result.output_targets.append(output_mesh)
            else:
                result.errors.append("Failed to apply combined delta to create target mesh")
                result.success = False
        else:
            result.errors.append("Delta engine not available")
            result.success = False

        result.elapsed_time = time.time() - start_time
        self._last_result = result

        # Statistics
        stats = CombinationStatistics(
            total_combinations=1,
            successful=1 if result.success else 0,
            failed=0 if result.success else 1,
            vertices_processed=combined_delta.vertex_count if combined_delta else 0,
            total_sources=len(combination.sources),
            total_outputs=len(result.output_targets),
            elapsed_time=result.elapsed_time
        )
        self._last_stats = stats

        return result

    def combine_selected(
        self,
        base_mesh: str,
        source_names: List[str],
        weights: Optional[List[float]] = None,
        output_name: Optional[str] = None,
        settings: Optional[CombinationSettings] = None,
    ) -> CombinationResult:
        """
        Combine selected source blendshapes from the selection.
        If weights not provided, equal weights are used.
        """
        if weights is None:
            weights = [1.0] * len(source_names)
        else:
            if len(weights) != len(source_names):
                raise ValueError("Source names and weights must have same length")
        # Auto-generate name
        if output_name is None:
            output_name = "_".join(source_names)
        comb = BlendshapeCombination(
            name=output_name,
            sources=source_names,
            weights=weights,
            output_name=output_name
        )
        return self.combine(comb, base_mesh, settings)

    def combine_all(
        self,
        base_mesh: str,
        source_node: str,
        settings: Optional[CombinationSettings] = None,
    ) -> CombinationResult:
        """
        Combine all targets from a blendshape node into a single target.
        This creates a composite of all shapes.
        """
        if not cmds.objExists(source_node) or cmds.nodeType(source_node) != 'blendShape':
            return CombinationResult(success=False, errors=["Invalid blendshape node"])
        targets = get_blendshape_targets(source_node)
        if not targets:
            return CombinationResult(success=False, warnings=["No targets found in blendshape node"])
        # Use equal weights
        weights = [1.0] * len(targets)
        comb = BlendshapeCombination(
            name=f"{source_node}_combined",
            sources=targets,
            weights=weights,
            output_name=f"{source_node}_all",
            combination_mode=CombinationMode.ADD
        )
        return self.combine(comb, base_mesh, settings)

    # ---- Delta Combination Methods ----

    def _combine_deltas(
        self,
        deltas: List[BlendshapeDelta],
        weights: List[float],
        mode: CombinationMode,
        settings: CombinationSettings
    ) -> Optional[BlendshapeDelta]:
        """
        Combine a list of deltas using the specified mode and weights.
        """
        if not deltas:
            return None

        # Normalize weights if needed
        if mode != CombinationMode.MULTIPLY:
            # For additive, average, max, min, we typically use weights directly.
            # For weighted average, we may normalize.
            total_weight = sum(weights)
            if mode == CombinationMode.AVERAGE and total_weight > 0:
                norm_weights = [w / total_weight for w in weights]
            else:
                norm_weights = weights[:]
        else:
            norm_weights = weights[:]  # Not used for multiply

        # Collect all vertex indices from all deltas
        all_vertices = set()
        for d in deltas:
            for vd in d.deltas:
                all_vertices.add(vd.index)
        vertex_count = max(d.vertex_count for d in deltas)

        if HAS_NUMPY and settings.use_numpy:
            return self._combine_deltas_numpy(deltas, norm_weights, mode, vertex_count)
        else:
            return self._combine_deltas_python(deltas, norm_weights, mode, vertex_count)

    def _combine_deltas_numpy(
        self,
        deltas: List[BlendshapeDelta],
        weights: List[float],
        mode: CombinationMode,
        vertex_count: int
    ) -> Optional[BlendshapeDelta]:
        """NumPy-accelerated delta combination."""
        import numpy as np
        # Initialize accumulation array (vertex_count x 3)
        acc = np.zeros((vertex_count, 3), dtype=np.float32)
        # For each delta, add weighted contributions
        for d, w in zip(deltas, weights):
            # Build a dense array for this delta
            dense = np.zeros((vertex_count, 3), dtype=np.float32)
            for vd in d.deltas:
                dense[vd.index] = vd.offset
            if mode == CombinationMode.ADD:
                acc += dense * w
            elif mode == CombinationMode.SUBTRACT:
                # First delta is base, subtract the rest
                if d == deltas[0]:
                    acc = dense * w
                else:
                    acc -= dense * w
            elif mode == CombinationMode.AVERAGE:
                acc += dense * w
            elif mode == CombinationMode.MAXIMUM:
                acc = np.maximum(acc, dense * w)
            elif mode == CombinationMode.MINIMUM:
                acc = np.minimum(acc, dense * w)
            elif mode == CombinationMode.MULTIPLY:
                # Multiply per-vertex; start with ones
                if d == deltas[0]:
                    acc = np.ones_like(dense) + dense * w  # 1 + delta
                else:
                    acc = acc * (1 + dense * w)
                # After multiply, we want deltas, not accumulated positions.
                # We'll handle outside.
        # For MODE_MULTIPLY, we need to subtract base (1) from acc.
        if mode == CombinationMode.MULTIPLY:
            acc = acc - 1.0

        # For AVERAGE, divide by total weight
        if mode == CombinationMode.AVERAGE and sum(weights) > 0:
            total_w = sum(weights)
            acc = acc / total_w

        # Build BlendshapeDelta from acc (only non-zero)
        new_deltas = []
        for i in range(vertex_count):
            dx, dy, dz = acc[i]
            if abs(dx) > 1e-8 or abs(dy) > 1e-8 or abs(dz) > 1e-8:
                new_deltas.append(VertexDelta(index=i, offset=(float(dx), float(dy), float(dz))))
        # Create a name
        name = "_".join([d.name for d in deltas]) + "_combined"
        # Ensure BlendshapeDelta is available before creating an instance
        if BlendshapeDelta is None:
            return None
        return BlendshapeDelta(
            name=name,
            vertex_count=vertex_count,
            deltas=new_deltas,
            metadata={"combined_mode": mode.value}
        )

    def _combine_deltas_python(
        self,
        deltas: List[BlendshapeDelta],
        weights: List[float],
        mode: CombinationMode,
        vertex_count: int
    ) -> Optional[BlendshapeDelta]:
        """Pure Python fallback for delta combination."""
        # Initialize dictionary for each vertex
        acc = {}  # idx -> (dx, dy, dz)
        # For multiply, start with ones (identity)
        if mode == CombinationMode.MULTIPLY:
            # We'll accumulate in a different way: product of (1 + delta_i)
            prod = {}  # idx -> (px, py, pz) product of (1+dx) etc.
            # We'll process first delta to initialize
            first = True
            for d, w in zip(deltas, weights):
                for vd in d.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    scaled = (dx*w, dy*w, dz*w)
                    if first:
                        prod[idx] = (1.0 + scaled[0], 1.0 + scaled[1], 1.0 + scaled[2])
                    else:
                        px, py, pz = prod.get(idx, (1.0, 1.0, 1.0))
                        prod[idx] = (px * (1.0 + scaled[0]), py * (1.0 + scaled[1]), pz * (1.0 + scaled[2]))
                first = False
            # Convert product to delta: delta = product - 1
            for idx, (px, py, pz) in prod.items():
                acc[idx] = (px - 1.0, py - 1.0, pz - 1.0)
        else:
            # For add, subtract, average, max, min
            for d, w in zip(deltas, weights):
                for vd in d.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    scaled = (dx*w, dy*w, dz*w)
                    if mode == CombinationMode.ADD:
                        prev = acc.get(idx, (0.0, 0.0, 0.0))
                        acc[idx] = (prev[0] + scaled[0], prev[1] + scaled[1], prev[2] + scaled[2])
                    elif mode == CombinationMode.SUBTRACT:
                        if d == deltas[0]:
                            acc[idx] = scaled
                        else:
                            prev = acc.get(idx, (0.0, 0.0, 0.0))
                            acc[idx] = (prev[0] - scaled[0], prev[1] - scaled[1], prev[2] - scaled[2])
                    elif mode == CombinationMode.AVERAGE:
                        prev = acc.get(idx, (0.0, 0.0, 0.0))
                        acc[idx] = (prev[0] + scaled[0], prev[1] + scaled[1], prev[2] + scaled[2])
                    elif mode == CombinationMode.MAXIMUM:
                        prev = acc.get(idx, (-float('inf'), -float('inf'), -float('inf')))
                        acc[idx] = (max(prev[0], scaled[0]), max(prev[1], scaled[1]), max(prev[2], scaled[2]))
                    elif mode == CombinationMode.MINIMUM:
                        prev = acc.get(idx, (float('inf'), float('inf'), float('inf')))
                        acc[idx] = (min(prev[0], scaled[0]), min(prev[1], scaled[1]), min(prev[2], scaled[2]))
            # For AVERAGE, divide by total weight
            if mode == CombinationMode.AVERAGE:
                total_w = sum(weights)
                if total_w > 0:
                    for idx in acc:
                        dx, dy, dz = acc[idx]
                        acc[idx] = (dx/total_w, dy/total_w, dz/total_w)

        # Build deltas
        new_deltas = []
        for idx, (dx, dy, dz) in acc.items():
            if abs(dx) > 1e-8 or abs(dy) > 1e-8 or abs(dz) > 1e-8:
                new_deltas.append(VertexDelta(index=idx, offset=(dx, dy, dz)))
        name = "_".join([d.name for d in deltas]) + "_combined"
        if BlendshapeDelta is None:
            return None
        return BlendshapeDelta(
            name=name,
            vertex_count=vertex_count,
            deltas=new_deltas,
            metadata={"combined_mode": mode.value}
        )

    def _add_deltas(
        self,
        deltas: List[BlendshapeDelta],
        weights: List[float],
        mode: CombinationMode,
        settings: CombinationSettings
    ) -> Optional[BlendshapeDelta]:
        """Helper to add deltas (simple add)."""
        return self._combine_deltas(deltas, weights, mode, settings)

    # ---- Corrective Generation ----

    def _generate_corrective(
        self,
        combined_delta: BlendshapeDelta,
        source_deltas: List[BlendshapeDelta],
        mode: CorrectiveMode,
        settings: CombinationSettings
    ) -> Optional[BlendshapeDelta]:
        """
        Generate a corrective delta to fix artifacts in combined shape.
        This is a placeholder; a real implementation would detect issues
        like intersections or volume loss and generate corrective deltas.
        """
        if mode == CorrectiveMode.NONE:
            return None
        if mode == CorrectiveMode.AUTOMATIC:
            # Simple: compute difference between combined and sum of sources?
            # For now, just return a zero delta (no correction).
            return None
        # POSE_SPACE or MANUAL would require additional data.
        return None

    # ---- Validation ----

    def _validate_combination(
        self,
        combination: BlendshapeCombination,
        base_mesh: str,
        settings: CombinationSettings
    ) -> None:
        """
        Validate that the combination is valid.
        Raises CombinationValidationError if invalid.
        """
        if not combination.sources:
            raise CombinationValidationError("No sources specified")
        if len(combination.sources) != len(combination.weights):
            raise CombinationValidationError("Source/weight count mismatch")
        # Check base_mesh exists
        if not cmds.objExists(base_mesh):
            raise CombinationValidationError(f"Base mesh '{base_mesh}' does not exist")
        # Validate each source (delta or target)
        # For now, we assume they exist (we'll handle errors during combination).
        # We could use validator to check mesh compatibility.
        if settings.validate and self._validator:
            report = self._validator.validate_mesh(base_mesh, level=ValidationLevel.NORMAL if ValidationLevel else None)
            if not report.is_valid:
                raise CombinationValidationError(f"Base mesh validation failed: {report.errors}")

    # ---- Utility Methods ----

    def _get_target_mesh_for_blendshape(self, blendshape_node: str, target_name: str) -> Optional[str]:
        """Get the mesh associated with a target. Simplified."""
        # We'll try to find a mesh connected to the blendshape node's target attribute.
        # This is heuristic.
        meshes = cmds.listConnections(blendshape_node, type='mesh') or []
        if meshes:
            return meshes[0]
        return None

    # ---- Batch Processing ----

    def batch_combine(
        self,
        tasks: List[CombinationTask],
        base_mesh: str,
        settings: Optional[CombinationSettings] = None,
    ) -> List[CombinationResult]:
        """Execute a batch of combination tasks."""
        results = []
        for task in tasks:
            if settings is None:
                task_settings = task.settings or self._settings
            else:
                task_settings = settings
            result = self.combine(task.combination, base_mesh, task_settings)
            results.append(result)
            if task.callback:
                task.callback(result)
        return results

    # ---- Statistics ----

    def get_last_result(self) -> Optional[CombinationResult]:
        return self._last_result

    def get_last_stats(self) -> Optional[CombinationStatistics]:
        return self._last_stats

    def reset(self) -> None:
        self._last_result = None
        self._last_stats = None

    # ---- Settings ----

    def set_settings(self, settings: CombinationSettings) -> None:
        self._settings = settings

    def get_settings(self) -> CombinationSettings:
        return self._settings


# ---- Part 5: Delta Composition (implemented above) ----------------------

# ---- Part 6: Weight Blending (implemented above) -----------------------

# ---- Part 7: Corrective Generation (implemented above) -----------------

# ---- Part 8: Pose Space Combination (placeholder) ----------------------

# ---- Part 9: ARKit Expression Combination -----------------------------

class ARKitCombiner:
    """
    Specialized combiner for ARKit expressions.
    Uses predefined ARKit expression templates.
    """
    def __init__(self, combiner: Optional[BlendshapeCombiner] = None):
        self._combiner = combiner or BlendshapeCombiner()
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None

    def create_expression(
        self,
        base_mesh: str,
        expression_name: str,
        intensity: float = 1.0,
        settings: Optional[CombinationSettings] = None,
    ) -> CombinationResult:
        """
        Create an ARKit expression by combining targets.
        For example, "Happy" = Smile + CheekRaise + EyeSquint.
        """
        # Get expression definition from library
        if self._library:
            expr_def = self._library.get_expression(expression_name)
            if expr_def is None:
                return CombinationResult(success=False, errors=[f"Expression '{expression_name}' not found in library"])
            # Build combination
            sources = expr_def.get("sources", [])
            weights = expr_def.get("weights", [1.0] * len(sources))
            if not sources:
                return CombinationResult(success=False, errors=[f"Expression '{expression_name}' has no sources"])
            comb = BlendshapeCombination(
                name=expression_name,
                sources=sources,
                weights=weights,
                output_name=expression_name,
                combination_mode=CombinationMode.ADD,
                blend_mode=BlendMode.LINEAR,
                corrective_mode=CorrectiveMode.NONE
            )
            # Scale intensity
            if intensity != 1.0:
                comb.weights = [w * intensity for w in comb.weights]
            return self._combiner.combine(comb, base_mesh, settings)
        else:
            return CombinationResult(success=False, errors=["Library not available"])

    def create_viseme(
        self,
        base_mesh: str,
        viseme_name: str,
        intensity: float = 1.0,
        settings: Optional[CombinationSettings] = None,
    ) -> CombinationResult:
        """Create a viseme target (e.g., 'AH', 'EE')."""
        # Similar to expression, but uses viseme definitions.
        if self._library:
            viseme_def = self._library.get_viseme(viseme_name)
            if viseme_def is None:
                return CombinationResult(success=False, errors=[f"Viseme '{viseme_name}' not found in library"])
            sources = viseme_def.get("sources", [])
            weights = viseme_def.get("weights", [1.0] * len(sources))
            if not sources:
                return CombinationResult(success=False, errors=[f"Viseme '{viseme_name}' has no sources"])
            comb = BlendshapeCombination(
                name=viseme_name,
                sources=sources,
                weights=weights,
                output_name=viseme_name,
                combination_mode=CombinationMode.ADD,
                blend_mode=BlendMode.LINEAR,
                corrective_mode=CorrectiveMode.NONE
            )
            if intensity != 1.0:
                comb.weights = [w * intensity for w in comb.weights]
            return self._combiner.combine(comb, base_mesh, settings)
        else:
            return CombinationResult(success=False, errors=["Library not available"])


# ---- Part 10: Batch Combination (implemented in BlendshapeCombiner) ----

# ---- Part 11: Validation (implemented in _validate_combination) -------

# ---- Part 12: Diagnostics & Statistics (implemented above) ------------

# ---- Part 13: Utility Functions --------------------------------------

def create_combination_from_dict(data: Dict[str, Any]) -> BlendshapeCombination:
    """Create a BlendshapeCombination from a dict."""
    return BlendshapeCombination.from_dict(data)


def create_combination_from_json(json_str: str) -> BlendshapeCombination:
    """Create a BlendshapeCombination from a JSON string."""
    data = json_to_dict(json_str)
    return BlendshapeCombination.from_dict(data)


def combination_to_json(combination: BlendshapeCombination) -> str:
    """Convert a combination to JSON."""
    return dict_to_json(combination.to_dict())


# ---- Part 14: Public API -----------------------------------------------

__all__ = [
    "BlendshapeCombiner",
    "ARKitCombiner",
    "BlendshapeCombination",
    "CombinationSettings",
    "CombinationTask",
    "CombinationResult",
    "CombinationStatistics",
    "CombinationMode",
    "BlendMode",
    "CorrectiveMode",
    "ConflictPolicy",
    "CombinationError",
    "InvalidCombinationError",
    "CombinationNotFoundError",
    "CombinationValidationError",
    "create_combination_from_dict",
    "create_combination_from_json",
    "combination_to_json",
]