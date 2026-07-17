# -*- coding: utf-8 -*-
"""
tools/controllers/settings.py

Configuration for controller operations.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from .types import ControllerShape, ControllerAxis


@dataclass
class ControllerSettings:
    """Global settings for controller tools."""

    # Creation defaults
    default_shape: ControllerShape = ControllerShape.CIRCLE
    default_size: float = 1.0
    default_axis: ControllerAxis = ControllerAxis.Y
    default_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)

    # Naming
    naming_prefix: str = ""
    naming_suffix: str = "_CTRL"
    use_namespace: bool = True

    # Mirroring
    mirror_translate: bool = True
    mirror_rotate: bool = True
    mirror_scale: bool = False
    mirror_axis: ControllerAxis = ControllerAxis.X

    # Behavior
    auto_lock: bool = False
    auto_hide: bool = False
    freeze_on_create: bool = True
    create_offset_group: bool = True

    # Attributes
    default_attributes: List[str] = field(default_factory=lambda: [
        "tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"
    ])
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    # UI
    show_handles: bool = True
    show_labels: bool = True
    label_offset: float = 1.5

    # Cache
    cache_enabled: bool = True
    cache_directory: Optional[str] = None

    # Undo
    undo_chunk_name: str = "Controller Operation"


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_CONTROLLER_SETTINGS = ControllerSettings()

# -----------------------------------------------------------------------------
# FACTORY FUNCTIONS
# -----------------------------------------------------------------------------

def get_controller_settings() -> ControllerSettings:
    """Get the default controller settings."""
    return DEFAULT_CONTROLLER_SETTINGS


def create_controller_settings(**kwargs) -> ControllerSettings:
    """Create a ControllerSettings instance with overrides."""
    settings = ControllerSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings