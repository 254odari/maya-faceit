# fc_dr_utils.py
# Maya Faceit Plugin - Fcurve and Driver Utilities
# Converted from Blender to Maya Python 3.11

"""
Fcurve and driver utilities for Maya Faceit plugin.
Handles animation curves, keyframes, modifiers, and drivers.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
import json


# ============================================================
# Fcurve Modifier Types
# ============================================================

MODIFIER_TYPES = [
    'GENERATOR',
    'FNGENERATOR',
    'ENVELOPE',
    'CYCLES',
    'NOISE',
    'LIMITS',
    'STEPPED',
]


# ============================================================
# Fcurve Utility Functions
# ============================================================

def get_fcurve_from_bpy_struct(
    anim_data: Any,
    data_path: str = '',
    array_index: int = -1,
    replace: bool = False
) -> Optional[str]:
    """
    Find or create an fcurve with specified data path.
    
    Args:
        anim_data: Animation data object (object or action)
        data_path: The data path string
        array_index: The fcurve index in array properties
        replace: Whether to replace existing fcurve
        
    Returns:
        Fcurve name or None
    """
    # In Maya, we use animCurve nodes
    if isinstance(anim_data, str):
        # Check if it's an action or object
        if cmds.objExists(anim_data):
            if cmds.nodeType(anim_data) == 'animCurve':
                # It's an animation curve
                curve = anim_data
            else:
                # It's an object or action
                curves = cmds.listAnimCurves(anim_data) or []
                curve = None
                for c in curves:
                    attr = cmds.getAttr(f"{c}.attributeName") or ""
                    if attr == data_path:
                        idx = cmds.getAttr(f"{c}.arrayIndex") or 0
                        if idx == array_index or array_index == -1:
                            curve = c
                            break
                
                if curve and replace:
                    cmds.delete(curve)
                    curve = None
                
                if not curve:
                    # Create new curve
                    curve = cmds.createNode("animCurveUA", name=f"{anim_data}_{data_path.replace('.', '_')}")
                    cmds.connectAttr(f"{curve}.output", f"{anim_data}.{data_path}")
                    
                    # Set array index
                    if array_index != -1:
                        cmds.setAttr(f"{curve}.arrayIndex", array_index)
    else:
        # It's a Maya object with animation data
        obj = anim_data
        if cmds.objExists(obj):
            # Get or create animation data
            if not cmds.listConnections(f"{obj}.animationData"):
                cmds.animData(obj, add=True)
            
            curves = cmds.listAnimCurves(obj) or []
            curve = None
            for c in curves:
                attr = cmds.getAttr(f"{c}.attributeName") or ""
                if attr == data_path:
                    idx = cmds.getAttr(f"{c}.arrayIndex") or 0
                    if idx == array_index or array_index == -1:
                        curve = c
                        break
            
            if curve and replace:
                cmds.delete(curve)
                curve = None
            
            if not curve:
                # Create new curve on object
                curve = cmds.createNode("animCurveUA", name=f"{obj}_{data_path.replace('.', '_')}")
                cmds.connectAttr(f"{curve}.output", f"{obj}.{data_path}")
                
                if array_index != -1:
                    cmds.setAttr(f"{curve}.arrayIndex", array_index)
    
    return curve


# ============================================================
# Fcurve Modifier Functions
# ============================================================

def get_fcurve_modifiers(curve: str) -> Dict:
    """
    Get fcurve modifiers as a dictionary.
    
    Args:
        curve: Fcurve name
        
    Returns:
        Dictionary of modifier data
    """
    if not cmds.objExists(curve):
        return {}
    
    mod_dict = {}
    modifiers = cmds.listConnections(f"{curve}.modifiers") or []
    
    for i, mod in enumerate(modifiers):
        if not cmds.objExists(mod):
            continue
        
        mod_type = cmds.nodeType(mod)
        mod_dict[i] = {
            'type': mod_type,
            'active': cmds.getAttr(f"{mod}.active") if cmds.attributeQuery("active", node=mod, exists=True) else True,
            'mute': cmds.getAttr(f"{mod}.mute") if cmds.attributeQuery("mute", node=mod, exists=True) else False,
            'influence': cmds.getAttr(f"{mod}.influence") if cmds.attributeQuery("influence", node=mod, exists=True) else 1.0,
        }
        
        # Get type-specific attributes
        if mod_type == 'generator':
            mod_dict[i].update({
                'coefficients': cmds.getAttr(f"{mod}.coefficients") or [],
                'mode': cmds.getAttr(f"{mod}.mode") if cmds.attributeQuery("mode", node=mod, exists=True) else 0,
                'poly_order': cmds.getAttr(f"{mod}.polyOrder") if cmds.attributeQuery("polyOrder", node=mod, exists=True) else 0,
                'use_additive': cmds.getAttr(f"{mod}.useAdditive") if cmds.attributeQuery("useAdditive", node=mod, exists=True) else False,
            })
        
        elif mod_type == 'cycles':
            mod_dict[i].update({
                'cycles_after': cmds.getAttr(f"{mod}.cyclesAfter") if cmds.attributeQuery("cyclesAfter", node=mod, exists=True) else 0,
                'cycles_before': cmds.getAttr(f"{mod}.cyclesBefore") if cmds.attributeQuery("cyclesBefore", node=mod, exists=True) else 0,
                'mode_after': cmds.getAttr(f"{mod}.modeAfter") if cmds.attributeQuery("modeAfter", node=mod, exists=True) else 0,
                'mode_before': cmds.getAttr(f"{mod}.modeBefore") if cmds.attributeQuery("modeBefore", node=mod, exists=True) else 0,
            })
        
        elif mod_type == 'envelope':
            control_points = {}
            points = cmds.listConnections(f"{mod}.controlPoints") or []
            for point in points:
                frame = cmds.getAttr(f"{point}.frame") if cmds.attributeQuery("frame", node=point, exists=True) else 0
                control_points[frame] = {
                    'max': cmds.getAttr(f"{point}.max") if cmds.attributeQuery("max", node=point, exists=True) else 0,
                    'min': cmds.getAttr(f"{point}.min") if cmds.attributeQuery("min", node=point, exists=True) else 0,
                }
            
            mod_dict[i].update({
                'control_points': control_points,
                'default_max': cmds.getAttr(f"{mod}.defaultMax") if cmds.attributeQuery("defaultMax", node=mod, exists=True) else 0,
                'default_min': cmds.getAttr(f"{mod}.defaultMin") if cmds.attributeQuery("defaultMin", node=mod, exists=True) else 0,
                'reference_value': cmds.getAttr(f"{mod}.referenceValue") if cmds.attributeQuery("referenceValue", node=mod, exists=True) else 0,
            })
        
        elif mod_type == 'fnGenerator':
            mod_dict[i].update({
                'amplitude': cmds.getAttr(f"{mod}.amplitude") if cmds.attributeQuery("amplitude", node=mod, exists=True) else 1.0,
                'function_type': cmds.getAttr(f"{mod}.functionType") if cmds.attributeQuery("functionType", node=mod, exists=True) else 0,
                'phase_multiplier': cmds.getAttr(f"{mod}.phaseMultiplier") if cmds.attributeQuery("phaseMultiplier", node=mod, exists=True) else 1.0,
                'phase_offset': cmds.getAttr(f"{mod}.phaseOffset") if cmds.attributeQuery("phaseOffset", node=mod, exists=True) else 0.0,
                'use_additive': cmds.getAttr(f"{mod}.useAdditive") if cmds.attributeQuery("useAdditive", node=mod, exists=True) else False,
                'value_offset': cmds.getAttr(f"{mod}.valueOffset") if cmds.attributeQuery("valueOffset", node=mod, exists=True) else 0.0,
            })
        
        elif mod_type == 'limits':
            mod_dict[i].update({
                'max_x': cmds.getAttr(f"{mod}.maxX") if cmds.attributeQuery("maxX", node=mod, exists=True) else 1.0,
                'max_y': cmds.getAttr(f"{mod}.maxY") if cmds.attributeQuery("maxY", node=mod, exists=True) else 1.0,
                'min_x': cmds.getAttr(f"{mod}.minX") if cmds.attributeQuery("minX", node=mod, exists=True) else 0.0,
                'min_y': cmds.getAttr(f"{mod}.minY") if cmds.attributeQuery("minY", node=mod, exists=True) else 0.0,
                'use_max_x': cmds.getAttr(f"{mod}.useMaxX") if cmds.attributeQuery("useMaxX", node=mod, exists=True) else False,
                'use_max_y': cmds.getAttr(f"{mod}.useMaxY") if cmds.attributeQuery("useMaxY", node=mod, exists=True) else False,
                'use_min_x': cmds.getAttr(f"{mod}.useMinX") if cmds.attributeQuery("useMinX", node=mod, exists=True) else False,
                'use_min_y': cmds.getAttr(f"{mod}.useMinY") if cmds.attributeQuery("useMinY", node=mod, exists=True) else False,
            })
        
        elif mod_type == 'noise':
            mod_dict[i].update({
                'blend_type': cmds.getAttr(f"{mod}.blendType") if cmds.attributeQuery("blendType", node=mod, exists=True) else 0,
                'depth': cmds.getAttr(f"{mod}.depth") if cmds.attributeQuery("depth", node=mod, exists=True) else 0,
                'offset': cmds.getAttr(f"{mod}.offset") if cmds.attributeQuery("offset", node=mod, exists=True) else 0.0,
                'phase': cmds.getAttr(f"{mod}.phase") if cmds.attributeQuery("phase", node=mod, exists=True) else 0.0,
                'scale': cmds.getAttr(f"{mod}.scale") if cmds.attributeQuery("scale", node=mod, exists=True) else 1.0,
                'strength': cmds.getAttr(f"{mod}.strength") if cmds.attributeQuery("strength", node=mod, exists=True) else 1.0,
            })
        
        elif mod_type == 'stepped':
            mod_dict[i].update({
                'frame_end': cmds.getAttr(f"{mod}.frameEnd") if cmds.attributeQuery("frameEnd", node=mod, exists=True) else 0,
                'frame_offset': cmds.getAttr(f"{mod}.frameOffset") if cmds.attributeQuery("frameOffset", node=mod, exists=True) else 0,
                'frame_start': cmds.getAttr(f"{mod}.frameStart") if cmds.attributeQuery("frameStart", node=mod, exists=True) else 0,
                'frame_step': cmds.getAttr(f"{mod}.frameStep") if cmds.attributeQuery("frameStep", node=mod, exists=True) else 1,
                'use_frame_end': cmds.getAttr(f"{mod}.useFrameEnd") if cmds.attributeQuery("useFrameEnd", node=mod, exists=True) else False,
                'use_frame_start': cmds.getAttr(f"{mod}.useFrameStart") if cmds.attributeQuery("useFrameStart", node=mod, exists=True) else False,
            })
    
    return mod_dict


def clear_all_fc_modifiers(curve: str) -> bool:
    """
    Clear all fcurve modifiers.
    
    Args:
        curve: Fcurve name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    modifiers = cmds.listConnections(f"{curve}.modifiers") or []
    for mod in modifiers:
        if cmds.objExists(mod):
            cmds.delete(mod)
    
    return True


def populate_modifiers(curve: str, mod_dict: Dict) -> bool:
    """
    Populate fcurve modifiers from dictionary.
    
    Args:
        curve: Fcurve name
        mod_dict: Modifier data dictionary
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    # Clear existing modifiers
    clear_all_fc_modifiers(curve)
    
    for i, mod_data in mod_dict.items():
        mod_type = mod_data.get('type', 'generator')
        
        # Create modifier
        mod = cmds.createNode(f"animCurveModifier{mod_type.capitalize()}", name=f"{curve}_mod{i}")
        cmds.connectAttr(f"{mod}.output", f"{curve}.modifiers[{i}]")
        
        # Set common attributes
        if 'active' in mod_data:
            cmds.setAttr(f"{mod}.active", mod_data['active'])
        if 'mute' in mod_data:
            cmds.setAttr(f"{mod}.mute", mod_data['mute'])
        if 'influence' in mod_data:
            cmds.setAttr(f"{mod}.influence", mod_data['influence'])
        
        # Set type-specific attributes
        if mod_type == 'generator':
            if 'coefficients' in mod_data:
                cmds.setAttr(f"{mod}.coefficients", mod_data['coefficients'])
            if 'mode' in mod_data:
                cmds.setAttr(f"{mod}.mode", mod_data['mode'])
            if 'poly_order' in mod_data:
                cmds.setAttr(f"{mod}.polyOrder", mod_data['poly_order'])
            if 'use_additive' in mod_data:
                cmds.setAttr(f"{mod}.useAdditive", mod_data['use_additive'])
        
        elif mod_type == 'cycles':
            if 'cycles_after' in mod_data:
                cmds.setAttr(f"{mod}.cyclesAfter", mod_data['cycles_after'])
            if 'cycles_before' in mod_data:
                cmds.setAttr(f"{mod}.cyclesBefore", mod_data['cycles_before'])
            if 'mode_after' in mod_data:
                cmds.setAttr(f"{mod}.modeAfter", mod_data['mode_after'])
            if 'mode_before' in mod_data:
                cmds.setAttr(f"{mod}.modeBefore", mod_data['mode_before'])
        
        elif mod_type == 'envelope':
            if 'control_points' in mod_data:
                for frame, data in mod_data['control_points'].items():
                    point = cmds.createNode("animCurveEnvelopePoint", name=f"{mod}_point{frame}")
                    cmds.connectAttr(f"{point}.output", f"{mod}.controlPoints[0]")
                    cmds.setAttr(f"{point}.frame", frame)
                    cmds.setAttr(f"{point}.max", data.get('max', 1.0))
                    cmds.setAttr(f"{point}.min", data.get('min', 0.0))
            
            if 'default_max' in mod_data:
                cmds.setAttr(f"{mod}.defaultMax", mod_data['default_max'])
            if 'default_min' in mod_data:
                cmds.setAttr(f"{mod}.defaultMin", mod_data['default_min'])
            if 'reference_value' in mod_data:
                cmds.setAttr(f"{mod}.referenceValue", mod_data['reference_value'])
        
        elif mod_type == 'fnGenerator':
            if 'amplitude' in mod_data:
                cmds.setAttr(f"{mod}.amplitude", mod_data['amplitude'])
            if 'function_type' in mod_data:
                cmds.setAttr(f"{mod}.functionType", mod_data['function_type'])
            if 'phase_multiplier' in mod_data:
                cmds.setAttr(f"{mod}.phaseMultiplier", mod_data['phase_multiplier'])
            if 'phase_offset' in mod_data:
                cmds.setAttr(f"{mod}.phaseOffset", mod_data['phase_offset'])
            if 'use_additive' in mod_data:
                cmds.setAttr(f"{mod}.useAdditive", mod_data['use_additive'])
            if 'value_offset' in mod_data:
                cmds.setAttr(f"{mod}.valueOffset", mod_data['value_offset'])
        
        elif mod_type == 'limits':
            if 'max_x' in mod_data:
                cmds.setAttr(f"{mod}.maxX", mod_data['max_x'])
            if 'max_y' in mod_data:
                cmds.setAttr(f"{mod}.maxY", mod_data['max_y'])
            if 'min_x' in mod_data:
                cmds.setAttr(f"{mod}.minX", mod_data['min_x'])
            if 'min_y' in mod_data:
                cmds.setAttr(f"{mod}.minY", mod_data['min_y'])
            if 'use_max_x' in mod_data:
                cmds.setAttr(f"{mod}.useMaxX", mod_data['use_max_x'])
            if 'use_max_y' in mod_data:
                cmds.setAttr(f"{mod}.useMaxY", mod_data['use_max_y'])
            if 'use_min_x' in mod_data:
                cmds.setAttr(f"{mod}.useMinX", mod_data['use_min_x'])
            if 'use_min_y' in mod_data:
                cmds.setAttr(f"{mod}.useMinY", mod_data['use_min_y'])
        
        elif mod_type == 'noise':
            if 'blend_type' in mod_data:
                cmds.setAttr(f"{mod}.blendType", mod_data['blend_type'])
            if 'depth' in mod_data:
                cmds.setAttr(f"{mod}.depth", mod_data['depth'])
            if 'offset' in mod_data:
                cmds.setAttr(f"{mod}.offset", mod_data['offset'])
            if 'phase' in mod_data:
                cmds.setAttr(f"{mod}.phase", mod_data['phase'])
            if 'scale' in mod_data:
                cmds.setAttr(f"{mod}.scale", mod_data['scale'])
            if 'strength' in mod_data:
                cmds.setAttr(f"{mod}.strength", mod_data['strength'])
        
        elif mod_type == 'stepped':
            if 'frame_end' in mod_data:
                cmds.setAttr(f"{mod}.frameEnd", mod_data['frame_end'])
            if 'frame_offset' in mod_data:
                cmds.setAttr(f"{mod}.frameOffset", mod_data['frame_offset'])
            if 'frame_start' in mod_data:
                cmds.setAttr(f"{mod}.frameStart", mod_data['frame_start'])
            if 'frame_step' in mod_data:
                cmds.setAttr(f"{mod}.frameStep", mod_data['frame_step'])
            if 'use_frame_end' in mod_data:
                cmds.setAttr(f"{mod}.useFrameEnd", mod_data['use_frame_end'])
            if 'use_frame_start' in mod_data:
                cmds.setAttr(f"{mod}.useFrameStart", mod_data['use_frame_start'])
    
    return True


# ============================================================
# Keyframe Utility Functions
# ============================================================

def get_keyframe_meta_data(curve: str) -> Dict:
    """
    Get keyframe metadata.
    
    Args:
        curve: Fcurve name
        
    Returns:
        Dictionary of keyframe metadata
    """
    if not cmds.objExists(curve):
        return {}
    
    meta_data = {}
    keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
    values = cmds.keyframe(curve, query=True, valueChange=True) or []
    
    for i, (t, v) in enumerate(zip(keyframes, values)):
        meta_data[i] = {
            'time': t,
            'value': v,
            'interpolation': cmds.keyframe(curve, query=True, interpolation=True, index=i) or ['linear'],
            'tangent_in': cmds.keyframe(curve, query=True, tangentInAngle=True, index=i) or [0],
            'tangent_out': cmds.keyframe(curve, query=True, tangentOutAngle=True, index=i) or [0],
        }
    
    return meta_data


def populate_kf_meta_data(curve: str, kf_data_dict: Dict) -> bool:
    """
    Populate keyframe metadata from dictionary.
    
    Args:
        curve: Fcurve name
        kf_data_dict: Keyframe metadata dictionary
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    for i, data in kf_data_dict.items():
        i = int(i)
        if 'time' in data:
            time = data['time']
        else:
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            if i < len(keyframes):
                time = keyframes[i]
            else:
                continue
        
        if 'value' in data:
            cmds.keyframe(curve, edit=True, absolute=True, valueChange=data['value'], index=i, time=(time,))
        
        if 'interpolation' in data:
            cmds.keyframe(curve, edit=True, interpolation=data['interpolation'], index=i, time=(time,))
        
        if 'tangent_in' in data:
            cmds.keyframe(curve, edit=True, tangentInAngle=data['tangent_in'], index=i, time=(time,))
        
        if 'tangent_out' in data:
            cmds.keyframe(curve, edit=True, tangentOutAngle=data['tangent_out'], index=i, time=(time,))
    
    return True


# ============================================================
# Driver Utility Functions
# ============================================================

def clear_invalid_drivers():
    """
    Clear invalid drivers from the scene.
    """
    # Find all driver nodes
    drivers = cmds.ls(type='animCurve') or []
    
    for driver in drivers:
        # Check if driver is connected to something valid
        outputs = cmds.listConnections(f"{driver}.output", destination=True) or []
        if not outputs:
            # Driver is not connected to anything
            cmds.delete(driver)
        else:
            # Check if the connection is valid
            for output in outputs:
                if not cmds.objExists(output):
                    cmds.delete(driver)
                    break


# ============================================================
# Keyframe Data Conversion Functions
# ============================================================

def kf_data_to_numpy_array(curve: str, attr: str = 'co') -> np.ndarray:
    """
    Get keyframe data from an fcurve as numpy array.
    
    Args:
        curve: Fcurve name
        attr: Attribute to get ('co', 'handle_left', 'handle_right')
        
    Returns:
        Numpy array of keyframe data
    """
    if not cmds.objExists(curve):
        return np.array([])
    
    if attr == 'co':
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        if not keyframes or not values:
            return np.array([])
        
        data = np.zeros((len(keyframes), 2), dtype=np.float32)
        data[:, 0] = keyframes
        data[:, 1] = values
        
        return data
    
    elif attr == 'handle_left':
        tangents = cmds.keyframe(curve, query=True, tangentInAngle=True) or []
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        
        if not keyframes or not tangents:
            return np.array([])
        
        data = np.zeros((len(keyframes), 2), dtype=np.float32)
        data[:, 0] = keyframes
        data[:, 1] = tangents
        
        return data
    
    elif attr == 'handle_right':
        tangents = cmds.keyframe(curve, query=True, tangentOutAngle=True) or []
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        
        if not keyframes or not tangents:
            return np.array([])
        
        data = np.zeros((len(keyframes), 2), dtype=np.float32)
        data[:, 0] = keyframes
        data[:, 1] = tangents
        
        return data
    
    return np.array([])


