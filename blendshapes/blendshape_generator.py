"""
blendshapes/blendshape_generator.py

Automatic Blendshape Generation Engine for Maya.

This module procedurally creates blendshape targets from meshes, facial landmarks,
ARKit definitions, symmetry rules, machine learning, pose libraries, or
mathematical deformation algorithms. It reduces the need for manual sculpting
by generating targets automatically.

Responsibilities:
- Generate blendshapes from facial landmarks (MediaPipe, FaceMesh, etc.)
- Generate symmetric blendshapes (mirror left/right)
- Generate blendshapes from delta operations
- Generate complete ARKit 52-shape library
- Generate viseme shapes for lip-sync
- Generate emotion expressions (happy, sad, angry, etc.)
- Generate corrective shapes (pose-space combinations)
- Batch generate across multiple meshes or characters
- Validate and optimize generated results

Dependencies:
- blendshape_creator.py: Create blendshape nodes and targets.
- blendshape_delta.py: Compute and apply vertex deltas.
- blendshape_combiner.py: Combine multiple deltas.
- blendshape_validator.py: Validate generated meshes and topology.
- blendshape_utils.py: Shared utilities.
- blendshape_optimizer.py: Optimize generated targets.
- blendshape_library.py: Store and manage generated targets.
- symmetry.py: Mirror shapes (if available).
- landmarks/: Facial landmark processing (if available).
- blendshapes/arkit/: ARKit definitions and constants.

The module uses Maya's Python API and may optionally leverage NumPy.
"""

from __future__ import annotations

import copy
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable

# Maya imports (with fallback for testing)
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists, currentTime # type: ignore
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
    from .blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType, CreationMode, WeightMode, NamingMode
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None
    CreationMode = None
    WeightMode = None
    NamingMode = None

try:
    from .blendshape_delta import BlendshapeDeltaEngine, BlendshapeDelta, VertexDelta, CombinationMode as DeltaCombinationMode
except ImportError:
    BlendshapeDeltaEngine = None
    BlendshapeDelta = None
    VertexDelta = None
    DeltaCombinationMode = None

try:
    from .blendshape_combiner import BlendshapeCombiner, BlendshapeCombination, CombinationMode, BlendMode, CorrectiveMode
except ImportError:
    BlendshapeCombiner = None
    BlendshapeCombination = None
    CombinationMode = None
    BlendMode = None
    CorrectiveMode = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel, ValidationReport
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None
    ValidationReport = None

try:
    from .blendshape_optimizer import BlendshapeOptimizer
except ImportError:
    BlendshapeOptimizer = None

try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions,
        get_vertex_position, set_vertex_position, clamp, lerp,
        sanitize_name, generate_unique_name, get_blendshape_targets,
        get_blendshape_weight, set_blendshape_weight, Timer, ProgressTracker,
        dict_to_json, json_to_dict, hash_data, checksum_mesh,
        get_active_weights, scale_weights, blend_weights, normalize_weights,
        remove_namespace, add_namespace, to_camel_case, to_snake_case,
        get_mesh_bounding_box, get_mesh_center, duplicate_mesh, freeze_transforms
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
    def dict_to_json(d, indent=2): return "{}"
    def json_to_dict(s): return {}
    def hash_data(d): return ""
    def checksum_mesh(m): return ""
    def get_active_weights(w, th): return {}
    def scale_weights(w, f): return {}
    def blend_weights(a,b,t): return {}
    def normalize_weights(w): return {}
    def remove_namespace(n): return n
    def add_namespace(n, ns): return n
    def to_camel_case(s): return s
    def to_snake_case(s): return s
    def get_mesh_bounding_box(m): return ((0,0,0),(0,0,0))
    def get_mesh_center(m): return (0,0,0)
    def duplicate_mesh(m, n): return m
    def freeze_transforms(m): pass

try:
    from .blendshape_library import BlendShapeLibrary
except ImportError:
    BlendShapeLibrary = None

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
class GeneratorError(Exception):
    """Base exception for generator operations."""
    pass

class GenerationCanceledError(GeneratorError):
    """Raised when generation is canceled."""
    pass

class InvalidLandmarkError(GeneratorError):
    """Raised when landmarks are invalid."""
    pass

