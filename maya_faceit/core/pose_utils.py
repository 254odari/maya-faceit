# pose_utils.py
# Maya Faceit Plugin - Pose Utilities
# Converted from Blender to Maya Python 3.11

"""
Pose utilities for Faceit Maya plugin.
Handles pose bone operations, resetting, and pose management.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MMatrix, MVector, MEulerRotation, MQuaternion
from typing import List, Dict, Optional, Tuple, Any
import math


# ============================================================
# Pose Reset Functions
# ============================================================

def reset_pose(rig: str) -> bool:
    """
    Reset a rig to its rest pose.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    # Get all joints in the rig
    joints = cmds.ls(f"{rig}.bones", type='joint') or []
    
    for joint in joints:
        reset_pb(joint)
    
    return True


def reset_pb(
    bone: str,
    reset_location: bool = True,
    reset_rotation: bool = True,
    reset_scale: bool = True
) -> bool:
    """
    Reset a pose bone to its bind/rest transforms.
    
    Args:
        bone: Bone name
        reset_location: Whether to reset location
        reset_rotation: Whether to reset rotation
        reset_scale: Whether to reset scale
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    # Get bone's rest position
    # For joints, we need to get the bind pose or rest pose
    
    # Reset location
    if reset_location:
        # Get rest position from the joint's parent space
        if cmds.objExists(f"{bone}.bindPose"):
            # Use bind pose if available
            bind_pos = cmds.getAttr(f"{bone}.bindPose")[0]
            cmds.setAttr(f"{bone}.translateX", bind_pos[0])
            cmds.setAttr(f"{bone}.translateY", bind_pos[1])
            cmds.setAttr(f"{bone}.translateZ", bind_pos[2])
        else:
            # Reset to zero
            cmds.setAttr(f"{bone}.translateX", 0)
            cmds.setAttr(f"{bone}.translateY", 0)
            cmds.setAttr(f"{bone}.translateZ", 0)
    
    # Reset rotation
    if reset_rotation:
        cmds.setAttr(f"{bone}.rotateX", 0)
        cmds.setAttr(f"{bone}.rotateY", 0)
        cmds.setAttr(f"{bone}.rotateZ", 0)
    
    # Reset scale
    if reset_scale:
        cmds.setAttr(f"{bone}.scaleX", 1)
        cmds.setAttr(f"{bone}.scaleY", 1)
        cmds.setAttr(f"{bone}.scaleZ", 1)
    
    return True


def is_pb_in_rest_pose(bone: str) -> bool:
    """
    Check if a pose bone is in its rest pose.
    
    Args:
        bone: Bone name
        
    Returns:
        True if in rest pose
    """
    if not cmds.objExists(bone):
        return False
    
    # Check location
    translate = cmds.getAttr(f"{bone}.translate")[0]
    if any(abs(t) > 0.001 for t in translate):
        return False
    
    # Check rotation
    rotate = cmds.getAttr(f"{bone}.rotate")[0]
    if any(abs(r) > 0.001 for r in rotate):
        return False
    
    # Check scale
    scale = cmds.getAttr(f"{bone}.scale")[0]
    if any(abs(s - 1.0) > 0.001 for s in scale):
        return False
    
    return True


# ============================================================
# Bone Transform Utilities
# ============================================================

def get_bone_matrix(bone: str, world_space: bool = True) -> List[List[float]]:
    """
    Get the transformation matrix of a bone.
    
    Args:
        bone: Bone name
        world_space: Whether to get world space matrix
        
    Returns:
        4x4 transformation matrix as list of lists
    """
    if not cmds.objExists(bone):
        return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    
    if world_space:
        matrix = cmds.xform(bone, query=True, worldSpace=True, matrix=True)
    else:
        matrix = cmds.getAttr(f"{bone}.matrix")
    
    if not matrix:
        return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    
    # Convert flat list to 4x4 matrix
    return [
        [matrix[0], matrix[1], matrix[2], matrix[3]],
        [matrix[4], matrix[5], matrix[6], matrix[7]],
        [matrix[8], matrix[9], matrix[10], matrix[11]],
        [matrix[12], matrix[13], matrix[14], matrix[15]]
    ]


def set_bone_matrix(bone: str, matrix: List[List[float]], world_space: bool = True) -> bool:
    """
    Set the transformation matrix of a bone.
    
    Args:
        bone: Bone name
        matrix: 4x4 transformation matrix
        world_space: Whether to set world space matrix
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    # Convert to flat list
    flat_matrix = [
        matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3],
        matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3],
        matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3],
        matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3]
    ]
    
    if world_space:
        cmds.xform(bone, worldSpace=True, matrix=flat_matrix)
    else:
        cmds.setAttr(f"{bone}.matrix", flat_matrix)
    
    return True