def frame_value_pairs_to_numpy_array(frames: List[float], values: List[float]) -> np.ndarray:
    """
    Convert frame-value pairs to numpy array.
    
    Args:
        frames: List of frame numbers
        values: List of values
        
    Returns:
        Numpy array of frame-value pairs
    """
    if not frames or not values:
        return np.array([])
    
    return np.array(list(zip(frames, values)))


def populate_keyframe_points_from_np_array(
    curve: str,
    data: np.ndarray,
    attr: str = 'co',
    add: bool = False,
    join_with_existing: bool = True
) -> bool:
    """
    Populate keyframe points from a numpy array.
    
    Args:
        curve: Fcurve name
        data: Numpy array of keyframe data
        attr: Attribute to set ('co', 'handle_left', 'handle_right')
        add: Whether to add keyframes
        join_with_existing: Whether to join with existing keyframes
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve) or data.size == 0:
        return False
    
    if add:
        # Get existing keyframes
        existing_frames = cmds.keyframe(curve, query=True, timeChange=True) or []
        
        if existing_frames and join_with_existing:
            # Join with existing data
            existing_data = kf_data_to_numpy_array(curve, attr)
            data = join_np_array_kf_data(existing_data, data)
        
        # Clear existing keyframes
        clear_fcurve_kf_points(curve)
    
    if attr == 'co':
        # Set keyframes
        for frame, value in data:
            cmds.setKeyframe(curve, t=frame, v=value)
    
    elif attr == 'handle_left':
        # Set tangent in angles
        for i, (frame, tangent) in enumerate(data):
            cmds.keyframe(curve, edit=True, tangentInAngle=tangent, index=i, time=(frame,))
    
    elif attr == 'handle_right':
        # Set tangent out angles
        for i, (frame, tangent) in enumerate(data):
            cmds.keyframe(curve, edit=True, tangentOutAngle=tangent, index=i, time=(frame,))
    
    return True


def clear_fcurve_kf_points(curve: str) -> bool:
    """
    Clear all keyframe points from an fcurve.
    
    Args:
        curve: Fcurve name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
    for t in keyframes:
        cmds.keyframe(curve, edit=True, remove=True, time=(t,))
    
    return True


def join_np_array_kf_data(data_old: np.ndarray, data_new: np.ndarray) -> np.ndarray:
    """
    Join two numpy arrays containing keyframe data.
    Intersection will be overwritten by data_new.
    
    Args:
        data_old: Old keyframe data
        data_new: New keyframe data
        
    Returns:
        Joined keyframe data
    """
    if data_old.size == 0:
        return data_new
    
    if data_new.size == 0:
        return data_old
    
    # Get frames from new data
    new_frames = data_new[:, 0]
    min_frame = np.min(new_frames)
    max_frame = np.max(new_frames)
    
    # Remove frames in range from old data
    mask = (data_old[:, 0] < min_frame) | (data_old[:, 0] > max_frame)
    data_old_filtered = data_old[mask]
    
    # Join data
    return np.vstack((data_old_filtered, data_new))


# ============================================================
# Fcurve Property Functions
# ============================================================

def get_fcurve_properties(curve: str) -> Dict:
    """
    Get fcurve properties as a dictionary.
    
    Args:
        curve: Fcurve name
        
    Returns:
        Dictionary of fcurve properties
    """
    if not cmds.objExists(curve):
        return {}
    
    props = {
        'data_path': cmds.getAttr(f"{curve}.attributeName") or "",
        'array_index': cmds.getAttr(f"{curve}.arrayIndex") or 0,
        'select': cmds.getAttr(f"{curve}.select") if cmds.attributeQuery("select", node=curve, exists=True) else False,
        'mute': cmds.getAttr(f"{curve}.mute") if cmds.attributeQuery("mute", node=curve, exists=True) else False,
        'lock': cmds.getAttr(f"{curve}.lock") if cmds.attributeQuery("lock", node=curve, exists=True) else False,
        'extrapolation': cmds.getAttr(f"{curve}.extrapolation") if cmds.attributeQuery("extrapolation", node=curve, exists=True) else 0,
        'color': cmds.getAttr(f"{curve}.color") if cmds.attributeQuery("color", node=curve, exists=True) else [0.5, 0.5, 0.5],
    }
    
    return props


