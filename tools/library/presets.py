# -*- coding: utf-8 -*-
"""
tools/library/presets.py

Presets for facial expressions/poses.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto

# =============================================================================
# ENUMS
# =============================================================================

class PresetCategory(Enum):
    """Category of a preset."""
    EXPRESSION = "expression"
    POSE = "pose"
    ARKIT = "arkit"
    FACS = "facs"
    CUSTOM = "custom"


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class Preset:
    """Definition of a preset (expression/pose)."""
    name: str
    category: PresetCategory = PresetCategory.CUSTOM
    description: str = ""
    controllers: Dict[str, float] = field(default_factory=dict)   # controller -> value
    blendshapes: Dict[str, float] = field(default_factory=dict)   # blendshape -> weight
    tags: List[str] = field(default_factory=list)
    author: str = "unknown"
    preview: Optional[str] = None  # path to preview image
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PRESET REGISTRY / MANAGER
# =============================================================================

class PresetLibrary:
    """Manager for presets."""

    _presets: Dict[str, Preset] = {}

    @classmethod
    def register(cls, preset: Preset) -> None:
        """Register a preset."""
        cls._presets[preset.name] = preset

    @classmethod
    def get(cls, name: str) -> Optional[Preset]:
        """Get a preset by name."""
        return cls._presets.get(name)

    @classmethod
    def list(cls, category: Optional[PresetCategory] = None) -> List[Preset]:
        """List all presets, optionally filtered by category."""
        if category:
            return [p for p in cls._presets.values() if p.category == category]
        return list(cls._presets.values())

    @classmethod
    def delete(cls, name: str) -> bool:
        """Delete a preset."""
        if name in cls._presets:
            del cls._presets[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all presets."""
        cls._presets.clear()


# =============================================================================
# PRESET APPLICATION
# =============================================================================

def apply_preset(preset: Union[str, Preset], blend: float = 1.0, mix: bool = True) -> bool:
    """
    Apply a preset to the scene.

    Args:
        preset: Preset name or Preset object.
        blend: Blend factor (0-1) for all values.
        mix: If True, add/scale existing values; if False, overwrite.

    Returns:
        True if successful.
    """
    if isinstance(preset, str):
        preset_obj = PresetLibrary.get(preset)
        if not preset_obj:
            return False
    else:
        preset_obj = preset

    success = True

    # Apply controller values
    for ctrl, val in preset_obj.controllers.items():
        if not cmds.objExists(ctrl):
            continue
        # Get current value
        current = 0.0
        try:
            current = cmds.getAttr(ctrl)
        except:
            continue
        # Blend
        new_val = current + (val - current) * blend if mix else val * blend
        try:
            cmds.setAttr(ctrl, new_val)
        except:
            success = False

    # Apply blendshape weights
    for bs_name, val in preset_obj.blendshapes.items():
        # Assume format: "blendshape_node.target"
        parts = bs_name.split('.')
        if len(parts) != 2:
            continue
        node, target = parts
        if not cmds.objExists(node):
            continue
        attr = f"{node}.{target}"
        if not cmds.objExists(attr):
            continue
        current = 0.0
        try:
            current = cmds.getAttr(attr)
        except:
            continue
        new_val = current + (val - current) * blend if mix else val * blend
        try:
            cmds.setAttr(attr, new_val)
        except:
            success = False

    return success


def save_preset(name: str, controllers: Optional[List[str]] = None,
                blendshapes: Optional[List[str]] = None,
                category: PresetCategory = PresetCategory.CUSTOM,
                description: str = "",
                tags: Optional[List[str]] = None) -> bool:
    """
    Save a preset from current scene state.

    Args:
        name: Name for the preset.
        controllers: List of controller names to save. If None, uses selected.
        blendshapes: List of blendshape attributes to save (e.g., "bs_node.target").
        category: Category of the preset.
        description: Description text.
        tags: List of tags.

    Returns:
        True if successful.
    """
    if not controllers:
        # Use selected objects
        controllers = cmds.ls(selection=True, long=True)

    # Filter only transforms
    ctrl_list = [c for c in controllers if cmds.nodeType(c) in ["transform", "joint"]]

    # Get values
    ctrl_vals = {}
    for c in ctrl_list:
        try:
            # Get transform attrs if not custom
            # We'll save all keyable attributes
            attrs = cmds.listAttr(c, keyable=True) or []
            for attr in attrs:
                full = f"{c}.{attr}"
                if cmds.objExists(full):
                    val = cmds.getAttr(full)
                    ctrl_vals[full] = val
        except:
            pass

    # Blendshape values
    bs_vals = {}
    if blendshapes:
        for bs_attr in blendshapes:
            if cmds.objExists(bs_attr):
                try:
                    bs_vals[bs_attr] = cmds.getAttr(bs_attr)
                except:
                    pass
    else:
        # Try to find all blendshape nodes
        all_bs = cmds.ls(type="blendShape")
        for bs in all_bs:
            targets = cmds.listAttr(bs, m=True, string="weight") or []
            for t in targets:
                attr = f"{bs}.{t}"
                try:
                    bs_vals[attr] = cmds.getAttr(attr)
                except:
                    pass

    preset = Preset(
        name=name,
        category=category,
        description=description,
        controllers=ctrl_vals,
        blendshapes=bs_vals,
        tags=tags or [],
    )
    PresetLibrary.register(preset)
    return True


def delete_preset(name: str) -> bool:
    """Delete a preset."""
    return PresetLibrary.delete(name)


def get_preset(name: str) -> Optional[Preset]:
    """Get a preset by name."""
    return PresetLibrary.get(name)


def list_presets(category: Optional[PresetCategory] = None) -> List[Preset]:
    """List all presets."""
    return PresetLibrary.list(category)


def load_preset_from_file(filepath: str) -> Optional[Preset]:
    """Load a preset from a file."""
    # Placeholder – uses serializer internally
    return None


def export_preset(name: str, filepath: str) -> bool:
    """Export a preset to a file."""
    # Placeholder – uses serializer
    return False