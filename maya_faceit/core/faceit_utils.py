# faceit_utils.py
# Maya Faceit Plugin - Core Utilities
# Converted from Blender to Maya Python 3.11

"""
Core utilities for Faceit Maya plugin.
Provides common utility functions for object management, scene state, and rig operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MVector
import numpy as np
from typing import List, Dict, Optional, Tuple, Any, Set, Union
import json

from .faceit_data import FACEIT_BONES, FACEIT_CTRL_BONES


# ============================================================
# Object Management Utilities
# ============================================================

def get_object(name: str) -> Optional[str]:
    """
    Get an object by name.
    
    Args:
        name: Object name
        
    Returns:
        Object name or None if not found
    """
    if isinstance(name, str):
        if cmds.objExists(name):
            return name
    return None


def clear_active_object() -> None:
    """Clear the active object selection."""
    cmds.select(clear=True)
    cmds.selectMode(object=True)


def set_active_object(obj: Union[str, None], select: bool = True) -> bool:
    """
    Set the active object.
    
    Args:
        obj: Object name or None
        select: Whether to select the object
        
    Returns:
        True if successful
    """
    if obj is None:
        clear_active_object()
        return True
    
    if isinstance(obj, str):
        if not cmds.objExists(obj):
            return False
    
    if select:
        cmds.select(obj, replace=True)
    
    cmds.selectMode(object=True)
    return True


def clear_object_selection() -> None:
    """Clear all object selection."""
    cmds.select(clear=True)


def get_selected_objects() -> List[str]:
    """
    Get all selected objects.
    
    Returns:
        List of selected object names
    """
    return cmds.ls(selection=True, type='transform') or []


# ============================================================
# Faceit Object Management
# ============================================================

def get_faceit_objects_list(clear_invalid_objects: bool = True) -> List[str]:
    """
    Get the registered Faceit objects.
    
    Args:
        clear_invalid_objects: Whether to remove invalid objects from the list
        
    Returns:
        List of Faceit object names
    """
    if not cmds.objExists("faceit_core_data"):
        return []
    
    if not cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
        return []
    
    objects_str = cmds.getAttr("faceit_core_data.faceit_objects") or ""
    objects = objects_str.split(',') if objects_str else []
    
    if clear_invalid_objects:
        valid_objects = [obj for obj in objects if cmds.objExists(obj)]
        if len(valid_objects) != len(objects):
            cmds.setAttr("faceit_core_data.faceit_objects", ",".join(valid_objects), type="string")
        return valid_objects
    
    return objects


def get_main_faceit_object() -> Optional[str]:
    """
    Get the main Faceit object (head or face).
    
    Returns:
        Main Faceit object name or None
    """
    faceit_objects = get_faceit_objects_list()
    
    for obj in faceit_objects:
        # Check if object has faceit_main vertex group
        if cmds.objExists(obj):
            # Check for vertex group
            if cmds.attributeQuery("faceit_main", node=obj, exists=True):
                return obj
    
    # Return first object if no main found
    return faceit_objects[0] if faceit_objects else None


def get_faceit_objects() -> List[str]:
    """
    Get all Faceit objects (alias for get_faceit_objects_list).
    
    Returns:
        List of Faceit object names
    """
    return get_faceit_objects_list()


def add_faceit_object(obj: str) -> bool:
    """
    Add an object to the Faceit objects list.
    
    Args:
        obj: Object name
        
    Returns:
        True if added successfully
    """
    if not cmds.objExists(obj):
        return False
    
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
        cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
    
    objects = get_faceit_objects_list(clear_invalid_objects=False)
    
    if obj in objects:
        return False
    
    objects.append(obj)
    cmds.setAttr("faceit_core_data.faceit_objects", ",".join(objects), type="string")
    
    return True


def remove_faceit_object(obj: str) -> bool:
    """
    Remove an object from the Faceit objects list.
    
    Args:
        obj: Object name
        
    Returns:
        True if removed successfully
    """
    objects = get_faceit_objects_list(clear_invalid_objects=False)
    
    if obj not in objects:
        return False
    
    objects.remove(obj)
    cmds.setAttr("faceit_core_data.faceit_objects", ",".join(objects), type="string")
    
    return True


# ============================================================
# Armature/Rig Management
# ============================================================

def get_faceit_armature(force_original: bool = False) -> Optional[str]:
    """
    Get the Faceit armature object.
    
    Args:
        force_original: Whether to force using the original Faceit rig
        
    Returns:
        Armature object name or None
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("armature", node="faceit_core_data", exists=True):
            armature = cmds.getAttr("faceit_core_data.armature") or ""
            if armature and cmds.objExists(armature):
                if force_original:
                    if is_faceit_original_armature(armature):
                        return armature
                    else:
                        # Try to find original armature
                        for obj in cmds.ls(type='transform'):
                            if is_faceit_original_armature(obj):
                                return obj
                        return None
                return armature
    
    # Try to find by name
    if cmds.objExists("FaceitRig"):
        return "FaceitRig"
    
    # Try to find any armature with Faceit bones
    for obj in cmds.ls(type='transform'):
        if is_faceit_original_armature(obj):
            return obj
    
    return None


