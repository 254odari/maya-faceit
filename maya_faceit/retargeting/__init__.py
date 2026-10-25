# __init__.py
# Maya Faceit Plugin - Retargeting Module
# Version: 1.0.0

"""
Faceit Retargeting Module for Maya
==================================

This module provides retargeting functionality for the Faceit pipeline.

Main Components:
    - ARKit retargeting list management
    - Shape key matching and initialization
    - Retargeting map import/export
    - Name scheme management
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import arkit_renaming_operators
from . import retarget_list_operators

# ============================================================
# Imports from arkit_renaming_operators
# ============================================================

from .arkit_renaming_operators import (
    ChangeRetargetingNameScheme,
    RetargetNames,
)

# ============================================================
# Imports from retarget_list_operators
# ============================================================

from .retarget_list_operators import (
    get_active_retarget_list,
    save_active_retarget_list,
    RetargetListBase,
    ResetRegions,
    EditTargetShape,
    RemoveTargetShape,
    ClearTargetShapes,
    SetDefaultRegions,
    InitRetargeting,
    ResetRetargetShapes,
    ImportRetargetMap,
    ExportRetargetMap,
    SetDefaultAmplifyValues,
    SetActiveShapeKeyIndex,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Operators
    'ChangeRetargetingNameScheme',
    'RetargetNames',
    'ResetRegions',
    'EditTargetShape',
    'RemoveTargetShape',
    'ClearTargetShapes',
    'SetDefaultRegions',
    'InitRetargeting',
    'ResetRetargetShapes',
    'ImportRetargetMap',
    'ExportRetargetMap',
    'SetDefaultAmplifyValues',
    'SetActiveShapeKeyIndex',
    
    # Utilities
    'get_active_retarget_list',
    'save_active_retarget_list',
    'RetargetListBase',
]