class GenerationValidationError(GeneratorError):
    """Raised when generated data fails validation."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class GeneratorType(Enum):
    """Types of generation algorithms."""
    LANDMARK = "landmark"
    DELTA = "delta"
    ARKIT = "arkit"
    VISEME = "viseme"
    EMOTION = "emotion"
    CORRECTIVE = "corrective"
    SYMMETRY = "symmetry"
    CUSTOM = "custom"


class GenerationMode(Enum):
    """Mode of generation."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    INTERACTIVE = "interactive"
    BATCH = "batch"


class OutputType(Enum):
    """What the generator produces."""
    MESH = "mesh"
    DELTA = "delta"
    BLENDSHAPE = "blendshape"
    POSE = "pose"
    LIBRARY = "library"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class GenerationSettings:
    """Settings for generation operations."""
    # General
    mode: GenerationMode = GenerationMode.AUTOMATIC
    output_type: OutputType = OutputType.BLENDSHAPE
    normalize_deltas: bool = True
    smooth_deltas: bool = False
    smooth_iterations: int = 1
    preserve_volume: bool = True
    # Symmetry
    symmetry: bool = True
    symmetry_axis: str = "x"
    symmetry_tolerance: float = 0.001
    # ARKit
    arkit_count: int = 52
    arkit_calibration: Optional[str] = None
    # Viseme
    viseme_set: str = "standard"  # 'standard', 'maya', 'unreal'
    # Emotions
    emotion_intensity: float = 1.0
    # Correctives
    corrective_threshold: float = 0.5
    # Batch
    batch_parallel: bool = False
    batch_max_workers: int = 4
    # Validation
    validate: bool = True
    validation_level: str = "normal"
    # Progress
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class GenerationTarget:
    """Definition of a target to generate."""
    name: str
    source_mesh: str  # The mesh to apply generation to
    target_mesh: Optional[str] = None  # Optional target mesh for deltas
    landmarks: Optional[List[Tuple[float, float, float]]] = None  # Facial landmarks
    generator_type: GeneratorType = GeneratorType.ARKIT
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_name: Optional[str] = None


@dataclass
class GenerationTask:
    """A batch generation task."""
    name: str
    targets: List[GenerationTarget]
    settings: GenerationSettings
    callback: Optional[Callable[[GenerationReport], None]] = None


@dataclass
class GenerationStatistics:
    """Statistics for generation operations."""
    total_generated: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    runtime_seconds: float = 0.0
    avg_time_per_target: float = 0.0