def get_faceit_control_armature() -> Optional[str]:
    """
    Get the Faceit control rig object.
    
    Returns:
        Control rig object name or None
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("control_rig", node="faceit_core_data", exists=True):
            control_rig = cmds.getAttr("faceit_core_data.control_rig") or ""
            if control_rig and cmds.objExists(control_rig):
                return control_rig
    
    # Try to find by name
    for obj in cmds.ls(type='transform'):
        if "FaceitControlRig" in obj:
            return obj
        if cmds.attributeQuery("ctrl_rig_id", node=obj, exists=True):
            return obj
    
    return None


def get_faceit_control_armatures() -> List[str]:
    """
    Get all Faceit control rigs in the scene.
    
    Returns:
        List of control rig object names
    """
    result = []
    
    for obj in cmds.ls(type='transform'):
        if "FaceitControlRig" in obj:
            result.append(obj)
        elif cmds.attributeQuery("ctrl_rig_id", node=obj, exists=True):
            result.append(obj)
    
    return result


def is_faceit_original_armature(rig: str) -> bool:
    """
    Check if the armature is the original Faceit armature.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if it's the original Faceit armature
    """
    if not cmds.objExists(rig):
        return False
    
    # Check by name
    if rig == "FaceitRig":
        return True
    
    # Check for Faceit armature attribute
    if cmds.attributeQuery("faceit_armature", node=rig, exists=True):
        return True
    
    # Check for required bones
    if cmds.nodeType(rig) != 'transform':
        return False
    
    # Get joints under this rig
    joints = cmds.ls(f"{rig}.bones", type='joint') or []
    if not joints:
        return False
    
    # Check if many Faceit bones exist
    faceit_bones_found = [b for b in FACEIT_BONES if b in joints]
    return len(faceit_bones_found) > 10  # Arbitrary threshold


def get_rig_type(rig: str = None) -> str:
    """
    Get the type of rig.
    
    Args:
        rig: Rig object name (uses get_faceit_armature if None)
        
    Returns:
        'FACEIT', 'RIGIFY', 'RIGIFY_NEW', or 'ANY'
    """
    if rig is None:
        rig = get_faceit_armature()
    
    if rig is None:
        return 'ANY'
    
    if not cmds.objExists(rig):
        return 'ANY'
    
    if is_faceit_original_armature(rig):
        return 'FACEIT'
    
    # Check for Rigify bones
    joints = cmds.ls(f"{rig}.bones", type='joint') or []
    
    if 'ORG-face' in joints:
        if any(b in joints for b in ['lip_end.L.001', 'eye_common']):
            return 'RIGIFY_NEW'
        else:
            return 'RIGIFY'
    
    return 'ANY'


def using_rigify_armature() -> bool:
    """
    Check if the user wants to use a Rigify face rig.
    
    Returns:
        True if using Rigify
    """
    armature = get_faceit_armature()
    if armature:
        rig_type = get_rig_type(armature)
        return rig_type in ('RIGIFY', 'RIGIFY_NEW')
    return False


def is_armature_bound_to_registered_objects(rig: str) -> bool:
    """
    Check whether the rig is bound to the registered objects.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if rig is bound to any registered object
    """
    if not cmds.objExists(rig):
        return False
    
    objects = get_faceit_objects_list()
    
    for obj in objects:
        if not cmds.objExists(obj):
            continue
        
        # Check for skin cluster using this rig
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'skinCluster':
                influences = cmds.skinCluster(node, query=True, influence=True) or []
                if rig in influences:
                    return True
    
    return False


# ============================================================
# Collection/Layer Management
# ============================================================

def get_faceit_collection(force_access: bool = True, create: bool = True) -> Optional[str]:
    """
    Get or create the Faceit collection.
    
    Args:
        force_access: Whether to force access (unhide)
        create: Whether to create if it doesn't exist
        
    Returns:
        Collection name or None
    """
    collection_name = "Faceit_Collection"
    
    # Check if collection exists
    if not cmds.objExists(collection_name):
        if not create:
            return None
        # Create collection
        cmds.createNode("transform", name=collection_name)
    
    if force_access:
        # Make visible
        cmds.setAttr(f"{collection_name}.visibility", 1)
    
    return collection_name


def get_layer_collection(collection_name: str) -> Optional[str]:
    """
    Get a layer collection.
    
    Args:
        collection_name: Collection name
        
    Returns:
        Collection name or None
    """
    if cmds.objExists(collection_name):
        return collection_name
    return None


# ============================================================
# Object Visibility Utilities
# ============================================================

def set_hide_obj(obj: str, hide: bool) -> bool:
    """
    Hide or unhide an object.
    
    Args:
        obj: Object name
        hide: True to hide, False to show
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    cmds.setAttr(f"{obj}.visibility", not hide)
    return True


