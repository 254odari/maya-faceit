# rig_scene_properties.py
# Maya Faceit Plugin - Rig Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Rig scene properties for Faceit Maya plugin.
Defines properties for rig management.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional

from ..core import faceit_utils as futils
from ..core import faceit_data as fdata


# ============================================================
# Helper Functions
# ============================================================

def faceit_armature_poll(obj: str) -> bool:
    """Check if an object is a valid Faceit rig."""
    if not cmds.objExists(obj):
        return False
    return cmds.nodeType(obj) == 'transform' and cmds.attributeQuery("bones", node=obj, exists=True)


def body_armature_poll(obj: str) -> bool:
    """Check if an object is a valid body rig."""
    if not cmds.objExists(obj):
        return False
    if cmds.nodeType(obj) != 'transform':
        return False
    if cmds.attributeQuery("bones", node=obj, exists=True):
        return not futils.is_faceit_original_armature(obj)
    return False


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit rig scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Armature
    if not cmds.attributeQuery("armature", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="armature", dt="string")
    
    if not cmds.attributeQuery("armature_missing", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="armature_missing", attributeType="bool", defaultValue=False)
    
    # Body armature
    if not cmds.attributeQuery("body_armature", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="body_armature", dt="string")
    
    if not cmds.attributeQuery("body_armature_head_bone", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="body_armature_head_bone", dt="string")
    
    # Eye pivots
    if not cmds.attributeQuery("use_eye_pivots", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="use_eye_pivots", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("anime_ref_eyebone_l", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="anime_ref_eyebone_l", dt="string")
    
    if not cmds.attributeQuery("anime_ref_eyebone_r", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="anime_ref_eyebone_r", dt="string")
    
    # Rigify
    if not cmds.attributeQuery("use_rigify_armature", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="use_rigify_armature", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("is_rigify_armature", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="is_rigify_armature", attributeType="bool", defaultValue=False)


def unregister() -> None:
    """
    Unregister Faceit rig scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "armature",
            "armature_missing",
            "body_armature",
            "body_armature_head_bone",
            "use_eye_pivots",
            "anime_ref_eyebone_l",
            "anime_ref_eyebone_r",
            "use_rigify_armature",
            "is_rigify_armature"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)