@dataclass
class GenerationReport:
    """Report for a generation operation."""
    success: bool
    generated_targets: List[str] = field(default_factory=list)
    skipped_targets: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[GenerationStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Generation Manager ---------------------------------------

class BlendshapeGenerator:
    """
    Main controller for automatic blendshape generation.
    """
    def __init__(self):
        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._combiner = BlendshapeCombiner() if BlendshapeCombiner else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._optimizer = BlendshapeOptimizer() if BlendshapeOptimizer else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        self._symmetry_engine = SymmetryEngine() if SymmetryEngine else None

        self._settings = GenerationSettings()
        self._last_report: Optional[GenerationReport] = None
        self._last_stats: Optional[GenerationStatistics] = None
        self._cancelled = False

    # ---- Main Generation API ----

    def generate(
        self,
        target: Union[GenerationTarget, List[GenerationTarget]],
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate blendshapes from a single target or a list of targets.
        """
        if settings is not None:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        if isinstance(target, list):
            # Batch generation
            return self._generate_batch(target, start_time)
        else:
            # Single generation
            return self._generate_single(target, start_time)

    def generate_arkit(
        self,
        base_mesh: str,
        output_prefix: str = "arkit_",
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate the complete ARKit 52-blendshape library.
        """
        if settings:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # Build targets for each ARKit shape
        targets = []
        for shape_name in ARKIT_BLENDSHAPES:
            target = GenerationTarget(
                name=shape_name,
                source_mesh=base_mesh,
                generator_type=GeneratorType.ARKIT,
                output_name=f"{output_prefix}{shape_name}",
                parameters={
                    "arkit_channel": shape_name,
                    "calibration": self._settings.arkit_calibration,
                }
            )
            targets.append(target)
        return self.generate(targets, settings)

    def generate_visemes(
        self,
        base_mesh: str,
        output_prefix: str = "viseme_",
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate viseme shapes for lip-sync.
        """
        if settings:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # Define standard viseme set (based on common phonemes)
        viseme_defs = {
            "AA": {"jawOpen": 0.8, "mouthStretchLeft": 0.2, "mouthStretchRight": 0.2},
            "AE": {"jawOpen": 0.6, "mouthStretchLeft": 0.6, "mouthStretchRight": 0.6},
            "AH": {"jawOpen": 0.7, "mouthLowerDownLeft": 0.4, "mouthLowerDownRight": 0.4},
            "AO": {"jawOpen": 0.5, "mouthFunnel": 0.6},
            "CH": {"jawOpen": 0.3, "mouthPucker": 0.6},
            "EE": {"jawOpen": 0.3, "mouthStretchLeft": 0.8, "mouthStretchRight": 0.8},
            "FV": {"jawOpen": 0.1, "mouthUpperUpLeft": 0.5, "mouthUpperUpRight": 0.5, "mouthLowerDownLeft": 0.2, "mouthLowerDownRight": 0.2},
            "IH": {"jawOpen": 0.4, "mouthSmileLeft": 0.2, "mouthSmileRight": 0.2},
            "L": {"jawOpen": 0.2, "mouthUpperUpLeft": 0.3, "mouthUpperUpRight": 0.3},
            "M": {"mouthClose": 0.8},
            "O": {"jawOpen": 0.5, "mouthPucker": 0.7},
            "OH": {"jawOpen": 0.4, "mouthFunnel": 0.8},
            "OU": {"jawOpen": 0.2, "mouthPucker": 0.4},
            "R": {"jawOpen": 0.2, "mouthPucker": 0.3, "mouthFunnel": 0.3},
            "S": {"jawOpen": 0.1, "mouthPressLeft": 0.4, "mouthPressRight": 0.4},
            "SH": {"jawOpen": 0.1, "mouthPucker": 0.5},
            "TH": {"jawOpen": 0.3, "mouthUpperUpLeft": 0.3, "mouthUpperUpRight": 0.3, "mouthLowerDownLeft": 0.3, "mouthLowerDownRight": 0.3},
            "U": {"jawOpen": 0.2, "mouthPucker": 0.8},
            "WQ": {"jawOpen": 0.3, "mouthPucker": 0.6, "mouthFunnel": 0.3},
        }
        targets = []
        for viseme, coefficients in viseme_defs.items():
            target = GenerationTarget(
                name=viseme,
                source_mesh=base_mesh,
                generator_type=GeneratorType.VISEME,
                output_name=f"{output_prefix}{viseme}",
                parameters={"coefficients": coefficients}
            )
            targets.append(target)
        return self.generate(targets, settings)

    def generate_emotions(
        self,
        base_mesh: str,
        output_prefix: str = "emotion_",
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate emotion expressions (happy, sad, angry, etc.)
        """
        if settings:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # Define emotion templates (coefficients for ARKit channel values)
        emotion_defs = {
            "Happy": {"mouthSmileLeft": 0.9, "mouthSmileRight": 0.9, "cheekSquintLeft": 0.4, "cheekSquintRight": 0.4, "eyeSquintLeft": 0.25, "eyeSquintRight": 0.25},
            "Sad": {"browInnerUp": 0.6, "mouthFrownLeft": 0.8, "mouthFrownRight": 0.8},
            "Angry": {"browDownLeft": 0.8, "browDownRight": 0.8, "mouthPressLeft": 0.9, "mouthPressRight": 0.9, "jawForward": 0.5},
            "Fear": {"browOuterUpLeft": 0.8, "browOuterUpRight": 0.8, "eyeWideLeft": 0.7, "eyeWideRight": 0.7, "jawOpen": 0.4},
            "Disgust": {"browDownLeft": 0.7, "browDownRight": 0.7, "noseSneerLeft": 0.9, "noseSneerRight": 0.9, "mouthUpperUpLeft": 0.6, "mouthUpperUpRight": 0.6},
            "Surprise": {"browInnerUp": 0.8, "eyeWideLeft": 0.9, "eyeWideRight": 0.9, "jawOpen": 0.7},
            "Neutral": {},
        }
        targets = []
        for emotion, coefficients in emotion_defs.items():
            target = GenerationTarget(
                name=emotion,
                source_mesh=base_mesh,
                generator_type=GeneratorType.EMOTION,
                output_name=f"{output_prefix}{emotion}",
                parameters={"coefficients": coefficients}
            )
            targets.append(target)
        return self.generate(targets, settings)

    def generate_correctives(
        self,
        base_mesh: str,
        source_targets: List[str],
        output_prefix: str = "corr_",
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate corrective blendshapes for combinations of targets.
        """
        if settings:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # For each combination of two targets, generate a corrective
        # This is simplified; production would use pose-space deformation.
        targets = []
        for i, t1 in enumerate(source_targets):
            for t2 in source_targets[i+1:]:
                combo_name = f"{t1}_{t2}"
                target = GenerationTarget(
                    name=combo_name,
                    source_mesh=base_mesh,
                    generator_type=GeneratorType.CORRECTIVE,
                    output_name=f"{output_prefix}{combo_name}",
                    parameters={"source_a": t1, "source_b": t2}
                )
                targets.append(target)
        return self.generate(targets, settings)

    def generate_symmetry(
        self,
        source_mesh: str,
        target_name: str,
        axis: str = "x",
        output_name: Optional[str] = None,
        settings: Optional[GenerationSettings] = None,
    ) -> GenerationReport:
        """
        Generate a symmetric version of an existing blendshape target.
        """
        if settings:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        target = GenerationTarget(
            name=target_name,
            source_mesh=source_mesh,
            generator_type=GeneratorType.SYMMETRY,
            output_name=output_name or f"{target_name}_mirrored",
            parameters={"axis": axis}
        )
        return self.generate(target, settings)

    # ---- Internal Generation Methods ----

    def _generate_single(self, target: GenerationTarget, start_time: float) -> GenerationReport:
        """
        Generate a single target.
        """
        report = GenerationReport(success=True)
        try:
            if self._cancelled:
                raise GenerationCanceledError("Generation canceled")

            # Dispatch to appropriate generator
            if target.generator_type == GeneratorType.ARKIT:
                result = self._generate_arkit_target(target)
            elif target.generator_type == GeneratorType.VISEME:
                result = self._generate_viseme_target(target)
            elif target.generator_type == GeneratorType.EMOTION:
                result = self._generate_emotion_target(target)
            elif target.generator_type == GeneratorType.CORRECTIVE:
                result = self._generate_corrective_target(target)
            elif target.generator_type == GeneratorType.SYMMETRY:
                result = self._generate_symmetry_target(target)
            elif target.generator_type == GeneratorType.LANDMARK:
                result = self._generate_landmark_target(target)
            elif target.generator_type == GeneratorType.DELTA:
                result = self._generate_delta_target(target)
            else:
                raise GeneratorError(f"Unsupported generator type: {target.generator_type}")

            if result:
                report.generated_targets.append(result)
            else:
                report.skipped_targets.append(target.name)

            # Validate
            if self._settings.validate and self._validator:
                val_report = self._validator.validate_mesh(result, level=self._settings.validation_level)
                if not val_report.is_valid:
                    report.warnings.extend([issue.message for issue in val_report.issues])
                    report.success = False

        except GenerationCanceledError:
            raise
        except Exception as e:
            report.errors.append(str(e))
            report.success = False

        # Statistics
        stats = GenerationStatistics(
            total_generated=1,
            successful=1 if report.success else 0,
            failed=0 if report.success else 1,
            runtime_seconds=time.time() - start_time,
            avg_time_per_target=time.time() - start_time,
        )
        report.statistics = stats
        self._last_report = report
        self._last_stats = stats
        return report

    def _generate_batch(self, targets: List[GenerationTarget], start_time: float) -> GenerationReport:
        """
        Generate multiple targets.
        """
        report = GenerationReport(success=True)
        total = len(targets)
        generated = []
        skipped = []
        errors = []

        for i, target in enumerate(targets):
            if self._cancelled:
                raise GenerationCanceledError("Batch generation canceled")
            if self._settings.progress_callback:
                self._settings.progress_callback(i / total, f"Generating {target.name}")

            single_report = self._generate_single(target, start_time)
            if single_report.success:
                generated.extend(single_report.generated_targets)
            else:
                errors.extend(single_report.errors)
                skipped.extend(single_report.skipped_targets)
                # Continue despite errors

        report.generated_targets = generated
        report.skipped_targets = skipped
        report.errors = errors
        report.success = len(errors) == 0

        # Statistics
        stats = GenerationStatistics(
            total_generated=total,
            successful=len(generated),
            failed=len(errors),
            skipped=len(skipped),
            runtime_seconds=time.time() - start_time,
            avg_time_per_target=(time.time() - start_time) / max(1, total),
        )
        report.statistics = stats
        self._last_report = report
        self._last_stats = stats
        return report

    # ---- Specific Generator Implementations ----

    def _generate_arkit_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a single ARKit target.
        This uses the coefficients defined in the ARKit spec.
        """
        channel = target.parameters.get("arkit_channel", target.name)
        # In a real implementation, we would use the ARKit mapping data
        # to generate the target mesh. For now, we'll create a dummy target
        # by duplicating the base mesh and applying a placeholder deformation.
        # This is a placeholder; production would use actual ARKit data.
        base_mesh = target.source_mesh
        output_name = target.output_name or f"arkit_{channel}"
        # Duplicate base mesh
        dup = duplicate_mesh(base_mesh, output_name)
        # Apply a simple deformation (for demonstration)
        # In reality, you'd use precomputed delta or procedural generation.
        # We'll just modify a few vertices to simulate.
        try:
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                # Move some vertices slightly
                for i in range(min(10, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        new_pos = (pos[0] + 0.01, pos[1], pos[2])
                        set_vertex_position(dup, i, new_pos)
            # Freeze transforms
            freeze_transforms(dup)
            # Create blendshape target via creator
            if self._creator:
                # Add as target to an existing blendshape node or create new
                # We'll assume the base mesh already has a blendshape node; if not, create one.
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                # Add target
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.ARKIT,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                # Compute delta and store in delta engine
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                logger.warning("BlendShapeCreator not available; returning mesh only")
                return dup
        except Exception as e:
            logger.error(f"Failed to generate ARKit target {channel}: {e}")
            return None

    def _generate_viseme_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a viseme target using coefficient blending.
        """
        coefficients = target.parameters.get("coefficients", {})
        # For visemes, we need to combine multiple blendshape channels.
        # We'll generate a target by applying the coefficients to the base mesh.
        # This is a placeholder; actual implementation would use delta blending.
        base_mesh = target.source_mesh
        output_name = target.output_name or f"viseme_{target.name}"
        # Duplicate base mesh
        dup = duplicate_mesh(base_mesh, output_name)
        # Apply deformation (placeholder: move some vertices)
        try:
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                # Simulate deformation based on coefficients (just for demo)
                for i in range(min(20, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        # Map coefficient sum to deformation
                        total = sum(coefficients.values()) * 0.01
                        new_pos = (pos[0] + total, pos[1] + total * 0.5, pos[2] + total * 0.3)
                        set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            # Add as blendshape target
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.STANDARD,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate viseme {target.name}: {e}")
            return None

    def _generate_emotion_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate an emotion target using coefficient blending.
        """
        coefficients = target.parameters.get("coefficients", {})
        # Similar to viseme, but for emotions.
        # We'll use a combination of blendshapes to create the expression.
        # For this placeholder, we'll just duplicate and deform.
        base_mesh = target.source_mesh
        output_name = target.output_name or f"emotion_{target.name}"
        dup = duplicate_mesh(base_mesh, output_name)
        try:
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                total = sum(coefficients.values()) * 0.02
                for i in range(min(30, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        new_pos = (pos[0] + total * 0.5, pos[1] + total, pos[2] + total * 0.3)
                        set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.STANDARD,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate emotion {target.name}: {e}")
            return None

    def _generate_corrective_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a corrective target by detecting difference between combined and base.
        """
        source_a = target.parameters.get("source_a")
        source_b = target.parameters.get("source_b")
        if not source_a or not source_b:
            logger.error("Corrective target requires source_a and source_b")
            return None
        base_mesh = target.source_mesh
        output_name = target.output_name or f"corr_{source_a}_{source_b}"
        # In a real implementation, we would:
        # 1. Get deltas for source_a and source_b.
        # 2. Combine them additively.
        # 3. Compare with base to find areas that need correction.
        # 4. Generate corrective delta.
        # For this placeholder, we'll just duplicate and deform.
        dup = duplicate_mesh(base_mesh, output_name)
        try:
            # Simple deformation: move vertices slightly
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                for i in range(min(5, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        new_pos = (pos[0] + 0.005, pos[1] + 0.01, pos[2] + 0.005)
                        set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.CORRECTIVE,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate corrective {target.name}: {e}")
            return None

    def _generate_symmetry_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a mirrored version of an existing target.
        """
        source_name = target.name
        axis = target.parameters.get("axis", "x")
        base_mesh = target.source_mesh
        output_name = target.output_name or f"{source_name}_mirrored"
        # In a real implementation, we would get the delta for source_name,
        # mirror it using symmetry engine, and apply to base_mesh.
        # For this placeholder, we'll duplicate and apply a simple flip.
        dup = duplicate_mesh(base_mesh, output_name)
        try:
            # Flip vertices across axis (simple mirror)
            vert_count = get_mesh_vertex_count(dup)
            positions = get_mesh_vertex_positions(dup)
            if positions:
                new_positions = []
                for pos in positions:
                    if axis == "x":
                        new_positions.append((-pos[0], pos[1], pos[2]))
                    elif axis == "y":
                        new_positions.append((pos[0], -pos[1], pos[2]))
                    elif axis == "z":
                        new_positions.append((pos[0], pos[1], -pos[2]))
                    else:
                        new_positions.append(pos)
                # Apply new positions
                for i, new_pos in enumerate(new_positions):
                    set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.STANDARD,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate symmetry target {target.name}: {e}")
            return None

    def _generate_landmark_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a blendshape from facial landmarks (placeholder).
        """
        # Placeholder: just duplicate and deform slightly.
        base_mesh = target.source_mesh
        output_name = target.output_name or f"landmark_{target.name}"
        dup = duplicate_mesh(base_mesh, output_name)
        try:
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                for i in range(min(10, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        new_pos = (pos[0] + 0.01, pos[1] + 0.01, pos[2])
                        set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.STANDARD,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate landmark target {target.name}: {e}")
            return None

    def _generate_delta_target(self, target: GenerationTarget) -> Optional[str]:
        """
        Generate a blendshape from a delta (placeholder).
        """
        # Placeholder: duplicate and apply a simple delta.
        base_mesh = target.source_mesh
        output_name = target.output_name or f"delta_{target.name}"
        dup = duplicate_mesh(base_mesh, output_name)
        try:
            vert_count = get_mesh_vertex_count(dup)
            if vert_count > 0:
                for i in range(min(10, vert_count)):
                    pos = get_vertex_position(dup, i)
                    if pos:
                        new_pos = (pos[0] + 0.02, pos[1] + 0.02, pos[2] + 0.02)
                        set_vertex_position(dup, i, new_pos)
            freeze_transforms(dup)
            if self._creator:
                bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
                if bs_nodes:
                    bs_node = bs_nodes[0]
                else:
                    bs_node = self._creator.create_node("BlendShape", base_mesh)
                target_def = BlendShapeTarget(
                    name=output_name,
                    mesh=dup,
                    target_type=TargetType.STANDARD,
                    weight=0.0,
                )
                self._creator.create_target(bs_node, target_def)
                if self._delta_engine:
                    delta = self._delta_engine.compute(base_mesh, dup, output_name)
                    self._delta_engine.add(delta)
                return output_name
            else:
                return dup
        except Exception as e:
            logger.error(f"Failed to generate delta target {target.name}: {e}")
            return None

    # ---- Utilities ----

    def cancel(self) -> None:
        """Cancel the current generation operation."""
        self._cancelled = True

    def get_last_report(self) -> Optional[GenerationReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[GenerationStatistics]:
        return self._last_stats

    def reset(self) -> None:
        self._last_report = None
        self._last_stats = None

    def set_settings(self, settings: GenerationSettings) -> None:
        self._settings = settings

    def get_settings(self) -> GenerationSettings:
        return self._settings


# ---- Part 15: Utility Functions ---------------------------------------

def create_generation_target(
    name: str,
    source_mesh: str,
    generator_type: GeneratorType = GeneratorType.ARKIT,
    output_name: Optional[str] = None,
    **kwargs
) -> GenerationTarget:
    """Factory function for GenerationTarget."""
    return GenerationTarget(
        name=name,
        source_mesh=source_mesh,
        generator_type=generator_type,
        output_name=output_name,
        parameters=kwargs
    )


# ---- Part 16: Public API ---------------------------------------------

__all__ = [
    "BlendshapeGenerator",
    "GenerationSettings",
    "GenerationTarget",
    "GenerationTask",
    "GenerationStatistics",
    "GenerationReport",
    "GeneratorType",
    "GenerationMode",
    "OutputType",
    "GeneratorError",
    "GenerationCanceledError",
    "InvalidLandmarkError",
    "GenerationValidationError",
    "create_generation_target",
]