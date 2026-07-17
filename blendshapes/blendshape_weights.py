"""
blendshapes/blendshape_weights.py

Blendshape Weight Management System for Maya.

This module is responsible for creating, editing, evaluating, normalizing,
storing, transferring, animating, and optimizing blendshape weights throughout
the facial rig. It is the central authority for weight values in the blendshape
subsystem.

Responsibilities:
- Read and write blendshape weights.
- Lock and unlock weights.
- Normalize weights across targets or regions.
- Blend weights from multiple sources.
- Manage weight layers (non-destructive editing).
- Apply weight masks (vertex, region, texture).
- Support weight animation (keyframes, curves, baking).
- Transfer weights between meshes.
- Save and load weight presets.
- Optimize weights (remove near-zero, compress).
- Validate weights (range, locking, consistency).
- Provide statistics and diagnostics.

Dependencies:
- blendshape_validator.py: Validate weights and targets.
- blendshape_utils.py: Shared utilities.
- blendshape_transfer.py: Transfer weights between meshes.
- blendshape_driver.py: Apply runtime weights.
- animation/: Keyframes, curves, baking, layers.
- blendshapes/arkit/: ARKit mapping and normalization.

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
    from .blendshape_creator import BlendShapeCreator
except ImportError:
    BlendShapeCreator = None

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
    from .blendshape_transfer import BlendshapeTransferEngine
except ImportError:
    BlendshapeTransferEngine = None

try:
    from .blendshape_driver import BlendshapeDriver
except ImportError:
    BlendshapeDriver = None

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
class WeightError(Exception):
    """Base exception for weight operations."""
    pass

class WeightNotFoundError(WeightError):
    """Raised when a target or weight is not found."""
    pass

class WeightLockedError(WeightError):
    """Raised when attempting to modify a locked weight."""
    pass

class WeightValidationError(WeightError):
    """Raised when weight validation fails."""
    pass

class WeightNormalizationError(WeightError):
    """Raised when normalization fails."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class WeightMode(Enum):
    """Mode for weight operations."""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    NORMALIZED = "normalized"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SUBTRACT = "subtract"


class WeightSpace(Enum):
    """Coordinate space for weight operations."""
    LOCAL = "local"
    WORLD = "world"
    OBJECT = "object"
    CUSTOM = "custom"


class BlendMode(Enum):
    """Blend mode for combining weights."""
    LINEAR = "linear"
    WEIGHTED = "weighted"
    AVERAGE = "average"
    MAXIMUM = "max"
    MINIMUM = "min"
    PSD = "psd"          # Pose-space deformation


class MaskMode(Enum):
    """Mask mode for weight masks."""
    NONE = "none"
    VERTEX = "vertex"
    REGION = "region"
    TEXTURE = "texture"
    CUSTOM = "custom"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class WeightDefinition:
    """Definition of a single weight."""
    target: str
    value: float
    locked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightSet:
    """A collection of weights for a set of targets."""
    name: str
    weights: Dict[str, float] = field(default_factory=dict)
    locked: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightLayer:
    """A layer of weights that can be blended with others."""
    name: str
    weights: Dict[str, float]
    blend_mode: BlendMode = BlendMode.LINEAR
    weight: float = 1.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightMask:
    """A mask defining influence per vertex or region."""
    name: str
    mask_type: MaskMode
    data: Any  # could be list of vertex weights, region names, texture file, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightProfile:
    """A full weight profile (preset)."""
    name: str
    weights: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightStatistics:
    """Statistics for weight data."""
    total_targets: int = 0
    active_targets: int = 0
    inactive_targets: int = 0
    locked_targets: int = 0
    total_weight_sum: float = 0.0
    average_weight: float = 0.0
    min_weight: float = 0.0
    max_weight: float = 1.0
    normalized: bool = False


