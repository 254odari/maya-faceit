# -*- coding: utf-8 -*-
"""
tools/attributes/visibility.py

Node and attribute visibility management.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Union, Tuple


# =============================================================================
# NODE VISIBILITY
# =============================================================================

def show_node(node: str) -> bool:
    """
    Show a node (set visibility to 1).

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    cmds.setAttr(f"{node}.visibility", 1)
    return True


def hide_node(node: str) -> bool:
    """
    Hide a node (set visibility to 0).

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    cmds.setAttr(f"{node}.visibility", 0)
    return True


def set_node_visibility(node: str, visible: bool) -> bool:
    """
    Set the visibility of a node.

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    cmds.setAttr(f"{node}.visibility", 1 if visible else 0)
    return True


def get_node_visibility(node: str) -> Optional[bool]:
    """
    Get the current visibility of a node.

    Returns:
        True if visible, False if hidden, None if node doesn't exist.
    """
    if not cmds.objExists(node):
        return None
    return cmds.getAttr(f"{node}.visibility") != 0


# =============================================================================
# DISPLAY OVERRIDE
# =============================================================================

def set_display_override(node: str, color: Optional[Tuple[float, float, float]] = None,
                         shading: Optional[int] = None,
                         draw_style: Optional[str] = None) -> bool:
    """
    Set display override for a node.

    Args:
        node: Node name.
        color: RGB color (0-1) tuple.
        shading: Shading mode (0=wireframe, 1=solid, 2=shaded).
        draw_style: "wireframe", "shaded", "boundingBox", etc.

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False

    # Enable override
    cmds.setAttr(f"{node}.overrideEnabled", 1)

    if color is not None:
        cmds.setAttr(f"{node}.overrideRGBColors", 1)
        cmds.setAttr(f"{node}.overrideColorR", color[0])
        cmds.setAttr(f"{node}.overrideColorG", color[1])
        cmds.setAttr(f"{node}.overrideColorB", color[2])

    if shading is not None:
        cmds.setAttr(f"{node}.overrideShading", shading)

    if draw_style is not None:
        # Map draw style to Maya constants (simplified)
        style_map = {
            "wireframe": 0,
            "shaded": 1,
            "boundingBox": 2,
            "points": 3,
        }
        if draw_style in style_map:
            cmds.setAttr(f"{node}.overrideDisplay", style_map[draw_style])

    return True


def clear_display_override(node: str) -> bool:
    """
    Remove display overrides (reset to default).

    Returns:
        True if successful.
    """
    if not cmds.objExists(node):
        return False
    cmds.setAttr(f"{node}.overrideEnabled", 0)
    return True


# =============================================================================
# DISPLAY LAYER VISIBILITY
# =============================================================================

def set_display_layer_visibility(layer: str, visible: bool) -> bool:
    """
    Set visibility of a display layer.

    Args:
        layer: Layer name.
        visible: True to show, False to hide.

    Returns:
        True if successful.
    """
    if not cmds.objExists(layer):
        return False
    cmds.setAttr(f"{layer}.visibility", 1 if visible else 0)
    return True


def get_display_layer_visibility(layer: str) -> Optional[bool]:
    """
    Get the visibility of a display layer.

    Returns:
        True if visible, False if hidden, None if layer doesn't exist.
    """
    if not cmds.objExists(layer):
        return None
    return cmds.getAttr(f"{layer}.visibility") != 0