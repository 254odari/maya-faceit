# mirror_utils.py
# Maya Faceit Plugin - Mirror Utilities
# Converted from Blender to Maya Python 3.11

"""
Mirror utilities for Faceit Maya plugin.
Handles mirroring of expressions, bones, and shapes.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple


# ============================================================
# Side Detection Utilities
# ============================================================

def get_side(name: str) -> str:
    """
    Get the side from a name.
    
    Args:
        name: Name string
        
    Returns:
        'L', 'R', or 'N'
    """
    # Check for left indicators
    left_indicators = ['_L', '_l', '.L', '.l', 'left', 'Left', 'LEFT']
    for indicator in left_indicators:
        if indicator in name:
            return 'L'
    
    # Check for right indicators
    right_indicators = ['_R', '_r', '.R', '.r', 'right', 'Right', 'RIGHT']
    for indicator in right_indicators:
        if indicator in name:
            return 'R'
    
    return 'N'


def get_mirror_name(name: str) -> str:
    """
    Get the mirror name.
    
    Args:
        name: Name string
        
    Returns:
        Mirrored name
    """
    side = get_side(name)
    
    if side == 'L':
        # Replace left with right
        replacements = [
            ('_L', '_R'), ('_l', '_r'),
            ('.L', '.R'), ('.l', '.r'),
            ('left', 'right'), ('Left', 'Right'), ('LEFT', 'RIGHT')
        ]
    elif side == 'R':
        # Replace right with left
        replacements = [
            ('_R', '_L'), ('_r', '_l'),
            ('.R', '.L'), ('.r', '.l'),
            ('right', 'left'), ('Right', 'Left'), ('RIGHT', 'LEFT')
        ]
    else:
        return name
    
    for old, new in replacements:
        if old in name:
            return name.replace(old, new)
    
    return name


def is_side_specific(name: str) -> bool:
    """
    Check if a name is side-specific.
    
    Args:
        name: Name string
        
    Returns:
        True if side-specific
    """
    return get_side(name) != 'N'


# ============================================================
# Mirror Bone Functions
# ============================================================

def mirror_bone_animation(
    bone_name: str,
    source_frame: int,
    target_frame: int,
    armature: str = None
) -> bool:
    """
    Mirror bone animation from one frame to another.
    
    Args:
        bone_name: Bone name
        source_frame: Source frame
        target_frame: Target frame
        armature: Armature object name
        
    Returns:
        True if successful
    """
    if armature is None:
        armature = cmds.ls(type='joint')[0] if cmds.ls(type='joint') else None
    
    if not armature or not cmds.objExists(bone_name):
        return False
    
    # Get source transforms
    cmds.currentTime(source_frame)
    translate = cmds.getAttr(f"{bone_name}.translate")[0]
    rotate = cmds.getAttr(f"{bone_name}.rotate")[0]
    scale = cmds.getAttr(f"{bone_name}.scale")[0]
    
    # Mirror transforms (X axis)
    translate_mirrored = [-translate[0], translate[1], translate[2]]
    rotate_mirrored = [-rotate[0], rotate[1], -rotate[2]]
    scale_mirrored = [scale[0], scale[1], scale[2]]
    
    # Set target transforms
    cmds.currentTime(target_frame)
    cmds.setAttr(f"{bone_name}.translateX", translate_mirrored[0])
    cmds.setAttr(f"{bone_name}.translateY", translate_mirrored[1])
    cmds.setAttr(f"{bone_name}.translateZ", translate_mirrored[2])
    cmds.setKeyframe(bone_name, attribute="translate", t=target_frame)
    
    cmds.setAttr(f"{bone_name}.rotateX", rotate_mirrored[0])
    cmds.setAttr(f"{bone_name}.rotateY", rotate_mirrored[1])
    cmds.setAttr(f"{bone_name}.rotateZ", rotate_mirrored[2])
    cmds.setKeyframe(bone_name, attribute="rotate", t=target_frame)
    
    cmds.setAttr(f"{bone_name}.scaleX", scale_mirrored[0])
    cmds.setAttr(f"{bone_name}.scaleY", scale_mirrored[1])
    cmds.setAttr(f"{bone_name}.scaleZ", scale_mirrored[2])
    cmds.setKeyframe(bone_name, attribute="scale", t=target_frame)
    
    return True


def mirror_all_bone_animation(
    source_frame: int,
    target_frame: int,
    armature: str = None
) -> int:
    """
    Mirror all bone animation from one frame to another.
    
    Args:
        source_frame: Source frame
        target_frame: Target frame
        armature: Armature object name
        
    Returns:
        Number of bones mirrored
    """
    if armature is None:
        armature = cmds.ls(type='joint')[0] if cmds.ls(type='joint') else None
    
    if not armature:
        return 0
    
    bones = cmds.ls(f"{armature}.bones", type='joint') or []
    mirrored = 0
    
    for bone in bones:
        if mirror_bone_animation(bone, source_frame, target_frame, armature):
            mirrored += 1
    
    return mirrored


# ============================================================
# Mirror Expression Functions
# ============================================================

def mirror_expression(
    expression_name: str,
    source_frame: int,
    target_frame: int,
    armature: str = None
) -> bool:
    """
    Mirror an expression from one frame to another.
    
    Args:
        expression_name: Expression name
        source_frame: Source frame
        target_frame: Target frame
        armature: Armature object name
        
    Returns:
        True if successful
    """
    # Get side
    side = get_side(expression_name)
    if side == 'N':
        return False
    
    # Get mirror name
    mirror_name = get_mirror_name(expression_name)
    if not mirror_name:
        return False
    
    # Mirror bone animation
    return mirror_all_bone_animation(source_frame, target_frame, armature) > 0


def mirror_all_expressions(
    source_frame: int,
    target_frame: int,
    armature: str = None
) -> int:
    """
    Mirror all expressions from one frame to another.
    
    Args:
        source_frame: Source frame
        target_frame: Target frame
        armature: Armature object name
        
    Returns:
        Number of expressions mirrored
    """
    # Get expression data
    if not cmds.objExists("faceit_core_data"):
        return 0
    
    names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
    frames_str = cmds.getAttr("faceit_core_data.expression_frames") or ""
    
    names = names_str.split(',') if names_str else []
    frames = [int(x) for x in frames_str.split(',')] if frames_str else []
    
    mirrored = 0
    
    for i, name in enumerate(names):
        if i < len(frames):
            if mirror_expression(name, frames[i], frames[i] + 1, armature):
                mirrored += 1
    
    return mirrored


# ============================================================
# Mirror Shape Key Functions
# ============================================================

def mirror_shape_key(
    mesh: str,
    source_sk: str,
    target_sk: str,
    axis: str = 'X'
) -> bool:
    """
    Mirror a shape key.
    
    Args:
        mesh: Mesh object name
        source_sk: Source shape key name
        target_sk: Target shape key name
        axis: Mirror axis ('X', 'Y', or 'Z')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    # Check if source shape key exists
    if not cmds.objExists(f"{mesh}.{source_sk}"):
        return False
    
    # Get source shape key value
    source_value = cmds.getAttr(f"{mesh}.{source_sk}")
    
    # Set source to 1.0
    cmds.setAttr(f"{mesh}.{source_sk}", 1.0)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_mirror")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Mirror duplicate
    _mirror_mesh(dup_mesh, axis)
    
    # Create mirrored blend shape
    blend_node = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_mirror_blendShape")[0]
    cmds.aliasAttr(target_sk, f"{blend_node}.weight[0]")
    cmds.setAttr(f"{blend_node}.{target_sk}", 0)
    
    # Restore source value
    cmds.setAttr(f"{mesh}.{source_sk}", source_value)
    
    # Clean up
    cmds.delete(dup_mesh)
    
    return True


