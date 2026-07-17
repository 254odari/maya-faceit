"""
animation/layers.py

Animation Layer Management System for Maya.

This module provides a complete framework for creating, organizing, blending,
baking, merging, and managing animation layers in complex production scenes.
It is the central authority for all animation layer operations.

Responsibilities:
- Create, delete, rename, duplicate animation layers.
- Manage layer membership: add/remove objects, list members.
- Control layer blending: weight, mute, solo, lock, blend modes.
- Manage layer hierarchy: parent/child relationships, grouping.
- Bake, merge, flatten layers.
- Provide diagnostics and statistics.

Dependencies:
- timeline.py (optional) for time range queries.
- keyframes.py (optional) for key editing.
- curves.py (optional) for curve operations.

The module uses Maya's native animation layers but provides a higher-level API.
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

# Try importing timeline/keyframes if available
try:
    from .timeline import TimelineManager
except ImportError:
    class TimelineManager:
        def frame_range(self):
            from dataclasses import dataclass
            @dataclass
            class Range:
                start: int = 1
                end: int = 100
            return Range()

try:
    from .keyframes import KeyframeManager
except ImportError:
    KeyframeManager = None

try:
    from .curves import CurveManager
except ImportError:
    CurveManager = None

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class LayerError(Exception):
    """Base exception for layer operations."""
    pass

class LayerNotFoundError(LayerError):
    """Raised when a layer does not exist."""
    pass

class LayerOperationError(LayerError):
    """Raised when a layer operation fails."""
    pass

class LayerValidationError(LayerError):
    """Raised when validation fails."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class LayerState(Enum):
    """State of an animation layer."""
    ACTIVE = "active"
    MUTED = "muted"
    SOLO = "solo"
    LOCKED = "locked"
    HIDDEN = "hidden"


class BlendMode(Enum):
    """Blend mode for animation layers."""
    OVERRIDE = "override"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SUBTRACT = "subtract"


