# -*- coding: utf-8 -*-
"""
tools/selection_sets/settings.py

Configuration for selection set tools.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SelectionSetSettings:
    """Global settings for selection set operations."""

    # Naming
    naming_prefix: str = ""
    naming_suffix: str = "_set"

    # Behavior
    auto_update: bool = True
    preserve_order: bool = True
    resolve_duplicates: bool = True
    use_undo: bool = True
    undo_chunk_name: str = "Selection Set Operation"

    # Storage
    cache_enabled: bool = True
    cache_directory: Optional[str] = None

    # Export/Import
    default_export_format: str = "json"
    include_metadata: bool = True


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_SETTINGS = SelectionSetSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_settings() -> SelectionSetSettings:
    """Get the default settings."""
    return DEFAULT_SETTINGS


def create_settings(**kwargs) -> SelectionSetSettings:
    """Create a SelectionSetSettings instance with overrides."""
    settings = SelectionSetSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings