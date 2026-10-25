# __init__.py
# Maya Faceit Plugin - Test Module
# Version: 1.0.0

"""
Faceit Test Module for Maya
===========================

This module provides testing functionality for the Faceit plugin.

Main Components:
    - Unit tests for core functionality
    - Integration tests for workflows
    - Test utilities and helpers
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import test_utils
from . import test_core
from . import test_operators

# ============================================================
# Imports from test_utils
# ============================================================

from .test_utils import (
    TestScene,
    TestData,
    TestAssertions,
    TestRunner,
)

# ============================================================
# Imports from test_core
# ============================================================

from .test_core import (
    test_core_data_initialization,
    test_faceit_objects_registration,
    test_shape_key_creation,
    test_vertex_group_operations,
    test_expression_data_storage,
    run_core_tests,
)

# ============================================================
# Imports from test_operators
# ============================================================

from .test_operators import (
    test_generate_landmarks,
    test_generate_rig,
    test_bind_weights,
    test_expression_animation,
    test_corrective_shape_keys,
    run_operators_tests,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Test utilities
    'TestScene',
    'TestData',
    'TestAssertions',
    'TestRunner',
    
    # Core tests
    'test_core_data_initialization',
    'test_faceit_objects_registration',
    'test_shape_key_creation',
    'test_vertex_group_operations',
    'test_expression_data_storage',
    'run_core_tests',
    
    # Operators tests
    'test_generate_landmarks',
    'test_generate_rig',
    'test_bind_weights',
    'test_expression_animation',
    'test_corrective_shape_keys',
    'run_operators_tests',
]