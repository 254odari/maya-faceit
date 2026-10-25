# __init__.py
# Maya Faceit Plugin - Control Rig Module
# Version: 1.0.0

"""
Faceit Control Rig Module for Maya
==================================

This module provides control rig generation, management, and animation functionality.

Main Components:
    - Control rig generation and matching
    - Control rig animation baking
    - Custom slider creation
    - Driver management
    - Control rig data and utilities
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import control_rig_data
from . import control_rig_utils
from . import custom_slider_utils
from . import control_rig_generate_operators
from . import control_rig_operators
from . import control_rig_prop_list_operators
from . import control_rig_animation_operators
from . import control_rig_custom_slider_operators
from . import control_rig_driver_operators
from . import draw_c_ranges

# ============================================================
# Imports from control_rig_data
# ============================================================

from .control_rig_data import (
    CNTRL_RIG_VERSION,
    get_random_rig_id,
    get_pose_bone_range_from_limit_constraint,
    get_default_driver_info_dict,
    get_driver_from_retarget_dictionary_fixed_slider_range,
    get_bone_settings_from_driver_dict,
    get_pose_bone_from_driver_dict,
    get_bone_animation_data,
    control_rig_drivers_dict,
    match_bones_asymmetry_dict,
    match_bones_symmetry_dict,
)

# ============================================================
# Imports from control_rig_utils
# ============================================================

from .control_rig_utils import (
    populate_control_rig_target_objects_from_scene,
    get_crig_objects_list,
    is_control_rig_connected,
    get_slider_bone_name_from_arkit_driver_dict,
    populate_control_rig_target_shapes_from_scene,
)

# ============================================================
# Imports from custom_slider_utils
# ============================================================

from .custom_slider_utils import (
    get_custom_slider_from_shape,
    get_custom_sliders_in_crig,
    get_custom_sliders_in_crig_targets_enum,
    get_custom_sliders_from_faceit_objects_enum,
    generate_extra_sliders,
    get_all_slider_bones,
    cleanup_unused_bone_shapes,
    generate_custom_curve_text,
    generate_custom_curve_box,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Version and data
    'CNTRL_RIG_VERSION',
    'get_random_rig_id',
    'get_pose_bone_range_from_limit_constraint',
    'get_default_driver_info_dict',
    'get_driver_from_retarget_dictionary_fixed_slider_range',
    'get_bone_settings_from_driver_dict',
    'get_pose_bone_from_driver_dict',
    'get_bone_animation_data',
    'control_rig_drivers_dict',
    'match_bones_asymmetry_dict',
    'match_bones_symmetry_dict',
    
    # Utilities
    'populate_control_rig_target_objects_from_scene',
    'get_crig_objects_list',
    'is_control_rig_connected',
    'get_slider_bone_name_from_arkit_driver_dict',
    'populate_control_rig_target_shapes_from_scene',
    
    # Custom slider utilities
    'get_custom_slider_from_shape',
    'get_custom_sliders_in_crig',
    'get_custom_sliders_in_crig_targets_enum',
    'get_custom_sliders_from_faceit_objects_enum',
    'generate_extra_sliders',
    'get_all_slider_bones',
    'cleanup_unused_bone_shapes',
    'generate_custom_curve_text',
    'generate_custom_curve_box',
]