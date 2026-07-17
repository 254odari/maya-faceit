# -*- coding: utf-8 -*-
"""
validation
~~~~~~~~~~

Scene validation toolkit for Maya FaceIT.

Provides:
- Generic scene/node validation (validator.py)
- Symmetry validation (symmetry.py)
- Naming convention validation (naming.py)

Usage:
    from maya_faceit.validation import Validator, SymmetryValidator, NamingValidator
    validator = Validator()
    validator.validate_scene()
"""

from .naming import Validator, ValidationResult, IssueSeverity
from .symmetry import SymmetryValidator, SymmetryIssue
from .naming import NamingValidator, NamingIssue

__all__ = [
    # Validator
    "Validator",
    "ValidationResult",
    "IssueSeverity",
    # Symmetry
    "SymmetryValidator",
    "SymmetryIssue",
    # Naming
    "NamingValidator",
    "NamingIssue",
]