def get_bone_edit_roll(bone: str) -> float:
    """
    Get the edit bone roll angle.
    
    Args:
        bone: Bone name
        
    Returns:
        Roll angle in degrees
    """
    if not cmds.objExists(bone):
        return 0.0
    
    # In Maya, joint orientation represents the roll
    # Get the joint orientation
    if cmds.attributeQuery("jointOrientation", node=bone, exists=True):
        orientation = cmds.getAttr(f"{bone}.jointOrientation")[0]
        # The roll is typically around the Y axis
        return orientation[1] * 180.0 / math.pi
    
    return 0.0


def set_bone_edit_roll(bone: str, angle: float) -> bool:
    """
    Set the edit bone roll angle.
    
    Args:
        bone: Bone name
        angle: Roll angle in degrees
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    # Set joint orientation
    if cmds.attributeQuery("jointOrientation", node=bone, exists=True):
        orientation = cmds.getAttr(f"{bone}.jointOrientation")[0]
        orientation[1] = angle * math.pi / 180.0
        cmds.setAttr(f"{bone}.jointOrientation", orientation)
        return True
    
    return False


# ============================================================
# Pose Copy/Paste Utilities
# ============================================================

def copy_pose(rig: str, bones: List[str] = None) -> Dict[str, Dict]:
    """
    Copy the pose of bones.
    
    Args:
        rig: Rig object name
        bones: List of bone names (None for all)
        
    Returns:
        Dictionary of bone pose data
    """
    if not cmds.objExists(rig):
        return {}
    
    if bones is None:
        bones = cmds.ls(f"{rig}.bones", type='joint') or []
    
    pose_data = {}
    
    for bone in bones:
        if not cmds.objExists(bone):
            continue
        
        pose_data[bone] = {
            'translate': cmds.getAttr(f"{bone}.translate")[0],
            'rotate': cmds.getAttr(f"{bone}.rotate")[0],
            'scale': cmds.getAttr(f"{bone}.scale")[0],
        }
    
    return pose_data


def paste_pose(rig: str, pose_data: Dict[str, Dict]) -> bool:
    """
    Paste a pose to bones.
    
    Args:
        rig: Rig object name
        pose_data: Pose data dictionary from copy_pose
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    for bone, data in pose_data.items():
        if not cmds.objExists(bone):
            continue
        
        if 'translate' in data:
            cmds.setAttr(f"{bone}.translateX", data['translate'][0])
            cmds.setAttr(f"{bone}.translateY", data['translate'][1])
            cmds.setAttr(f"{bone}.translateZ", data['translate'][2])
        
        if 'rotate' in data:
            cmds.setAttr(f"{bone}.rotateX", data['rotate'][0])
            cmds.setAttr(f"{bone}.rotateY", data['rotate'][1])
            cmds.setAttr(f"{bone}.rotateZ", data['rotate'][2])
        
        if 'scale' in data:
            cmds.setAttr(f"{bone}.scaleX", data['scale'][0])
            cmds.setAttr(f"{bone}.scaleY", data['scale'][1])
            cmds.setAttr(f"{bone}.scaleZ", data['scale'][2])
    
    return True


