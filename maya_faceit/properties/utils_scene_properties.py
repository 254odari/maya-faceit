# utils_scene_properties.py
# Maya Faceit Plugin - Utils Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Utils scene properties for Faceit Maya plugin.
Defines utility properties for shape key ranges.
"""

import maya.cmds as cmds # type: ignore


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit utils scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Shape key slider range
    if not cmds.attributeQuery("shape_key_slider_min", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="shape_key_slider_min", attributeType="float", defaultValue=0.0)
    
    if not cmds.attributeQuery("shape_key_slider_max", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="shape_key_slider_max", attributeType="float", defaultValue=1.0)


def unregister() -> None:
    """
    Unregister Faceit utils scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = ["shape_key_slider_min", "shape_key_slider_max"]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Property Accessors
# ============================================================

def get_shape_key_slider_min() -> float:
    """Get the shape key slider minimum."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shape_key_slider_min", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.shape_key_slider_min")
    return 0.0


def set_shape_key_slider_min(value: float) -> None:
    """Set the shape key slider minimum."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shape_key_slider_min", node="faceit_core_data", exists=True):
            # Ensure min < max
            max_val = get_shape_key_slider_max()
            if value >= max_val:
                value = max_val - 0.001
            cmds.setAttr("faceit_core_data.shape_key_slider_min", value)


def get_shape_key_slider_max() -> float:
    """Get the shape key slider maximum."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shape_key_slider_max", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.shape_key_slider_max")
    return 1.0


def set_shape_key_slider_max(value: float) -> None:
    """Set the shape key slider maximum."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shape_key_slider_max", node="faceit_core_data", exists=True):
            # Ensure max > min
            min_val = get_shape_key_slider_min()
            if value <= min_val:
                value = min_val + 0.001
            cmds.setAttr("faceit_core_data.shape_key_slider_max", value)