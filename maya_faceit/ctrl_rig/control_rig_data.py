# control_rig_data.py
# Maya Faceit Plugin - Control Rig Data
# Converted from Blender to Maya Python 3.11

"""
Control rig data definitions for Faceit Maya plugin.
Contains driver dictionaries, bone matching data, and helper functions.
"""

import maya.cmds as cmds
from random import randint
from typing import List, Dict, Optional, Tuple, Any

# ============================================================
# Version and Constants
# ============================================================

CNTRL_RIG_VERSION = 1.2


def get_random_rig_id() -> int:
    """Generate a random rig ID."""
    return randint(10000, 99999)


# ============================================================
# Bone Range Utilities
# ============================================================

def get_pose_bone_range_from_limit_constraint(pose_bone: str) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """
    Get the limit location constraint limits for a pose bone.
    
    Args:
        pose_bone: Pose bone name
        
    Returns:
        Tuple of (max_limits, min_limits) as lists of [x, y, z] or None
    """
    if not cmds.objExists(pose_bone):
        return None, None
    
    max_limits = None
    min_limits = None
    
    # Get constraints on the bone
    constraints = cmds.listConnections(f"{pose_bone}.constraints") or []
    
    for constraint in constraints:
        if not cmds.objExists(constraint):
            continue
        
        constraint_type = cmds.nodeType(constraint)
        
        if constraint_type in ['constraint', 'limitConstraint']:
            # Check for limit location attributes
            if cmds.attributeQuery("limitX", node=constraint, exists=True):
                max_limits = [
                    cmds.getAttr(f"{constraint}.maxX") if cmds.attributeQuery("maxX", node=constraint, exists=True) else 0.0,
                    cmds.getAttr(f"{constraint}.maxY") if cmds.attributeQuery("maxY", node=constraint, exists=True) else 0.0,
                    cmds.getAttr(f"{constraint}.maxZ") if cmds.attributeQuery("maxZ", node=constraint, exists=True) else 0.0,
                ]
                min_limits = [
                    cmds.getAttr(f"{constraint}.minX") if cmds.attributeQuery("minX", node=constraint, exists=True) else 0.0,
                    cmds.getAttr(f"{constraint}.minY") if cmds.attributeQuery("minY", node=constraint, exists=True) else 0.0,
                    cmds.getAttr(f"{constraint}.minZ") if cmds.attributeQuery("minZ", node=constraint, exists=True) else 0.0,
                ]
                break
    
    return max_limits, min_limits


