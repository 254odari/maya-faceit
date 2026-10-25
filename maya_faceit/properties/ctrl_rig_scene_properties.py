# ctrl_rig_scene_properties.py
# Maya Faceit Plugin - Control Rig Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Control rig scene properties for Faceit Maya plugin.
Defines properties for control rig management.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Dict, Any, List
import json


# ============================================================
# Helper Functions
# ============================================================

def is_armature_object(obj: str) -> bool:
    """Check if an object is a valid armature."""
    if not cmds.objExists(obj):
        return False
    return cmds.nodeType(obj) == 'transform' and cmds.attributeQuery("bones", node=obj, exists=True)


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit control rig scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Add properties
    if not cmds.attributeQuery("draw_handler_name", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="draw_handler_name", dt="string")
    
    if not cmds.attributeQuery("show_landmarks_ctrl_rig", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="show_landmarks_ctrl_rig", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("control_armature", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="control_armature", dt="string")
    
    if not cmds.attributeQuery("crig_targets", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="crig_targets", dt="string")
    
    if not cmds.attributeQuery("crig_targets_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="crig_targets_index", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("new_slider", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="new_slider", dt="string")
    
    if not cmds.attributeQuery("crig_objects", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="crig_objects", dt="string")
    
    if not cmds.attributeQuery("crig_objects_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="crig_objects_index", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("crig_face_regions", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="crig_face_regions", dt="string")


def unregister() -> None:
    """
    Unregister Faceit control rig scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "draw_handler_name",
            "show_landmarks_ctrl_rig",
            "control_armature",
            "crig_targets",
            "crig_targets_index",
            "new_slider",
            "crig_objects",
            "crig_objects_index",
            "crig_face_regions"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Control Rig Targets Storage
# ============================================================

def get_crig_targets() -> Dict[str, Any]:
    """Get control rig targets as dictionary."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("crig_targets", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.crig_targets") or "{}"
            try:
                return json.loads(data_str)
            except:
                return {}
    return {}


def set_crig_targets(targets: Dict[str, Any]) -> None:
    """Set control rig targets from dictionary."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("crig_targets", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.crig_targets", json.dumps(targets), type="string")


def get_crig_objects() -> List[str]:
    """Get control rig objects as list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("crig_objects", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.crig_objects") or "[]"
            try:
                return json.loads(data_str)
            except:
                return []
    return []


def set_crig_objects(objects: List[str]) -> None:
    """Set control rig objects from list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("crig_objects", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.crig_objects", json.dumps(objects), type="string")