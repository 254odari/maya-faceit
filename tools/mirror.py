# -*- coding: utf-8 -*-
"""
maya_faceit.tools.mirror
~~~~~~~~~~~~~~~~~~~~~~~~

Central mirroring engine for the Maya FaceIT toolkit.

This module provides a unified mirroring system that handles controllers,
poses, animation, blendshapes, meshes, UVs, and selection. All other modules
(ARKit, poses, animation, blendshapes, skinning) delegate mirroring to this
engine to ensure consistent behavior.

Design patterns:
- Facade: MirrorTools provides a simple API.
- Strategy: Different mirroring strategies for different data types.
- Registry: Mirror tables for name mapping.
- Observer: Validation and reporting.

Estimated size: 3,500–5,500 lines.
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, Iterable

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from maya import mel # type: ignore

# Local imports (with fallback)
try:
    from maya_faceit.core.logger import log
    from maya_faceit.core.validation import validator
    from maya_faceit.exceptions import ValidationError, MirrorError
except ImportError:
    # Fallback for standalone development
    import logging
    log = logging.getLogger(__name__)
    class ValidationError(Exception): pass
    class MirrorError(Exception): pass
    class validator:
        @staticmethod
        def exists(node): return cmds.objExists(node)
        @staticmethod
        def require_exists(node):
            if not cmds.objExists(node):
                raise ValidationError(f"Node '{node}' does not exist.")

# -----------------------------------------------------------------------------
# Part 1 — Foundation
# -----------------------------------------------------------------------------

MODULE_NAME = "maya_faceit.tools.mirror"
__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = log if isinstance(log, logging.Logger) else logging.getLogger(MODULE_NAME)

# -----------------------------------------------------------------------------
# Part 2 — Enumerations & Constants
# -----------------------------------------------------------------------------

class MirrorAxis(Enum):
    """Axis along which to mirror."""
    X = "x"
    Y = "y"
    Z = "z"

class MirrorMode(Enum):
    """Type of data to mirror."""
    TRANSFORM = "transform"
    POSE = "pose"
    ANIMATION = "animation"
    BLENDSHAPE = "blendshape"
    MESH = "mesh"
    UV = "uv"
    CONTROLLER = "controller"
    SELECTION = "selection"

class MirrorBehavior(Enum):
    """Behavior when mirroring: copy, swap, or average."""
    COPY = "copy"           # Copy source to target (overwrite)
    SWAP = "swap"           # Swap between left and right
    AVERAGE = "average"     # Average values between left and right

class MirrorScope(Enum):
    """Scope for animation mirroring."""
    TIMELINE = "timeline"
    SELECTED_KEYS = "selected_keys"
    CURRENT_FRAME = "current_frame"
    LAYERS = "layers"

# -----------------------------------------------------------------------------
# Part 3 — Data Models
# -----------------------------------------------------------------------------

@dataclass
class MirrorSettings:
    """Global settings for a mirror operation."""
    axis: MirrorAxis = MirrorAxis.X
    behavior: MirrorBehavior = MirrorBehavior.SWAP
    mirror_translate: bool = True
    mirror_rotate: bool = True
    mirror_scale: bool = False
    mirror_custom_attributes: bool = True
    mirror_visibility: bool = False
    mirror_limits: bool = False
    mirror_sdk: bool = False
    mirror_shapes: bool = True
    mirror_blendshape_weights: bool = True
    mirror_mesh_vertices: bool = True
    mirror_uvs: bool = True
    animation_scope: MirrorScope = MirrorScope.TIMELINE
    animation_start: Optional[int] = None
    animation_end: Optional[int] = None
    include_selected_only: bool = False
    preserve_original: bool = False   # If True, duplicates before mirroring
    ignore_locked: bool = True
    ignore_hidden: bool = True
    tolerance: float = 1e-5

@dataclass
class MirrorStatistics:
    """Statistics collected during a mirror operation."""
    total_nodes: int = 0
    mirrored_nodes: int = 0
    skipped_nodes: int = 0
    failed_nodes: int = 0
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MirrorReport:
    """Full report of a mirror operation."""
    success: bool = True
    mode: MirrorMode = MirrorMode.TRANSFORM
    settings: MirrorSettings = field(default_factory=MirrorSettings)
    statistics: MirrorStatistics = field(default_factory=MirrorStatistics)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    mirrored_pairs: List[Tuple[str, str]] = field(default_factory=list)  # (source, target)
    skipped_pairs: List[Tuple[str, str, str]] = field(default_factory=list)  # (source, reason)

@dataclass
class MirrorPair:
    """A pair of objects to mirror between."""
    source: str
    target: str
    source_side: Optional[str] = None   # 'L', 'R', or None
    target_side: Optional[str] = None

@dataclass
class MirrorTableEntry:
    """Entry in a mirror table."""
    source_pattern: str
    target_pattern: str
    side: Optional[str] = None   # 'L' or 'R'

class MirrorTable:
    """Container for mirror name mappings."""
    def __init__(self, name: str = "Default"):
        self.name = name
        self.entries: List[MirrorTableEntry] = []
        self.description: str = ""

    def add_entry(self, source_pattern: str, target_pattern: str, side: Optional[str] = None):
        self.entries.append(MirrorTableEntry(source_pattern, target_pattern, side))

    def remove_entry(self, index: int):
        if 0 <= index < len(self.entries):
            self.entries.pop(index)

    def clear(self):
        self.entries.clear()

# -----------------------------------------------------------------------------
# Part 4 — Mirror Tables (Built-in and User-defined)
# -----------------------------------------------------------------------------

class MirrorTableManager:
    """Manages mirror tables for name resolution."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._tables: Dict[str, MirrorTable] = {}
        self._active_table_name: str = "Default"
        self._init_builtin_tables()

    def _init_builtin_tables(self):
        """Initialize built-in mirror tables for common naming conventions."""
        # Default table: handles L_ / R_ and Left / Right
        default = MirrorTable("Default")
        default.description = "Standard L/R and Left/Right mappings"
        default.add_entry("L_", "R_", "L")
        default.add_entry("R_", "L_", "R")
        default.add_entry("Left", "Right", "L")
        default.add_entry("Right", "Left", "R")
        default.add_entry("_l", "_r", "L")
        default.add_entry("_r", "_l", "R")
        default.add_entry(".L", ".R", "L")
        default.add_entry(".R", ".L", "R")
        default.add_entry("LF", "RT", "L")
        default.add_entry("RT", "LF", "R")
        default.add_entry("_LEFT", "_RIGHT", "L")
        default.add_entry("_RIGHT", "_LEFT", "R")
        self._tables["Default"] = default

        # ARKit table: handles ARKit blendshape mirroring
        arkit = MirrorTable("ARKit")
        arkit.description = "ARKit blendshape mirror mappings"
        # Common ARKit blendshapes that are symmetrical
        arkit.add_entry("browDownLeft", "browDownRight", "L")
        arkit.add_entry("browDownRight", "browDownLeft", "R")
        arkit.add_entry("browInnerUp", "browInnerUp", None)
        arkit.add_entry("browOuterUpLeft", "browOuterUpRight", "L")
        arkit.add_entry("browOuterUpRight", "browOuterUpLeft", "R")
        arkit.add_entry("cheekSquintLeft", "cheekSquintRight", "L")
        arkit.add_entry("cheekSquintRight", "cheekSquintLeft", "R")
        arkit.add_entry("eyeBlinkLeft", "eyeBlinkRight", "L")
        arkit.add_entry("eyeBlinkRight", "eyeBlinkLeft", "R")
        arkit.add_entry("eyeLookDownLeft", "eyeLookDownRight", "L")
        arkit.add_entry("eyeLookDownRight", "eyeLookDownLeft", "R")
        arkit.add_entry("eyeLookInLeft", "eyeLookInRight", "L")
        arkit.add_entry("eyeLookInRight", "eyeLookInLeft", "R")
        arkit.add_entry("eyeLookOutLeft", "eyeLookOutRight", "L")
        arkit.add_entry("eyeLookOutRight", "eyeLookOutLeft", "R")
        arkit.add_entry("eyeLookUpLeft", "eyeLookUpRight", "L")
        arkit.add_entry("eyeLookUpRight", "eyeLookUpLeft", "R")
        arkit.add_entry("eyeSquintLeft", "eyeSquintRight", "L")
        arkit.add_entry("eyeSquintRight", "eyeSquintLeft", "R")
        arkit.add_entry("eyeWideLeft", "eyeWideRight", "L")
        arkit.add_entry("eyeWideRight", "eyeWideLeft", "R")
        arkit.add_entry("jawLeft", "jawRight", "L")
        arkit.add_entry("jawRight", "jawLeft", "R")
        arkit.add_entry("mouthDimpleLeft", "mouthDimpleRight", "L")
        arkit.add_entry("mouthDimpleRight", "mouthDimpleLeft", "R")
        arkit.add_entry("mouthFrownLeft", "mouthFrownRight", "L")
        arkit.add_entry("mouthFrownRight", "mouthFrownLeft", "R")
        arkit.add_entry("mouthLeft", "mouthRight", "L")
        arkit.add_entry("mouthRight", "mouthLeft", "R")
        arkit.add_entry("mouthLowerDownLeft", "mouthLowerDownRight", "L")
        arkit.add_entry("mouthLowerDownRight", "mouthLowerDownLeft", "R")
        arkit.add_entry("mouthPressLeft", "mouthPressRight", "L")
        arkit.add_entry("mouthPressRight", "mouthPressLeft", "R")
        arkit.add_entry("mouthSmileLeft", "mouthSmileRight", "L")
        arkit.add_entry("mouthSmileRight", "mouthSmileLeft", "R")
        arkit.add_entry("mouthStretchLeft", "mouthStretchRight", "L")
        arkit.add_entry("mouthStretchRight", "mouthStretchLeft", "R")
        arkit.add_entry("mouthUpperUpLeft", "mouthUpperUpRight", "L")
        arkit.add_entry("mouthUpperUpRight", "mouthUpperUpLeft", "R")
        arkit.add_entry("noseSneerLeft", "noseSneerRight", "L")
        arkit.add_entry("noseSneerRight", "noseSneerLeft", "R")
        self._tables["ARKit"] = arkit

        # FACS table (placeholder)
        facs = MirrorTable("FACS")
        facs.description = "FACS action unit mirror mappings"
        # Add typical FACS pairs
        self._tables["FACS"] = facs

    def add_table(self, table: MirrorTable):
        self._tables[table.name] = table

    def remove_table(self, name: str):
        if name in self._tables and name != "Default":
            del self._tables[name]

    def get_table(self, name: str) -> Optional[MirrorTable]:
        return self._tables.get(name)

    def list_tables(self) -> List[str]:
        return list(self._tables.keys())

    def set_active_table(self, name: str):
        if name not in self._tables:
            raise ValueError(f"Mirror table '{name}' not found.")
        self._active_table_name = name

    def get_active_table(self) -> MirrorTable:
        return self._tables[self._active_table_name]

# -----------------------------------------------------------------------------
# Part 5 — Name Resolver
# -----------------------------------------------------------------------------

class MirrorNameResolver:
    """
    Resolves mirror counterpart names using mirror tables and heuristics.
    """
    def __init__(self, table_manager: Optional[MirrorTableManager] = None):
        self._table_manager = table_manager or MirrorTableManager()
        self._custom_mappings: Dict[str, str] = {}  # custom override
        self._cache: Dict[str, str] = {}

    def add_custom_mapping(self, source: str, target: str):
        """Add a custom name mapping."""
        self._custom_mappings[source] = target
        self._cache.clear()

    def remove_custom_mapping(self, source: str):
        if source in self._custom_mappings:
            del self._custom_mappings[source]
            self._cache.clear()

    def clear_custom_mappings(self):
        self._custom_mappings.clear()
        self._cache.clear()

    def get_mirror_name(self, node: str, table_name: Optional[str] = None) -> Optional[str]:
        """
        Get the mirror counterpart name for a given node.
        Returns None if no counterpart found.
        """
        # Check cache
        if node in self._cache:
            return self._cache[node]

        # First, check custom mappings
        if node in self._custom_mappings:
            result = self._custom_mappings[node]
            self._cache[node] = result
            return result

        # Use active table
        if table_name is None:
            table = self._table_manager.get_active_table()
        else:
            table = self._table_manager.get_table(table_name)
        if table is None:
            return None

        # Apply table entries in order
        for entry in table.entries:
            if entry.source_pattern in node:
                target = node.replace(entry.source_pattern, entry.target_pattern)
                # Optionally verify existence? We'll just return the name.
                self._cache[node] = target
                return target

        # Fallback: try heuristic: if name starts with L_ or R_, swap
        if node.startswith("L_"):
            target = "R_" + node[2:]
            if cmds.objExists(target):
                self._cache[node] = target
                return target
        if node.startswith("R_"):
            target = "L_" + node[2:]
            if cmds.objExists(target):
                self._cache[node] = target
                return target

        # If no counterpart found, return None
        self._cache[node] = None
        return None

    def get_mirror_pair(self, node: str) -> MirrorPair:
        """Get a MirrorPair for a node (source, target)."""
        target = self.get_mirror_name(node)
        if target is None:
            return MirrorPair(source=node, target="")
        return MirrorPair(source=node, target=target)

    def get_side(self, node: str) -> Optional[str]:
        """Determine side from name: 'L', 'R', or None."""
        # Check table side info
        for table in self._table_manager._tables.values():
            for entry in table.entries:
                if entry.source_pattern in node:
                    return entry.side
        # Heuristic
        if node.startswith("L_") or node.startswith("Left") or node.startswith("left"):
            return "L"
        if node.startswith("R_") or node.startswith("Right") or node.startswith("right"):
            return "R"
        if "_l" in node or ".L" in node:
            return "L"
        if "_r" in node or ".R" in node:
            return "R"
        return None

