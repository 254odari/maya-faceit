# landmarks_scene_properties.py
# Maya Faceit Plugin - Landmarks Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Landmarks scene properties for Faceit Maya plugin.
Defines properties for landmarks management.
"""

import maya.cmds as cmds # type: ignore


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit landmarks scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    if not cmds.attributeQuery("asymmetric", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="asymmetric", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("show_locator_empties", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="show_locator_empties", attributeType="bool", defaultValue=False)


def unregister() -> None:
    """
    Unregister Faceit landmarks scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = ["asymmetric", "show_locator_empties"]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Property Accessors
# ============================================================

def get_asymmetric() -> bool:
    """Get the asymmetric property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("asymmetric", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.asymmetric")
    return False


def set_asymmetric(value: bool) -> None:
    """Set the asymmetric property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("asymmetric", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.asymmetric", value)


def get_show_locator_empties() -> bool:
    """Get the show_locator_empties property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("show_locator_empties", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.show_locator_empties")
    return False


def set_show_locator_empties(value: bool) -> None:
    """Set the show_locator_empties property."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("show_locator_empties", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.show_locator_empties", value)