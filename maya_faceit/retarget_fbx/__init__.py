# __init__.py
# Maya Faceit Plugin - Retarget FBX Module
# Version: 1.0.0

"""
Faceit Retarget FBX Module for Maya
===================================

This module provides FBX retargeting functionality for the Faceit pipeline.

Main Components:
    - FBX action retargeting
    - Shape key mapping
    - Retargeting list management
    - Preset import/export
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import retarget_fbx_operators
from . import retarget_list_fbx_operators

# ============================================================
# Imports from retarget_fbx_operators
# ============================================================

from .retarget_fbx_operators import (
    RetargetFBXAction,
    get_enum_sk_actions,
    update_action_name,
)

# ============================================================
# Imports from retarget_list_fbx_operators
# ============================================================

from .retarget_list_fbx_operators import (
    FBXRetargetBase,
    EditFBXTargetShape,
    RemoveFBXTargetShape,
    ClearFBXTargetShapes,
    InitFBXRetargeting,
    ClearFBXRetargeting,
    ImportFBXRetargetPreset,
    ExportFBXRetargetPreset,
    get_target_shapes_enum,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Operators
    'RetargetFBXAction',
    'EditFBXTargetShape',
    'RemoveFBXTargetShape',
    'ClearFBXTargetShapes',
    'InitFBXRetargeting',
    'ClearFBXRetargeting',
    'ImportFBXRetargetPreset',
    'ExportFBXRetargetPreset',
    
    # Utilities
    'get_enum_sk_actions',
    'update_action_name',
    'FBXRetargetBase',
    'get_target_shapes_enum',
]