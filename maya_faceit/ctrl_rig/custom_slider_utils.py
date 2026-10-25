# custom_slider_utils.py
# Maya Faceit Plugin - Custom Slider Utilities
# Converted from Blender to Maya Python 3.11

"""
Custom slider utilities for Faceit Maya plugin.
Handles creation and management of custom sliders in the control rig.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Tuple, Any

from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils


def get_custom_slider_from_shape(c_rig: str, shape_name: str) -> Optional[str]:
    """
    Get the control slider by comparing the bone name to shape name.
    
    Args:
        c_rig: Control rig object name
        shape_name: Target shape name
        
    Returns:
        Bone name or None
    """
    if not cmds.objExists(c_rig):
        return None
    
    # Check if it's an ARKit shape
    arkit_ref_data = fdata.get_arkit_shape_data()
    
    if shape_name in arkit_ref_data:
        return None
    
    # Check for custom slider bone
    bone_name = f'c_{shape_name}_slider'
    if cmds.objExists(bone_name):
        return bone_name
    
    return None


def get_custom_sliders_in_crig(c_rig: str) -> List[str]:
    """
    Get all custom sliders in the control rig.
    
    Args:
        c_rig: Control rig object name
        
    Returns:
        List of custom slider names
    """
    shape_key_names = []
    
    if not cmds.objExists(c_rig):
        return shape_key_names
    
    # Get all bones with 'slider' in name
    bones = cmds.ls(type='joint') or []
    
    for bone in bones:
        if 'slider' in bone and '_' in bone and not bone.startswith('c_'):
            # Extract shape name from bone name
            parts = bone.split('_')
            if len(parts) >= 3:
                shape_name = '_'.join(parts[1:-1])
                if shape_name:
                    shape_key_names.append(shape_name)
    
    return shape_key_names


def get_custom_sliders_in_crig_targets_enum() -> List[Tuple[str, str, str]]:
    """
    Get custom sliders in control rig as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    shapes = []
    
    c_rig = futils.get_faceit_control_armature()
    
    if c_rig:
        for i, name in enumerate(get_custom_sliders_in_crig(c_rig)):
            shapes.append((name, name, name, i))
    else:
        shapes.append(("None", "None", "None"))
    
    return shapes


def get_custom_sliders_from_faceit_objects_enum() -> List[Tuple[str, str, str]]:
    """
    Get custom sliders from Faceit objects as enum items.
    
    Returns:
        List of (value, label, description) tuples
    """
    shapes = []
    
    if not cmds.objExists("faceit_core_data"):
        shapes.append(("None", "None", "None"))
        return shapes
    
    faceit_objects = futils.get_faceit_objects_list()
    
    if faceit_objects:
        crig = futils.get_faceit_control_armature()
        
        # Get existing crig target shapes
        crig_target_shapes = []
        if crig and cmds.attributeQuery("faceit_crig_targets", node=crig, exists=True):
            targets_str = cmds.getAttr(f"{crig}.faceit_crig_targets") or "{}"
            try:
                import json
                crig_target_shapes = list(json.loads(targets_str).keys())
            except:
                pass
        
        shape_key_names = [
            n for n in shape_key_utils.get_shape_key_names_from_objects(faceit_objects)
            if n not in crig_target_shapes
        ]
        
        for i, name in enumerate(shape_key_names):
            shapes.append((name, name, name, i))
    else:
        shapes.append(("None", "None", "None"))
    
    return shapes


def generate_extra_sliders(
    context: Any,
    shape_name: str,
    slider_range: str,
    rig_obj: str,
    max_rows: int = 10,
    overwrite: bool = False
) -> Optional[str]:
    """
    Create standard shape key sliders in the control rig armature.
    
    Args:
        context: Maya context
        shape_name: Name of new slider
        slider_range: Range type ('full_range' or 'pos_range')
        rig_obj: Control rig object name
        max_rows: Maximum rows per column
        overwrite: Whether to overwrite existing sliders
        
    Returns:
        Name of the new slider bone or None
    """
    if not cmds.objExists(rig_obj):
        return None
    
    # Check if slider already exists
    bone_name = f'c_{shape_name}_slider'
    
    if cmds.objExists(bone_name) and not overwrite:
        return bone_name
    
    # Get reference bones
    if slider_range == 'full_range':
        ref_parent = 'c_slider_ref_parent'
        ref_bone = 'c_slider_ref'
        ref_txt = 'c_slider_ref_txt'
    else:
        ref_parent = 'c_slider_small_ref_parent'
        ref_bone = 'c_slider_small_ref'
        ref_txt = 'c_slider_small_ref_txt'
    
    if not cmds.objExists(ref_parent):
        return None
    
    # Get reference position
    parent_pos = cmds.xform(ref_parent, query=True, worldSpace=True, translation=True)
    
    if not parent_pos:
        return None
    
    # Create new bones
    pos = list(parent_pos)
    
    # Get existing sliders
    existing_sliders = get_all_slider_bones(rig_obj, only_controllers=True)
    total_slider_count = len(existing_sliders)
    
    # Calculate position
    ref_length = cmds.getAttr(f"{ref_parent}.scaleX") or 1.0
    
    if total_slider_count > 0:
        slider_pos_x = (total_slider_count // max_rows) * ref_length * 2
        slider_pos_z = (total_slider_count % max_rows) * ref_length / 2
        pos[0] += slider_pos_x
        pos[2] += slider_pos_z
    
    # Create slider bones
    # In Maya, we would create joints
    new_parent = cmds.joint(
        name=f'c_{shape_name}_slider_parent',
        position=pos
    )
    
    new_pos = [pos[0], pos[1], pos[2] + ref_length]
    new_bone = cmds.joint(
        name=f'c_{shape_name}_slider',
        position=new_pos
    )
    
    # Parent the bone
    cmds.parent(new_bone, new_parent)
    
    # Create text bone (for display)
    txt_pos = [pos[0] - ref_length, pos[1], pos[2] + ref_length]
    txt_bone = cmds.joint(
        name=f'c_{shape_name}_slider_txt',
        position=txt_pos
    )
    cmds.parent(txt_bone, new_parent)
    
    # Hide select for parent and text bones
    cmds.setAttr(f"{new_parent}.overrideEnabled", 1)
    cmds.setAttr(f"{new_parent}.overrideDisplayType", 2)  # Reference
    
    cmds.setAttr(f"{txt_bone}.overrideEnabled", 1)
    cmds.setAttr(f"{txt_bone}.overrideDisplayType", 2)  # Reference
    
    # Add custom attribute to mark as slider
    cmds.addAttr(new_bone, ln="faceit_slider", attributeType="long", min=0, max=1, defaultValue=1)
    
    return f'c_{shape_name}_slider'


def get_all_slider_bones(rig: str, filter_str: str = '', only_controllers: bool = False) -> List[str]:
    """
    Get all slider bones in a rig.
    
    Args:
        rig: Rig object name
        filter_str: Filter string
        only_controllers: Whether to return only controller bones
        
    Returns:
        List of bone names
    """
    if not cmds.objExists(rig):
        return []
    
    slider_bones = []
    bones = cmds.ls(f"{rig}.bones", type='joint') or []
    
    for bone in bones:
        if filter_str and filter_str not in bone:
            continue
        
        if '_ref' in bone:
            continue
        
        if only_controllers:
            if cmds.attributeQuery("faceit_slider", node=bone, exists=True):
                if cmds.getAttr(f"{bone}.faceit_slider"):
                    slider_bones.append(bone)
            continue
        
        if 'slider' in bone:
            slider_bones.append(bone)
    
    return slider_bones


def cleanup_unused_bone_shapes(name: str) -> None:
    """
    Clean up unused bone shapes.
    
    Args:
        name: Shape name
    """
    # In Maya, bone shapes are handled differently
    # This is a placeholder for cleanup
    pass


def generate_custom_curve_text(name: str) -> Optional[str]:
    """
    Generate custom curve text for a bone.
    
    Args:
        name: Shape name
        
    Returns:
        Curve object name or None
    """
    # In Maya, we'd create a text curve
    # This is a placeholder
    return None


def generate_custom_curve_box(
    bs_name: str,
    h: float,
    w: float,
    pos: List[float] = None
) -> Optional[str]:
    """
    Generate a custom curve box for a bone.
    
    Args:
        bs_name: Shape name
        h: Height
        w: Width
        pos: Position
        
    Returns:
        Curve object name or None
    """
    # In Maya, we'd create a curve
    # This is a placeholder
    return None