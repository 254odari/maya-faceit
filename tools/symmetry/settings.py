# -*- coding: utf-8 -*-
"""
tools/symmetry/settings.py

Default settings for symmetry analysis.
"""

from .types import SymmetrySettings


DEFAULT_SYMMETRY_SETTINGS = SymmetrySettings()


def get_symmetry_settings() -> SymmetrySettings:
    """Get the default symmetry settings."""
    return DEFAULT_SYMMETRY_SETTINGS


def create_symmetry_settings(**kwargs) -> SymmetrySettings:
    """Create a SymmetrySettings instance with overrides."""
    settings = SymmetrySettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings