# rig_utils.py
# Maya Faceit Plugin - Rig Utilities
# Converted from Blender to Maya Python 3.11

"""
Rig utilities for Faceit Maya plugin.
Handles rig creation, bone management, and rig operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple
import math


# ============================================================
# Rig Detection Functions
# ============================================================

def get_faceit_armature() -> Optional[str]:
    """
    Get the Faceit armature object.
    
    Returns:
        Armature object name or None
    """
    if cmds.objExists("faceit_core_data"):
        armature = cmds.getAttr("faceit_core_data.armature") or ""
        if armature and cmds.objExists(armature):
            return armature
    return None


def get_faceit_control_rig() -> Optional[str]:
    """
    Get the Faceit control rig object.
    
    Returns:
        Control rig object name or None
    """
    if cmds.objExists("faceit_core_data"):
        ctrl_rig = cmds.getAttr("faceit_core_data.control_rig") or ""
        if ctrl_rig and cmds.objExists(ctrl_rig):
            return ctrl_rig
    return None


def is_faceit_original_armature(armature: str) -> bool:
    """
    Check if the armature is the original Faceit armature.
    
    Args:
        armature: Armature object name
        
    Returns:
        True if it's the original Faceit armature
    """
    if not cmds.objExists(armature):
        return False
    
    # Check by name
    if armature == "FaceitRig":
        return True
    
    # Check for Faceit armature attribute
    if cmds.attributeQuery("faceit_armature", node=armature, exists=True):
        return True
    
    # Check for required bones
    from .faceit_data import FACEIT_BONES
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    # Check if all Faceit bones exist
    required_bones = [b for b in FACEIT_BONES if b in bones]
    return len(required_bones) > 10  # Arbitrary threshold


def get_rig_type(armature: str) -> str:
    """
    Get the type of rig.
    
    Args:
        armature: Armature object name
        
    Returns:
        'FACEIT', 'RIGIFY', 'RIGIFY_NEW', or 'ANY'
    """
    if not armature or not cmds.objExists(armature):
        return 'ANY'
    
    if is_faceit_original_armature(armature):
        return 'FACEIT'
    
    # Check for Rigify bones
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    if 'ORG-face' in bones:
        if any(b in bones for b in ['lip_end.L.001', 'eye_common']):
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


# ============================================================
# Bone Management Functions
# ============================================================

def get_faceit_bones(armature: str = None) -> List[str]:
    """
    Get all Faceit bones from the armature.
    
    Args:
        armature: Armature object name (uses get_faceit_armature if None)
        
    Returns:
        List of bone names
    """
    if armature is None:
        armature = get_faceit_armature()
    
    if not armature or not cmds.objExists(armature):
        return []
    
    from .faceit_data import FACEIT_BONES
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    # Filter to Faceit bones
    return [b for b in bones if b in FACEIT_BONES]


def get_control_bones(armature: str = None) -> List[str]:
    """
    Get all control bones from the armature.
    
    Args:
        armature: Armature object name (uses get_faceit_armature if None)
        
    Returns:
        List of control bone names
    """
    if armature is None:
        armature = get_faceit_armature()
    
    if not armature or not cmds.objExists(armature):
        return []
    
    from .faceit_data import FACEIT_CTRL_BONES
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    return [b for b in bones if b in FACEIT_CTRL_BONES]


def get_deform_bones(armature: str = None) -> List[str]:
    """
    Get all deform bones from the armature.
    
    Args:
        armature: Armature object name (uses get_faceit_armature if None)
        
    Returns:
        List of deform bone names
    """
    if armature is None:
        armature = get_faceit_armature()
    
    if not armature or not cmds.objExists(armature):
        return []
    
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    # Find bones with DEF- prefix or deform attribute
    deform_bones = []
    for bone in bones:
        if bone.startswith('DEF-'):
            deform_bones.append(bone)
        elif cmds.attributeQuery("deform", node=bone, exists=True):
            if cmds.getAttr(f"{bone}.deform"):
                deform_bones.append(bone)
    
    return deform_bones


def get_bone_children(bone_name: str) -> List[str]:
    """
    Get all children of a bone.
    
    Args:
        bone_name: Bone name
        
    Returns:
        List of child bone names
    """
    if not cmds.objExists(bone_name):
        return []
    
    children = cmds.listRelatives(bone_name, children=True, type='joint') or []
    return children


def get_bone_parent(bone_name: str) -> Optional[str]:
    """
    Get the parent of a bone.
    
    Args:
        bone_name: Bone name
        
    Returns:
        Parent bone name or None
    """
    if not cmds.objExists(bone_name):
        return None
    
    parent = cmds.listRelatives(bone_name, parent=True, type='joint')
    return parent[0] if parent else None


# ============================================================
# Bone Transform Functions
# ============================================================

def get_bone_translation(bone_name: str, world_space: bool = True) -> Tuple[float, float, float]:
    """
    Get the translation of a bone.
    
    Args:
        bone_name: Bone name
        world_space: If True, get world space translation
        
    Returns:
        Tuple of (x, y, z)
    """
    if not cmds.objExists(bone_name):
        return (0.0, 0.0, 0.0)
    
    if world_space:
        pos = cmds.xform(bone_name, query=True, worldSpace=True, translation=True) or [0, 0, 0]
    else:
        pos = cmds.getAttr(f"{bone_name}.translate")[0]
    
    return (pos[0], pos[1], pos[2])


def get_bone_rotation(bone_name: str, world_space: bool = True) -> Tuple[float, float, float]:
    """
    Get the rotation of a bone.
    
    Args:
        bone_name: Bone name
        world_space: If True, get world space rotation
        
    Returns:
        Tuple of (x, y, z) in degrees
    """
    if not cmds.objExists(bone_name):
        return (0.0, 0.0, 0.0)
    
    if world_space:
        rot = cmds.xform(bone_name, query=True, worldSpace=True, rotation=True) or [0, 0, 0]
    else:
        rot = cmds.getAttr(f"{bone_name}.rotate")[0]
    
    return (rot[0], rot[1], rot[2])


def get_bone_scale(bone_name: str, world_space: bool = True) -> Tuple[float, float, float]:
    """
    Get the scale of a bone.
    
    Args:
        bone_name: Bone name
        world_space: If True, get world space scale
        
    Returns:
        Tuple of (x, y, z)
    """
    if not cmds.objExists(bone_name):
        return (1.0, 1.0, 1.0)
    
    if world_space:
        scale = cmds.xform(bone_name, query=True, worldSpace=True, scale=True) or [1, 1, 1]
    else:
        scale = cmds.getAttr(f"{bone_name}.scale")[0]
    
    return (scale[0], scale[1], scale[2])


def set_bone_translation(bone_name: str, x: float, y: float, z: float, world_space: bool = True):
    """
    Set the translation of a bone.
    
    Args:
        bone_name: Bone name
        x, y, z: Translation values
        world_space: If True, set world space translation
    """
    if not cmds.objExists(bone_name):
        return
    
    if world_space:
        cmds.xform(bone_name, worldSpace=True, translation=[x, y, z])
    else:
        cmds.setAttr(f"{bone_name}.translateX", x)
        cmds.setAttr(f"{bone_name}.translateY", y)
        cmds.setAttr(f"{bone_name}.translateZ", z)


def set_bone_rotation(bone_name: str, x: float, y: float, z: float, world_space: bool = True):
    """
    Set the rotation of a bone.
    
    Args:
        bone_name: Bone name
        x, y, z: Rotation values in degrees
        world_space: If True, set world space rotation
    """
    if not cmds.objExists(bone_name):
        return
    
    if world_space:
        cmds.xform(bone_name, worldSpace=True, rotation=[x, y, z])
    else:
        cmds.setAttr(f"{bone_name}.rotateX", x)
        cmds.setAttr(f"{bone_name}.rotateY", y)
        cmds.setAttr(f"{bone_name}.rotateZ", z)


# ============================================================
# Rig Building Functions
# ============================================================

def create_faceit_rig(mesh_name: str) -> Optional[str]:
    """
    Create a Faceit rig for a mesh.
    
    Args:
        mesh_name: Mesh object name
        
    Returns:
        Created armature name or None
    """
    # This would be a complex operation - placeholder
    # In a real implementation, this would build the full Faceit rig
    pass


def create_control_rig(armature: str) -> Optional[str]:
    """
    Create a control rig for an armature.
    
    Args:
        armature: Armature object name
        
    Returns:
        Created control rig name or None
    """
    # Placeholder for control rig creation
    pass


def auto_rig_mesh(
    mesh: str,
    landmark_data: Dict[str, Tuple[float, float, float]]
) -> Optional[str]:
    """
    Auto-rig a mesh using landmark data.
    
    Args:
        mesh: Mesh object name
        landmark_data: Dictionary of landmark positions
        
    Returns:
        Created armature name or None
    """
    # Placeholder for auto-rigging
    pass


# ============================================================
# Rig Testing and Validation
# ============================================================

def validate_rig(armature: str) -> List[str]:
    """
    Validate a Faceit rig.
    
    Args:
        armature: Armature object name
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not cmds.objExists(armature):
        errors.append(f"Armature '{armature}' does not exist")
        return errors
    
    # Check for required bones
    required_bones = ['jaw_master', 'eyes', 'nose']
    for bone in required_bones:
        if not cmds.objExists(f"{armature}.bones.{bone}"):
            errors.append(f"Required bone '{bone}' not found")
    
    # Check for deform bones
    deform_bones = get_deform_bones(armature)
    if len(deform_bones) < 10:
        errors.append("Too few deform bones found")
    
    return errors


