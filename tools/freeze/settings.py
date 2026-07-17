# -*- coding: utf-8 -*-
"""
tools/freeze/settings.py

Configuration for the freeze toolkit.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import FreezeMode, FreezeScope, FreezeChannel


@dataclass
class FreezeSettings:
    """Global settings for freeze operations."""

    # Mode
    mode: FreezeMode = FreezeMode.SAFE
    scope: FreezeScope = FreezeScope.SELECTED

    # Channels to freeze
    freeze_translate: bool = True
    freeze_rotate: bool = True
    freeze_scale: bool = True
    freeze_pivots: bool = False

    # Preservation
    preserve_animation: bool = True
    preserve_constraints: bool = True
    preserve_skinning: bool = True
    preserve_blendshapes: bool = True
    preserve_custom_attributes: bool = True

    # Behavior
    create_offset_group: bool = True
    auto_backup: bool = False
    verbose: bool = False
    undo_chunk_name: str = "Freeze Operation"

    # Cache
    cache_enabled: bool = True
    cache_directory: Optional[str] = None


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_FREEZE_SETTINGS = FreezeSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_freeze_settings() -> FreezeSettings:
    """Get the default freeze settings."""
    return DEFAULT_FREEZE_SETTINGS


def create_freeze_settings(**kwargs) -> FreezeSettings:
    """Create a FreezeSettings instance with overrides."""
    settings = FreezeSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings