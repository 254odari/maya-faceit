# __init__.py
# Maya Faceit Plugin - Setup Module
# Version: 1.0.0

"""
Faceit Setup Module for Maya
============================

This module provides setup functionality for the Faceit pipeline.

Main Components:
    - Object registration
    - Vertex group assignment
    - Warning checking
    - Main group assignment with modal picker
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import assign_groups_operators
from . import register_objects_operators
from . import warnings_operators

# ============================================================
# Imports from assign_groups_operators
# ============================================================

from .assign_groups_operators import (
    is_picker_running,
    AssignMainModal,
    AssignMain,
    AssignGroup,
    RemoveFaceitGroup,
    RemoveFaceitGroupList,
    RemoveAllFaceitGroups,
    SelectFaceitGroup,
    DrawFaceitVertexGroup,
    MaskMainObject,
    MaskGroup,
    UnmaskMainObject,
)

# ============================================================
# Imports from register_objects_operators
# ============================================================

from .register_objects_operators import (
    AddFacialPart,
    SelectFacialPart,
    RemoveFacialPart,
    ClearFaceitObjects,
    MoveFaceObject,
    GoToTab,
    OpenWeb,
)

# ============================================================
# Imports from warnings_operators
# ============================================================

from .warnings_operators import (
    WARNINGS_OUT,
    all_verts_in_main_group,
    get_island_count_in_main_group,
    check_warnings_for_face_item,
    CheckWarning,
    DisplayWarning,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Assign groups operators
    'is_picker_running',
    'AssignMainModal',
    'AssignMain',
    'AssignGroup',
    'RemoveFaceitGroup',
    'RemoveFaceitGroupList',
    'RemoveAllFaceitGroups',
    'SelectFaceitGroup',
    'DrawFaceitVertexGroup',
    'MaskMainObject',
    'MaskGroup',
    'UnmaskMainObject',
    
    # Register objects operators
    'AddFacialPart',
    'SelectFacialPart',
    'RemoveFacialPart',
    'ClearFaceitObjects',
    'MoveFaceObject',
    'GoToTab',
    'OpenWeb',
    
    # Warnings operators
    'WARNINGS_OUT',
    'all_verts_in_main_group',
    'get_island_count_in_main_group',
    'check_warnings_for_face_item',
    'CheckWarning',
    'DisplayWarning',
]