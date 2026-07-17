# -*- coding: utf-8 -*-
"""
tools/relax/settings.py

Default settings for the relaxation toolkit.
"""

from .types import RelaxSettings


DEFAULT_RELAX_SETTINGS = RelaxSettings()


def get_relax_settings() -> RelaxSettings:
    """Get the default relax settings."""
    return DEFAULT_RELAX_SETTINGS


def create_relax_settings(**kwargs) -> RelaxSettings:
    """Create a RelaxSettings instance with overrides."""
    settings = RelaxSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings