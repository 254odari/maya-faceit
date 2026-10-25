# __init__.py
# Maya Faceit Plugin - Rigging Module
# Version: 1.0.0

"""
Faceit Rigging Module for Maya
==============================

This module provides rigging functionality for the Faceit pipeline.

Main Components:
    - Rig generation and matching
    - Rig joining to body armature
    - Locator generation
    - Rig utilities
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import rig_data
from . import rig_utils
from . import rig_operators
from . import rig_join_to_body

# ============================================================
# Imports from rig_data
# ============================================================

from .rig_data import (
    bone_dict_asymmetric,
    bone_dict_symmetric,
)

# ============================================================
# Imports from rig_utils
# ============================================================

from .rig_utils import (
    get_evaluated_vertex_group_positions,
    get_bounds_from_locations,
    reset_stretch,
    get_bone_delta,
    set_lid_follow_constraints,
    child_of_set_inverse,
    get_bone_groups_dict,
    set_bone_groups_from_dict,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Data
    'bone_dict_asymmetric',
    'bone_dict_symmetric',
    
    # Utilities
    'get_evaluated_vertex_group_positions',
    'get_bounds_from_locations',
    'reset_stretch',
    'get_bone_delta',
    'set_lid_follow_constraints',
    'child_of_set_inverse',
    'get_bone_groups_dict',
    'set_bone_groups_from_dict',
]