def get_hide_obj(obj: str) -> bool:
    """
    Check if an object is hidden.
    
    Args:
        obj: Object name
        
    Returns:
        True if hidden
    """
    if not cmds.objExists(obj):
        return True
    
    return not cmds.getAttr(f"{obj}.visibility")


def set_hidden_state_object(
    object_to_hide: str,
    hide_viewport: bool,
    hide_render: bool
) -> bool:
    """
    Set the hidden state of an object.
    
    Args:
        object_to_hide: Object name
        hide_viewport: Whether to hide in viewport
        hide_render: Whether to hide in render
        
    Returns:
        True if successful
    """
    if not cmds.objExists(object_to_hide):
        return False
    
    cmds.setAttr(f"{object_to_hide}.visibility", not hide_viewport)
    
    # For render visibility
    if cmds.attributeQuery("renderVisibility", node=object_to_hide, exists=True):
        cmds.setAttr(f"{object_to_hide}.renderVisibility", not hide_render)
    
    return True


def set_hidden_states(
    objects_hidden_states: Dict[str, Tuple[bool, bool]] = None,
    overwrite: bool = False,
    objects: List[str] = None,
    hide_value: bool = False
) -> None:
    """
    Set hidden states for multiple objects.
    
    Args:
        objects_hidden_states: Dictionary mapping object names to (viewport_hidden, render_hidden)
        overwrite: Whether to overwrite all objects with hide_value
        objects: List of objects to hide/unhide
        hide_value: Value to set if overwrite is True
    """
    if overwrite and objects:
        for obj in objects:
            if cmds.objExists(obj):
                set_hidden_state_object(obj, hide_value, hide_value)
    
    if objects_hidden_states:
        for obj_name, states in objects_hidden_states.items():
            obj = get_object(obj_name)
            if obj:
                hide_viewport, hide_render = states
                set_hidden_state_object(obj, hide_viewport, hide_render)


def get_hidden_states(objects_to_hide: List[str]) -> Dict[str, Tuple[bool, bool]]:
    """
    Get hidden states of objects.
    
    Args:
        objects_to_hide: List of object names
        
    Returns:
        Dictionary mapping object names to (viewport_hidden, render_hidden)
    """
    states = {}
    
    for obj in objects_to_hide:
        if not cmds.objExists(obj):
            continue
        
        viewport_hidden = not cmds.getAttr(f"{obj}.visibility")
        render_hidden = False
        
        if cmds.attributeQuery("renderVisibility", node=obj, exists=True):
            render_hidden = not cmds.getAttr(f"{obj}.renderVisibility")
        
        states[obj] = (viewport_hidden, render_hidden)
    
    return states


def is_collection_visible(collection_name: str) -> bool:
    """
    Check if a collection is visible.
    
    Args:
        collection_name: Collection name
        
    Returns:
        True if visible
    """
    if not cmds.objExists(collection_name):
        return False
    
    return cmds.getAttr(f"{collection_name}.visibility")


# ============================================================
# Scene State Management
# ============================================================

def save_scene_state() -> Dict:
    """
    Save the current scene state.
    
    Returns:
        Dictionary containing scene state
    """
    # Get selected objects
    selected_objects = cmds.ls(selection=True, type='transform') or []
    
    # Get active object
    active_obj = cmds.ls(selection=True)[0] if cmds.ls(selection=True) else None
    
    # Get hidden states
    all_objects = cmds.ls(type='transform')
    hidden_states = get_hidden_states(all_objects)
    
    # Get current time
    current_time = cmds.currentTime(query=True)
    
    state_dict = {
        'hidden_states': hidden_states,
        'selected_objects': selected_objects,
        'active_obj': active_obj,
        'current_time': current_time,
    }
    
    return state_dict


def restore_scene_state(state_dict: Dict) -> None:
    """
    Restore a saved scene state.
    
    Args:
        state_dict: Dictionary containing scene state
    """
    # Restore hidden states
    hidden_states = state_dict.get('hidden_states', {})
    for obj, states in hidden_states.items():
        if cmds.objExists(obj):
            set_hidden_state_object(obj, states[0], states[1])
    
    # Restore selection
    cmds.select(clear=True)
    selected_objects = state_dict.get('selected_objects', [])
    for obj in selected_objects:
        if cmds.objExists(obj):
            cmds.select(obj, add=True)
    
    # Restore active object
    active_obj = state_dict.get('active_obj')
    if active_obj and cmds.objExists(active_obj):
        cmds.select(active_obj, replace=True)
    
    # Restore time
    current_time = state_dict.get('current_time')
    if current_time is not None:
        cmds.currentTime(current_time)


# ============================================================
# Context/State Utilities
# ============================================================

CONTEXT_TO_OBJECT_MODE = {
    'mesh': 'EDIT',
    'curve': 'EDIT',
    'surface': 'EDIT',
    'text': 'EDIT',
    'armature': 'EDIT',
    'metaball': 'EDIT',
    'lattice': 'EDIT',
    'pose': 'POSE',
    'sculpt': 'SCULPT',
    'weight_paint': 'WEIGHT_PAINT',
    'vertex_paint': 'VERTEX_PAINT',
    'texture_paint': 'TEXTURE_PAINT',
    'particle': 'PARTICLE_EDIT',
    'object': 'OBJECT',
}


def get_object_mode_from_context_mode(context_mode: str) -> str:
    """
    Convert context mode to object mode.
    
    Args:
        context_mode: Context mode string
        
    Returns:
        Object mode string
    """
    return CONTEXT_TO_OBJECT_MODE.get(context_mode, 'OBJECT')


def get_object_mode() -> str:
    """
    Get the current object mode.
    
    Returns:
        Current mode string
    """
    return cmds.selectMode(query=True)


def set_object_mode(mode: str) -> bool:
    """
    Set the object mode.
    
    Args:
        mode: Mode to set
        
    Returns:
        True if successful
    """
    try:
        cmds.selectMode(mode.lower())
        return True
    except:
        return False


def exit_nla_tweak_mode() -> None:
    """
    Exit NLA tweak mode.
    """
    # Maya doesn't have NLA tweak mode like Blender
    # This is a placeholder for compatibility
    pass


# ============================================================
# Math Utilities
# ============================================================

def get_median_pos(locations: List[List[float]]) -> Tuple[float, float, float]:
    """
    Calculate the median position of multiple points.
    
    Args:
        locations: List of (x, y, z) positions
        
    Returns:
        Median position (x, y, z)
    """
    if not locations:
        return (0, 0, 0)
    
    arr = np.array(locations)
    median = np.median(arr, axis=0)
    return (median[0], median[1], median[2])


def get_center_pos(locations: List[List[float]]) -> Tuple[float, float, float]:
    """
    Calculate the center position of multiple points.
    
    Args:
        locations: List of (x, y, z) positions
        
    Returns:
        Center position (x, y, z)
    """
    if not locations:
        return (0, 0, 0)
    
    arr = np.array(locations)
    center = np.mean(arr, axis=0)
    return (center[0], center[1], center[2])


# ============================================================
# Action/Animation Utilities
# ============================================================

