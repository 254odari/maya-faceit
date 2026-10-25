# scale_utils.py
# Maya Faceit Plugin - Scale Utilities
# Converted from Blender to Maya Python 3.11

"""
Scale utilities for Faceit Maya plugin.
Handles scaling of animations, poses, and rigs.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple
import numpy as np


# ============================================================
# Action Scaling Functions
# ============================================================

def scale_action(
    action: str,
    scale_factors: Tuple[float, float, float],
    filter_bones: List[str] = None,
    frames: List[int] = None
) -> bool:
    """
    Scale an action.
    
    Args:
        action: Action name
        scale_factors: (x, y, z) scale factors
        filter_bones: List of bone names to scale (None for all)
        frames: List of frames to scale (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(action):
        return False
    
    # Get animation curves
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        # Get data path
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Check if it's a transform curve
        if not any(x in data_path for x in ['translate', 'rotate', 'scale']):
            continue
        
        # Check bone filter
        if filter_bones:
            bone_name = data_path.split('.')[0] if '.' in data_path else ""
            if bone_name not in filter_bones:
                continue
        
        # Get axis
        if data_path.endswith('X'):
            idx = 0
        elif data_path.endswith('Y'):
            idx = 1
        elif data_path.endswith('Z'):
            idx = 2
        else:
            continue
        
        scale = scale_factors[idx]
        
        # Scale keyframes
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, (t, v) in enumerate(zip(keyframes, values)):
            if frames is not None and t not in frames:
                continue
            
            if 'scale' in data_path:
                # Scale from 1.0
                new_value = ((v - 1.0) * scale) + 1.0
            else:
                # Scale from 0.0
                new_value = v * scale
            
            cmds.keyframe(curve, edit=True, absolute=True, valueChange=new_value, index=i, time=(t,))
    
    return True


def scale_action_to_rig(
    action: str,
    armature: str,
    filter_bones: List[str] = None
) -> bool:
    """
    Scale an action to match a rig.
    
    Args:
        action: Action name
        armature: Armature object name
        filter_bones: List of bone names to scale
        
    Returns:
        True if successful
    """
    if not cmds.objExists(action) or not cmds.objExists(armature):
        return False
    
    # Get rig dimensions
    rig_dims = get_rig_dimensions(armature)
    
    # Get action dimensions
    action_dims = get_action_dimensions(action)
    
    # Calculate scale factors
    scale_factors = []
    for i in range(3):
        if action_dims[i] != 0:
            scale_factors.append(rig_dims[i] / action_dims[i])
        else:
            scale_factors.append(1.0)
    
    # Scale action
    return scale_action(action, tuple(scale_factors), filter_bones)


# ============================================================
# Rig Dimension Functions
# ============================================================

def get_rig_dimensions(armature: str) -> Tuple[float, float, float]:
    """
    Get the dimensions of a rig.
    
    Args:
        armature: Armature object name
        
    Returns:
        (width, height, depth)
    """
    if not cmds.objExists(armature):
        return (1.0, 1.0, 1.0)
    
    # Get all joints
    joints = cmds.ls(f"{armature}.bones", type='joint') or []
    
    if not joints:
        return (1.0, 1.0, 1.0)
    
    x_vals, y_vals, z_vals = [], [], []
    
    for joint in joints:
        pos = cmds.xform(joint, query=True, worldSpace=True, translation=True)
        if pos:
            x_vals.append(pos[0])
            y_vals.append(pos[1])
            z_vals.append(pos[2])
    
    if not x_vals:
        return (1.0, 1.0, 1.0)
    
    width = max(x_vals) - min(x_vals)
    height = max(y_vals) - min(y_vals)
    depth = max(z_vals) - min(z_vals)
    
    return (width, height, depth)


def get_action_dimensions(action: str) -> Tuple[float, float, float]:
    """
    Get the dimensions of an action.
    
    Args:
        action: Action name
        
    Returns:
        (width, height, depth)
    """
    if not cmds.objExists(action):
        return (1.0, 1.0, 1.0)
    
    # Get animation curves
    curves = cmds.listAnimCurves(action) or []
    
    x_vals, y_vals, z_vals = [], [], []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        if 'translate' not in data_path:
            continue
        
        # Get values
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        if data_path.endswith('X'):
            x_vals.extend(values)
        elif data_path.endswith('Y'):
            y_vals.extend(values)
        elif data_path.endswith('Z'):
            z_vals.extend(values)
    
    if not x_vals:
        return (1.0, 1.0, 1.0)
    
    width = max(x_vals) - min(x_vals) if x_vals else 1.0
    height = max(y_vals) - min(y_vals) if y_vals else 1.0
    depth = max(z_vals) - min(z_vals) if z_vals else 1.0
    
    return (width, height, depth)


# ============================================================
# Pose Scaling Functions
# ============================================================

def scale_pose(
    armature: str,
    frame: int,
    scale_factors: Tuple[float, float, float],
    filter_bones: List[str] = None
) -> bool:
    """
    Scale a pose at a specific frame.
    
    Args:
        armature: Armature object name
        frame: Frame number
        scale_factors: (x, y, z) scale factors
        filter_bones: List of bone names to scale
        
    Returns:
        True if successful
    """
    if not cmds.objExists(armature):
        return False
    
    # Go to frame
    cmds.currentTime(frame)
    
    # Get bones
    if filter_bones:
        bones = [b for b in filter_bones if cmds.objExists(b)]
    else:
        bones = cmds.ls(f"{armature}.bones", type='joint') or []
    
    for bone in bones:
        # Get current translate
        translate = cmds.getAttr(f"{bone}.translate")[0]
        
        # Scale translate
        new_translate = [
            translate[0] * scale_factors[0],
            translate[1] * scale_factors[1],
            translate[2] * scale_factors[2]
        ]
        
        cmds.setAttr(f"{bone}.translateX", new_translate[0])
        cmds.setAttr(f"{bone}.translateY", new_translate[1])
        cmds.setAttr(f"{bone}.translateZ", new_translate[2])
        
        # Set keyframe
        cmds.setKeyframe(bone, attribute="translate", t=frame)
    
    return True


def scale_all_poses(
    armature: str,
    scale_factors: Tuple[float, float, float],
    filter_bones: List[str] = None,
    frames: List[int] = None
) -> int:
    """
    Scale all poses in an action.
    
    Args:
        armature: Armature object name
        scale_factors: (x, y, z) scale factors
        filter_bones: List of bone names to scale
        frames: List of frames to scale
        
    Returns:
        Number of poses scaled
    """
    if not cmds.objExists(armature):
        return 0
    
    if frames is None:
        # Get all frames with keyframes
        curves = cmds.listAnimCurves(armature) or []
        frames = []
        for curve in curves:
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            frames.extend([int(t) for t in keyframes if int(t) not in frames])
        frames = sorted(frames)
    
    scaled = 0
    for frame in frames:
        if scale_pose(armature, frame, scale_factors, filter_bones):
            scaled += 1
    
    return scaled


# ============================================================
# Eye Scaling Functions
# ============================================================

def scale_eye_animation(
    armature: str,
    scale_factor: float,
    action: str = None
) -> bool:
    """
    Scale eye animation.
    
    Args:
        armature: Armature object name
        scale_factor: Scale factor
        action: Action name (None for current action)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(armature):
        return False
    
    # Get lid bones
    lid_bones = []
    for side in ['L', 'R']:
        for bone in [f'lid.T.{side}.001', f'lid.T.{side}.002', f'lid.T.{side}.003',
                     f'lid.B.{side}.001', f'lid.B.{side}.002', f'lid.B.{side}.003']:
            if cmds.objExists(bone):
                lid_bones.append(bone)
    
    if not lid_bones:
        return False
    
    # Scale animation
    if action:
        return scale_action(action, (scale_factor, scale_factor, scale_factor), lid_bones)
    else:
        # Scale current animation on armature
        curves = cmds.listAnimCurves(armature) or []
        for curve in curves:
            data_path = cmds.getAttr(f"{curve}.attributeName") or ""
            bone_name = data_path.split('.')[0] if '.' in data_path else ""
            
            if bone_name not in lid_bones:
                continue
            
            if 'translate' in data_path:
                keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                values = cmds.keyframe(curve, query=True, valueChange=True) or []
                
                for i, (t, v) in enumerate(zip(keyframes, values)):
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=v * scale_factor, index=i, time=(t,))
        
        return True


def scale_eye_look_animation(
    armature: str,
    scale_factor: float = 0.25,
    action: str = None
) -> bool:
    """
    Scale eye look animation for anime eyes.
    
    Args:
        armature: Armature object name
        scale_factor: Scale factor
        action: Action name (None for current action)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(armature):
        return False
    
    # Get eye bones
    eye_bones = ['eye.R', 'eye.L', 'eyes', 'eye_common']
    eye_bones = [b for b in eye_bones if cmds.objExists(b)]
    
    if not eye_bones:
        return False
    
    # Scale animation
    if action:
        return scale_action(action, (scale_factor, scale_factor, scale_factor), eye_bones)
    else:
        # Scale current animation on armature
        curves = cmds.listAnimCurves(armature) or []
        for curve in curves:
            data_path = cmds.getAttr(f"{curve}.attributeName") or ""
            bone_name = data_path.split('.')[0] if '.' in data_path else ""
            
            if bone_name not in eye_bones:
                continue
            
            if 'translate' in data_path:
                keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                values = cmds.keyframe(curve, query=True, valueChange=True) or []
                
                for i, (t, v) in enumerate(zip(keyframes, values)):
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=v * scale_factor, index=i, time=(t,))
        
        return True


# ============================================================
# Amplify Functions
# ============================================================

def amplify_pose(
    action: str,
    frame: int,
    scale_factor: float = 1.0,
    filter_bones: List[str] = None
) -> bool:
    """
    Amplify a pose.
    
    Args:
        action: Action name
        frame: Frame number
        scale_factor: Amplify factor
        filter_bones: List of bone names to amplify
        
    Returns:
        True if successful
    """
    if not cmds.objExists(action):
        return False
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Check if it's a transform curve
        if not any(x in data_path for x in ['translate', 'rotate', 'scale']):
            continue
        
        # Check bone filter
        if filter_bones:
            bone_name = data_path.split('.')[0] if '.' in data_path else ""
            if bone_name not in filter_bones:
                continue
        
        # Find keyframe at frame
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, (t, v) in enumerate(zip(keyframes, values)):
            if t != frame:
                continue
            
            if 'scale' in data_path:
                # Amplify from 1.0
                new_value = ((v - 1.0) * scale_factor) + 1.0
            else:
                # Amplify from 0.0
                new_value = v * scale_factor
            
            cmds.keyframe(curve, edit=True, absolute=True, valueChange=new_value, index=i, time=(t,))
    
    return True


def amplify_all_poses(
    action: str,
    scale_factor: float = 1.0,
    filter_bones: List[str] = None,
    frames: List[int] = None
) -> int:
    """
    Amplify all poses in an action.
    
    Args:
        action: Action name
        scale_factor: Amplify factor
        filter_bones: List of bone names to amplify
        frames: List of frames to amplify
        
    Returns:
        Number of poses amplified
    """
    if not cmds.objExists(action):
        return 0
    
    if frames is None:
        # Get all frames with keyframes
        curves = cmds.listAnimCurves(action) or []
        frames = []
        for curve in curves:
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            frames.extend([int(t) for t in keyframes if int(t) not in frames])
        frames = sorted(frames)
    
    amplified = 0
    for frame in frames:
        if amplify_pose(action, frame, scale_factor, filter_bones):
            amplified += 1
    
    return amplified