def get_default_driver_info_dict(expression_name: str, range_type: str = 'all') -> Dict:
    """
    Get default driver info dictionary.
    
    Args:
        expression_name: Expression name
        range_type: Range type ('all', 'pos', 'neg')
        
    Returns:
        Driver info dictionary
    """
    return {
        'variables': {
            'var': {
                'bone_name': f'c_{expression_name}_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': range_type,
        'main_dir': 1,
    }


# ============================================================
# Driver Creation Utilities
# ============================================================

def get_driver_from_retarget_dictionary_fixed_slider_range(
    expression_name: str,
    target_shape_key_name: str,
    control_rig_id: str,
    shape_key_data: Any = None,
    custom_slider: bool = False,
    current_range: str = 'all',
    jaw_open_shape: str = 'jawOpen'
) -> Tuple[bool, Optional[str]]:
    """
    Create a driver from the retargeting dictionary.
    
    Args:
        expression_name: Expression name
        target_shape_key_name: Target shape key name
        control_rig_id: Control rig object name
        shape_key_data: Shape key data
        custom_slider: Whether it's a custom slider
        current_range: Current range ('all', 'pos', 'neg')
        jaw_open_shape: Jaw open shape name
        
    Returns:
        Tuple of (success, bone_name)
    """
    if not expression_name or not control_rig_id:
        return False, None
    
    if not shape_key_data:
        return False, None
    
    if not target_shape_key_name:
        return False, None
    
    # Get driver info
    if custom_slider:
        dr_info = get_default_driver_info_dict(expression_name, range_type=current_range)
    else:
        dr_info = control_rig_drivers_dict.get(expression_name)
    
    if not dr_info:
        return False, None
    
    # Get bone name
    bone_name, transform_type, transform_space = get_bone_settings_from_driver_dict(dr_info)
    
    # Return the bone name
    return True, bone_name


def get_bone_settings_from_driver_dict(dr_info: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get bone transform settings from driver info dictionary.
    
    Args:
        dr_info: Driver info dictionary
        
    Returns:
        Tuple of (bone_name, transform_type, transform_space)
    """
    bone_name = None
    transform_type = None
    transform_space = None
    
    variables = dr_info.get('variables', {})
    var = variables.get('var', {})
    
    if var:
        bone_name = var.get('bone_name')
        transform_type = var.get('transform_type')
        transform_space = var.get('transform_space')
    
    return bone_name, transform_type, transform_space


def get_pose_bone_from_driver_dict(rig: str, arkit_shape_name: str) -> Optional[str]:
    """
    Get the pose bone specified in the target variable of the shape key driver.
    
    Args:
        rig: Rig object name
        arkit_shape_name: ARKit shape name
        
    Returns:
        Pose bone name or None
    """
    dr_info = control_rig_drivers_dict.get(arkit_shape_name)
    
    if not dr_info:
        return None
    
    bone_name, _, _ = get_bone_settings_from_driver_dict(dr_info)
    
    if bone_name and cmds.objExists(bone_name):
        return bone_name
    
    return None


def get_bone_animation_data(shape_key_name: str, c_rig: str) -> Tuple[str, int, float, float, str, int, str]:
    """
    Get bone animation data for retargeting.
    
    Args:
        shape_key_name: Shape key name
        c_rig: Control rig object name
        
    Returns:
        Tuple of (data_path, array_index, max_range, min_range, bone_range, main_dir, bone_name)
    """
    dr_info = control_rig_drivers_dict.get(shape_key_name)
    
    if not dr_info:
        dr_info = get_default_driver_info_dict(shape_key_name)
    
    bone_name, transform_type, _ = get_bone_settings_from_driver_dict(dr_info)
    
    if not bone_name or not cmds.objExists(bone_name):
        bone_name = 'c_slider_ref'
    
    # Get data path and array index
    transform, axis = transform_type.split('_') if '_' in transform_type else (transform_type, 'Y')
    array_index = get_array_index_from_driver.get(axis, 1)
    driver_data_path = get_data_path_from_driver_transform.get(transform, 'location')
    
    dp = f'pose.bones["{bone_name}"].{driver_data_path}'
    
    # Get bone range
    max_range, min_range = get_pose_bone_range_from_limit_constraint(bone_name)
    
    if max_range and array_index < len(max_range):
        max_val = max_range[array_index]
    else:
        max_val = 1.0
    
    if min_range and array_index < len(min_range):
        min_val = min_range[array_index]
    else:
        min_val = 0.0
    
    bone_range = dr_info.get('range', 'pos')
    main_dir = dr_info.get('main_dir', 1)
    
    return dp, array_index, max_val, min_val, bone_range, main_dir, bone_name


# ============================================================
# Data Path Mappings
# ============================================================

get_data_path_from_driver_transform = {
    'LOC': 'location',
    'ROT': 'rotation_euler',
    'SCALE': 'scale',
}

get_array_index_from_driver = {
    'X': 0,
    'Y': 1,
    'Z': 2,
    'AVG': 0,
}


# ============================================================
# Control Rig Drivers Dictionary
# ============================================================

control_rig_drivers_dict = {
    'eyeBlinkLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookInLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookOutLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeSquintLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_lower.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'eyeWideLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeBlinkRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookInRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeLookOutRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'eyeLookUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eye.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'eyeSquintRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_lower.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'eyeWideRight': {
        'variables': {
            'var': {
                'bone_name': 'c_eyelid_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'jawForward': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'jawLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'jawRight': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'jawOpen': {
        'variables': {
            'var': {
                'bone_name': 'c_jaw_target',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthClose': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_closed',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
        'main_dir': 1,
    },
    'mouthFunnel': {
        'variables': {
            'var': {
                'bone_name': 'c_mouthFunnel_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthPucker': {
        'variables': {
            'var': {
                'bone_name': 'c_mouthPucker_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthRight': {
        'variables': {
            'var': {
                'bone_name': 'c_mouth_controller',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'mouthLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_mouth_controller',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'mouthSmileLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'mouthSmileRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'pos',
    },
    'mouthFrownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'mouthFrownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'neg',
    },
    'mouthDimpleLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthDimpleRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_Z',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthStretchLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthStretchRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_X',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthRollLower': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_lower_roll',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthRollUpper': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_upper_roll',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthShrugLower': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_lower',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthShrugUpper': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_upper',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthPressLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthPressRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_corner_adjust.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthLowerDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_lower.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthLowerDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_lower.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': -1,
    },
    'mouthUpperUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'mouthUpperUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_lips_outer_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browDownLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_inner.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browDownRight': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_inner.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browInnerUp': {
        'variables': {
            'var': {
                'bone_name': 'c_eyebrow_mid',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browOuterUpLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_outer.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'browOuterUpRight': {
        'variables': {
            'var': {
                'bone_name': 'c_brow_outer.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekPuff': {
        'variables': {
            'var': {
                'bone_name': 'c_cheekPuff_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekSquintLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_cheek_upper.L',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'cheekSquintRight': {
        'variables': {
            'var': {
                'bone_name': 'c_cheek_upper.R',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
    'noseSneerLeft': {
        'variables': {
            'var': {
                'bone_name': 'c_nose_sneer.L',
                'transform_type': 'SCALE_AVG',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'all',
        'main_dir': -1,
    },
    'noseSneerRight': {
        'variables': {
            'var': {
                'bone_name': 'c_nose_sneer.R',
                'transform_type': 'SCALE_AVG',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'overwrite_expression': False,
        'range': 'all',
        'main_dir': -1,
    },
    'tongueOut': {
        'variables': {
            'var': {
                'bone_name': 'c_tongueOut_slider',
                'transform_type': 'LOC_Y',
                'transform_space': 'LOCAL_SPACE',
            },
        },
        'range': 'all',
        'main_dir': 1,
    },
}


# ============================================================
# Bone Matching Dictionaries
# ============================================================

match_bones_asymmetry_dict = {
    0: {'head': [], 'tail': [], 'all': ['c_jaw_target']},
    3: {'head': [], 'tail': [], 'all': ['c_lips_lower_roll']},
    6: {'head': [], 'tail': [], 'all': ['c_lips_lower', 'c_mouth_controller']},
    7: {'head': [], 'tail': [], 'all': ['c_lips_outer_lower.R']},
    8: {'head': [], 'tail': [], 'all': ['c_lips_outer_lower.L']},
    9: {'head': [], 'tail': [], 'all': ['c_lips_upper']},
    10: {'head': [], 'tail': [], 'all': ['c_lips_outer_upper.R']},
    11: {'head': [], 'tail': [], 'all': ['c_lips_outer_upper.L']},
    12: {'head': [], 'tail': [], 'all': ['c_lips_corner.L', 'c_lips_corner_adjust.L']},
    13: {'head': [], 'tail': [], 'all': ['c_lips_corner.R', 'c_lips_corner_adjust.R']},
    14: {'head': [], 'tail': [], 'all': ['c_lips_upper_roll']},
    22: {'head': [], 'tail': [], 'all': ['c_cheek_upper.R']},
    23: {'head': [], 'tail': [], 'all': ['c_cheek_upper.L']},
    26: {'head': [], 'tail': [], 'all': ['c_nose_sneer.L']},
    27: {'head': [], 'tail': [], 'all': ['c_nose_sneer.R']},
    30: {'head': [], 'tail': [], 'all': ['c_eyelid_lower.L']},
    31: {'head': [], 'tail': [], 'all': ['c_eyelid_lower.R']},
    43: {'head': [], 'tail': [], 'all': ['c_eyelid_upper.R']},
    44: {'head': [], 'tail': [], 'all': ['c_eyelid_upper.L']},
    57: {'head': [], 'tail': [], 'all': ['c_brow_inner.L']},
    58: {'head': [], 'tail': [], 'all': ['c_brow_inner.R']},
    61: {'head': [], 'tail': [], 'all': ['c_brow_outer.R']},
    62: {'head': [], 'tail': [], 'all': ['c_brow_outer.L']},
    63: {'head': [], 'tail': [], 'all': ['c_brow_master.L']},
    64: {'head': [], 'tail': [], 'all': ['c_brow_master.R']},
    101: {'head': [], 'tail': [], 'all': ['c_eyebrow_mid']},
    102: {'head': [], 'tail': [], 'all': ['c_lower_lips', 'c_lips_parent', 'c_jaw_target_master', 'c_face_main']},
    103: {'head': [], 'tail': [], 'all': ['c_eye_lookat', 'c_eye.L', 'c_eye.R']},
}


match_bones_symmetry_dict = {
    1: {'head': [], 'tail': [], 'all': ['c_jaw_target']},
    3: {'head': [], 'tail': [], 'all': ['c_lips_lower_roll']},
    5: {'head': [], 'tail': [], 'all': ['c_lips_lower', 'c_mouth_controller']},
    6: {'head': [], 'tail': [], 'all': ['c_lips_outer_lower.L']},
    7: {'head': [], 'tail': [], 'all': ['c_lips_corner.L', 'c_lips_corner_adjust.L']},
    8: {'head': [], 'tail': [], 'all': ['c_lips_upper']},
    9: {'head': [], 'tail': [], 'all': ['c_lips_outer_upper.L']},
    10: {'head': [], 'tail': [], 'all': ['c_lips_upper_roll']},
    15: {'head': [], 'tail': [], 'all': ['c_cheek_upper.L']},
    16: {'head': [], 'tail': [], 'all': ['c_nose_sneer.L']},
    19: {'head': [], 'tail': [], 'all': ['c_eyelid_lower.L']},
    27: {'head': [], 'tail': [], 'all': ['c_eyelid_upper.L']},
    30: {'head': [], 'tail': [], 'all': ['c_brow_inner.L']},
    34: {'head': [], 'tail': [], 'all': ['c_brow_master.L']},
    35: {'head': [], 'tail': [], 'all': ['c_brow_outer.L']},
    101: {'head': [], 'tail': [], 'all': ['c_eyebrow_mid']},
    102: {'head': [], 'tail': [], 'all': ['c_lower_lips', 'c_lips_parent', 'c_jaw_target_master', 'c_face_main']},
    103: {'head': [], 'tail': [], 'all': ['c_eye_lookat', 'c_eye.L', 'c_eye.R']},
}