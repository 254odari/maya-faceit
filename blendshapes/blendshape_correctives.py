"""
blendshapes/blendshape_correctives.py

Corrective Blendshape System for Maya.

This module manages corrective blendshapes that fix undesirable mesh deformation
caused by joints, multiple blendshape combinations, pose-space deformation (PSD),
or complex facial expressions. It is a core component of high-end facial rigs.

Responsibilities:
- Generate and manage PSD (Pose Space Deformation) correctives.
- Create joint-based correctives for jaw, eyes, brows, tongue, etc.
- Generate correctives for blendshape combinations (e.g., Smile + JawOpen).
- Support ARKit-specific correctives beyond the standard 52 shapes.
- Automatically detect and generate correctives from deformation analysis.
- Evaluate corrective activation based on driver values and rules.
- Batch process, validate, and report on corrective networks.

Dependencies:
- blendshape_driver.py: Provides driver values (joint rotations, blendshape weights).
- blendshape_pose.py: Pose-space data for PSD evaluation.
- blendshape_combiner.py: Combines deltas for corrective targets.
- blendshape_delta.py: Delta computation and application.
- blendshape_validator.py: Validation of meshes and dependencies.
- blendshape_utils.py: Shared utilities.
- blendshape_generator.py: Procedural generation of shapes.
- blendshape_inbetweens.py: Intermediate targets for smooth transitions.
- blendshape_creator.py: Creates blendshape nodes and targets.
- animation/: Timeline, keyframes, baking.
- rig/: Controller and joint definitions.
- blendshapes/arkit/: ARKit constants.

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

# Maya imports
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode, selected, ls, exists
    import pymel.core as pm
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
    from .blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None

try:
    from .blendshape_delta import BlendshapeDeltaEngine, BlendshapeDelta, VertexDelta
except ImportError:
    BlendshapeDeltaEngine = None
    BlendshapeDelta = None
    VertexDelta = None

try:
    from .blendshape_combiner import BlendshapeCombiner, BlendshapeCombination, CombinationMode
except ImportError:
    BlendshapeCombiner = None
    BlendshapeCombination = None
    CombinationMode = None

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
        duplicate_mesh, freeze_transforms, remove_namespace, get_mesh_center,
        distance_point_to_point, normalize_vector, get_mesh_bounding_box
    )
except ImportError:
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
    def get_mesh_center(m): return (0,0,0)
    def distance_point_to_point(a,b): return 0.0
    def normalize_vector(v): return (0,0,0)
    def get_mesh_bounding_box(m): return ((0,0,0),(0,0,0))

try:
    from .blendshape_pose import PoseManager
except ImportError:
    PoseManager = None

try:
    from .blendshape_driver import BlendshapeDriver, DriverType
except ImportError:
    BlendshapeDriver = None
    DriverType = None

try:
    from .blendshape_generator import BlendshapeGenerator, GenerationTarget, GeneratorType
except ImportError:
    BlendshapeGenerator = None
    GenerationTarget = None
    GeneratorType = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager
except ImportError:
    BlendshadeInbetweenManager = None

try:
    from .blendshape_optimizer import BlendshapeOptimizer
except ImportError:
    BlendshapeOptimizer = None

try:
    from ..blendshapes.arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class CorrectiveError(Exception):
    """Base exception for corrective operations."""
    pass

class CorrectiveNotFoundError(CorrectiveError):
    """Raised when a corrective definition is not found."""
    pass

class CorrectiveCreationError(CorrectiveError):
    """Raised when corrective creation fails."""
    pass

class CorrectiveValidationError(CorrectiveError):
    """Raised when corrective validation fails."""
    pass

class CorrectiveSolverError(CorrectiveError):
    """Raised when corrective solver encounters an error."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class CorrectiveType(Enum):
    """Types of corrective targets."""
    POSE_SPACE = "pose_space"
    JOINT = "joint"
    BLENDSHAPE = "blendshape"
    ARKIT = "arkit"
    AUTOMATIC = "automatic"
    CUSTOM = "custom"


class TriggerType(Enum):
    """What triggers a corrective."""
    JOINT_ROTATION = "joint_rotation"
    JOINT_TRANSLATION = "joint_translation"
    BLENDSHAPE_WEIGHT = "blendshape_weight"
    CONTROLLER = "controller"
    ARKIT = "arkit"
    SDK = "sdk"
    CUSTOM = "custom"


class SolverMode(Enum):
    """How corrective weights are solved."""
    LINEAR = "linear"
    PSD = "psd"
    MATRIX = "matrix"
    DELTA = "delta"
    HYBRID = "hybrid"


class EvaluationMode(Enum):
    """Evaluation mode for corrective network."""
    REALTIME = "realtime"
    MANUAL = "manual"
    BAKED = "baked"
    GPU = "gpu"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CorrectiveDefinition:
    """Definition of a corrective target."""
    name: str
    corrective_type: CorrectiveType
    triggers: List[Tuple[TriggerType, str]]  # List of (trigger type, source identifier)
    target_blendshape: str  # The blendshape target name
    weight: float = 1.0
    solver_mode: SolverMode = SolverMode.LINEAR
    enabled: bool = True
    priority: int = 0  # Higher priority applies first (lower number = higher priority)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrectiveTarget:
    """A corrective target mesh (the result of corrective)."""
    name: str
    mesh: str
    base_mesh: str
    delta: Optional[BlendshapeDelta] = None


@dataclass
class CorrectivePose:
    """A pose used in PSD corrective generation."""
    name: str
    joints: Dict[str, Tuple[float, float, float]]  # joint -> (rx, ry, rz)
    blendshapes: Dict[str, float]  # blendshape -> weight
    mesh: Optional[str] = None


@dataclass
class CorrectiveRule:
    """A rule for evaluating corrective activation."""
    triggers: List[Tuple[TriggerType, str]]
    threshold: float = 0.5  # Weight threshold for activation
    function: Optional[Callable[[Dict[str, float]], float]] = None  # Custom evaluation


@dataclass
class CorrectiveSettings:
    """Settings for corrective operations."""
    solver_mode: SolverMode = SolverMode.LINEAR
    evaluation_mode: EvaluationMode = EvaluationMode.REALTIME
    auto_generate_threshold: float = 0.05  # Deformation magnitude threshold
    validate: bool = True
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class CorrectiveStatistics:
    """Statistics for corrective system."""
    total_correctives: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    active_correctives: int = 0
    disabled_correctives: int = 0
    average_triggers: float = 0.0


@dataclass
class CorrectiveReport:
    """Diagnostic report."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[CorrectiveStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Corrective Manager ---------------------------------------

class BlendshapeCorrectiveManager:
    """
    Main controller for corrective blendshape system.
    """
    def __init__(self):
        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._delta_engine = BlendshapeDeltaEngine() if BlendshapeDeltaEngine else None
        self._combiner = BlendshapeCombiner() if BlendshapeCombiner else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._driver = BlendshapeDriver() if BlendshapeDriver else None
        self._pose_manager = PoseManager() if PoseManager else None
        self._generator = BlendshapeGenerator() if BlendshapeGenerator else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._optimizer = BlendshapeOptimizer() if BlendshapeOptimizer else None

        self._settings = CorrectiveSettings()
        self._last_report: Optional[CorrectiveReport] = None
        self._last_stats: Optional[CorrectiveStatistics] = None
        self._definitions: Dict[str, CorrectiveDefinition] = {}  # name -> definition
        self._targets: Dict[str, CorrectiveTarget] = {}  # name -> target mesh info

    # ---- Creation Methods ----

    def create_psd_corrective(
        self,
        name: str,
        base_mesh: str,
        joint_name: str,
        joint_axis: str,
        min_angle: float,
        max_angle: float,
        corrective_mesh: Optional[str] = None,
    ) -> CorrectiveDefinition:
        """
        Create a PSD (Pose Space Deformation) corrective for a joint rotation.
        """
        # Validate joint
        if not cmds.objExists(joint_name) or cmds.nodeType(joint_name) != 'joint':
            raise CorrectiveCreationError(f"Joint '{joint_name}' does not exist or is not a joint")
        # Axis validation
        if joint_axis not in ('rx', 'ry', 'rz'):
            raise CorrectiveCreationError(f"Invalid joint axis: {joint_axis}. Must be 'rx', 'ry', or 'rz'.")

        # Create a target mesh (if not provided, generate one)
        if corrective_mesh is None:
            corrective_mesh = self._generate_corrective_mesh_from_pose(
                base_mesh, {joint_name: {joint_axis: 1.0}},
                name
            )
            if not corrective_mesh:
                raise CorrectiveCreationError("Failed to generate corrective mesh")

        # Register definition
        defn = CorrectiveDefinition(
            name=name,
            corrective_type=CorrectiveType.POSE_SPACE,
            triggers=[(TriggerType.JOINT_ROTATION, joint_name)],
            target_blendshape=name,
            solver_mode=SolverMode.PSD,
            metadata={
                'joint': joint_name,
                'axis': joint_axis,
                'min_angle': min_angle,
                'max_angle': max_angle,
                'mesh': corrective_mesh,
            }
        )
        self._definitions[name] = defn
        self._targets[name] = CorrectiveTarget(
            name=name,
            mesh=corrective_mesh,
            base_mesh=base_mesh,
        )

        # Compute delta
        if self._delta_engine:
            delta = self._delta_engine.compute(base_mesh, corrective_mesh, name)
            self._targets[name].delta = delta
            self._delta_engine.add(delta)

        logger.info(f"Created PSD corrective '{name}' for joint '{joint_name}.{joint_axis}'")
        return defn

    def create_joint_corrective(
        self,
        name: str,
        base_mesh: str,
        joint_name: str,
        corrective_mesh: Optional[str] = None,
    ) -> CorrectiveDefinition:
        """
        Create a joint corrective (general) from a joint's deformation.
        """
        # Similar to PSD but more general
        if not cmds.objExists(joint_name) or cmds.nodeType(joint_name) != 'joint':
            raise CorrectiveCreationError(f"Joint '{joint_name}' does not exist or is not a joint")
        if corrective_mesh is None:
            # Generate a mesh by sampling the joint at neutral pose and at some rotation?
            # For simplicity, we'll use a placeholder.
            corrective_mesh = duplicate_mesh(base_mesh, f"{name}_mesh")
            if not corrective_mesh:
                raise CorrectiveCreationError("Failed to duplicate base mesh")
            # Apply a simple deformation to simulate corrective
            self._apply_simple_deformation(corrective_mesh)

        defn = CorrectiveDefinition(
            name=name,
            corrective_type=CorrectiveType.JOINT,
            triggers=[(TriggerType.JOINT_ROTATION, joint_name)],
            target_blendshape=name,
            solver_mode=SolverMode.LINEAR,
            metadata={'joint': joint_name, 'mesh': corrective_mesh}
        )
        self._definitions[name] = defn
        self._targets[name] = CorrectiveTarget(name=name, mesh=corrective_mesh, base_mesh=base_mesh)
        if self._delta_engine:
            delta = self._delta_engine.compute(base_mesh, corrective_mesh, name)
            self._targets[name].delta = delta
            self._delta_engine.add(delta)
        logger.info(f"Created joint corrective '{name}' for joint '{joint_name}'")
        return defn

    def create_blendshape_corrective(
        self,
        name: str,
        base_mesh: str,
        source_targets: List[str],
        corrective_mesh: Optional[str] = None,
        combination_mode: str = "add",
    ) -> CorrectiveDefinition:
        """
        Create a corrective for a combination of blendshape targets.
        Example: Smile + JawOpen.
        """
        if not source_targets:
            raise CorrectiveCreationError("At least one source target must be provided")
        # Validate that source targets exist in the scene
        valid_targets = []
        for t in source_targets:
            if self._driver:
                # Check if target exists in driver system
                # For simplicity, we check if the target exists in a blendshape node.
                if self._find_blendshape_node_for_target(t):
                    valid_targets.append(t)
                else:
                    logger.warning(f"Target '{t}' not found in any blendshape node; skipping.")
            else:
                # Fallback: assume it exists
                valid_targets.append(t)
        if not valid_targets:
            raise CorrectiveCreationError("No valid source targets found")

        # Generate corrective mesh if not provided
        if corrective_mesh is None:
            # Use combiner to combine targets and generate a mesh
            if self._combiner and self._delta_engine:
                # We need to combine the deltas of the source targets
                # This is a placeholder: we'll use combiner to generate combined mesh.
                # For now, duplicate base mesh and apply a combined deformation.
                corrective_mesh = self._generate_combined_mesh(base_mesh, valid_targets, name)
                if not corrective_mesh:
                    raise CorrectiveCreationError("Failed to generate combined corrective mesh")
            else:
                corrective_mesh = duplicate_mesh(base_mesh, f"{name}_mesh")
                self._apply_simple_deformation(corrective_mesh)

        defn = CorrectiveDefinition(
            name=name,
            corrective_type=CorrectiveType.BLENDSHAPE,
            triggers=[(TriggerType.BLENDSHAPE_WEIGHT, t) for t in valid_targets],
            target_blendshape=name,
            solver_mode=SolverMode.LINEAR,
            metadata={'source_targets': valid_targets, 'combination_mode': combination_mode, 'mesh': corrective_mesh}
        )
        self._definitions[name] = defn
        self._targets[name] = CorrectiveTarget(name=name, mesh=corrective_mesh, base_mesh=base_mesh)
        if self._delta_engine:
            delta = self._delta_engine.compute(base_mesh, corrective_mesh, name)
            self._targets[name].delta = delta
            self._delta_engine.add(delta)
        logger.info(f"Created blendshape corrective '{name}' for targets {valid_targets}")
        return defn

    def create_arkit_corrective(
        self,
        name: str,
        base_mesh: str,
        arkit_channel: str,
        corrective_mesh: Optional[str] = None,
    ) -> CorrectiveDefinition:
        """
        Create an ARKit-specific corrective (e.g., for jawOpen at extreme values).
        """
        if arkit_channel not in ARKIT_SET:
            logger.warning(f"ARKit channel '{arkit_channel}' not in standard ARKit list; continuing.")
        if corrective_mesh is None:
            corrective_mesh = duplicate_mesh(base_mesh, f"{name}_mesh")
            self._apply_simple_deformation(corrective_mesh)

        defn = CorrectiveDefinition(
            name=name,
            corrective_type=CorrectiveType.ARKIT,
            triggers=[(TriggerType.ARKIT, arkit_channel)],
            target_blendshape=name,
            solver_mode=SolverMode.LINEAR,
            metadata={'arkit_channel': arkit_channel, 'mesh': corrective_mesh}
        )
        self._definitions[name] = defn
        self._targets[name] = CorrectiveTarget(name=name, mesh=corrective_mesh, base_mesh=base_mesh)
        if self._delta_engine:
            delta = self._delta_engine.compute(base_mesh, corrective_mesh, name)
            self._targets[name].delta = delta
            self._delta_engine.add(delta)
        logger.info(f"Created ARKit corrective '{name}' for channel '{arkit_channel}'")
        return defn

    # ---- Evaluation ----

    def evaluate(self, frame: Dict[str, float]) -> Dict[str, float]:
        """
        Evaluate corrective weights based on current driver values.
        frame: Dict of driver name -> value (e.g., {'jawOpen': 0.5, 'CTRL_smile.tx': 0.7})
        Returns: Dict of corrective target name -> weight.
        """
        result = {}
        for name, defn in self._definitions.items():
            if not defn.enabled:
                continue
            # Evaluate triggers
            weight = self._evaluate_definition(defn, frame)
            if weight is not None:
                result[name] = weight * defn.weight
        # Apply priority? Could be handled in driver.
        return result

    def _evaluate_definition(self, defn: CorrectiveDefinition, frame: Dict[str, float]) -> Optional[float]:
        """
        Evaluate a single corrective definition.
        Returns the weight to apply (0-1), or None if not triggered.
        """
        # Determine trigger values
        trigger_values = []
        for trigger_type, trigger_id in defn.triggers:
            if trigger_type == TriggerType.JOINT_ROTATION:
                # For joints, we expect frame to contain joint rotation values.
                # Frame may have key like 'joint.rx' or 'joint|rx'? We'll use a heuristic.
                # For simplicity, we'll check if trigger_id exists in frame directly.
                if trigger_id in frame:
                    trigger_values.append(abs(frame[trigger_id]))
                else:
                    # Try to get from Maya directly if not in frame
                    if cmds.objExists(trigger_id):
                        # Get current rotation
                        rot = cmds.getAttr(f"{trigger_id}.r")[0]
                        # We need axis; we can't infer from id alone. We'll use the defn's metadata.
                        # For now, we'll use the absolute value of the rotation magnitude.
                        # Better: use the specific axis from metadata.
                        axis = defn.metadata.get('axis', 'rx')
                        # We'll not implement full axis support here.
                        trigger_values.append(abs(rot[0]))  # dummy
            elif trigger_type == TriggerType.BLENDSHAPE_WEIGHT:
                # Frame may contain blendshape weights
                if trigger_id in frame:
                    trigger_values.append(frame[trigger_id])
                else:
                    # Try to get from Maya
                    # Find the blendshape node that has this target
                    bs_node = self._find_blendshape_node_for_target(trigger_id)
                    if bs_node:
                        weight = get_blendshape_weight(bs_node, trigger_id)
                        trigger_values.append(weight)
                    else:
                        trigger_values.append(0.0)
            elif trigger_type == TriggerType.ARKIT:
                if trigger_id in frame:
                    trigger_values.append(frame[trigger_id])
                else:
                    # Assume default 0
                    trigger_values.append(0.0)
            else:
                # For other types, assume value from frame or 0
                trigger_values.append(frame.get(trigger_id, 0.0))

        # Determine if triggers are active (all triggers above threshold? Or any?)
        # For simplicity, we compute the average of trigger values.
        if not trigger_values:
            return None
        avg = sum(trigger_values) / len(trigger_values)
        # Apply a threshold
        threshold = 0.1  # Could be per-definition
        if avg < threshold:
            return None
        # For PSD, we might use a custom function.
        if defn.solver_mode == SolverMode.PSD:
            # Apply PSD logic (linear interpolation between min and max angles)
            # Use metadata for min/max.
            min_angle = defn.metadata.get('min_angle', -45.0)
            max_angle = defn.metadata.get('max_angle', 45.0)
            # Assuming the trigger value is the absolute joint rotation.
            # We map the rotation to 0-1 range.
            if max_angle != min_angle:
                t = (avg - min_angle) / (max_angle - min_angle)
                return clamp(t, 0.0, 1.0)
            else:
                return 1.0 if avg > min_angle else 0.0
        else:
            # Linear solver: scale by trigger average
            return clamp(avg, 0.0, 1.0)

    def _find_blendshape_node_for_target(self, target: str) -> Optional[str]:
        """Find the blendshape node that contains a given target alias."""
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            if target in targets:
                return node
        return None

    # ---- Delete, Edit ----

    def delete_corrective(self, name: str) -> bool:
        """Delete a corrective definition and its target mesh (optional)."""
        if name not in self._definitions:
            return False
        defn = self._definitions[name]
        # Delete target mesh if it's a generated mesh
        if name in self._targets:
            mesh = self._targets[name].mesh
            if cmds.objExists(mesh) and mesh not in self._definitions:  # Not shared
                cmds.delete(mesh)
            del self._targets[name]
        # Remove from delta engine
        if self._delta_engine:
            self._delta_engine.remove(name)
        del self._definitions[name]
        logger.info(f"Deleted corrective '{name}'")
        return True

    def rename_corrective(self, old_name: str, new_name: str) -> bool:
        """Rename a corrective definition."""
        if old_name not in self._definitions:
            return False
        if new_name in self._definitions:
            return False
        defn = self._definitions.pop(old_name)
        defn.name = new_name
        self._definitions[new_name] = defn
        if old_name in self._targets:
            target = self._targets.pop(old_name)
            target.name = new_name
            self._targets[new_name] = target
        logger.info(f"Renamed corrective '{old_name}' to '{new_name}'")
        return True

    def enable_corrective(self, name: str, enabled: bool = True) -> bool:
        """Enable or disable a corrective."""
        if name not in self._definitions:
            return False
        self._definitions[name].enabled = enabled
        return True

    # ---- Automatic Generation ----

    def auto_generate(
        self,
        base_mesh: str,
        source_mesh: str,
        driver_values: Dict[str, float],
        threshold: float = 0.05,
    ) -> List[str]:
        """
        Automatically detect deformation errors and generate corrective targets.
        """
        # Compare base_mesh and source_mesh (deformed by some drivers).
        # Identify vertices with large deltas.
        # Group them into clusters and generate corrective mesh.
        generated = []
        # Placeholder: use delta engine to compute difference.
        if self._delta_engine:
            delta = self._delta_engine.compute(base_mesh, source_mesh, "temp_delta")
            if not delta:
                return []
            # Analyze delta magnitudes
            active = [d for d in delta.deltas if d.magnitude() > threshold]
            if not active:
                logger.info("No significant deformation detected for automatic corrective")
                return []
            # Generate a mesh from the delta (apply to base mesh)
            corrective_mesh = self._delta_engine.apply(base_mesh, delta, output_mesh=f"auto_corr_{int(time.time())}")
            if corrective_mesh:
                # Register as a corrective
                name = f"auto_corrective_{len(self._definitions)}"
                defn = CorrectiveDefinition(
                    name=name,
                    corrective_type=CorrectiveType.AUTOMATIC,
                    triggers=[(TriggerType.CUSTOM, "auto")],
                    target_blendshape=name,
                    metadata={'source': source_mesh}
                )
                self._definitions[name] = defn
                self._targets[name] = CorrectiveTarget(name=name, mesh=corrective_mesh, base_mesh=base_mesh)
                if self._delta_engine:
                    self._delta_engine.add(delta)
                generated.append(name)
                logger.info(f"Generated automatic corrective '{name}' with {len(active)} active vertices")
        return generated

    # ---- Batch Processing ----

    def batch_generate_psd(
        self,
        base_mesh: str,
        joint_definitions: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Generate PSD correctives for multiple joints/axes.
        joint_definitions: list of dicts with 'joint', 'axis', 'min', 'max', 'name'
        """
        results = []
        for jdef in joint_definitions:
            name = jdef.get('name', f"psd_{jdef['joint']}_{jdef['axis']}")
            try:
                defn = self.create_psd_corrective(
                    name=name,
                    base_mesh=base_mesh,
                    joint_name=jdef['joint'],
                    joint_axis=jdef['axis'],
                    min_angle=jdef.get('min', -45.0),
                    max_angle=jdef.get('max', 45.0),
                )
                results.append(name)
            except Exception as e:
                logger.error(f"Failed to generate PSD for {name}: {e}")
        return results

    # ---- Validation ----

    def validate(self) -> CorrectiveReport:
        """Validate all corrective definitions and targets."""
        report = CorrectiveReport(success=True)
        for name, defn in self._definitions.items():
            # Check target mesh exists
            if name in self._targets:
                mesh = self._targets[name].mesh
                if not cmds.objExists(mesh):
                    report.errors.append(f"Target mesh for corrective '{name}' does not exist: {mesh}")
                    report.success = False
            else:
                report.warnings.append(f"No target data for corrective '{name}'")
            # Check triggers
            for trigger_type, trigger_id in defn.triggers:
                if trigger_type in (TriggerType.JOINT_ROTATION, TriggerType.JOINT_TRANSLATION):
                    if not cmds.objExists(trigger_id) or cmds.nodeType(trigger_id) != 'joint':
                        report.errors.append(f"Joint '{trigger_id}' for corrective '{name}' does not exist")
                        report.success = False
                elif trigger_type == TriggerType.BLENDSHAPE_WEIGHT:
                    # Check if the target exists somewhere
                    bs_node = self._find_blendshape_node_for_target(trigger_id)
                    if not bs_node:
                        report.warnings.append(f"Blendshape target '{trigger_id}' for corrective '{name}' not found in any node")
        # Compute statistics
        stats = self.get_statistics()
        report.statistics = stats
        self._last_report = report
        return report

    # ---- Statistics ----

    def get_statistics(self) -> CorrectiveStatistics:
        """Compute statistics for corrective system."""
        stats = CorrectiveStatistics()
        stats.total_correctives = len(self._definitions)
        by_type = {}
        active = 0
        disabled = 0
        total_triggers = 0
        for defn in self._definitions.values():
            by_type[defn.corrective_type.value] = by_type.get(defn.corrective_type.value, 0) + 1
            if defn.enabled:
                active += 1
            else:
                disabled += 1
            total_triggers += len(defn.triggers)
        stats.by_type = by_type
        stats.active_correctives = active
        stats.disabled_correctives = disabled
        if stats.total_correctives > 0:
            stats.average_triggers = total_triggers / stats.total_correctives
        return stats

    # ---- Utilities ----

    def _generate_corrective_mesh_from_pose(
        self,
        base_mesh: str,
        joint_rotations: Dict[str, Dict[str, float]],
        name: str
    ) -> Optional[str]:
        """
        Generate a corrective mesh by sampling a pose.
        This is a placeholder: in production, we would use actual deformation.
        """
        # Duplicate base mesh
        new_mesh = duplicate_mesh(base_mesh, f"{name}_mesh")
        if not new_mesh:
            return None
        # Apply simple deformation: move vertices slightly
        vert_count = get_mesh_vertex_count(new_mesh)
        if vert_count > 0:
            # Move a few vertices based on joint rotations
            total_rotation = sum(abs(v) for rot in joint_rotations.values() for v in rot.values())
            scale = clamp(total_rotation * 0.01, 0.0, 0.05)
            for i in range(min(20, vert_count)):
                pos = get_vertex_position(new_mesh, i)
                if pos:
                    new_pos = (pos[0] + scale * (i % 3 - 1) * 0.01,
                               pos[1] + scale * ((i+1) % 3 - 1) * 0.01,
                               pos[2] + scale * ((i+2) % 3 - 1) * 0.01)
                    set_vertex_position(new_mesh, i, new_pos)
        freeze_transforms(new_mesh)
        return new_mesh

    def _generate_combined_mesh(self, base_mesh: str, target_names: List[str], name: str) -> Optional[str]:
        """Generate a mesh combining multiple blendshape targets."""
        # Placeholder: use combiner to blend deltas
        if self._combiner and self._delta_engine:
            # Retrieve deltas for each target
            deltas = []
            for t in target_names:
                delta = self._delta_engine.get(t)
                if delta:
                    deltas.append(delta)
                else:
                    # Try to compute delta from blendshape node
                    bs_node = self._find_blendshape_node_for_target(t)
                    if bs_node:
                        # Need the target mesh for this target
                        # We'll assume we can get it via connection.
                        # This is complex; fallback to simple duplication.
                        pass
            if deltas:
                # Combine deltas (additive)
                combined = deltas[0]
                for d in deltas[1:]:
                    # We need to combine vertex by vertex.
                    # This is simplified; in production, we'd use combiner.
                    pass
                # Apply combined delta to base mesh
                combined_delta = self._delta_engine._combine_deltas_python(deltas, [1.0]*len(deltas), CombinationMode.ADD, get_mesh_vertex_count(base_mesh))
                if combined_delta:
                    new_mesh = self._delta_engine.apply(base_mesh, combined_delta, output_mesh=f"{name}_mesh")
                    return new_mesh
        # Fallback: duplicate and deform
        new_mesh = duplicate_mesh(base_mesh, f"{name}_mesh")
        if not new_mesh:
            return None
        # Apply a generic deformation
        vert_count = get_mesh_vertex_count(new_mesh)
        if vert_count > 0:
            for i in range(min(10, vert_count)):
                pos = get_vertex_position(new_mesh, i)
                if pos:
                    new_pos = (pos[0] + 0.01, pos[1] + 0.015, pos[2] + 0.005)
                    set_vertex_position(new_mesh, i, new_pos)
        freeze_transforms(new_mesh)
        return new_mesh

    def _apply_simple_deformation(self, mesh: str) -> None:
        """Apply a small deformation to a mesh (for testing)."""
        vert_count = get_mesh_vertex_count(mesh)
        if vert_count > 0:
            for i in range(min(20, vert_count)):
                pos = get_vertex_position(mesh, i)
                if pos:
                    new_pos = (pos[0] + 0.01, pos[1] + 0.01, pos[2] + 0.01)
                    set_vertex_position(mesh, i, new_pos)
        freeze_transforms(mesh)

    # ---- Settings ----

    def set_settings(self, settings: CorrectiveSettings) -> None:
        self._settings = settings

    def get_settings(self) -> CorrectiveSettings:
        return self._settings

    # ---- Reports ----

    def get_last_report(self) -> Optional[CorrectiveReport]:
        return self._last_report

    def reset(self) -> None:
        self._definitions.clear()
        self._targets.clear()
        self._last_report = None
        self._last_stats = None


# ---- Part 14: Utilities -----------------------------------------------

def get_corrective_definitions(manager: BlendshapeCorrectiveManager) -> Dict[str, CorrectiveDefinition]:
    """Return all corrective definitions from a manager."""
    return manager._definitions


def has_correctives(manager: BlendshapeCorrectiveManager) -> bool:
    """Check if the manager has any corrective definitions."""
    return len(manager._definitions) > 0


# ---- Part 15: Public API -----------------------------------------------

__all__ = [
    "BlendshapeCorrectiveManager",
    "CorrectiveDefinition",
    "CorrectiveTarget",
    "CorrectivePose",
    "CorrectiveRule",
    "CorrectiveSettings",
    "CorrectiveStatistics",
    "CorrectiveReport",
    "CorrectiveType",
    "TriggerType",
    "SolverMode",
    "EvaluationMode",
    "CorrectiveError",
    "CorrectiveNotFoundError",
    "CorrectiveCreationError",
    "CorrectiveValidationError",
    "CorrectiveSolverError",
    "get_corrective_definitions",
    "has_correctives",
]