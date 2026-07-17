# -*- coding: utf-8 -*-
"""
tools/smooth/settings.py

Default settings for the smooth toolkit.
"""

from .types import SmoothSettings, SmoothAlgorithm, SmoothBoundary, SmoothFalloff


DEFAULT_SMOOTH_SETTINGS = SmoothSettings()


def get_smooth_settings() -> SmoothSettings:
    """Get the default smooth settings."""
    return DEFAULT_SMOOTH_SETTINGS


def create_smooth_settings(**kwargs) -> SmoothSettings:
    """Create a SmoothSettings instance with overrides."""
    settings = SmoothSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings