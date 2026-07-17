"""
tools/mesh/settings.py

Configuration settings and presets for mesh operations in maya_faceit.
Provides reusable setting profiles and validation for MeshSettings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional,Union

from .types import MeshSettings, MeshOperation, NormalMode, UVProjection


# =============================================================================
# PREDEFINED OPERATION PROFILES
# =============================================================================

@dataclass
class OperationProfile:
    """Predefined configuration profile for common operations."""
    name: str
    settings: MeshSettings
    description: str = ""


class MeshOperationProfiles:
    """Collection of recommended setting profiles."""

    @staticmethod
    def default() -> MeshSettings:
        """Standard safe defaults for general mesh operations."""
        return MeshSettings(
            preserve_uvs=True,
            preserve_normals=True,
            preserve_history=False,
            cleanup_after_operation=True,
            maintain_symmetry=False,
            symmetry_tolerance=0.001,
            freeze_transforms=False,
            delete_history_on_finish=False,
            use_undo_chunk=True
        )

    @staticmethod
    def destructive() -> MeshSettings:
        """Settings optimized for heavy destructive operations (remesh, reduce, etc.)."""
        return MeshSettings(
            preserve_uvs=False,
            preserve_normals=True,
            preserve_history=False,
            cleanup_after_operation=True,
            maintain_symmetry=False,
            freeze_transforms=True,
            delete_history_on_finish=True,
            use_undo_chunk=True
        )

    @staticmethod
    def safe() -> MeshSettings:
        """Maximum safety - preserve everything possible."""
        return MeshSettings(
            preserve_uvs=True,
            preserve_normals=True,
            preserve_history=True,
            cleanup_after_operation=False,
            maintain_symmetry=True,
            symmetry_tolerance=0.0005,
            freeze_transforms=False,
            delete_history_on_finish=False,
            use_undo_chunk=True
        )

    @staticmethod
    def retopology() -> MeshSettings:
        """Optimized for retopology and quad-based workflows."""
        return MeshSettings(
            preserve_uvs=True,
            preserve_normals=True,
            preserve_history=False,
            cleanup_after_operation=True,
            maintain_symmetry=True,
            symmetry_tolerance=0.001,
            freeze_transforms=True,
            delete_history_on_finish=True,
            use_undo_chunk=True
        )

    @staticmethod
    def uv_only() -> MeshSettings:
        """UV-specific operations - don't touch geometry."""
        return MeshSettings(
            preserve_uvs=True,
            preserve_normals=True,
            preserve_history=True,
            cleanup_after_operation=False,
            maintain_symmetry=False,
            freeze_transforms=False,
            delete_history_on_finish=False,
            use_undo_chunk=True
        )


# =============================================================================
# GLOBAL DEFAULT SETTINGS
# =============================================================================

DEFAULT_MESH_SETTINGS = MeshOperationProfiles.default()


# =============================================================================
# OPERATION-SPECIFIC DEFAULTS
# =============================================================================

OPERATION_DEFAULTS: Dict[MeshOperation, MeshSettings] = {
    MeshOperation.REMESH: MeshOperationProfiles.destructive(),
    MeshOperation.POLY_REDUCE: MeshOperationProfiles.destructive(),
    MeshOperation.CLEANUP: MeshOperationProfiles.safe(),
    MeshOperation.OPTIMIZE: MeshOperationProfiles.safe(),
    MeshOperation.BEVEL: MeshOperationProfiles.default(),
    MeshOperation.EXTRUDE: MeshOperationProfiles.default(),
    MeshOperation.BRIDGE: MeshOperationProfiles.default(),
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_settings_for_operation(
    operation: Union[MeshOperation, str],
    override: Optional[MeshSettings] = None
) -> MeshSettings:
    """
    Get recommended settings for a specific operation with optional overrides.
    """
    if isinstance(operation, str):
        try:
            operation = MeshOperation[operation.upper()]
        except KeyError:
            operation = MeshOperation.CLEANUP  # fallback

    # Start with operation-specific defaults or general default
    base_settings = OPERATION_DEFAULTS.get(operation, DEFAULT_MESH_SETTINGS)

    if override is None:
        return base_settings

    # Apply overrides
    final_settings = MeshSettings(**base_settings.__dict__)
    for key, value in override.__dict__.items():
        if value is not None:  # Only override if explicitly set
            setattr(final_settings, key, value)

    return final_settings


def validate_settings(settings: MeshSettings) -> tuple[bool, list[str]]:
    """Basic validation of MeshSettings."""
    warnings = []

    if settings.symmetry_tolerance < 0:
        warnings.append("symmetry_tolerance should be positive.")

    if not settings.preserve_uvs and not settings.cleanup_after_operation:
        warnings.append("Disabling preserve_uvs without cleanup may leave invalid UVs.")

    return len(warnings) == 0, warnings


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    "MeshSettings",
    "MeshOperationProfiles",
    "DEFAULT_MESH_SETTINGS",
    "OPERATION_DEFAULTS",
    "get_settings_for_operation",
    "validate_settings",
]