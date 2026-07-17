# -*- coding: utf-8 -*-
"""
export/settings.py

Default export settings.
"""

from .types import ExportSettings


DEFAULT_EXPORT_SETTINGS = ExportSettings()


def get_export_settings() -> ExportSettings:
    """Get the default export settings."""
    return DEFAULT_EXPORT_SETTINGS


def create_export_settings(**kwargs) -> ExportSettings:
    """Create an ExportSettings instance with overrides."""
    settings = ExportSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings