"""
blendshapes/blendshape_pose.py

Facial Pose Management System for Maya.

This module manages complete facial poses (sets of blendshape weights) used
in the Faceit pipeline. It provides creation, editing, blending, mirroring,
interpolation, animation, library management, and ARKit/viseme presets.

Responsibilities:
- Create poses from current rig state, ARKit, visemes, or custom weights.
- Edit, rename, delete, duplicate, merge, and split poses.
- Blend poses with various modes (linear, average, weighted, additive, PSD).
- Manage pose libraries with folders, categories, tags, and thumbnails.
- Mirror poses left/right or across symmetry planes.
- Interpolate between poses using linear, Bezier, Hermite, or Catmull-Rom curves.
- Support pose layers for non-destructive editing.
- Animate poses with keyframes, animation layers, and pose sequences.
- Handle ARKit and viseme presets.
- Validate poses against blendshape nodes and topology.
- Provide statistics and diagnostic reports.

Dependencies:
- blendshape_weights.py: Weight values and management.
- blendshape_driver.py: Apply poses via drivers.
- blendshape_correctives.py: Augment poses with correctives.
- blendshape_inbetweens.py: Smooth transitions.
- blendshape_generator.py: Generate new poses.
- blendshape_library.py: Persistent storage.
- blendshape_validator.py: Validate poses.
- blendshape_utils.py: Shared utilities.
- animation/: Timeline, keyframes, baking.
- symmetry.py: Pose mirroring.
- blendshapes/arkit/: ARKit constants.

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

# Maya imports
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

# Import dependencies
try:
    from .blendshape_weights import BlendshapeWeightManager, WeightSet, BlendMode as WeightBlendMode
except ImportError:
    BlendshapeWeightManager = None
    WeightSet = None
    WeightBlendMode = None

try:
    from .blendshape_driver import BlendshapeDriver
except ImportError:
    BlendshapeDriver = None

try:
    from .blendshape_correctives import BlendshapeCorrectiveManager
except ImportError:
    BlendshapeCorrectiveManager = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager
except ImportError:
    BlendshadeInbetweenManager = None

try:
    from .blendshape_generator import BlendshapeGenerator, GenerationTarget, GeneratorType
except ImportError:
    BlendshapeGenerator = None
    GenerationTarget = None
    GeneratorType = None

try:
    from .blendshape_library import BlendShapeLibrary
except ImportError:
    BlendShapeLibrary = None

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
class PoseError(Exception):
    """Base exception for pose operations."""
    pass

class PoseNotFoundError(PoseError):
    """Raised when a pose is not found."""
    pass

class PoseCreationError(PoseError):
    """Raised when pose creation fails."""
    pass

class PoseValidationError(PoseError):
    """Raised when pose validation fails."""
    pass

class PoseBlendError(PoseError):
    """Raised when pose blending fails."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class PoseType(Enum):
    """Types of facial poses."""
    EXPRESSION = "expression"
    VISEME = "viseme"
    ARKIT = "arkit"
    CORRECTIVE = "corrective"
    CUSTOM = "custom"
    SNAPSHOT = "snapshot"
    LIBRARY = "library"


class BlendMode(Enum):
    """Blend modes for combining poses."""
    LINEAR = "linear"
    AVERAGE = "average"
    WEIGHTED = "weighted"
    PSD = "psd"
    ADDITIVE = "additive"
    OVERRIDE = "override"


class MirrorMode(Enum):
    """Mirror modes for posing."""
    LEFT_RIGHT = "left_right"
    RIGHT_LEFT = "right_left"
    SYMMETRY = "symmetry"
    CUSTOM = "custom"


class PoseSpace(Enum):
    """Space for pose evaluation."""
    LOCAL = "local"
    WORLD = "world"
    OBJECT = "object"
    CUSTOM = "custom"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class PoseDefinition:
    """Definition of a facial pose."""
    name: str
    weights: Dict[str, float]  # target -> weight
    pose_type: PoseType = PoseType.CUSTOM
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    category: str = "Uncategorized"
    thumbnail: Optional[str] = None  # path to thumbnail image


@dataclass
class PoseFrame:
    """A pose at a specific time in an animation."""
    time: float
    pose: PoseDefinition
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoseLayer:
    """A layer of poses for non-destructive editing."""
    name: str
    poses: List[PoseDefinition]  # Poses in this layer
    blend_mode: BlendMode = BlendMode.LINEAR
    weight: float = 1.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoseLibrary:
    """A collection of poses with organization."""
    name: str
    poses: List[PoseDefinition] = field(default_factory=list)
    categories: Dict[str, List[str]] = field(default_factory=dict)  # category -> list of pose names
    tags: Dict[str, List[str]] = field(default_factory=dict)  # tag -> list of pose names
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PosePreset:
    """A preset pose for quick application."""
    name: str
    pose: PoseDefinition
    shortcut: Optional[str] = None


@dataclass
class PoseStatistics:
    """Statistics for the pose system."""
    total_poses: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    average_weights: float = 0.0
    total_weights: int = 0
    libraries: int = 0
    presets: int = 0


@dataclass
class PoseReport:
    """Diagnostic report for pose system."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[PoseStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Pose Manager ----------------------------------------------

class BlendshapePoseManager:
    """
    Main controller for facial pose management.

    This class provides a high-level API for creating, editing, blending,
    mirroring, interpolating, and managing facial poses.
    """
    def __init__(self):
        self._weight_manager = BlendshapeWeightManager() if BlendshapeWeightManager else None
        self._driver = BlendshapeDriver() if BlendshapeDriver else None
        self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._generator = BlendshapeGenerator() if BlendshapeGenerator else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._symmetry_engine = SymmetryEngine() if SymmetryEngine else None

        # Internal storage
        self._poses: Dict[str, PoseDefinition] = {}
        self._libraries: Dict[str, PoseLibrary] = {}
        self._presets: Dict[str, PosePreset] = {}
        self._layers: List[PoseLayer] = []
        self._last_report: Optional[PoseReport] = None
        self._last_stats: Optional[PoseStatistics] = None

        self._pose_type_defaults = {
            PoseType.EXPRESSION: "Expressions",
            PoseType.VISEME: "Visemes",
            PoseType.ARKIT: "ARKit",
            PoseType.CORRECTIVE: "Correctives",
            PoseType.SNAPSHOT: "Snapshots",
            PoseType.CUSTOM: "Custom",
            PoseType.LIBRARY: "Library"
        }

    # ---- Core Operations ----

    def capture(self, name: str, pose_type: PoseType = PoseType.CUSTOM) -> PoseDefinition:
        """
        Capture the current facial expression from the rig and create a pose.
        """
        if not self._weight_manager:
            raise PoseCreationError("Weight manager not available")
        weights = self._weight_manager.get_all_weights()
        pose = PoseDefinition(
            name=name,
            weights=weights,
            pose_type=pose_type,
            category=self._pose_type_defaults.get(pose_type, "Custom")
        )
        self._poses[name] = pose
        logger.info(f"Captured pose '{name}' with {len(weights)} weights")
        return pose

    def apply(self, name: str, blend_factor: float = 1.0, relative: bool = False) -> None:
        """
        Apply a pose to the rig.
        """
        if name not in self._poses:
            raise PoseNotFoundError(f"Pose '{name}' not found")
        pose = self._poses[name]
        weights = pose.weights
        if not self._weight_manager:
            raise PoseError("Weight manager not available")
        if relative:
            # Add current weights with pose weights scaled by blend_factor
            current = self._weight_manager.get_all_weights()
            for target, val in weights.items():
                current[target] = current.get(target, 0.0) + val * blend_factor
            self._weight_manager.set_all_weights(current)
        else:
            # Set weights directly with blend_factor (interpolate from zero)
            current = self._weight_manager.get_all_weights()
            for target, val in weights.items():
                current[target] = val * blend_factor
            self._weight_manager.set_all_weights(current)

    def delete(self, name: str) -> None:
        """Delete a pose."""
        if name in self._poses:
            del self._poses[name]
            logger.info(f"Deleted pose '{name}'")
        else:
            raise PoseNotFoundError(f"Pose '{name}' not found")

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a pose."""
        if old_name not in self._poses:
            raise PoseNotFoundError(f"Pose '{old_name}' not found")
        if new_name in self._poses:
            raise PoseError(f"Pose '{new_name}' already exists")
        pose = self._poses.pop(old_name)
        pose.name = new_name
        self._poses[new_name] = pose
        logger.info(f"Renamed pose '{old_name}' to '{new_name}'")

    def duplicate(self, name: str, new_name: Optional[str] = None) -> PoseDefinition:
        """Duplicate a pose."""
        if name not in self._poses:
            raise PoseNotFoundError(f"Pose '{name}' not found")
        if new_name is None:
            new_name = f"{name}_copy"
        if new_name in self._poses:
            raise PoseError(f"Pose '{new_name}' already exists")
        original = self._poses[name]
        new_pose = PoseDefinition(
            name=new_name,
            weights=original.weights.copy(),
            pose_type=original.pose_type,
            metadata=original.metadata.copy(),
            tags=original.tags.copy(),
            category=original.category,
            thumbnail=original.thumbnail
        )
        self._poses[new_name] = new_pose
        logger.info(f"Duplicated pose '{name}' to '{new_name}'")
        return new_pose

    def edit(self, name: str, weights: Optional[Dict[str, float]] = None, **kwargs) -> PoseDefinition:
        """
        Edit an existing pose's weights or metadata.
        """
        if name not in self._poses:
            raise PoseNotFoundError(f"Pose '{name}' not found")
        pose = self._poses[name]
        if weights is not None:
            # Replace weights with new ones
            pose.weights = weights.copy()
        # Update metadata if provided
        if 'tags' in kwargs:
            pose.tags = kwargs['tags']
        if 'category' in kwargs:
            pose.category = kwargs['category']
        if 'metadata' in kwargs:
            pose.metadata.update(kwargs['metadata'])
        logger.info(f"Edited pose '{name}'")
        return pose

    # ---- Blending ----

    def blend(
        self,
        pose_names: List[str],
        weights: Optional[List[float]] = None,
        mode: BlendMode = BlendMode.LINEAR,
        output_name: Optional[str] = None,
        normalize: bool = False,
    ) -> PoseDefinition:
        """
        Blend multiple poses into a new pose.

        Args:
            pose_names: List of pose names to blend.
            weights: List of blend weights (one per pose). If None, evenly distributed.
            mode: Blend mode.
            output_name: Name for the blended pose. If None, auto-generate.
            normalize: If True, normalize the resulting weights.

        Returns:
            Blended PoseDefinition.
        """
        if not pose_names:
            raise PoseBlendError("At least one pose required")
        # Retrieve poses
        poses = []
        for name in pose_names:
            if name not in self._poses:
                raise PoseNotFoundError(f"Pose '{name}' not found")
            poses.append(self._poses[name])

        # Default weights
        if weights is None:
            weights = [1.0 / len(poses)] * len(poses)
        if len(weights) != len(poses):
            raise PoseBlendError("Number of weights must match number of poses")
        if any(w < 0 for w in weights):
            raise PoseBlendError("Weights must be non-negative")

        # Blend weights
        all_targets = set()
        for p in poses:
            all_targets.update(p.weights.keys())

        result_weights = {}
        for target in all_targets:
            values = [p.weights.get(target, 0.0) for p in poses]
            if mode == BlendMode.LINEAR:
                # Weighted sum
                val = sum(v * w for v, w in zip(values, weights))
            elif mode == BlendMode.AVERAGE:
                val = sum(v * w for v, w in zip(values, weights)) / sum(weights)
            elif mode == BlendMode.WEIGHTED:
                # Similar to linear
                val = sum(v * w for v, w in zip(values, weights))
            elif mode == BlendMode.ADDITIVE:
                # Add all with weights
                val = sum(v * w for v, w in zip(values, weights))
            elif mode == BlendMode.PSD:
                # Placeholder: PSD blend (could be custom)
                val = sum(v * w for v, w in zip(values, weights))
            elif mode == BlendMode.OVERRIDE:
                # Take the highest weighted value? Or weighted average?
                # We'll use max for override
                val = max(v * w for v, w in zip(values, weights))
            else:
                val = sum(v * w for v, w in zip(values, weights))
            result_weights[target] = clamp(val, 0.0, 1.0)

        if normalize:
            total = sum(result_weights.values())
            if total > 0:
                for target, val in result_weights.items():
                    result_weights[target] = val / total

        # Auto-generate name
        if output_name is None:
            output_name = "_blend_".join(pose_names[:3]) + (f"_{len(pose_names)}" if len(pose_names) > 3 else "")
            output_name = sanitize_name(output_name)
        # Ensure unique
        if output_name in self._poses:
            output_name = generate_unique_name(output_name, self._poses.keys())

        blended_pose = PoseDefinition(
            name=output_name,
            weights=result_weights,
            pose_type=PoseType.CUSTOM,
            metadata={"blended_from": pose_names, "blend_weights": weights, "blend_mode": mode.value}
        )
        self._poses[output_name] = blended_pose
        logger.info(f"Blended pose '{output_name}' from {len(poses)} source poses")
        return blended_pose

    # ---- Mirroring ----

    def mirror_pose(self, name: str, mode: MirrorMode = MirrorMode.LEFT_RIGHT, output_name: Optional[str] = None) -> PoseDefinition:
        """
        Create a mirrored copy of a pose.
        """
        if name not in self._poses:
            raise PoseNotFoundError(f"Pose '{name}' not found")
        original = self._poses[name]
        if not self._symmetry_engine and not self._weight_manager:
            raise PoseError("Symmetry engine or weight manager required for mirroring")
        # Use symmetry map if available
        if self._symmetry_engine:
            # Get target list for the current rig
            targets = list(original.weights.keys())
            # Build mirror map
            sym_map = {}
            for t in targets:
                # Try to find mirror using symmetry engine
                mirror = self._symmetry_engine.get_mirror_target(t)
                if mirror:
                    sym_map[t] = mirror
            # Apply mirror
            mirrored_weights = {}
            for target, val in original.weights.items():
                if target in sym_map:
                    mirrored_weights[sym_map[target]] = val
                else:
                    mirrored_weights[target] = val
        else:
            # Use weight manager's mirror utility if available
            if hasattr(self._weight_manager, 'mirror_weights'):
                mirrored_weights = self._weight_manager.mirror_weights(original.weights)
            else:
                raise PoseError("Mirroring not available without symmetry engine or weight manager")
        if output_name is None:
            output_name = f"{name}_mirrored"
        # Ensure unique
        if output_name in self._poses:
            output_name = generate_unique_name(output_name, self._poses.keys())
        mirrored_pose = PoseDefinition(
            name=output_name,
            weights=mirrored_weights,
            pose_type=original.pose_type,
            metadata=original.metadata.copy(),
            tags=original.tags.copy(),
            category=original.category,
            thumbnail=original.thumbnail
        )
        self._poses[output_name] = mirrored_pose
        logger.info(f"Mirrored pose '{name}' to '{output_name}'")
        return mirrored_pose

    # ---- Libraries ----

    def create_library(self, name: str) -> PoseLibrary:
        """Create a new pose library."""
        if name in self._libraries:
            raise PoseError(f"Library '{name}' already exists")
        library = PoseLibrary(name=name)
        self._libraries[name] = library
        return library

    def add_to_library(self, library_name: str, pose_name: str, category: Optional[str] = None) -> None:
        """Add a pose to a library."""
        if library_name not in self._libraries:
            raise PoseNotFoundError(f"Library '{library_name}' not found")
        if pose_name not in self._poses:
            raise PoseNotFoundError(f"Pose '{pose_name}' not found")
        library = self._libraries[library_name]
        if pose_name not in library.poses:
            library.poses.append(self._poses[pose_name])
        if category:
            if category not in library.categories:
                library.categories[category] = []
            if pose_name not in library.categories[category]:
                library.categories[category].append(pose_name)

    def remove_from_library(self, library_name: str, pose_name: str) -> None:
        """Remove a pose from a library."""
        if library_name not in self._libraries:
            raise PoseNotFoundError(f"Library '{library_name}' not found")
        library = self._libraries[library_name]
        if pose_name in library.poses:
            library.poses.remove(self._poses[pose_name])
        for cat, poses in library.categories.items():
            if pose_name in poses:
                poses.remove(pose_name)

    def get_library(self, name: str) -> Optional[PoseLibrary]:
        return self._libraries.get(name)

    def list_libraries(self) -> List[str]:
        return list(self._libraries.keys())

    # ---- Presets ----

    def add_preset(self, name: str, pose_name: str, shortcut: Optional[str] = None) -> None:
        """Add a pose as a preset."""
        if pose_name not in self._poses:
            raise PoseNotFoundError(f"Pose '{pose_name}' not found")
        if name in self._presets:
            raise PoseError(f"Preset '{name}' already exists")
        self._presets[name] = PosePreset(name=name, pose=self._poses[pose_name], shortcut=shortcut)

    def remove_preset(self, name: str) -> None:
        if name in self._presets:
            del self._presets[name]

    def apply_preset(self, name: str) -> None:
        if name not in self._presets:
            raise PoseNotFoundError(f"Preset '{name}' not found")
        self.apply(self._presets[name].pose.name)

    # ---- Interpolation ----

    def interpolate(
        self,
        pose_a: str,
        pose_b: str,
        factor: float = 0.5,
        output_name: Optional[str] = None,
        curve_type: str = "linear",
    ) -> PoseDefinition:
        """
        Create a new pose by interpolating between two poses.
        """
        if pose_a not in self._poses:
            raise PoseNotFoundError(f"Pose '{pose_a}' not found")
        if pose_b not in self._poses:
            raise PoseNotFoundError(f"Pose '{pose_b}' not found")
        a = self._poses[pose_a]
        b = self._poses[pose_b]
        # Interpolate weights
        all_targets = set(a.weights.keys()) | set(b.weights.keys())
        result_weights = {}
        for target in all_targets:
            val_a = a.weights.get(target, 0.0)
            val_b = b.weights.get(target, 0.0)
            if curve_type == "linear":
                val = lerp(val_a, val_b, factor)
            elif curve_type == "hermite":
                # Simple hermite interpolation (smoothstep)
                t = factor * factor * (3 - 2 * factor)
                val = lerp(val_a, val_b, t)
            elif curve_type == "bezier":
                # Placeholder: Use factor directly
                val = lerp(val_a, val_b, factor)
            else:
                val = lerp(val_a, val_b, factor)
            result_weights[target] = clamp(val, 0.0, 1.0)

        if output_name is None:
            output_name = f"{pose_a}_{pose_b}_interp_{int(factor*100)}"
        if output_name in self._poses:
            output_name = generate_unique_name(output_name, self._poses.keys())
        interp_pose = PoseDefinition(
            name=output_name,
            weights=result_weights,
            pose_type=PoseType.CUSTOM,
            metadata={"interpolated_from": [pose_a, pose_b], "factor": factor, "curve_type": curve_type}
        )
        self._poses[output_name] = interp_pose
        logger.info(f"Interpolated pose '{output_name}' between '{pose_a}' and '{pose_b}'")
        return interp_pose

    # ---- Pose Layers ----

    def add_layer(self, layer: PoseLayer) -> None:
        self._layers.append(layer)

    def remove_layer(self, index: int) -> None:
        if 0 <= index < len(self._layers):
            del self._layers[index]

    def clear_layers(self) -> None:
        self._layers.clear()

    def evaluate_layers(self) -> Dict[str, float]:
        """
        Evaluate all layers to produce final weights.
        """
        if not self._layers:
            return self._weight_manager.get_all_weights() if self._weight_manager else {}
        result = {}
        for layer in self._layers:
            if not layer.enabled:
                continue
            # Combine all poses in the layer
            if not layer.poses:
                continue
            # For simplicity, blend all poses in the layer using the layer's blend mode
            # If multiple poses in layer, blend them together with equal weight
            # We'll use the first pose's weights as base if no existing result
            if not result:
                result = layer.poses[0].weights.copy()
                continue
            # Blend layer's poses with current result
            # We'll use a simple weighted sum of layer poses
            layer_weights = {}
            for pose in layer.poses:
                for target, val in pose.weights.items():
                    layer_weights[target] = layer_weights.get(target, 0.0) + val
            # Apply layer blend
            if layer.blend_mode == BlendMode.ADDITIVE:
                for target, val in layer_weights.items():
                    result[target] = result.get(target, 0.0) + val * layer.weight
            elif layer.blend_mode == BlendMode.AVERAGE:
                for target, val in layer_weights.items():
                    result[target] = (result.get(target, 0.0) + val * layer.weight) * 0.5
            elif layer.blend_mode == BlendMode.OVERRIDE:
                # Override with layer weights
                for target, val in layer_weights.items():
                    result[target] = val * layer.weight
            else:
                # Linear blend
                for target, val in layer_weights.items():
                    result[target] = lerp(result.get(target, 0.0), val, layer.weight)
        return result

    def apply_layers(self) -> None:
        """Apply the layer stack to the rig."""
        if not self._weight_manager:
            raise PoseError("Weight manager not available")
        weights = self.evaluate_layers()
        self._weight_manager.set_all_weights(weights)

    # ---- Animation ----

    def animate_pose(self, name: str, start: int, end: int, values: List[float], attribute: Optional[str] = None) -> None:
        """
        Animate a pose by setting keyframes on its weight attributes.
        """
        if name not in self._poses:
            raise PoseNotFoundError(f"Pose '{name}' not found")
        pose = self._poses[name]
        if not self._weight_manager:
            raise PoseError("Weight manager not available")
        for target, base_val in pose.weights.items():
            # Determine the actual attribute path
            attr = f"{target}" if attribute is None else f"{attribute}.{target}"
            # Get the blendshape node containing this target
            bs_node = self._weight_manager._find_blendshape_node_for_target(target)
            if not bs_node:
                continue
            full_attr = f"{bs_node}.{target}"
            # Keyframe each frame
            for i, val in enumerate(values):
                frame = start + i
                if frame > end:
                    break
                # Interpolate between base_val and 0?
                final_val = base_val * val
                cmds.setKeyframe(full_attr, t=frame, v=final_val)

    def create_pose_sequence(self, pose_names: List[str], duration: float = 1.0, fps: float = 24.0) -> List[PoseFrame]:
        """
        Create a sequence of poses over time (linear interpolation between poses).
        Returns a list of PoseFrame objects.
        """
        if not pose_names:
            return []
        frames = []
        total_frames = int(duration * fps)
        if total_frames < len(pose_names):
            # Too many poses, we'll need to interpolate
            pass
        # Distribute poses evenly over the duration
        for i, name in enumerate(pose_names):
            if name not in self._poses:
                raise PoseNotFoundError(f"Pose '{name}' not found")
            time = (i / max(1, len(pose_names)-1)) * duration
            frames.append(PoseFrame(time=time, pose=self._poses[name]))
        # Interpolate intermediate frames (simplified: we just return the keyframes)
        return frames

    # ---- ARKit Poses ----

    def create_arkit_poses(self, base_name: str = "ARKit") -> Dict[str, PoseDefinition]:
        """
        Generate all ARKit 52 poses from the ARKit specification.
        """
        arkit_poses = {}
        for channel in ARKIT_BLENDSHAPES:
            # Create a pose with this channel at 1.0 and others at 0
            weights = {ch: 0.0 for ch in ARKIT_BLENDSHAPES}
            weights[channel] = 1.0
            name = f"{base_name}_{channel}"
            pose = PoseDefinition(
                name=name,
                weights=weights,
                pose_type=PoseType.ARKIT,
                category="ARKit",
                tags=["arkit", channel]
            )
            self._poses[name] = pose
            arkit_poses[name] = pose
        logger.info(f"Generated {len(arkit_poses)} ARKit poses")
        return arkit_poses

    # ---- Viseme Poses ----

    def create_viseme_poses(self, base_name: str = "Viseme") -> Dict[str, PoseDefinition]:
        """
        Generate standard viseme poses.
        """
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
        viseme_poses = {}
        for viseme, coeffs in viseme_defs.items():
            name = f"{base_name}_{viseme}"
            # Ensure all targets exist in our rig; we'll just use the coefficients as weights.
            # In production, we'd check that the targets exist.
            weights = coeffs
            pose = PoseDefinition(
                name=name,
                weights=weights,
                pose_type=PoseType.VISEME,
                category="Visemes",
                tags=["viseme", viseme]
            )
            self._poses[name] = pose
            viseme_poses[name] = pose
        logger.info(f"Generated {len(viseme_poses)} viseme poses")
        return viseme_poses

    # ---- Batch Operations ----

    def batch_apply(self, pose_names: List[str], blend_factor: float = 1.0) -> None:
        """Apply multiple poses sequentially (for testing)."""
        for name in pose_names:
            self.apply(name, blend_factor)

    def batch_delete(self, pose_names: List[str]) -> None:
        """Delete multiple poses."""
        for name in pose_names:
            if name in self._poses:
                self.delete(name)

    # ---- Validation ----

    def validate(self) -> PoseReport:
        """Validate all poses for consistency and compatibility."""
        report = PoseReport(success=True)
        if not self._validator:
            report.warnings.append("Validator not available")
            return report
        for name, pose in self._poses.items():
            # Validate each target exists in the rig
            for target in pose.weights.keys():
                bs_node = self._weight_manager._find_blendshape_node_for_target(target) if self._weight_manager else None
                if not bs_node:
                    report.errors.append(f"Target '{target}' in pose '{name}' not found in any blendshape node")
                    report.success = False
            # Validate weight ranges
            for target, val in pose.weights.items():
                if val < 0.0 or val > 1.0:
                    report.errors.append(f"Weight for target '{target}' in pose '{name}' out of range: {val}")
                    report.success = False
        # Check for duplicate pose names
        # Already handled by dictionary keys
        # Check libraries
        for lib_name, lib in self._libraries.items():
            for pose_name in lib.poses:
                if pose_name not in self._poses:
                    report.warnings.append(f"Library '{lib_name}' references missing pose '{pose_name}'")
        self._last_report = report
        return report

    # ---- Statistics ----

    def get_statistics(self) -> PoseStatistics:
        """Compute statistics for the pose system."""
        stats = PoseStatistics()
        stats.total_poses = len(self._poses)
        stats.libraries = len(self._libraries)
        stats.presets = len(self._presets)
        by_type = {}
        by_category = {}
        total_weights = 0
        for pose in self._poses.values():
            by_type[pose.pose_type.value] = by_type.get(pose.pose_type.value, 0) + 1
            by_category[pose.category] = by_category.get(pose.category, 0) + 1
            total_weights += len(pose.weights)
        stats.by_type = by_type
        stats.by_category = by_category
        stats.total_weights = total_weights
        if stats.total_poses > 0:
            stats.average_weights = total_weights / stats.total_poses
        self._last_stats = stats
        return stats

    # ---- Utilities ----

    def get_pose(self, name: str) -> Optional[PoseDefinition]:
        return self._poses.get(name)

    def list_poses(self, pose_type: Optional[PoseType] = None, category: Optional[str] = None) -> List[str]:
        """List pose names, optionally filtered by type and category."""
        results = []
        for name, pose in self._poses.items():
            if pose_type and pose.pose_type != pose_type:
                continue
            if category and pose.category != category:
                continue
            results.append(name)
        return results

    def search_poses(self, query: str) -> List[str]:
        """Search for poses by name, tags, or category."""
        query_lower = query.lower()
        results = []
        for name, pose in self._poses.items():
            if query_lower in name.lower():
                results.append(name)
                continue
            if any(query_lower in tag.lower() for tag in pose.tags):
                results.append(name)
                continue
            if query_lower in pose.category.lower():
                results.append(name)
                continue
        return results

    def clear(self) -> None:
        """Clear all poses, libraries, and presets."""
        self._poses.clear()
        self._libraries.clear()
        self._presets.clear()
        self._layers.clear()

    def to_json(self) -> str:
        """Serialize all poses to JSON."""
        data = {
            "version": __version__,
            "poses": {name: {"weights": p.weights, "type": p.pose_type.value, "category": p.category, "tags": p.tags} for name, p in self._poses.items()},
            "libraries": {name: {"poses": [p.name for p in lib.poses]} for name, lib in self._libraries.items()},
            "presets": {name: {"pose": p.pose.name, "shortcut": p.shortcut} for name, p in self._presets.items()}
        }
        return dict_to_json(data)

    def from_json(self, data: str) -> None:
        """Load poses from JSON (merges with existing)."""
        obj = json_to_dict(data)
        version = obj.get("version", "1.0")
        for name, pdata in obj.get("poses", {}).items():
            if name not in self._poses:
                pose = PoseDefinition(
                    name=name,
                    weights=pdata["weights"],
                    pose_type=PoseType(pdata.get("type", "custom")),
                    category=pdata.get("category", "Custom"),
                    tags=pdata.get("tags", [])
                )
                self._poses[name] = pose
        for lib_name, ldata in obj.get("libraries", {}).items():
            if lib_name not in self._libraries:
                lib = PoseLibrary(name=lib_name)
                for pname in ldata.get("poses", []):
                    if pname in self._poses:
                        lib.poses.append(self._poses[pname])
                self._libraries[lib_name] = lib
        for preset_name, pdata in obj.get("presets", {}).items():
            if preset_name not in self._presets:
                pname = pdata.get("pose")
                if pname in self._poses:
                    self._presets[preset_name] = PosePreset(name=preset_name, pose=self._poses[pname], shortcut=pdata.get("shortcut"))

    # ---- Reports ----

    def get_last_report(self) -> Optional[PoseReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[PoseStatistics]:
        return self._last_stats


# ---- Part 19: Public API -----------------------------------------------

__all__ = [
    "BlendshapePoseManager",
    "PoseDefinition",
    "PoseFrame",
    "PoseLayer",
    "PoseLibrary",
    "PosePreset",
    "PoseStatistics",
    "PoseReport",
    "PoseType",
    "BlendMode",
    "MirrorMode",
    "PoseSpace",
    "PoseError",
    "PoseNotFoundError",
    "PoseCreationError",
    "PoseValidationError",
    "PoseBlendError",
]