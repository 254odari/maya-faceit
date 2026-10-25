# __init__.py
# Maya Faceit Plugin - Landmarks Module
# Version: 1.0.0

"""
Faceit Landmarks Module for Maya
================================

This module provides facial landmark creation, editing, and management functionality.

Main Components:
    - Landmark mesh creation and placement
    - Landmark projection and editing
    - Viewport locking and control
    - Mirror operations
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import landmarks_data
from . import landmarks_utils
from . import landmarks_operators

# ============================================================
# Imports from landmarks_data
# ============================================================

from .landmarks_data import (
    LOCATOR_NAMES,
    LANDMARKS_MIRROR_VERTICES_DICT,
    LANDMAKRS_MID_VERTICES_DICT,
)

# ============================================================
# Imports from landmarks_utils
# ============================================================

from .landmarks_utils import (
    check_is_quad_view,
    check_if_area_is_active,
    set_front_view,
    unlock_3d_view,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Data
    'LOCATOR_NAMES',
    'LANDMARKS_MIRROR_VERTICES_DICT',
    'LANDMAKRS_MID_VERTICES_DICT',
    
    # Utilities
    'check_is_quad_view',
    'check_if_area_is_active',
    'set_front_view',
    'unlock_3d_view',
]