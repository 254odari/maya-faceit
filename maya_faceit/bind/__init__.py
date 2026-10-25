# __init__.py
# Maya Faceit Plugin - Bind Module
# Version: 1.0.0

"""
Faceit Bind Module for Maya
===========================

This module provides binding functionality for the Faceit pipeline.

Main Components:
    - Smart binding with automatic weight optimization
    - Weight transfer between objects
    - Faceit group management
    - Corrective smoothing
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import bind_operators
from . import bind_utils

# ============================================================
# Imports from bind_operators
# ============================================================

from .bind_operators import (
    SmartBind,
    PairArmature,
    UnbindFacial,
    CorrectiveSmooth,
)

# ============================================================
# Imports from bind_utils
# ============================================================

from .bind_utils import (
    remove_weights_from_non_facial_geometry,
    scale_bind_objects,
    data_transfer_vertex_groups,
    split_by_faceit_groups,
    split_object,
    create_facial_hull,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Operators
    'SmartBind',
    'PairArmature',
    'UnbindFacial',
    'CorrectiveSmooth',
    
    # Utilities
    'remove_weights_from_non_facial_geometry',
    'scale_bind_objects',
    'data_transfer_vertex_groups',
    'split_by_faceit_groups',
    'split_object',
    'create_facial_hull',
]