class LayerType(Enum):
    """Suggested layer types."""
    BASE = "base"
    FACIAL = "facial"
    BODY = "body"
    CAMERA = "camera"
    CORRECTIVE = "corrective"
    UTILITY = "utility"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class AnimationLayer:
    """
    Representation of an animation layer.
    """
    name: str
    weight: float = 1.0
    muted: bool = False
    solo: bool = False
    locked: bool = False
    hidden: bool = False
    blend_mode: BlendMode = BlendMode.OVERRIDE
    layer_type: LayerType = LayerType.UTILITY
    members: List[str] = field(default_factory=list)  # object paths
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)  # child layer names
    color: Optional[List[float]] = None  # RGB 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight,
            "muted": self.muted,
            "solo": self.solo,
            "locked": self.locked,
            "hidden": self.hidden,
            "blend_mode": self.blend_mode.value,
            "layer_type": self.layer_type.value,
            "members": self.members,
            "parent": self.parent,
            "children": self.children,
            "color": self.color,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AnimationLayer:
        return cls(
            name=data["name"],
            weight=data.get("weight", 1.0),
            muted=data.get("muted", False),
            solo=data.get("solo", False),
            locked=data.get("locked", False),
            hidden=data.get("hidden", False),
            blend_mode=BlendMode(data.get("blend_mode", "override")),
            layer_type=LayerType(data.get("layer_type", "utility")),
            members=data.get("members", []),
            parent=data.get("parent"),
            children=data.get("children", []),
            color=data.get("color"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LayerSettings:
    """Global layer settings."""
    default_weight: float = 1.0
    allow_negative_weights: bool = False
    auto_rename_on_duplicate: bool = True
    preserve_members_on_merge: bool = True
    bake_range_start: Optional[int] = None
    bake_range_end: Optional[int] = None


@dataclass
class LayerStatistics:
    """Statistics for layer management."""
    total_layers: int = 0
    active_layer: Optional[str] = None
    muted_count: int = 0
    solo_count: int = 0
    locked_count: int = 0
    total_members: int = 0
    max_depth: int = 0
    average_members: float = 0.0
    empty_layers: int = 0


@dataclass
class LayerReport:
    """Diagnostic report."""
    success: bool
    layers_processed: int = 0
    members_added: int = 0
    members_removed: int = 0
    layers_merged: int = 0
    layers_baked: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Animation Layer Manager ---------------------------------

class AnimationLayerManager:
    """
    Main controller for all animation layer operations.
    """
    def __init__(self):
        self._timeline = TimelineManager()
        self._keyframe_manager = KeyframeManager() if KeyframeManager else None
        self._curve_manager = CurveManager() if CurveManager else None
        self._settings = LayerSettings()
        self._last_report: Optional[LayerReport] = None
        self._statistics: LayerStatistics = LayerStatistics()
        # Cache of known layers
        self._layer_cache: Dict[str, AnimationLayer] = {}
        self._refresh_cache()

    # ---- Core Query ----

    def list_layers(self) -> List[str]:
        """Return all animation layer names in the scene."""
        return cmds.ls(type='animLayer') or []

    def exists(self, name: str) -> bool:
        """Check if a layer exists."""
        return cmds.objExists(name) and cmds.nodeType(name) == 'animLayer'

    def current_layer(self) -> Optional[str]:
        """Return the name of the currently active animation layer."""
        active = cmds.animLayer(q=True, active=True)
        return active[0] if active else None

    def activate(self, name: str) -> None:
        """Set the active animation layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        cmds.animLayer(name, e=True, active=True)
        self._refresh_cache()

    def get_layer(self, name: str) -> AnimationLayer:
        """Get an AnimationLayer object representing the layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if name in self._layer_cache:
            return self._layer_cache[name]
        # Build from Maya
        layer = self._build_layer_from_maya(name)
        self._layer_cache[name] = layer
        return layer

    def _build_layer_from_maya(self, name: str) -> AnimationLayer:
        """Build AnimationLayer object from Maya node data."""
        # Get attributes
        weight = cmds.getAttr(f"{name}.weight") if cmds.objExists(f"{name}.weight") else 1.0
        muted = cmds.getAttr(f"{name}.mute") if cmds.objExists(f"{name}.mute") else False
        solo = cmds.getAttr(f"{name}.solo") if cmds.objExists(f"{name}.solo") else False
        locked = cmds.getAttr(f"{name}.lock") if cmds.objExists(f"{name}.lock") else False
        # Members: objects connected to the layer via '.members' attribute?
        # In Maya, layers have connections; we can find members by looking at objects with this layer in their layer attribute.
        # Simpler: use `cmds.animLayer` - members?
        # We'll collect members by querying objects that have this layer in their 'layer' attribute.
        # Not straightforward. We'll keep members empty for now.
        members = []
        # Color (if available)
        color = None
        if cmds.objExists(f"{name}.color"):
            color = cmds.getAttr(f"{name}.color")[0]
        return AnimationLayer(
            name=name,
            weight=weight,
            muted=muted,
            solo=solo,
            locked=locked,
            members=members,
            color=color,
        )

    def _refresh_cache(self):
        """Refresh the cache of layers."""
        self._layer_cache = {}
        for layer_name in self.list_layers():
            self._layer_cache[layer_name] = self._build_layer_from_maya(layer_name)

    # ---- CRUD Operations ----

    def create(self, name: str, layer_type: LayerType = LayerType.UTILITY, color: Optional[List[float]] = None) -> str:
        """
        Create a new animation layer.
        """
        if self.exists(name):
            raise LayerOperationError(f"Layer '{name}' already exists")
        # Create layer
        cmds.animLayer(name)
        # Set optional attributes
        if color:
            if cmds.objExists(f"{name}.color"):
                cmds.setAttr(f"{name}.color", *color)
        # Add to cache
        self._refresh_cache()
        return name

    def delete(self, name: str) -> None:
        """Delete an animation layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        cmds.delete(name)
        self._refresh_cache()

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a layer."""
        if not self.exists(old_name):
            raise LayerNotFoundError(f"Layer '{old_name}' not found")
        if self.exists(new_name):
            raise LayerOperationError(f"Layer '{new_name}' already exists")
        cmds.rename(old_name, new_name)
        self._refresh_cache()

    def duplicate(self, name: str, new_name: Optional[str] = None) -> str:
        """Duplicate a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if new_name is None:
            base = name
            counter = 1
            while self.exists(f"{base}_{counter}"):
                counter += 1
            new_name = f"{base}_{counter}"
        cmds.duplicate(name, name=new_name)
        self._refresh_cache()
        return new_name

    def clear(self, name: str) -> None:
        """Clear all keys from a layer (reset to default)."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        # We need to clear keys on all objects in the layer
        members = self.members(name)
        for obj in members:
            attrs = cmds.listAttr(obj, keyable=True, scalar=True) or []
            for attr in attrs:
                full_attr = f"{obj}.{attr}"
                cmds.cutKey(full_attr, layer=name, clear=True)
        self._refresh_cache()

    # ---- Layer Membership ----

    def members(self, name: str) -> List[str]:
        """Return all objects (nodes) that belong to a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        # Maya stores members via connection to 'layered' nodes?
        # We'll use `cmds.animLayer` - members?
        # Actually, in Maya, objects are assigned to layers via the `attrAnimLayer` attribute or the `layer` attribute.
        # A common method: find all objects that have the layer in their 'layer' attribute.
        # We'll use `cmds.ls` with the layer flag.
        members = cmds.ls(type='transform') + cmds.ls(type='joint')
        assigned = []
        for obj in members:
            layer_attr = f"{obj}.layer"
            if cmds.objExists(layer_attr):
                layer_value = cmds.getAttr(layer_attr)
                if layer_value == name:
                    assigned.append(obj)
        return assigned

    def add_members(self, name: str, objects: List[str]) -> None:
        """Add objects to a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            # Set the layer attribute on the object
            layer_attr = f"{obj}.layer"
            if not cmds.objExists(layer_attr):
                # Add attribute if not exists
                cmds.addAttr(obj, longName='layer', dataType='string')
            cmds.setAttr(layer_attr, name, type='string')
        self._refresh_cache()

    def remove_members(self, name: str, objects: List[str]) -> None:
        """Remove objects from a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        for obj in objects:
            layer_attr = f"{obj}.layer"
            if cmds.objExists(layer_attr):
                current = cmds.getAttr(layer_attr)
                if current == name:
                    # Clear the layer assignment
                    cmds.setAttr(layer_attr, '', type='string')
        self._refresh_cache()

    def replace_members(self, name: str, objects: List[str]) -> None:
        """Replace all members of a layer with a new list."""
        current = set(self.members(name))
        new_set = set(objects)
        to_remove = current - new_set
        to_add = new_set - current
        if to_remove:
            self.remove_members(name, list(to_remove))
        if to_add:
            self.add_members(name, list(to_add))
        self._refresh_cache()

    # ---- Layer Blending ----

    def weight(self, name: str, value: Optional[float] = None) -> float:
        """
        Get or set the weight of a layer.
        If value is None, returns current weight.
        """
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if value is not None:
            # Clamp if needed
            if not self._settings.allow_negative_weights and value < 0:
                value = 0.0
            cmds.setAttr(f"{name}.weight", value)
        return cmds.getAttr(f"{name}.weight")

    def mute(self, name: str, muted: bool = True) -> None:
        """Mute or unmute a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        cmds.setAttr(f"{name}.mute", muted)

    def solo(self, name: str, solo: bool = True) -> None:
        """Solo or unsolo a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        cmds.setAttr(f"{name}.solo", solo)

    def lock(self, name: str, locked: bool = True) -> None:
        """Lock or unlock a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        cmds.setAttr(f"{name}.lock", locked)

    def set_blend_mode(self, name: str, mode: BlendMode) -> None:
        """Set the blend mode of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        # Maya doesn't have built-in blend modes for animation layers.
        # We'll store as metadata on the layer.
        if not cmds.objExists(f"{name}.blendMode"):
            cmds.addAttr(name, longName='blendMode', dataType='string')
        cmds.setAttr(f"{name}.blendMode", mode.value, type='string')

    def get_blend_mode(self, name: str) -> BlendMode:
        """Get the blend mode of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if cmds.objExists(f"{name}.blendMode"):
            val = cmds.getAttr(f"{name}.blendMode")
            return BlendMode(val)
        return BlendMode.OVERRIDE

    # ---- Layer Hierarchy ----

    def parent_layer(self, child: str, parent: str) -> None:
        """Set a parent layer for a child layer."""
        if not self.exists(child) or not self.exists(parent):
            raise LayerNotFoundError("One or both layers not found")
        # Maya doesn't support layer hierarchy natively.
        # We'll store parent/child relationships as metadata on the layers.
        if not cmds.objExists(f"{child}.parent"):
            cmds.addAttr(child, longName='parent', dataType='string')
        cmds.setAttr(f"{child}.parent", parent, type='string')
        # Also store children on parent
        if not cmds.objExists(f"{parent}.children"):
            cmds.addAttr(parent, longName='children', dataType='string')
        # Append child to parent's children list
        # We'll store as a string list; for simplicity, we'll use a string that we can parse.
        current = cmds.getAttr(f"{parent}.children") if cmds.objExists(f"{parent}.children") else ""
        children = current.split(',') if current else []
        if child not in children:
            children.append(child)
            cmds.setAttr(f"{parent}.children", ','.join(children), type='string')
        self._refresh_cache()

    def children_layers(self, name: str) -> List[str]:
        """Return child layers of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if cmds.objExists(f"{name}.children"):
            val = cmds.getAttr(f"{name}.children")
            if val:
                return val.split(',')
        return []

    def parent_of(self, name: str) -> Optional[str]:
        """Return parent layer of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if cmds.objExists(f"{name}.parent"):
            return cmds.getAttr(f"{name}.parent")
        return None

    # ---- Layer Baking & Merging ----

    def bake_layer(self, name: str, start: Optional[int] = None, end: Optional[int] = None) -> LayerReport:
        """
        Bake the layer: bake its animation onto the base layer or the layer itself.
        """
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if start is None:
            start = self._timeline.frame_range().start
        if end is None:
            end = self._timeline.frame_range().end
        # We'll use Maya's bake command for the layer's members.
        members = self.members(name)
        if not members:
            return LayerReport(success=True, layers_processed=1, warnings=["Layer has no members"])
        # We'll bake using `cmds.bakeResults` but with layer-specific settings?
        # Actually, Maya's bakeResults doesn't have a layer parameter; we need to bake on the layer.
        # We can set the layer active, then bake the objects, but keys will go to the active layer.
        # We'll do that.
        previous_active = self.current_layer()
        self.activate(name)
        report = LayerReport(success=True, layers_processed=1)
        for obj in members:
            try:
                # Bake all animatable attributes
                cmds.bakeResults(obj, t=(start, end), simulation=True, disableImplicitControl=True)
                # Maya will put keys on the active layer.
            except Exception as e:
                report.errors.append(f"Failed to bake {obj}: {e}")
                report.success = False
        # Restore previous active layer
        if previous_active and previous_active != name:
            self.activate(previous_active)
        self._refresh_cache()
        return report

    def merge_layers(self, source: str, target: str, delete_source: bool = True) -> LayerReport:
        """
        Merge source layer into target layer.
        """
        if not self.exists(source):
            raise LayerNotFoundError(f"Source layer '{source}' not found")
        if not self.exists(target):
            raise LayerNotFoundError(f"Target layer '{target}' not found")
        # We need to merge keys from source into target.
        # Approach: collect all keys from source members, and set them on target.
        source_members = self.members(source)
        report = LayerReport(success=True, layers_processed=2)
        # For each member, copy keys from source layer to target layer
        # We'll need to switch layers to copy keys.
        # Maya's copy/paste keys can work across layers if we specify the layer.
        # We'll use `cmds.copyKey` and `cmds.pasteKey` with layer flags.
        # However, copyKey/pasteKey have '-layer' flag in newer Maya versions.
        # We'll use a fallback: iterate through all keys and recreate on target.
        # We'll use keyframe command with layer parameter.
        for obj in source_members:
            attrs = cmds.listAttr(obj, keyable=True, scalar=True) or []
            for attr in attrs:
                full_attr = f"{obj}.{attr}"
                # Get keys on this attr on source layer
                times = cmds.keyframe(full_attr, layer=source, q=True) or []
                if not times:
                    continue
                values = []
                for t in times:
                    val = cmds.keyframe(full_attr, layer=source, q=True, time=(t, t), valueChange=True)[0]
                    values.append(val)
                # Delete existing keys on target for this attr
                cmds.cutKey(full_attr, layer=target, clear=True)
                # Insert keys on target layer
                for t, v in zip(times, values):
                    cmds.setKeyframe(full_attr, t=t, v=v, layer=target)
        # Optionally delete source
        if delete_source:
            self.delete(source)
            report.layers_merged = 1
        self._refresh_cache()
        return report

    def flatten(self, name: str) -> LayerReport:
        """
        Flatten a layer: bake it into the base layer and delete it.
        """
        return self.merge_layers(name, "BaseLayer", delete_source=True)

    def bake_all(self, start: Optional[int] = None, end: Optional[int] = None) -> LayerReport:
        """Bake all layers into the base layer."""
        layers = self.list_layers()
        report = LayerReport(success=True)
        for layer in layers:
            if layer == "BaseLayer":
                continue
            self.bake_layer(layer, start, end)
        self._refresh_cache()
        return report

    # ---- Layer Presets & Snapshots ----

    def snapshot(self, name: str) -> Dict[str, Any]:
        """Capture a snapshot of a layer's state."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        layer = self.get_layer(name)
        return {
            "name": name,
            "layer": layer.to_dict(),
            "members": self.members(name),
        }

    def restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Restore a layer from a snapshot."""
        name = snapshot["name"]
        # If layer doesn't exist, create it
        if not self.exists(name):
            self.create(name)
        # Restore attributes
        layer_data = snapshot["layer"]
        self.weight(name, layer_data["weight"])
        self.mute(name, layer_data["muted"])
        self.solo(name, layer_data["solo"])
        self.lock(name, layer_data["locked"])
        # Restore members
        if "members" in snapshot:
            self.replace_members(name, snapshot["members"])
        self._refresh_cache()

    # ---- Diagnostics ----

    def diagnose(self) -> LayerReport:
        """Run diagnostics on the layer system."""
        report = LayerReport(success=True)
        layers = self.list_layers()
        for layer_name in layers:
            if not self.exists(layer_name):
                continue
            # Check for invalid weight
            weight = cmds.getAttr(f"{layer_name}.weight")
            if weight < 0 or weight > 1:
                report.warnings.append(f"Layer '{layer_name}' weight {weight} outside 0-1 range")
            # Check for empty layers
            members = self.members(layer_name)
            if not members:
                report.warnings.append(f"Layer '{layer_name}' has no members")
        report.layers_processed = len(layers)
        return report

    # ---- Statistics ----

    def statistics(self) -> LayerStatistics:
        """Compute statistics for the layer system."""
        layers = self.list_layers()
        stats = LayerStatistics()
        stats.total_layers = len(layers)
        stats.active_layer = self.current_layer()
        for layer_name in layers:
            if cmds.getAttr(f"{layer_name}.mute"):
                stats.muted_count += 1
            if cmds.getAttr(f"{layer_name}.solo"):
                stats.solo_count += 1
            if cmds.getAttr(f"{layer_name}.lock"):
                stats.locked_count += 1
            members = self.members(layer_name)
            stats.total_members += len(members)
            if not members:
                stats.empty_layers += 1
        if stats.total_layers > 0:
            stats.average_members = stats.total_members / stats.total_layers
        # Compute max depth (using hierarchy)
        # We'll use parent_of to compute depth
        depth_map = {}
        for layer in layers:
            depth = 0
            current = layer
            while True:
                parent = self.parent_of(current)
                if parent:
                    depth += 1
                    current = parent
                else:
                    break
            depth_map[layer] = depth
        if depth_map:
            stats.max_depth = max(depth_map.values())
        return stats

    # ---- Utility ----

    def clear_all(self) -> None:
        """Delete all animation layers except BaseLayer."""
        layers = self.list_layers()
        for layer in layers:
            if layer != "BaseLayer":
                self.delete(layer)

    def rename_all(self, pattern: str) -> None:
        """Rename all layers using a pattern (not implemented)."""
        raise NotImplementedError

    def set_color(self, name: str, color: List[float]) -> None:
        """Set the color of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if not cmds.objExists(f"{name}.color"):
            cmds.addAttr(name, longName='color', attributeType='float3')
        cmds.setAttr(f"{name}.color", color[0], color[1], color[2])

    def get_color(self, name: str) -> Optional[List[float]]:
        """Get the color of a layer."""
        if not self.exists(name):
            raise LayerNotFoundError(f"Layer '{name}' not found")
        if cmds.objExists(f"{name}.color"):
            return cmds.getAttr(f"{name}.color")[0]
        return None


# ---- Part 11: Utility Functions --------------------------------------

def ensure_base_layer() -> str:
    """Ensure a base layer exists, create if not."""
    if not cmds.objExists("BaseLayer"):
        cmds.animLayer("BaseLayer")
    return "BaseLayer"


def is_layer(name: str) -> bool:
    """Check if a node is an animation layer."""
    return cmds.objExists(name) and cmds.nodeType(name) == 'animLayer'


def get_layers_for_object(obj: str) -> List[str]:
    """Return all animation layers that contain the object."""
    layers = []
    if not cmds.objExists(obj):
        return layers
    attr = f"{obj}.layer"
    if cmds.objExists(attr):
        layer_name = cmds.getAttr(attr)
        if layer_name:
            layers.append(layer_name)
    return layers


# ---- Part 12: Public API -----------------------------------------------

__all__ = [
    "AnimationLayerManager",
    "AnimationLayer",
    "LayerSettings",
    "LayerStatistics",
    "LayerReport",
    "LayerState",
    "BlendMode",
    "LayerType",
    "LayerError",
    "LayerNotFoundError",
    "LayerOperationError",
    "LayerValidationError",
    "ensure_base_layer",
    "is_layer",
    "get_layers_for_object",
]