def populate_fcurve_properties(curve: str, fc_data_dict: Dict) -> bool:
    """
    Populate fcurve properties from dictionary.
    
    Args:
        curve: Fcurve name
        fc_data_dict: Fcurve property dictionary
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    if 'select' in fc_data_dict:
        cmds.setAttr(f"{curve}.select", fc_data_dict['select'])
    
    if 'mute' in fc_data_dict:
        cmds.setAttr(f"{curve}.mute", fc_data_dict['mute'])
    
    if 'lock' in fc_data_dict:
        cmds.setAttr(f"{curve}.lock", fc_data_dict['lock'])
    
    if 'extrapolation' in fc_data_dict:
        cmds.setAttr(f"{curve}.extrapolation", fc_data_dict['extrapolation'])
    
    if 'color' in fc_data_dict:
        cmds.setAttr(f"{curve}.color", fc_data_dict['color'])
    
    return True


# ============================================================
# Fcurve Copy Functions
# ============================================================

def copy_fcurve_data(
    curve: str,
    apply_keyframes: bool = True,
    apply_kf_props: bool = True,
    apply_handles: bool = True,
    apply_properties: bool = True,
    apply_modifiers: bool = True
) -> Dict:
    """
    Copy fcurve data to a dictionary.
    
    Args:
        curve: Fcurve name
        apply_keyframes: Whether to copy keyframes
        apply_kf_props: Whether to copy keyframe properties
        apply_handles: Whether to copy handles
        apply_properties: Whether to copy fcurve properties
        apply_modifiers: Whether to copy modifiers
        
    Returns:
        Dictionary of fcurve data
    """
    if not cmds.objExists(curve):
        return {}
    
    fcurve_data = {}
    
    # Get keyframe coordinates
    if apply_keyframes:
        fcurve_data['kf_coordinates'] = kf_data_to_numpy_array(curve, 'co')
    
    # Get handle coordinates
    if apply_handles:
        fcurve_data['kf_hl_coordinates'] = kf_data_to_numpy_array(curve, 'handle_left')
        fcurve_data['kf_hr_coordinates'] = kf_data_to_numpy_array(curve, 'handle_right')
    
    # Get keyframe properties
    if apply_kf_props:
        fcurve_data['kf_properties'] = get_keyframe_meta_data(curve)
    
    # Get fcurve properties
    if apply_properties:
        fcurve_data['properties'] = get_fcurve_properties(curve)
    
    # Get modifiers
    if apply_modifiers:
        fcurve_data['modifiers'] = get_fcurve_modifiers(curve)
    
    return fcurve_data


def populate_stored_fcurve_data(
    fc_data: Dict,
    curve: str = None,
    action: str = None,
    data_path: str = '',
    array_index: int = -1,
    join_with_existing_data: bool = True,
    apply_keyframes: bool = True,
    apply_kf_props: bool = True,
    apply_handles: bool = True,
    apply_properties: bool = True,
    apply_modifiers: bool = True
) -> bool:
    """
    Populate fcurve data from stored dictionary.
    
    Args:
        fc_data: Fcurve data dictionary
        curve: Fcurve name
        action: Action name
        data_path: Data path
        array_index: Array index
        join_with_existing_data: Whether to join with existing data
        apply_keyframes: Whether to apply keyframes
        apply_kf_props: Whether to apply keyframe properties
        apply_handles: Whether to apply handles
        apply_properties: Whether to apply fcurve properties
        apply_modifiers: Whether to apply modifiers
        
    Returns:
        True if successful
    """
    if not fc_data:
        return False
    
    # Get or create curve
    if curve:
        target_curve = curve
    elif action:
        target_curve = get_fcurve_from_bpy_struct(action, data_path, array_index, replace=not join_with_existing_data)
    else:
        return False
    
    if not target_curve:
        return False
    
    # Apply keyframes
    if apply_keyframes and 'kf_coordinates' in fc_data:
        kf_data = fc_data['kf_coordinates']
        if kf_data.size > 0:
            populate_keyframe_points_from_np_array(
                target_curve, kf_data, 'co', add=True, join_with_existing=join_with_existing_data
            )
    
    # Apply handles
    if apply_handles:
        if 'kf_hl_coordinates' in fc_data:
            hl_data = fc_data['kf_hl_coordinates']
            if hl_data.size > 0:
                populate_keyframe_points_from_np_array(target_curve, hl_data, 'handle_left')
        
        if 'kf_hr_coordinates' in fc_data:
            hr_data = fc_data['kf_hr_coordinates']
            if hr_data.size > 0:
                populate_keyframe_points_from_np_array(target_curve, hr_data, 'handle_right')
    
    # Apply keyframe properties
    if apply_kf_props and 'kf_properties' in fc_data:
        populate_kf_meta_data(target_curve, fc_data['kf_properties'])
    
    # Apply fcurve properties
    if apply_properties and 'properties' in fc_data:
        populate_fcurve_properties(target_curve, fc_data['properties'])
    
    # Apply modifiers
    if apply_modifiers and 'modifiers' in fc_data:
        populate_modifiers(target_curve, fc_data['modifiers'])
    
    return True


# ============================================================
# Driver Copy Functions
# ============================================================

def copy_driver_data(curve: str) -> Dict:
    """
    Copy driver data to a dictionary.
    
    Args:
        curve: Fcurve name with driver
        
    Returns:
        Dictionary of driver data
    """
    if not cmds.objExists(curve):
        return {}
    
    # Check if it's a driver curve
    if not cmds.listConnections(f"{curve}.driver"):
        return {}
    
    driver_dict = {}
    
    # Get driver connection
    driver = cmds.listConnections(f"{curve}.driver")[0]
    if not cmds.objExists(driver):
        return {}
    
    # Get driver properties
    driver_dict['driver'] = {
        'type': cmds.nodeType(driver),
        'expression': cmds.getAttr(f"{driver}.expression") if cmds.attributeQuery("expression", node=driver, exists=True) else "",
        'use_self': cmds.getAttr(f"{driver}.useSelf") if cmds.attributeQuery("useSelf", node=driver, exists=True) else False,
    }
    
    # Get driver variables
    variables = cmds.listConnections(f"{driver}.variables") or []
    var_dict = {}
    
    for var in variables:
        if not cmds.objExists(var):
            continue
        
        var_name = cmds.getAttr(f"{var}.name") if cmds.attributeQuery("name", node=var, exists=True) else ""
        var_dict[var_name] = {
            'type': cmds.getAttr(f"{var}.type") if cmds.attributeQuery("type", node=var, exists=True) else 0,
        }
        
        # Get variable targets
        targets = cmds.listConnections(f"{var}.targets") or []
        target_dict = {}
        
        for target in targets:
            if not cmds.objExists(target):
                continue
            
            target_data = {
                'id_type': cmds.getAttr(f"{target}.idType") if cmds.attributeQuery("idType", node=target, exists=True) else "",
                'data_path': cmds.getAttr(f"{target}.dataPath") if cmds.attributeQuery("dataPath", node=target, exists=True) else "",
                'bone_target': cmds.getAttr(f"{target}.boneTarget") if cmds.attributeQuery("boneTarget", node=target, exists=True) else "",
                'transform_type': cmds.getAttr(f"{target}.transformType") if cmds.attributeQuery("transformType", node=target, exists=True) else 0,
                'transform_space': cmds.getAttr(f"{target}.transformSpace") if cmds.attributeQuery("transformSpace", node=target, exists=True) else 0,
            }
            
            # Get target index
            idx = 0
            if cmds.attributeQuery("targetIndex", node=target, exists=True):
                idx = cmds.getAttr(f"{target}.targetIndex")
            
            target_dict[idx] = target_data
        
        var_dict[var_name]['targets'] = target_dict
    
    driver_dict['driver']['variables'] = var_dict
    
    # Get fcurve data
    driver_dict['fc'] = copy_fcurve_data(curve)
    
    # Get modifiers
    driver_dict['modifiers'] = get_fcurve_modifiers(curve)
    
    return driver_dict


def populate_driver_data(driver_dict: Dict, curve: str) -> bool:
    """
    Populate driver data from dictionary.
    
    Args:
        driver_dict: Driver data dictionary
        curve: Fcurve name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(curve):
        return False
    
    # Get driver data
    dr_data = driver_dict.get('driver', {})
    if not dr_data:
        return False
    
    # Create driver
    driver = cmds.createNode("driver", name=f"{curve}_driver")
    cmds.connectAttr(f"{driver}.output", f"{curve}.driver")
    
    # Set driver properties
    if 'expression' in dr_data:
        cmds.setAttr(f"{driver}.expression", dr_data['expression'], type="string")
    
    if 'use_self' in dr_data:
        cmds.setAttr(f"{driver}.useSelf", dr_data['use_self'])
    
    # Create variables
    variables = dr_data.get('variables', {})
    for var_name, var_data in variables.items():
        var = cmds.createNode("driverVariable", name=f"{driver}_{var_name}")
        cmds.connectAttr(f"{var}.output", f"{driver}.variables[0]")
        cmds.setAttr(f"{var}.name", var_name, type="string")
        
        if 'type' in var_data:
            cmds.setAttr(f"{var}.type", var_data['type'])
        
        # Create targets
        targets = var_data.get('targets', {})
        for idx, target_data in targets.items():
            target = cmds.createNode("driverTarget", name=f"{var}_target{idx}")
            cmds.connectAttr(f"{target}.output", f"{var}.targets[{idx}]")
            
            if 'id_type' in target_data and target_data['id_type']:
                cmds.setAttr(f"{target}.idType", target_data['id_type'])
            
            if 'data_path' in target_data and target_data['data_path']:
                cmds.setAttr(f"{target}.dataPath", target_data['data_path'], type="string")
            
            if 'bone_target' in target_data and target_data['bone_target']:
                cmds.setAttr(f"{target}.boneTarget", target_data['bone_target'], type="string")
            
            if 'transform_type' in target_data:
                cmds.setAttr(f"{target}.transformType", target_data['transform_type'])
            
            if 'transform_space' in target_data:
                cmds.setAttr(f"{target}.transformSpace", target_data['transform_space'])
    
    # Populate fcurve data
    if 'fc' in driver_dict:
        fc_data = driver_dict['fc']
        populate_stored_fcurve_data(fc_data, curve)
    
    # Populate modifiers
    if 'modifiers' in driver_dict:
        populate_modifiers(curve, driver_dict['modifiers'])
    
    return True


# ============================================================
# Sample Points Functions
# ============================================================

def sampled_points_to_numpy_array(curve: str, attr: str = 'sampled_points') -> np.ndarray:
    """
    Get sampled points from an fcurve as numpy array.
    
    Args:
        curve: Fcurve name
        attr: Attribute to get
        
    Returns:
        Numpy array of sampled points
    """
    if not cmds.objExists(curve):
        return np.array([])
    
    # Get sampled points
    samples = cmds.getAttr(f"{curve}.sampledPoints") if cmds.attributeQuery("sampledPoints", node=curve, exists=True) else []
    
    if not samples:
        return np.array([])
    
    # Convert to numpy array
    data = np.array(samples).reshape(-1, 2)
    
    return data