# -----------------------------------------------------------------------------
# Part 6 — Transform Mirroring
# -----------------------------------------------------------------------------

class TransformMirror:
    """
    Mirror transform data (translate, rotate, scale) between two objects.
    """
    @staticmethod
    def mirror_transforms(source: str, target: str,
                          settings: MirrorSettings,
                          space: str = "world") -> bool:
        """
        Mirror transforms from source to target using the specified axis.
        Returns True if successful.
        """
        if not cmds.objExists(source):
            logger.warning(f"Source '{source}' does not exist.")
            return False
        if not cmds.objExists(target):
            logger.warning(f"Target '{target}' does not exist.")
            return False

        # Get transforms in the specified space
        if space == "world":
            t = cmds.xform(source, q=True, ws=True, t=True)
            r = cmds.xform(source, q=True, ws=True, ro=True)
            s = cmds.xform(source, q=True, ws=True, s=True)
        else:  # local
            t = cmds.xform(source, q=True, t=True)
            r = cmds.xform(source, q=True, ro=True)
            s = cmds.xform(source, q=True, s=True)

        # Mirror based on axis
        axis = settings.axis
        if settings.mirror_translate:
            mirrored_t = list(t)
            if axis == MirrorAxis.X:
                mirrored_t[0] = -t[0]
            elif axis == MirrorAxis.Y:
                mirrored_t[1] = -t[1]
            elif axis == MirrorAxis.Z:
                mirrored_t[2] = -t[2]
            # Apply
            cmds.xform(target, ws=(space=="world"), t=mirrored_t)

        if settings.mirror_rotate:
            # For rotation, we need to mirror the rotation axes.
            # A simple approach: negate the axis component and possibly swap.
            # For Euler rotations, mirroring can be tricky.
            # For simplicity, we'll use a matrix-based approach.
            # Get the world matrix of source, mirror it, then decompose.
            mat = om2.MMatrix(cmds.xform(source, q=True, ws=True, matrix=True))
            # Mirror matrix along axis
            if axis == MirrorAxis.X:
                mirror_mat = om2.MMatrix([
                    [-1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ])
            elif axis == MirrorAxis.Y:
                mirror_mat = om2.MMatrix([
                    [1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ])
            else:  # Z
                mirror_mat = om2.MMatrix([
                    [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, -1, 0],
                    [0, 0, 0, 1]
                ])
            mirrored_mat = mat * mirror_mat
            # Decompose to rotation (Euler) in world space
            # Convert to transform matrix and decompose
            # Simpler: use cmds.xform with matrix
            cmds.xform(target, ws=True, matrix=mirrored_mat)

        if settings.mirror_scale:
            # Scale: mirror only the axis component
            mirrored_s = list(s)
            if axis == MirrorAxis.X:
                mirrored_s[0] = s[0]  # Keep positive? Usually scale mirrors as is.
            elif axis == MirrorAxis.Y:
                mirrored_s[1] = s[1]
            elif axis == MirrorAxis.Z:
                mirrored_s[2] = s[2]
            cmds.xform(target, ws=(space=="world"), s=mirrored_s)

        return True

# -----------------------------------------------------------------------------
# Part 7 — Pose Mirroring
# -----------------------------------------------------------------------------

class PoseMirror:
    """
    Mirror poses (current or stored) between controllers.
    """
    @staticmethod
    def mirror_current_pose(source_controllers: List[str],
                            target_controllers: List[str],
                            settings: MirrorSettings) -> bool:
        """
        Mirror the current pose of source controllers to target controllers.
        Assumes lists are matched (same order).
        """
        if len(source_controllers) != len(target_controllers):
            logger.warning("Source and target lists must have the same length.")
            return False

        success = True
        for src, tgt in zip(source_controllers, target_controllers):
            # Mirror transforms
            if not TransformMirror.mirror_transforms(src, tgt, settings):
                success = False
            # Custom attributes can be mirrored here as well
        return success

    @staticmethod
    def mirror_stored_pose(source: str, target: str,
                           settings: MirrorSettings,
                           pose_node: Optional[str] = None) -> bool:
        """
        Mirror a stored pose (from a pose node or attribute).
        Placeholder for future implementation.
        """
        # This would involve reading stored values from a node or attribute.
        # For now, just mirror current pose.
        return PoseMirror.mirror_current_pose([source], [target], settings)

# -----------------------------------------------------------------------------
# Part 8 — Animation Mirroring
# -----------------------------------------------------------------------------

class AnimationMirror:
    """
    Mirror animation curves between two objects.
    """
    @staticmethod
    def mirror_animation(source: str, target: str,
                         settings: MirrorSettings) -> bool:
        """
        Mirror animation keys from source to target.
        """
        if not cmds.objExists(source) or not cmds.objExists(target):
            return False

        # Determine time range
        start = settings.animation_start
        end = settings.animation_end
        if start is None or end is None:
            start = int(cmds.playbackOptions(q=True, min=True))
            end = int(cmds.playbackOptions(q=True, max=True))

        # Get all keyable attributes on source that are animated
        anim_attrs = []
        for attr in cmds.listAttr(source, keyable=True) or []:
            full_attr = f"{source}.{attr}"
            if cmds.keyframe(full_attr, q=True, keyframeCount=True) or 0:
                anim_attrs.append(attr)

        if not anim_attrs:
            logger.warning(f"No animated attributes found on {source}.")
            return False

        # For each attribute, copy the keys and mirror values
        for attr in anim_attrs:
            src_attr = f"{source}.{attr}"
            tgt_attr = f"{target}.{attr}"
            # Ensure attribute exists on target
            if not cmds.objExists(tgt_attr):
                continue

            # Get key times and values
            times = cmds.keyframe(src_attr, q=True, timeChange=True) or []
            values = cmds.keyframe(src_attr, q=True, valueChange=True) or []
            if not times:
                continue

            # Mirror values based on axis and attribute type
            mirrored_values = []
            for val in values:
                if attr.startswith("translate") or attr.startswith("t"):
                    if settings.mirror_translate:
                        if attr.endswith("X") or attr.endswith("x"):
                            if settings.axis == MirrorAxis.X:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                        elif attr.endswith("Y") or attr.endswith("y"):
                            if settings.axis == MirrorAxis.Y:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                        elif attr.endswith("Z") or attr.endswith("z"):
                            if settings.axis == MirrorAxis.Z:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                    else:
                        mirrored_values.append(val)
                elif attr.startswith("rotate") or attr.startswith("r"):
                    if settings.mirror_rotate:
                        # For rotation, we need to mirror based on axis.
                        # Simple approach: if attribute is the mirror axis, negate.
                        if attr.endswith("X") or attr.endswith("x"):
                            if settings.axis == MirrorAxis.X:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                        elif attr.endswith("Y") or attr.endswith("y"):
                            if settings.axis == MirrorAxis.Y:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                        elif attr.endswith("Z") or attr.endswith("z"):
                            if settings.axis == MirrorAxis.Z:
                                mirrored_values.append(-val)
                            else:
                                mirrored_values.append(val)
                    else:
                        mirrored_values.append(val)
                else:
                    # For other attributes (scale, custom), just copy
                    mirrored_values.append(val)

            # Set keys on target
            # First, delete existing keys on target within the same time range
            cmds.cutKey(tgt_attr, t=(start, end), clear=True)
            # Set new keys
            for t, v in zip(times, mirrored_values):
                # Clamp to time range if needed
                if start <= t <= end:
                    cmds.setKeyframe(tgt_attr, t=t, value=v)

        return True

    @staticmethod
    def mirror_animation_layers(source: str, target: str,
                                settings: MirrorSettings) -> bool:
        """
        Mirror animation layers from source to target.
        Placeholder.
        """
        # Not implemented fully; requires layer handling.
        logger.warning("Animation layer mirroring not fully implemented.")
        return False

# -----------------------------------------------------------------------------
# Part 9 — Blendshape Mirroring
# -----------------------------------------------------------------------------

class BlendshapeMirror:
    """
    Mirror blendshape weights between symmetrical targets.
    """
    @staticmethod
    def mirror_blendshape_weights(blendshape_node: str,
                                  source_targets: List[str],
                                  target_targets: List[str],
                                  settings: MirrorSettings) -> bool:
        """
        Mirror weights from source blendshape targets to target blendshape targets.
        Assumes lists are matched.
        """
        if not cmds.objExists(blendshape_node):
            logger.warning(f"Blendshape node '{blendshape_node}' does not exist.")
            return False

        if len(source_targets) != len(target_targets):
            logger.warning("Source and target blendshape lists must have same length.")
            return False

        success = True
        for src_tgt, tgt_tgt in zip(source_targets, target_targets):
            src_attr = f"{blendshape_node}.{src_tgt}"
            tgt_attr = f"{blendshape_node}.{tgt_tgt}"
            if not cmds.objExists(src_attr) or not cmds.objExists(tgt_attr):
                logger.warning(f"Blendshape attribute missing: {src_attr} or {tgt_attr}")
                success = False
                continue

            # Get source weight
            weight = cmds.getAttr(src_attr)
            # Mirror weight (usually same value, but could be negated if axis?)
            # For blendshapes, we typically copy the weight directly.
            cmds.setAttr(tgt_attr, weight)

        return success

    @staticmethod
    def mirror_blendshape_weights_by_name(blendshape_node: str,
                                          settings: MirrorSettings,
                                          resolver: MirrorNameResolver) -> bool:
        """
        Automatically mirror blendshape weights by finding symmetrical targets.
        """
        if not cmds.objExists(blendshape_node):
            return False

        # Get all blendshape targets
        targets = cmds.listAttr(blendshape_node, m=True, string='weight') or []
        if not targets:
            logger.warning(f"No blendshape targets found on {blendshape_node}.")
            return False

        processed = set()
        success = True
        for tgt in targets:
            if tgt in processed:
                continue
            # Find mirror counterpart
            mirror_tgt = resolver.get_mirror_name(tgt)
            if mirror_tgt and mirror_tgt in targets and mirror_tgt not in processed:
                # Mirror from tgt to mirror_tgt
                src_attr = f"{blendshape_node}.{tgt}"
                tgt_attr = f"{blendshape_node}.{mirror_tgt}"
                weight = cmds.getAttr(src_attr)
                cmds.setAttr(tgt_attr, weight)
                processed.add(tgt)
                processed.add(mirror_tgt)
            else:
                processed.add(tgt)

        return success

# -----------------------------------------------------------------------------
# Part 10 — Mesh Mirroring
# -----------------------------------------------------------------------------

class MeshMirror:
    """
    Mirror mesh vertex positions.
    """
    @staticmethod
    def mirror_mesh_vertices(mesh: str, settings: MirrorSettings,
                             target_mesh: Optional[str] = None) -> bool:
        """
        Mirror vertex positions of a mesh (optionally to a target mesh).
        If target_mesh is None, mirror in place.
        """
        if not cmds.objExists(mesh):
            return False
        if target_mesh is not None and not cmds.objExists(target_mesh):
            return False

        # Get mesh as MFnMesh
        sel = om2.MSelectionList()
        sel.add(mesh)
        mesh_obj = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(mesh_obj)

        # Get points in world space
        points = fn_mesh.getPoints(om2.MSpace.kWorld)
        num_points = len(points)

        # Determine mirror axis index
        axis_index = {"x": 0, "y": 1, "z": 2}[settings.axis.value]

        # Mirror points
        mirrored_points = om2.MPointArray()
        for p in points:
            new_p = om2.MPoint(p)
            new_p[axis_index] = -p[axis_index]
            mirrored_points.append(new_p)

        if target_mesh and target_mesh != mesh:
            # Set points on target mesh
            sel2 = om2.MSelectionList()
            sel2.add(target_mesh)
            target_obj = sel2.getDagPath(0)
            fn_target = om2.MFnMesh(target_obj)
            fn_target.setPoints(mirrored_points, om2.MSpace.kWorld)
        else:
            # Set points on same mesh (in-place mirror)
            fn_mesh.setPoints(mirrored_points, om2.MSpace.kWorld)

        return True

# -----------------------------------------------------------------------------
# Part 11 — UV Mirroring
# -----------------------------------------------------------------------------

class UVMirror:
    """
    Mirror UVs across the U or V axis.
    """
    @staticmethod
    def mirror_uvs(mesh: str, axis: MirrorAxis = MirrorAxis.X,
                   uvs: Optional[List[int]] = None) -> bool:
        """
        Mirror UVs of a mesh along the U or V direction.
        axis: 'x' mirrors U, 'y' mirrors V.
        """
        if not cmds.objExists(mesh):
            return False

        # Get mesh
        sel = om2.MSelectionList()
        sel.add(mesh)
        mesh_obj = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(mesh_obj)

        # Get UVs
        uvs = fn_mesh.getUVs()
        u_array = uvs[0]
        v_array = uvs[1]
        num_uvs = len(u_array)

        # Mirror based on axis
        if axis == MirrorAxis.X:
            # Mirror U: u' = 1 - u
            for i in range(num_uvs):
                u_array[i] = 1.0 - u_array[i]
        elif axis == MirrorAxis.Y:
            # Mirror V: v' = 1 - v
            for i in range(num_uvs):
                v_array[i] = 1.0 - v_array[i]

        # Set UVs back
        fn_mesh.setUVs(u_array, v_array)
        return True

# -----------------------------------------------------------------------------
# Part 12 — Controller Shape Mirroring
# -----------------------------------------------------------------------------

class ControllerShapeMirror:
    """
    Mirror controller shapes (NURBS curves, etc.) from source to target.
    """
    @staticmethod
    def mirror_controller_shape(source: str, target: str,
                                settings: MirrorSettings) -> bool:
        """
        Mirror the shape of a controller (duplicate shape and mirror transforms).
        """
        if not cmds.objExists(source) or not cmds.objExists(target):
            return False

        # Get shapes of source
        shapes = cmds.listRelatives(source, shapes=True, fullPath=True) or []
        if not shapes:
            logger.warning(f"No shapes found on {source}.")
            return False

        # Duplicate source shape to target
        # We'll duplicate the source, parent to target, then delete original shape?
        # Simpler: create a duplicate of source and parent to target, then mirror transforms.
        # But we want to preserve the target's existing shape?
        # For now, we'll replace the target's shape with a mirrored copy of source.

        # Delete existing shapes on target (optionally)
        target_shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        for s in target_shapes:
            cmds.delete(s)

        # Duplicate source shape and parent to target
        dup = cmds.duplicate(source, returnRootsOnly=True)[0]
        dup_shapes = cmds.listRelatives(dup, shapes=True, fullPath=True) or []
        for s in dup_shapes:
            cmds.parent(s, target, shape=True, add=True)

        # Delete the temporary duplicate transform
        cmds.delete(dup)

        # Now mirror the shape transforms (they are children of target)
        # Actually, the shape is now under target; we need to mirror its CVs? 
        # For NURBS, we can mirror the control vertices.
        # For simplicity, we'll just set the shape's transform to mirror.
        # A more robust approach: use cmds.xform on the shape's CVs.

        # For now, we'll just mirror the transform (scale -1 on axis)
        # But the shape might need to have its CVs mirrored.
        # We'll implement CV mirroring for NURBS curves.

        # Get all shapes of target
        target_shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        for shape in target_shapes:
            if cmds.nodeType(shape) == "nurbsCurve":
                # Get control points
                cvs = cmds.getAttr(f"{shape}.controlPoints[*]")
                if not cvs:
                    continue
                # Mirror CVs
                mirrored_cvs = []
                axis_index = {"x": 0, "y": 1, "z": 2}[settings.axis.value]
                for cv in cvs:
                    new_cv = list(cv)
                    new_cv[axis_index] = -cv[axis_index]
                    mirrored_cvs.append(new_cv)
                # Set CVs
                for i, cv in enumerate(mirrored_cvs):
                    cmds.setAttr(f"{shape}.controlPoints[{i}]", *cv)

        return True

# -----------------------------------------------------------------------------
# Part 13 — Selection Mirroring
# -----------------------------------------------------------------------------

class SelectionMirror:
    """
    Mirror selection: select the mirror counterparts of currently selected objects.
    """
    @staticmethod
    def mirror_selection(resolver: MirrorNameResolver,
                         replace: bool = True) -> List[str]:
        """
        Get the mirror counterparts of the current selection.
        If replace is True, select the mirrored objects; else return list.
        """
        selected = cmds.ls(selection=True, long=True)
        if not selected:
            logger.warning("Nothing selected.")
            return []

        mirrored = []
        for node in selected:
            mirror_name = resolver.get_mirror_name(node)
            if mirror_name and cmds.objExists(mirror_name):
                mirrored.append(mirror_name)
            else:
                logger.warning(f"No mirror counterpart found for {node}")

        if replace and mirrored:
            cmds.select(mirrored, replace=True)
        return mirrored

# -----------------------------------------------------------------------------
# Part 14 — Validation (Pre-Mirror Checks)
# -----------------------------------------------------------------------------

class MirrorValidator:
    """
    Validate that mirror operation can proceed.
    """
    @staticmethod
    def validate_pair(source: str, target: str, settings: MirrorSettings) -> List[str]:
        """
        Validate a source-target pair. Returns list of error messages.
        """
        errors = []
        if not cmds.objExists(source):
            errors.append(f"Source '{source}' does not exist.")
        if not cmds.objExists(target):
            errors.append(f"Target '{target}' does not exist.")
        if settings.ignore_locked:
            # Check if source or target is locked
            if cmds.getAttr(f"{source}.locked", lock=True) if cmds.objExists(source) else False:
                errors.append(f"Source '{source}' is locked.")
        return errors

    @staticmethod
    def validate_blendshape_node(node: str) -> List[str]:
        errors = []
        if not cmds.objExists(node):
            errors.append(f"Blendshape node '{node}' does not exist.")
        elif cmds.nodeType(node) != "blendShape":
            errors.append(f"'{node}' is not a blendShape node.")
        return errors

# -----------------------------------------------------------------------------
# Part 15 — Diagnostics (Reporting)
# -----------------------------------------------------------------------------

class MirrorDiagnostics:
    """
    Collect statistics and generate reports.
    """
    @staticmethod
    def generate_report(operation: str, settings: MirrorSettings,
                        stats: MirrorStatistics,
                        warnings: List[str], errors: List[str],
                        pairs: List[Tuple[str, str]]) -> MirrorReport:
        """
        Create a MirrorReport from collected data.
        """
        report = MirrorReport(
            success=len(errors) == 0,
            mode=MirrorMode(operation),
            settings=settings,
            statistics=stats,
            warnings=warnings,
            errors=errors,
            mirrored_pairs=pairs,
        )
        return report

# -----------------------------------------------------------------------------
# Part 16 — Utilities (Helper Functions)
# -----------------------------------------------------------------------------

class MirrorUtils:
    """
    Miscellaneous helper functions for mirroring.
    """
    @staticmethod
    def get_children_by_side(node: str, side: str) -> List[str]:
        """Get children of a node that have a specific side in their name."""
        children = cmds.listRelatives(node, children=True, fullPath=True) or []
        result = []
        for child in children:
            if side == "L" and (child.startswith("L_") or child.startswith("Left")):
                result.append(child)
            elif side == "R" and (child.startswith("R_") or child.startswith("Right")):
                result.append(child)
        return result

    @staticmethod
    def get_mirror_controller_pairs(controllers: List[str],
                                    resolver: MirrorNameResolver) -> List[MirrorPair]:
        """Get mirror pairs for a list of controllers."""
        pairs = []
        processed = set()
        for ctrl in controllers:
            if ctrl in processed:
                continue
            mirror = resolver.get_mirror_name(ctrl)
            if mirror and mirror in controllers:
                pairs.append(MirrorPair(source=ctrl, target=mirror))
                processed.add(ctrl)
                processed.add(mirror)
            else:
                # No mirror found, still add as single?
                pairs.append(MirrorPair(source=ctrl, target=""))
                processed.add(ctrl)
        return pairs

    @staticmethod
    def get_axis_multiplier(axis: MirrorAxis) -> Tuple[float, float, float]:
        """Get the multiplier for each axis when mirroring."""
        if axis == MirrorAxis.X:
            return (-1.0, 1.0, 1.0)
        elif axis == MirrorAxis.Y:
            return (1.0, -1.0, 1.0)
        else:  # Z
            return (1.0, 1.0, -1.0)

    @staticmethod
    def ensure_visibility(node: str) -> None:
        """Make sure a node is visible and unlocked."""
        if cmds.objExists(node):
            cmds.setAttr(f"{node}.visibility", 1)
            for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]:
                full = f"{node}.{attr}"
                if cmds.objExists(full):
                    cmds.setAttr(full, lock=False)

# -----------------------------------------------------------------------------
# Part 17 — Main MirrorTools Class (Public API)
# -----------------------------------------------------------------------------

class MirrorTools:
    """
    Main facade for all mirroring operations.
    """
    def __init__(self):
        self.table_manager = MirrorTableManager()
        self.resolver = MirrorNameResolver(self.table_manager)
        self.validator = MirrorValidator()
        self.diagnostics = MirrorDiagnostics()
        self.utils = MirrorUtils()
        self._last_report: Optional[MirrorReport] = None

    # ---------- Settings ----------
    def create_settings(self, **kwargs) -> MirrorSettings:
        """Create a MirrorSettings object with optional overrides."""
        settings = MirrorSettings()
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        return settings

    # ---------- Name Resolution ----------
    def set_mirror_table(self, table_name: str):
        self.table_manager.set_active_table(table_name)

    def add_custom_mapping(self, source: str, target: str):
        self.resolver.add_custom_mapping(source, target)

    def get_mirror_name(self, node: str) -> Optional[str]:
        return self.resolver.get_mirror_name(node)

    # ---------- Mirror Operations ----------
    def mirror_transform(self, source: str, target: str,
                         settings: Optional[MirrorSettings] = None) -> bool:
        """
        Mirror transforms from source to target.
        """
        if settings is None:
            settings = self.create_settings()
        return TransformMirror.mirror_transforms(source, target, settings)

    def mirror_pose(self, source_controllers: List[str],
                    target_controllers: List[str],
                    settings: Optional[MirrorSettings] = None) -> bool:
        """
        Mirror the current pose from source controllers to target controllers.
        """
        if settings is None:
            settings = self.create_settings()
        return PoseMirror.mirror_current_pose(source_controllers, target_controllers, settings)

    def mirror_animation(self, source: str, target: str,
                         settings: Optional[MirrorSettings] = None) -> bool:
        """
        Mirror animation from source to target.
        """
        if settings is None:
            settings = self.create_settings()
        return AnimationMirror.mirror_animation(source, target, settings)

    def mirror_blendshapes(self, blendshape_node: str,
                           resolver: Optional[MirrorNameResolver] = None) -> bool:
        """
        Mirror blendshape weights by name.
        """
        if resolver is None:
            resolver = self.resolver
        return BlendshapeMirror.mirror_blendshape_weights_by_name(blendshape_node,
                                                                  self.create_settings(),
                                                                  resolver)

    def mirror_mesh(self, mesh: str, target_mesh: Optional[str] = None,
                    settings: Optional[MirrorSettings] = None) -> bool:
        """
        Mirror mesh vertices.
        """
        if settings is None:
            settings = self.create_settings()
        return MeshMirror.mirror_mesh_vertices(mesh, settings, target_mesh)

    def mirror_uvs(self, mesh: str, axis: MirrorAxis = MirrorAxis.X) -> bool:
        """
        Mirror UVs.
        """
        return UVMirror.mirror_uvs(mesh, axis)

    def mirror_controller_shape(self, source: str, target: str,
                                settings: Optional[MirrorSettings] = None) -> bool:
        """
        Mirror controller shapes.
        """
        if settings is None:
            settings = self.create_settings()
        return ControllerShapeMirror.mirror_controller_shape(source, target, settings)

    def mirror_selected(self, replace: bool = True) -> List[str]:
        """
        Mirror the current selection.
        """
        return SelectionMirror.mirror_selection(self.resolver, replace)

    # ---------- Validation ----------
    def validate_pair(self, source: str, target: str,
                      settings: Optional[MirrorSettings] = None) -> List[str]:
        if settings is None:
            settings = self.create_settings()
        return self.validator.validate_pair(source, target, settings)

    def validate_blendshape_node(self, node: str) -> List[str]:
        return self.validator.validate_blendshape_node(node)

    # ---------- Reporting ----------
    def get_last_report(self) -> Optional[MirrorReport]:
        return self._last_report

    def generate_report(self, operation: str, settings: MirrorSettings,
                        stats: MirrorStatistics, warnings: List[str],
                        errors: List[str], pairs: List[Tuple[str, str]]) -> MirrorReport:
        return self.diagnostics.generate_report(operation, settings, stats,
                                                warnings, errors, pairs)

    # ---------- Full workflow ----------
    def mirror(self, mode: MirrorMode, nodes: Union[str, List[str]],
               settings: Optional[MirrorSettings] = None) -> MirrorReport:
        """
        Generic mirror entry point.
        """
        if settings is None:
            settings = self.create_settings()

        start_time = time.time()
        stats = MirrorStatistics()
        warnings = []
        errors = []
        pairs = []

        # Determine what to do based on mode
        if mode == MirrorMode.SELECTION:
            mirrored = self.mirror_selected()
            stats.mirrored_nodes = len(mirrored)
            report = self.generate_report("selection", settings, stats, warnings, errors, [])
            self._last_report = report
            return report

        # Convert nodes to list
        if isinstance(nodes, str):
            nodes = [nodes]

        # For each node, find mirror counterpart and perform operation
        for node in nodes:
            target = self.resolver.get_mirror_name(node)
            if not target:
                warnings.append(f"No mirror counterpart found for {node}")
                stats.skipped_nodes += 1
                continue

            # Validate
            validation_errors = self.validate_pair(node, target, settings)
            if validation_errors:
                errors.extend(validation_errors)
                stats.failed_nodes += 1
                continue

            # Perform operation based on mode
            success = False
            if mode == MirrorMode.TRANSFORM or mode == MirrorMode.CONTROLLER:
                success = TransformMirror.mirror_transforms(node, target, settings)
            elif mode == MirrorMode.POSE:
                success = PoseMirror.mirror_current_pose([node], [target], settings)
            elif mode == MirrorMode.ANIMATION:
                success = AnimationMirror.mirror_animation(node, target, settings)
            elif mode == MirrorMode.BLENDSHAPE:
                # This mode expects a blendshape node and handles all targets
                # For simplicity, call the blendshape mirror function separately
                success = BlendshapeMirror.mirror_blendshape_weights_by_name(
                    node, settings, self.resolver
                )
            elif mode == MirrorMode.MESH:
                success = MeshMirror.mirror_mesh_vertices(node, settings, target)
            elif mode == MirrorMode.UV:
                success = UVMirror.mirror_uvs(node, settings.axis)
            else:
                errors.append(f"Unsupported mirror mode: {mode}")
                continue

            if success:
                stats.mirrored_nodes += 1
                pairs.append((node, target))
            else:
                stats.failed_nodes += 1
                errors.append(f"Failed to mirror {node} to {target}")

        stats.total_nodes = len(nodes)
        stats.duration_ms = (time.time() - start_time) * 1000

        report = self.generate_report(mode.value, settings, stats, warnings, errors, pairs)
        self._last_report = report
        return report

# -----------------------------------------------------------------------------
# Singleton and Convenience Functions (Public API)
# -----------------------------------------------------------------------------

_mirror_tools: Optional[MirrorTools] = None

def get_mirror_tools() -> MirrorTools:
    """Get the global MirrorTools instance."""
    global _mirror_tools
    if _mirror_tools is None:
        _mirror_tools = MirrorTools()
    return _mirror_tools

def mirror_transform(source: str, target: str,
                     axis: MirrorAxis = MirrorAxis.X,
                     behavior: MirrorBehavior = MirrorBehavior.SWAP) -> bool:
    """Quick mirror transform."""
    tools = get_mirror_tools()
    settings = tools.create_settings(axis=axis, behavior=behavior)
    return tools.mirror_transform(source, target, settings)

def mirror_selected(axis: MirrorAxis = MirrorAxis.X,
                    behavior: MirrorBehavior = MirrorBehavior.SWAP) -> List[str]:
    """Quick mirror selected objects."""
    tools = get_mirror_tools()
    settings = tools.create_settings(axis=axis, behavior=behavior)
    return tools.mirror_selected()

def mirror_animation(source: str, target: str,
                     start: Optional[int] = None,
                     end: Optional[int] = None,
                     axis: MirrorAxis = MirrorAxis.X) -> bool:
    """Quick mirror animation."""
    tools = get_mirror_tools()
    settings = tools.create_settings(axis=axis, animation_start=start, animation_end=end)
    return tools.mirror_animation(source, target, settings)

def mirror_blendshapes(blendshape_node: str) -> bool:
    """Quick mirror blendshape weights."""
    tools = get_mirror_tools()
    return tools.mirror_blendshapes(blendshape_node)

def mirror_mesh(mesh: str, target_mesh: Optional[str] = None,
                axis: MirrorAxis = MirrorAxis.X) -> bool:
    """Quick mirror mesh vertices."""
    tools = get_mirror_tools()
    settings = tools.create_settings(axis=axis)
    return tools.mirror_mesh(mesh, target_mesh, settings)

def mirror_uvs(mesh: str, axis: MirrorAxis = MirrorAxis.X) -> bool:
    """Quick mirror UVs."""
    tools = get_mirror_tools()
    return tools.mirror_uvs(mesh, axis)

def get_mirror_name(node: str) -> Optional[str]:
    """Get mirror counterpart name."""
    tools = get_mirror_tools()
    return tools.get_mirror_name(node)

def set_mirror_table(table_name: str):
    """Set active mirror table."""
    tools = get_mirror_tools()
    tools.set_mirror_table(table_name)

def add_custom_mirror_mapping(source: str, target: str):
    """Add a custom name mapping."""
    tools = get_mirror_tools()
    tools.add_custom_mapping(source, target)

# -----------------------------------------------------------------------------
# Self-test (if run directly)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal test (requires Maya)
    print("Mirror module loaded. Use within Maya.")