def get_rig_dimensions(armature: str) -> Tuple[float, float, float]:
    """
    Get the dimensions of a rig.
    
    Args:
        armature: Armature object name
        
    Returns:
        Tuple of (width, height, depth)
    """
    if not cmds.objExists(armature):
        return (1.0, 1.0, 1.0)
    
    control_bones = get_control_bones(armature)
    if not control_bones:
        return (1.0, 1.0, 1.0)
    
    x_vals, y_vals, z_vals = [], [], []
    
    for bone in control_bones:
        pos = get_bone_translation(bone, world_space=True)
        x_vals.append(pos[0])
        y_vals.append(pos[1])
        z_vals.append(pos[2])
    
    if not x_vals:
        return (1.0, 1.0, 1.0)
    
    width = max(x_vals) - min(x_vals)
    height = max(y_vals) - min(y_vals)
    depth = max(z_vals) - min(z_vals)
    
    return (width, height, depth)


# ============================================================
# Bone Mirroring Functions
# ============================================================

def mirror_bone_name(bone_name: str) -> str:
    """
    Mirror a bone name (L <-> R).
    
    Args:
        bone_name: Original bone name
        
    Returns:
        Mirrored bone name
    """
    if '.L' in bone_name:
        return bone_name.replace('.L', '.R')
    elif '.R' in bone_name:
        return bone_name.replace('.R', '.L')
    elif '_L' in bone_name:
        return bone_name.replace('_L', '_R')
    elif '_R' in bone_name:
        return bone_name.replace('_R', '_L')
    elif 'left' in bone_name.lower():
        return bone_name.replace('left', 'right')
    elif 'right' in bone_name.lower():
        return bone_name.replace('right', 'left')
    return bone_name


def mirror_bone_transform(armature: str, bone_name: str) -> bool:
    """
    Mirror a bone's transform across the X axis.
    
    Args:
        armature: Armature object name
        bone_name: Bone name to mirror
        
    Returns:
        True if successful
    """
    if not cmds.objExists(armature) or not cmds.objExists(bone_name):
        return False
    
    # Get current position
    pos = get_bone_translation(bone_name, world_space=True)
    rot = get_bone_rotation(bone_name, world_space=True)
    
    # Mirror position (X axis)
    pos_mirrored = (-pos[0], pos[1], pos[2])
    
    # Mirror rotation
    rot_mirrored = (-rot[0], rot[1], -rot[2])
    
    # Set mirrored transform
    set_bone_translation(bone_name, pos_mirrored[0], pos_mirrored[1], pos_mirrored[2], world_space=True)
    set_bone_rotation(bone_name, rot_mirrored[0], rot_mirrored[1], rot_mirrored[2], world_space=True)
    
    return True