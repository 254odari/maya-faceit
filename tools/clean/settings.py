# -*- coding: utf-8 -*-
"""
tools/clean/settings.py

Configuration for the clean toolkit.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import CleanupMode, HistoryMode, ReferenceMode


@dataclass
class CleanupSettings:
    """Global settings for cleanup operations."""

    # Mode
    mode: CleanupMode = CleanupMode.STANDARD

    # What to clean
    clean_scene: bool = True
    clean_mesh: bool = True
    clean_materials: bool = True
    clean_animation: bool = True
    clean_rig: bool = True
    clean_blendshape: bool = True
    clean_namespace: bool = False

    # Scene
    remove_unknown_nodes: bool = True
    remove_orphan_nodes: bool = True
    remove_empty_groups: bool = True
    remove_empty_transforms: bool = True
    remove_empty_display_layers: bool = True
    remove_empty_render_layers: bool = True
    delete_history: bool = True
    history_mode: HistoryMode = HistoryMode.NON_DEFORMER

    # Mesh
    merge_duplicate_vertices: bool = True
    delete_non_manifold: bool = True
    delete_lamina_faces: bool = True
    delete_unused_uv_sets: bool = True
    unlock_normals: bool = True
    freeze_transforms: bool = False

    # Materials
    remove_unused_materials: bool = True
    remove_unused_textures: bool = True
    remove_unused_shading_groups: bool = True

    # Animation
    remove_static_channels: bool = True
    remove_empty_curves: bool = True
    remove_unused_animation_layers: bool = True
    remove_unused_constraints: bool = True

    # Rig
    remove_unused_joints: bool = True
    remove_orphan_constraints: bool = True
    remove_orphan_controllers: bool = True

    # Blendshape
    remove_empty_targets: bool = True
    remove_duplicate_targets: bool = True
    compress_data: bool = False

    # Namespace
    merge_namespaces: bool = False
    flatten_namespaces: bool = False

    # References
    reference_mode: ReferenceMode = ReferenceMode.PRESERVE
    preserve_references: bool = True

    # Behavior
    auto_backup: bool = False
    backup_directory: Optional[str] = None
    verbose: bool = False
    undo_chunk_name: str = "Scene Cleanup"


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_CLEANUP_SETTINGS = CleanupSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_cleanup_settings() -> CleanupSettings:
    """Get the default cleanup settings."""
    return DEFAULT_CLEANUP_SETTINGS


def create_cleanup_settings(**kwargs) -> CleanupSettings:
    """Create a CleanupSettings instance with overrides."""
    settings = CleanupSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings