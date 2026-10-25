# bind_scene_properties.py
# Maya Faceit Plugin - Bind Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Bind scene properties for Faceit Maya plugin.
Defines properties for bind state management.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional


# ============================================================
# Scene Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit bind scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Add properties
    if not cmds.attributeQuery("weights_restorable", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="weights_restorable", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("expressions_restorable", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="expressions_restorable", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("corrective_sk_restorable", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="corrective_sk_restorable", attributeType="bool", defaultValue=False)


def unregister() -> None:
    """
    Unregister Faceit bind scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = ["weights_restorable", "expressions_restorable", "corrective_sk_restorable"]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Property Accessors
# ============================================================

def get_weights_restorable() -> bool:
    """Get the weights_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("weights_restorable", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.weights_restorable")
    return False


def set_weights_restorable(value: bool) -> None:
    """Set the weights_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("weights_restorable", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.weights_restorable", value)


def get_expressions_restorable() -> bool:
    """Get the expressions_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expressions_restorable", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.expressions_restorable")
    return False


def set_expressions_restorable(value: bool) -> None:
    """Set the expressions_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expressions_restorable", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.expressions_restorable", value)


def get_corrective_sk_restorable() -> bool:
    """Get the corrective_sk_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("corrective_sk_restorable", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.corrective_sk_restorable")
    return False


def set_corrective_sk_restorable(value: bool) -> None:
    """Set the corrective_sk_restorable property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("corrective_sk_restorable", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.corrective_sk_restorable", value)