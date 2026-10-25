# bake_scene_properties.py
# Maya Faceit Plugin - Bake Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Bake scene properties for Faceit Maya plugin.
Defines scene properties for baking.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional


# ============================================================
# Scene Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit bake scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Add shapes_generated attribute
    if not cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="shapes_generated", attributeType="bool", defaultValue=False)


def unregister() -> None:
    """
    Unregister Faceit bake scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
            cmds.deleteAttr("faceit_core_data", attribute="shapes_generated")


# ============================================================
# Property Accessors
# ============================================================

def get_shapes_generated() -> bool:
    """
    Get the shapes_generated property.
    
    Returns:
        True if shapes are generated
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.shapes_generated")
    return False


def set_shapes_generated(value: bool) -> None:
    """
    Set the shapes_generated property.
    
    Args:
        value: New value
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("shapes_generated", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.shapes_generated", value)