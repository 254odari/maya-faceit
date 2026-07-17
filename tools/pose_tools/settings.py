# -*- coding: utf-8 -*-
"""
tools/pose_tools/settings.py

Configuration for pose tools.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import PoseCategory, PoseBlendMode


@dataclass
class PoseSettings:
    """Global settings for pose operations."""

    # Naming
    naming_prefix: str = ""
    naming_suffix: str = "_pose"

    # Behavior
    auto_normalize: bool = True
    auto_clamp: bool = True
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    use_undo: bool = True
    undo_chunk_name: str = "Pose Operation"

    # Blending
    default_blend_mode: PoseBlendMode = PoseBlendMode.OVERWRITE
    default_blend_factor: float = 0.5

    # Categories
    default_category: PoseCategory = PoseCategory.CUSTOM

    # Storage
    cache_enabled: bool = True
    cache_directory: Optional[str] = None
    library_file: Optional[str] = None

    # Export/Import
    default_export_format: str = "json"  # "json", "xml"


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_POSE_SETTINGS = PoseSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_settings() -> PoseSettings:
    """Get the default settings."""
    return DEFAULT_POSE_SETTINGS


def create_settings(**kwargs) -> PoseSettings:
    """Create a PoseSettings instance with overrides."""
    settings = PoseSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings