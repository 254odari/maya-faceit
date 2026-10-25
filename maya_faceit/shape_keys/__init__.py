# __init__.py
# Maya Faceit Plugin - Shape Keys Module
# Version: 1.0.0

"""
Faceit Shape Keys Module for Maya
=================================

This module provides shape key management functionality for the Faceit pipeline.

Main Components:
    - Corrective shape key management
    - Shape key application and reordering
    - Test action generation
    - Modifier application with shape keys
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import corrective_shape_keys_operators
from . import corrective_shape_keys_utils
from . import other_shape_key_operators

# ============================================================
# Imports from corrective_shape_keys_operators
# ============================================================

from .corrective_shape_keys_operators import (
    ReevaluateCorrectiveShapeKeys,
    AddCorrectiveShapeKeyToExpression,
    RemoveCorrectiveShapeKey,
    ClearCorrectiveShapeKeys,
)

# ============================================================
# Imports from corrective_shape_keys_utils
# ============================================================

from .corrective_shape_keys_utils import (
    CORRECTIVE_SK_ACTION_NAME,
    reevaluate_corrective_shape_keys,
    mute_corrective_shape_keys,
    get_corrective_sk_action,
    assign_corrective_sk_action,
    keyframe_corrective_sk_action,
    clear_all_corrective_shape_keys,
    remove_corrective_shape_key,
    get_objects_with_corrective_shape_key_for_expression,
)

# ============================================================
# Imports from other_shape_key_operators
# ============================================================

from .other_shape_key_operators import (
    ClearShapeKeyAction,
    ApplyShapeKeysToMesh,
    GenerateTestAction,
    SetShapeKeyRange,
    ReorderKeys,
    ApplyModifierObjectWithShapeKeys,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Corrective shape keys operators
    'ReevaluateCorrectiveShapeKeys',
    'AddCorrectiveShapeKeyToExpression',
    'RemoveCorrectiveShapeKey',
    'ClearCorrectiveShapeKeys',
    
    # Corrective shape keys utilities
    'CORRECTIVE_SK_ACTION_NAME',
    'reevaluate_corrective_shape_keys',
    'mute_corrective_shape_keys',
    'get_corrective_sk_action',
    'assign_corrective_sk_action',
    'keyframe_corrective_sk_action',
    'clear_all_corrective_shape_keys',
    'remove_corrective_shape_key',
    'get_objects_with_corrective_shape_key_for_expression',
    
    # Other shape key operators
    'ClearShapeKeyAction',
    'ApplyShapeKeysToMesh',
    'GenerateTestAction',
    'SetShapeKeyRange',
    'ReorderKeys',
    'ApplyModifierObjectWithShapeKeys',
]