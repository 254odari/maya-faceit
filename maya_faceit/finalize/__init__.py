# __init__.py
# Maya Faceit Plugin - Finalize Module
# Version: 1.0.0

"""
Faceit Finalize Module for Maya
===============================

This module provides cleanup and finalization functionality for the Faceit pipeline.

Main Components:
    - Object cleanup (remove rigs, weights, vertex groups)
    - Scene cleanup (remove all Faceit data)
    - Property reset
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import finalize_operators

# ============================================================
# Imports from finalize_operators
# ============================================================

from .finalize_operators import (
    CleanUpObjects,
    CleanUpScene,
)

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    'CleanUpObjects',
    'CleanUpScene',
]