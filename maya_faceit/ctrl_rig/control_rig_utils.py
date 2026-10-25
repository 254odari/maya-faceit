# control_rig_utils.py
# Maya Faceit Plugin - Control Rig Utilities
# Converted from Blender to Maya Python 3.11

"""
Control rig utilities for Faceit Maya plugin.
Handles control rig data population and management.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from ..core.faceit_utils import (
    get_faceit_objects_list,
    get_faceit_control_armature,
    get_object,
)
from ..core.shape_key_utils import has_shape_keys, get_shape_key_names_from_objects
from ..core.retarget_list_utils import get_target_shapes_dict, set_base_regions_from_dict
from . import control_rig_data as ctrl_data
from . import custom_slider_utils


def populate_control_rig_target_objects_from_scene(c_rig: str) -> bool:
    """
    Populate the target objects property on the control rig object from the current faceit_objects.
    
    Args:
        c_rig: Control rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(c_rig):
        return False
    
    faceit_objects = get_faceit_objects_list()
    
    # Store objects in a custom attribute
    if not cmds.attributeQuery("faceit_crig_objects", node=c_rig, exists=True):
        cmds.addAttr(c_rig, ln="faceit_crig_objects", dt="string")
    
    cmds.setAttr(f"{c_rig}.faceit_crig_objects", ",".join(faceit_objects), type="string")
    
    return True


def get_crig_objects_list(c_rig: str) -> List[str]:
    """
    Get a list of all target objects found in the scene.
    
    Args:
        c_rig: Control rig object name
        
    Returns:
        List of object names
    """
    if not cmds.objExists(c_rig):
        return []
    
    if not cmds.attributeQuery("faceit_crig_objects", node=c_rig, exists=True):
        return []
    
    objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
    objects = objects_str.split(',') if objects_str else []
    
    # Filter to objects that exist
    return [obj for obj in objects if cmds.objExists(obj)]


def is_control_rig_connected(ctrl_rig: str) -> bool:
    """
    Check if the control rig is connected to target objects.
    
    Args:
        ctrl_rig: Control rig object name
        
    Returns:
        True if connected
    """
    if not cmds.objExists(ctrl_rig):
        return False
    
    target_objects = get_crig_objects_list(ctrl_rig)
    
    if not target_objects:
        return False
    
    # Search for drivers
    for obj in target_objects:
        if not cmds.objExists(obj):
            continue
        
        if has_shape_keys(obj):
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'blendShape':
                    # Check if there are connections from the control rig
                    connections = cmds.listConnections(node, source=True, destination=False) or []
                    if ctrl_rig in connections:
                        return True
    
    return False


def get_slider_bone_name_from_arkit_driver_dict(shape_name: str) -> Optional[str]:
    """
    Get the slider bone name from the ARKit driver dictionary.
    
    Args:
        shape_name: Shape name
        
    Returns:
        Bone name or None
    """
    driver_dict = ctrl_data.control_rig_drivers_dict.get(shape_name)
    
    if driver_dict:
        variables = driver_dict.get('variables', {})
        var = variables.get('var', {})
        return var.get('bone_name')
    
    return None


def populate_control_rig_target_shapes_from_scene(
    c_rig: str,
    update: bool = False,
    populate_amplify_values: bool = False
) -> bool:
    """
    Populate the crig_targets on the control rig object from the ARKit target shapes.
    
    Args:
        c_rig: Control rig object name
        update: Whether to try to find existing amplify values
        populate_amplify_values: Whether to populate amplify values
        
    Returns:
        True if successful
    """
    if not cmds.objExists(c_rig):
        return False
    
    # Store target shapes in a custom attribute
    if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
        cmds.addAttr(c_rig, ln="faceit_crig_targets", dt="string")
    
    # Get target shapes from scene
    # In Maya, we'd need to get this from scene data
    # For now, use a placeholder
    target_shapes_dict = {}
    
    # Store as JSON string
    import json
    cmds.setAttr(f"{c_rig}.faceit_crig_targets", json.dumps(target_shapes_dict), type="string")
    
    return True