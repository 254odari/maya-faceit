# animate_utils.py
# Maya Faceit Plugin - Animation Utilities
# Converted from Blender to Maya Python 3.11

"""
Animation utilities for Maya Faceit plugin.
Contains helper functions for animation operations.
"""

import math
from typing import List, Dict, Optional, Tuple, Set, Union, Iterable

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MVector, MMatrix, MQuaternion, MEulerRotation
import numpy as np


# ============================================================
# Rotation Helper Functions
# ============================================================

def get_rotation_mode(obj: str) -> str:
    """
    Get the rotation mode of an object.
    
    Args:
        obj: Object name
        
    Returns:
        Rotation mode: 'EULER', 'QUATERNION', or 'AXIS_ANGLE'
    """
    if not cmds.objExists(obj):
        return 'EULER'
    
    rot_mode = cmds.getAttr(f"{obj}.rotateOrder") or 0
    # Rotate order: 0=XYZ, 1=YZX, 2=ZXY, 3=XZY, 4=YXZ, 5=ZYX
    return 'EULER'  # Maya uses Euler by default


def get_data_path_from_rotation_mode(rot_mode: str) -> str:
    """
    Get the data path string for a rotation mode.
    
    Args:
        rot_mode: 'EULER', 'QUATERNION', or 'AXIS_ANGLE'
        
    Returns:
        Data path string
    """
    if rot_mode == 'EULER':
        return 'rotation_euler'
    elif rot_mode == 'QUATERNION':
        return 'rotation_quaternion'
    else:
        return 'rotation_axis_angle'


def get_rotation_mode_from_data_path(data_path: str) -> str:
    """
    Get rotation mode from a data path string.
    
    Args:
        data_path: Data path string
        
    Returns:
        Rotation mode
    """
    if 'euler' in data_path.lower():
        return 'EULER'
    elif 'quaternion' in data_path.lower():
        return 'QUATERNION'
    elif 'axis' in data_path.lower():
        return 'AXIS_ANGLE'