def mirror_pose(
    rig: str,
    source_bones: List[str],
    target_bones: List[str],
    mirror_axis: str = 'X'
) -> bool:
    """
    Mirror a pose from source bones to target bones.
    
    Args:
        rig: Rig object name
        source_bones: List of source bone names
        target_bones: List of target bone names
        mirror_axis: Mirror axis ('X', 'Y', or 'Z')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    if len(source_bones) != len(target_bones):
        return False
    
    # Get axis index
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}[mirror_axis]
    
    for src, tgt in zip(source_bones, target_bones):
        if not cmds.objExists(src) or not cmds.objExists(tgt):
            continue
        
        # Get source transforms
        translate = cmds.getAttr(f"{src}.translate")[0]
        rotate = cmds.getAttr(f"{src}.rotate")[0]
        scale = cmds.getAttr(f"{src}.scale")[0]
        
        # Mirror transforms
        translate_mirrored = list(translate)
        translate_mirrored[axis_index] = -translate_mirrored[axis_index]
        
        rotate_mirrored = list(rotate)
        rotate_mirrored[axis_index] = -rotate_mirrored[axis_index]
        
        scale_mirrored = list(scale)
        
        # Set target transforms
        cmds.setAttr(f"{tgt}.translateX", translate_mirrored[0])
        cmds.setAttr(f"{tgt}.translateY", translate_mirrored[1])
        cmds.setAttr(f"{tgt}.translateZ", translate_mirrored[2])
        
        cmds.setAttr(f"{tgt}.rotateX", rotate_mirrored[0])
        cmds.setAttr(f"{tgt}.rotateY", rotate_mirrored[1])
        cmds.setAttr(f"{tgt}.rotateZ", rotate_mirrored[2])
        
        cmds.setAttr(f"{tgt}.scaleX", scale_mirrored[0])
        cmds.setAttr(f"{tgt}.scaleY", scale_mirrored[1])
        cmds.setAttr(f"{tgt}.scaleZ", scale_mirrored[2])
    
    return True


# ============================================================
# Pose Keyframe Utilities
# ============================================================

def keyframe_pose(rig: str, frame: int, bones: List[str] = None) -> bool:
    """
    Keyframe the current pose of bones.
    
    Args:
        rig: Rig object name
        frame: Frame number
        bones: List of bone names (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    if bones is None:
        bones = cmds.ls(f"{rig}.bones", type='joint') or []
    
    for bone in bones:
        if not cmds.objExists(bone):
            continue
        
        cmds.setKeyframe(bone, attribute="translate", t=frame)
        cmds.setKeyframe(bone, attribute="rotate", t=frame)
        cmds.setKeyframe(bone, attribute="scale", t=frame)
    
    return True


def clear_keyframes(rig: str, frame: int, bones: List[str] = None) -> bool:
    """
    Clear keyframes on bones at a specific frame.
    
    Args:
        rig: Rig object name
        frame: Frame number
        bones: List of bone names (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    if bones is None:
        bones = cmds.ls(f"{rig}.bones", type='joint') or []
    
    for bone in bones:
        if not cmds.objExists(bone):
            continue
        
        # Remove keyframes at this frame
        cmds.cutKey(bone, time=(frame, frame), attribute="translate")
        cmds.cutKey(bone, time=(frame, frame), attribute="rotate")
        cmds.cutKey(bone, time=(frame, frame), attribute="scale")
    
    return True


# ============================================================
# Bone Selection Utilities
# ============================================================

def select_pose_bones(bone_names: List[str]) -> bool:
    """
    Select pose bones.
    
    Args:
        bone_names: List of bone names
        
    Returns:
        True if successful
    """
    for bone in bone_names:
        if cmds.objExists(bone):
            cmds.select(bone, add=True)
    
    return True


def get_selected_pose_bones() -> List[str]:
    """
    Get selected pose bones.
    
    Returns:
        List of selected bone names
    """
    selection = cmds.ls(selection=True, type='joint') or []
    return selection


def get_pose_bones_in_rig(rig: str) -> List[str]:
    """
    Get all pose bones in a rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        List of bone names
    """
    if not cmds.objExists(rig):
        return []
    
    return cmds.ls(f"{rig}.bones", type='joint') or []


# ============================================================
# Pose Blending Utilities
# ============================================================

def blend_poses(
    rig: str,
    pose1: Dict[str, Dict],
    pose2: Dict[str, Dict],
    blend_factor: float
) -> Dict[str, Dict]:
    """
    Blend two poses.
    
    Args:
        rig: Rig object name
        pose1: First pose data
        pose2: Second pose data
        blend_factor: Blend factor (0 = pose1, 1 = pose2)
        
    Returns:
        Blended pose data
    """
    result = {}
    
    for bone, data1 in pose1.items():
        if bone not in pose2:
            result[bone] = data1
            continue
        
        data2 = pose2[bone]
        blended = {}
        
        if 'translate' in data1 and 'translate' in data2:
            blended['translate'] = [
                data1['translate'][0] + (data2['translate'][0] - data1['translate'][0]) * blend_factor,
                data1['translate'][1] + (data2['translate'][1] - data1['translate'][1]) * blend_factor,
                data1['translate'][2] + (data2['translate'][2] - data1['translate'][2]) * blend_factor,
            ]
        
        if 'rotate' in data1 and 'rotate' in data2:
            blended['rotate'] = [
                data1['rotate'][0] + (data2['rotate'][0] - data1['rotate'][0]) * blend_factor,
                data1['rotate'][1] + (data2['rotate'][1] - data1['rotate'][1]) * blend_factor,
                data1['rotate'][2] + (data2['rotate'][2] - data1['rotate'][2]) * blend_factor,
            ]
        
        if 'scale' in data1 and 'scale' in data2:
            blended['scale'] = [
                data1['scale'][0] + (data2['scale'][0] - data1['scale'][0]) * blend_factor,
                data1['scale'][1] + (data2['scale'][1] - data1['scale'][1]) * blend_factor,
                data1['scale'][2] + (data2['scale'][2] - data1['scale'][2]) * blend_factor,
            ]
        
        result[bone] = blended
    
    return result


def apply_pose_to_bones(rig: str, pose_data: Dict[str, Dict]) -> bool:
    """
    Apply pose data to bones.
    
    Args:
        rig: Rig object name
        pose_data: Pose data dictionary
        
    Returns:
        True if successful
    """
    return paste_pose(rig, pose_data)


# ============================================================
# Bone Constraint Utilities
# ============================================================

def get_bone_constraints(bone: str) -> List[str]:
    """
    Get all constraints on a bone.
    
    Args:
        bone: Bone name
        
    Returns:
        List of constraint names
    """
    if not cmds.objExists(bone):
        return []
    
    constraints = cmds.listConnections(f"{bone}.constraints") or []
    return constraints


def remove_bone_constraints(bone: str, constraint_types: List[str] = None) -> bool:
    """
    Remove constraints from a bone.
    
    Args:
        bone: Bone name
        constraint_types: List of constraint types to remove (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    constraints = get_bone_constraints(bone)
    
    for constraint in constraints:
        if constraint_types:
            constraint_type = cmds.nodeType(constraint)
            if constraint_type not in constraint_types:
                continue
        
        cmds.delete(constraint)
    
    return True


# ============================================================
# Maya-Specific Pose Utilities
# ============================================================

def set_joint_orientation(bone: str, orientation: List[float]) -> bool:
    """
    Set the joint orientation.
    
    Args:
        bone: Bone name
        orientation: Euler angles in radians
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    if cmds.attributeQuery("jointOrientation", node=bone, exists=True):
        cmds.setAttr(f"{bone}.jointOrientation", orientation)
        return True
    
    return False


def get_joint_orientation(bone: str) -> List[float]:
    """
    Get the joint orientation.
    
    Args:
        bone: Bone name
        
    Returns:
        Euler angles in radians
    """
    if not cmds.objExists(bone):
        return [0, 0, 0]
    
    if cmds.attributeQuery("jointOrientation", node=bone, exists=True):
        return cmds.getAttr(f"{bone}.jointOrientation")[0]
    
    return [0, 0, 0]


def set_joint_rotation_order(bone: str, order: str) -> bool:
    """
    Set the joint rotation order.
    
    Args:
        bone: Bone name
        order: Rotation order ('xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    # Map string to Maya order value
    order_map = {
        'xyz': 0,
        'yzx': 1,
        'zxy': 2,
        'xzy': 3,
        'yxz': 4,
        'zyx': 5,
    }
    
    if order in order_map:
        cmds.setAttr(f"{bone}.rotateOrder", order_map[order])
        return True
    
    return False


def get_joint_rotation_order(bone: str) -> str:
    """
    Get the joint rotation order.
    
    Args:
        bone: Bone name
        
    Returns:
        Rotation order string
    """
    if not cmds.objExists(bone):
        return 'xyz'
    
    order_map = {
        0: 'xyz',
        1: 'yzx',
        2: 'zxy',
        3: 'xzy',
        4: 'yxz',
        5: 'zyx',
    }
    
    if cmds.attributeQuery("rotateOrder", node=bone, exists=True):
        order = cmds.getAttr(f"{bone}.rotateOrder")
        return order_map.get(order, 'xyz')
    
    return 'xyz'