def _mirror_mesh(mesh: str, axis: str = 'X'):
    """
    Mirror a mesh across an axis.
    
    Args:
        mesh: Mesh object name
        axis: Mirror axis ('X', 'Y', or 'Z')
    """
    if not cmds.objExists(mesh):
        return
    
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    
    for vtx in vertices:
        pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        if pos:
            pos[axis_index] = -pos[axis_index]
            cmds.xform(vtx, worldSpace=True, translation=pos)
    
    # Flip normals
    cmds.polyNormal(mesh, normalMode=0, userNormalMode=0, ch=1)


# ============================================================
# Mirror Blend Shape Functions
# ============================================================

def mirror_blend_shape_target(
    mesh: str,
    source_target: str,
    target_target: str,
    axis: str = 'X'
) -> bool:
    """
    Mirror a blend shape target.
    
    Args:
        mesh: Mesh object name
        source_target: Source target name
        target_target: Target target name
        axis: Mirror axis ('X', 'Y', or 'Z')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    # Find blend shape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    blend_node = None
    
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            if cmds.attributeQuery(source_target, node=node, exists=True):
                blend_node = node
                break
    
    if not blend_node:
        return False
    
    # Get source weight
    source_weight = cmds.getAttr(f"{blend_node}.{source_target}")
    
    # Set source to 1.0
    cmds.setAttr(f"{blend_node}.{source_target}", 1.0)
    
    # Duplicate mesh
    dup_mesh = cmds.duplicate(mesh, name=f"{mesh}_mirror")[0]
    cmds.delete(dup_mesh, constructionHistory=True)
    
    # Mirror duplicate
    _mirror_mesh(dup_mesh, axis)
    
    # Create mirrored blend shape
    new_blend = cmds.blendShape(mesh, dup_mesh, name=f"{mesh}_mirror_blendShape")[0]
    cmds.aliasAttr(target_target, f"{new_blend}.weight[0]")
    cmds.setAttr(f"{new_blend}.{target_target}", 0)
    
    # Restore source weight
    cmds.setAttr(f"{blend_node}.{source_target}", source_weight)
    
    # Clean up
    cmds.delete(dup_mesh)
    
    return True


# ============================================================
# Mirror Utility Functions
# ============================================================

def mirror_name_list(names: List[str]) -> List[str]:
    """
    Mirror a list of names.
    
    Args:
        names: List of names
        
    Returns:
        List of mirrored names
    """
    mirrored = []
    for name in names:
        mirrored_name = get_mirror_name(name)
        if mirrored_name != name:
            mirrored.append(mirrored_name)
    return mirrored


def get_mirror_pairs(names: List[str]) -> Dict[str, str]:
    """
    Get mirror pairs from a list of names.
    
    Args:
        names: List of names
        
    Returns:
        Dictionary mapping source to mirror
    """
    pairs = {}
    for name in names:
        mirror_name = get_mirror_name(name)
        if mirror_name != name and mirror_name in names:
            pairs[name] = mirror_name
    return pairs


def is_mirror_pair(name1: str, name2: str) -> bool:
    """
    Check if two names are mirror pairs.
    
    Args:
        name1: First name
        name2: Second name
        
    Returns:
        True if they are mirror pairs
    """
    return get_mirror_name(name1) == name2 or get_mirror_name(name2) == name1