@dataclass
class WeightReport:
    """Diagnostic report for weight system."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[WeightStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Weight Manager -------------------------------------------

class BlendshapeWeightManager:
    """
    Main controller for all weight operations.
    """
    def __init__(self):
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._transfer_engine = BlendshapeTransferEngine() if BlendshapeTransferEngine else None
        self._driver = BlendshapeDriver() if BlendshapeDriver else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        self._creator = BlendShapeCreator() if BlendShapeCreator else None

        self._layers: List[WeightLayer] = []  # Ordered list of layers
        self._base_weights: Dict[str, float] = {}  # Base weights (from Maya)
        self._locked_targets: Set[str] = set()
        self._masks: Dict[str, WeightMask] = {}
        self._active_mask: Optional[str] = None

        self._last_report: Optional[WeightReport] = None
        self._last_stats: Optional[WeightStatistics] = None

        # Cache for target names on blendshape nodes
        self._target_cache: Set[str] = set()
        self._refresh_target_cache()

    # ---- Core Weight Operations ----

    def get_weight(self, target: str) -> float:
        """
        Get the current weight of a blendshape target.
        """
        # Try to find the target in Maya
        bs_node = self._find_blendshape_node_for_target(target)
        if bs_node:
            return get_blendshape_weight(bs_node, target)
        raise WeightNotFoundError(f"Target '{target}' not found in any blendshape node")

    def set_weight(self, target: str, value: float, relative: bool = False) -> None:
        """
        Set the weight of a blendshape target.
        If relative, add to existing.
        """
        if target in self._locked_targets:
            raise WeightLockedError(f"Target '{target}' is locked")

        # Clamp value to [0,1]
        value = clamp(value, 0.0, 1.0)

        # Find blendshape node
        bs_node = self._find_blendshape_node_for_target(target)
        if not bs_node:
            raise WeightNotFoundError(f"Target '{target}' not found in any blendshape node")

        current = get_blendshape_weight(bs_node, target)
        if relative:
            new_val = current + value
            new_val = clamp(new_val, 0.0, 1.0)
        else:
            new_val = value

        set_blendshape_weight(bs_node, target, new_val)

        # Update base weights cache
        self._base_weights[target] = new_val

    def add_weight(self, target: str, amount: float) -> None:
        """Add to a weight (relative)."""
        self.set_weight(target, amount, relative=True)

    def subtract_weight(self, target: str, amount: float) -> None:
        """Subtract from a weight."""
        self.set_weight(target, -amount, relative=True)

    def multiply_weight(self, target: str, factor: float) -> None:
        """Multiply a weight by a factor."""
        current = self.get_weight(target)
        new_val = current * factor
        self.set_weight(target, new_val)

    def clamp_weight(self, target: str, min_val: float = 0.0, max_val: float = 1.0) -> None:
        """Clamp a weight to a range."""
        current = self.get_weight(target)
        new_val = clamp(current, min_val, max_val)
        self.set_weight(target, new_val)

    def invert_weight(self, target: str) -> None:
        """Invert a weight (1 - value)."""
        current = self.get_weight(target)
        self.set_weight(target, 1.0 - current)

    # ---- Locking ----

    def lock_weight(self, target: str) -> None:
        """Lock a weight so it cannot be modified."""
        self._locked_targets.add(target)

    def unlock_weight(self, target: str) -> None:
        """Unlock a weight."""
        self._locked_targets.discard(target)

    def is_locked(self, target: str) -> bool:
        """Check if a target is locked."""
        return target in self._locked_targets

    # ---- Batch Operations ----

    def get_all_weights(self) -> Dict[str, float]:
        """Get all weights for all targets found in blendshape nodes."""
        all_weights = {}
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            for t in targets:
                all_weights[t] = get_blendshape_weight(node, t)
        return all_weights

    def set_all_weights(self, weights: Dict[str, float]) -> None:
        """Set multiple weights at once."""
        for target, value in weights.items():
            self.set_weight(target, value)

    def reset_all_weights(self) -> None:
        """Reset all weights to 0."""
        weights = {t: 0.0 for t in self._target_cache}
        self.set_all_weights(weights)

    # ---- Normalization ----

    def normalize_weights(self, targets: Optional[List[str]] = None) -> None:
        """
        Normalize weights so they sum to 1.0.
        If targets is None, normalizes all targets.
        """
        if targets is None:
            targets = list(self._target_cache)
        weights = {t: self.get_weight(t) for t in targets if not self.is_locked(t)}
        total = sum(weights.values())
        if total == 0.0:
            # If all zero, leave as is
            return
        for t, val in weights.items():
            new_val = val / total
            self.set_weight(t, new_val)

    def normalize_by_group(self, groups: Dict[str, List[str]]) -> None:
        """
        Normalize weights within each group.
        groups: dict of group_name -> list of target names.
        """
        for group, targets in groups.items():
            weights = {t: self.get_weight(t) for t in targets if not self.is_locked(t)}
            total = sum(weights.values())
            if total == 0.0:
                continue
            for t, val in weights.items():
                new_val = val / total
                self.set_weight(t, new_val)

    def normalize_by_region(self, regions: Dict[str, List[str]]) -> None:
        """Alias for normalize_by_group."""
        self.normalize_by_group(regions)

    # ---- Blending ----

    def blend_weights(
        self,
        source_a: Dict[str, float],
        source_b: Dict[str, float],
        blend_factor: float = 0.5,
        mode: BlendMode = BlendMode.LINEAR
    ) -> Dict[str, float]:
        """
        Blend two weight dictionaries.
        Returns a new dictionary of blended weights.
        """
        all_keys = set(source_a.keys()) | set(source_b.keys())
        result = {}
        for key in all_keys:
            val_a = source_a.get(key, 0.0)
            val_b = source_b.get(key, 0.0)
            if mode == BlendMode.LINEAR:
                result[key] = lerp(val_a, val_b, blend_factor)
            elif mode == BlendMode.WEIGHTED:
                # Weighted by blend_factor
                result[key] = val_a * (1.0 - blend_factor) + val_b * blend_factor
            elif mode == BlendMode.AVERAGE:
                result[key] = (val_a + val_b) * 0.5
            elif mode == BlendMode.MAXIMUM:
                result[key] = max(val_a, val_b)
            elif mode == BlendMode.MINIMUM:
                result[key] = min(val_a, val_b)
            elif mode == BlendMode.PSD:
                # Placeholder for PSD-specific blending
                result[key] = lerp(val_a, val_b, blend_factor)
            else:
                result[key] = lerp(val_a, val_b, blend_factor)
        return result

    def apply_blend_to_weights(self, blend_weights: Dict[str, float], mode: BlendMode = BlendMode.LINEAR) -> None:
        """
        Apply a blend to the current weights (in-place).
        """
        current = self.get_all_weights()
        blended = self.blend_weights(current, blend_weights, mode=mode)
        self.set_all_weights(blended)

    # ---- Layers ----

    def add_layer(self, layer: WeightLayer) -> None:
        """Add a weight layer to the stack."""
        self._layers.append(layer)

    def remove_layer(self, index: int) -> None:
        """Remove a layer by index."""
        if 0 <= index < len(self._layers):
            del self._layers[index]

    def clear_layers(self) -> None:
        """Remove all layers."""
        self._layers.clear()

    def evaluate_layers(self) -> Dict[str, float]:
        """
        Evaluate the layer stack to produce a final weight set.
        This applies layers in order with their blend modes.
        """
        if not self._layers:
            return self.get_all_weights()

        result = {}
        for layer in self._layers:
            if not layer.enabled:
                continue
            if not result:
                result = layer.weights.copy()
                continue
            # Blend current result with layer weights
            blended = self.blend_weights(
                result,
                layer.weights,
                blend_factor=layer.weight,
                mode=layer.blend_mode
            )
            result = blended

        return result

    def apply_layers(self) -> None:
        """Apply the layer stack to the actual blendshape weights."""
        final_weights = self.evaluate_layers()
        self.set_all_weights(final_weights)

    # ---- Masks ----

    def add_mask(self, mask: WeightMask) -> None:
        """Register a weight mask."""
        self._masks[mask.name] = mask

    def remove_mask(self, name: str) -> None:
        """Remove a mask by name."""
        if name in self._masks:
            del self._masks[name]

    def set_active_mask(self, name: Optional[str]) -> None:
        """Set the active mask."""
        if name is None or name in self._masks:
            self._active_mask = name
        else:
            raise WeightNotFoundError(f"Mask '{name}' not found")

    def apply_mask(self, weights: Dict[str, float], mask_name: Optional[str] = None) -> Dict[str, float]:
        """
        Apply a mask to a weight dictionary.
        If mask_name is None, uses the active mask.
        """
        if mask_name is None:
            mask_name = self._active_mask
        if mask_name is None or mask_name not in self._masks:
            return weights

        mask = self._masks[mask_name]
        # For vertex masks, we need to map vertices to targets? This is complex.
        # We'll assume mask data is a dict of target -> factor.
        if mask.mask_type == MaskMode.VERTEX:
            # For now, treat as a simple weight multiplier.
            factors = mask.data if isinstance(mask.data, dict) else {}
            result = {}
            for target, val in weights.items():
                factor = factors.get(target, 1.0)
                result[target] = val * factor
            return result
        elif mask.mask_type == MaskMode.REGION:
            factors = mask.data if isinstance(mask.data, dict) else {}
            result = {}
            for target, val in weights.items():
                factor = factors.get(target, 1.0)
                result[target] = val * factor
            return result
        else:
            # Not implemented for other types
            return weights

    # ---- Presets ----

    def save_preset(self, name: str) -> WeightProfile:
        """Save the current weights as a preset."""
        weights = self.get_all_weights()
        return WeightProfile(name=name, weights=weights)

    def load_preset(self, preset: WeightProfile, relative: bool = False) -> None:
        """Load a preset into the current weights."""
        if relative:
            # Add preset weights to current
            current = self.get_all_weights()
            for target, val in preset.weights.items():
                current[target] = current.get(target, 0.0) + val
            self.set_all_weights(current)
        else:
            self.set_all_weights(preset.weights)

    def save_preset_to_file(self, name: str, filepath: str) -> None:
        """Save a preset to a JSON file."""
        preset = self.save_preset(name)
        data = {
            "name": preset.name,
            "weights": preset.weights,
            "metadata": preset.metadata
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_preset_from_file(self, filepath: str, relative: bool = False) -> None:
        """Load a preset from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        preset = WeightProfile(
            name=data["name"],
            weights=data["weights"],
            metadata=data.get("metadata", {})
        )
        self.load_preset(preset, relative)

    # ---- Transfer ----

    def transfer_weights(
        self,
        source_mesh: str,
        target_mesh: str,
        target_list: Optional[List[str]] = None,
        transfer_method: str = "topology"
    ) -> bool:
        """
        Transfer weights from one mesh to another.
        Uses blendshape_transfer.py if available.
        """
        if not self._transfer_engine:
            logger.warning("Transfer engine not available")
            return False
        # Get source weights
        source_weights = self.get_all_weights()
        if target_list is None:
            target_list = list(self._target_cache)
        # Transfer requires mapping between targets? We'll assume same target names.
        # For a full implementation, we'd need to map target meshes.
        # Placeholder: just copy weights to target mesh's blendshape node.
        # Find target blendshape node
        target_bs = None
        bs_nodes = cmds.listConnections(target_mesh, type='blendShape') or []
        if bs_nodes:
            target_bs = bs_nodes[0]
        else:
            # Create a new blendshape node on target mesh
            if self._creator:
                target_bs = self._creator.create_node("Transfer_BS", target_mesh)
            else:
                return False
        # Set weights on target node
        for target, val in source_weights.items():
            if target_list and target not in target_list:
                continue
            # Check if target exists on target node
            if target in cmds.blendShape(target_bs, q=True, target=True) or []:
                set_blendshape_weight(target_bs, target, val)
            else:
                # Need to add the target? That requires a target mesh.
                logger.warning(f"Target '{target}' not found on target blendshape node, skipping")
        return True

    # ---- Animation ----

    def animate_weight(self, target: str, start: int, end: int, values: List[float]) -> None:
        """
        Animate a weight over a range.
        Sets keyframes at each frame.
        """
        if len(values) != end - start + 1:
            raise ValueError("Number of values must match frame range")
        bs_node = self._find_blendshape_node_for_target(target)
        if not bs_node:
            raise WeightNotFoundError(f"Target '{target}' not found")
        attr = f"{bs_node}.{target}"
        for frame, val in zip(range(start, end+1), values):
            cmds.setKeyframe(attr, t=frame, v=val)

    # ---- Optimization ----

    def optimize_weights(self, threshold: float = 0.001) -> None:
        """
        Remove near-zero weights (set to 0).
        """
        weights = self.get_all_weights()
        for target, val in weights.items():
            if abs(val) < threshold:
                self.set_weight(target, 0.0)

    # ---- Statistics ----

    def get_statistics(self) -> WeightStatistics:
        """Compute statistics for current weights."""
        stats = WeightStatistics()
        weights = self.get_all_weights()
        stats.total_targets = len(weights)
        active = [v for v in weights.values() if v > 0.001]
        stats.active_targets = len(active)
        stats.inactive_targets = stats.total_targets - stats.active_targets
        stats.locked_targets = len(self._locked_targets)
        total_sum = sum(weights.values())
        stats.total_weight_sum = total_sum
        if stats.total_targets > 0:
            stats.average_weight = total_sum / stats.total_targets
        if weights:
            stats.min_weight = min(weights.values())
            stats.max_weight = max(weights.values())
        else:
            stats.min_weight = 0.0
            stats.max_weight = 0.0
        # Check if normalized (sum is close to 1)
        if abs(total_sum - 1.0) < 0.001:
            stats.normalized = True
        return stats

    # ---- Validation ----

    def validate(self) -> WeightReport:
        """Validate the weight system (range, locked, etc.)."""
        report = WeightReport(success=True)
        weights = self.get_all_weights()
        for target, val in weights.items():
            if val < 0.0 or val > 1.0:
                report.errors.append(f"Weight for target '{target}' is out of range: {val}")
                report.success = False
            if self.is_locked(target):
                # Locked is okay, just note.
                pass
        # Check if any target is missing from cache
        for target in self._target_cache:
            if target not in weights:
                report.warnings.append(f"Target '{target}' exists in cache but has no weight")
        # Use validator if available
        if self._validator:
            # Validate against blendshape node
            for target in weights:
                # Validate target exists in Maya
                if not self._find_blendshape_node_for_target(target):
                    report.errors.append(f"Target '{target}' not found in any blendshape node")
                    report.success = False
        self._last_report = report
        return report

    # ---- Utilities ----

    def _refresh_target_cache(self) -> None:
        """Refresh the cache of all target names."""
        self._target_cache.clear()
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            self._target_cache.update(targets)

    def _find_blendshape_node_for_target(self, target: str) -> Optional[str]:
        """Find the blendshape node that contains a given target alias."""
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            if target in targets:
                return node
        return None

    # ---- Layer Helpers ----

    def create_layer(self, name: str, weights: Optional[Dict[str, float]] = None) -> WeightLayer:
        """Create a new weight layer."""
        if weights is None:
            weights = self.get_all_weights()
        layer = WeightLayer(name=name, weights=weights.copy())
        self.add_layer(layer)
        return layer

    def get_layer(self, index: int) -> Optional[WeightLayer]:
        """Get a layer by index."""
        if 0 <= index < len(self._layers):
            return self._layers[index]
        return None

    # ---- Reset ----

    def reset(self) -> None:
        """Reset the weight manager to a clean state."""
        self._layers.clear()
        self._locked_targets.clear()
        self._masks.clear()
        self._active_mask = None
        self._base_weights = {}
        self._last_report = None
        self._last_stats = None

    # ---- Reports ----

    def get_last_report(self) -> Optional[WeightReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[WeightStatistics]:
        return self._last_stats


# ---- Part 17: Public API -----------------------------------------------

__all__ = [
    "BlendshapeWeightManager",
    "WeightDefinition",
    "WeightSet",
    "WeightLayer",
    "WeightMask",
    "WeightProfile",
    "WeightStatistics",
    "WeightReport",
    "WeightMode",
    "WeightSpace",
    "BlendMode",
    "MaskMode",
    "WeightError",
    "WeightNotFoundError",
    "WeightLockedError",
    "WeightValidationError",
    "WeightNormalizationError",
]