def get_action_frame_range(action: str) -> Tuple[float, float]:
    """
    Get the frame range of an action.
    
    Args:
        action: Action name
        
    Returns:
        Tuple of (start_frame, end_frame)
    """
    if not cmds.objExists(action):
        return (1, 250)
    
    # Get animation curve range
    curves = cmds.listAnimCurves(action) or []
    if not curves:
        return (1, 250)
    
    start_frames = []
    end_frames = []
    
    for curve in curves:
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        if keyframes:
            start_frames.append(min(keyframes))
            end_frames.append(max(keyframes))
    
    if start_frames and end_frames:
        return (min(start_frames), max(end_frames))
    
    return (1, 250)


def set_action_frame_range(action: str, start: float, end: float) -> bool:
    """
    Set the frame range of an action.
    
    Args:
        action: Action name
        start: Start frame
        end: End frame
        
    Returns:
        True if successful
    """
    if not cmds.objExists(action):
        return False
    
    # Set start and end frames
    cmds.setAttr(f"{action}.startFrame", start)
    cmds.setAttr(f"{action}.endFrame", end)
    
    return True


# ============================================================
# UI Refresh Utilities
# ============================================================

def ui_refresh_properties() -> None:
    """Refresh the properties panel."""
    # Force UI refresh
    cmds.refresh()


def ui_refresh_view_3d() -> None:
    """Refresh the 3D view."""
    cmds.refresh()


def ui_refresh_all() -> None:
    """Refresh all UI elements."""
    cmds.refresh()


# ============================================================
# Collection Property Utilities
# ============================================================

def remove_item_from_collection_prop(collection_attr: str, item_name: str) -> bool:
    """
    Remove an item from a collection property.
    
    Args:
        collection_attr: Collection attribute name
        item_name: Item name to remove
        
    Returns:
        True if removed successfully
    """
    if not cmds.objExists("faceit_core_data"):
        return False
    
    if not cmds.attributeQuery(collection_attr, node="faceit_core_data", exists=True):
        return False
    
    items_str = cmds.getAttr(f"faceit_core_data.{collection_attr}") or ""
    items = items_str.split(',') if items_str else []
    
    if item_name not in items:
        return False
    
    items.remove(item_name)
    cmds.setAttr(f"faceit_core_data.{collection_attr}", ",".join(items), type="string")
    
    return True


def find_collection_in_children(collection_name: str, target_name: str) -> Optional[str]:
    """
    Find a collection in children.
    
    Args:
        collection_name: Parent collection name
        target_name: Target collection name
        
    Returns:
        Found collection name or None
    """
    if collection_name == target_name:
        return collection_name
    
    # In Maya, collections are transforms with children
    children = cmds.listRelatives(collection_name, children=True, type='transform') or []
    for child in children:
        found = find_collection_in_children(child, target_name)
        if found:
            return found
    
    return None


# ============================================================
# Duplicate Utilities
# ============================================================

def duplicate_obj(obj: str, link: bool = False) -> Optional[str]:
    """
    Duplicate an object.
    
    Args:
        obj: Object name
        link: Whether to create a linked duplicate (instance)
        
    Returns:
        Duplicated object name or None
    """
    if not cmds.objExists(obj):
        return None
    
    if link:
        # Create instance
        new_obj = cmds.instance(obj)[0]
    else:
        # Create copy
        new_obj = cmds.duplicate(obj)[0]
    
    return new_obj


# ============================================================
# Maya Version Utilities
# ============================================================

def get_maya_version() -> Tuple[int, int, int]:
    """
    Get the Maya version.
    
    Returns:
        Tuple of (major, minor, patch)
    """
    version = cmds.about(version=True)
    parts = version.split('.')
    
    if len(parts) >= 3:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    elif len(parts) >= 2:
        return (int(parts[0]), int(parts[1]), 0)
    else:
        return (int(parts[0]), 0, 0)


def is_maya_version_at_least(major: int, minor: int = 0) -> bool:
    """
    Check if Maya version is at least the specified version.
    
    Args:
        major: Major version
        minor: Minor version
        
    Returns:
        True if Maya version is at least the specified version
    """
    version = get_maya_version()
    if version[0] > major:
        return True
    if version[0] == major and version[1] >= minor:
        return True
    return False