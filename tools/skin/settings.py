# -*- coding: utf-8 -*-
"""
tools/skin/settings.py

Configuration for the skin toolkit.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .types import SkinType, NormalizeMode, PruneMode


@dataclass
class SkinSettings:
    """Global settings for skin operations."""
    # General
    max_influences: int = 5
    skin_type: SkinType = SkinType.STANDARD
    normalize_mode: NormalizeMode = NormalizeMode.TOTAL

    # Pruning
    prune_threshold: float = 0.001
    prune_mode: PruneMode = PruneMode.BY_BOTH
    prune_keep_count: int = 4

    # Mirroring
    mirror_translate: bool = True
    mirror_rotate: bool = True
    mirror_scale: bool = False

    # Transfer
    transfer_method: str = "closest_point"  # "closest_point", "barycentric"
    transfer_tolerance: float = 0.001

    # Behavior
    auto_normalize: bool = True
    preserve_locked: bool = True
    use_undo: bool = True
    verbose: bool = False
    undo_chunk_name: str = "Skin Operation"

    # Cache
    cache_enabled: bool = True
    cache_directory: Optional[str] = None


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_SKIN_SETTINGS = SkinSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_skin_settings() -> SkinSettings:
    """Get the default skin settings."""
    return DEFAULT_SKIN_SETTINGS


def create_skin_settings(**kwargs) -> SkinSettings:
    """Create a SkinSettings instance with overrides."""
    settings = SkinSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings