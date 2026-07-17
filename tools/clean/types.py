# -*- coding: utf-8 -*-
"""
tools/clean/types.py

Enums and dataclasses for the clean toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# =============================================================================
# ENUMS
# =============================================================================

class CleanupType(Enum):
    """Type of cleanup operation."""
    SCENE = "scene"
    MESH = "mesh"
    MATERIAL = "material"
    ANIMATION = "animation"
    RIG = "rig"
    BLENDSHAPE = "blendshape"
    NAMESPACE = "namespace"


class CleanupMode(Enum):
    """Cleanup aggressiveness."""
    SAFE = "safe"              # Only remove obviously unused data
    STANDARD = "standard"      # Remove most unnecessary data
    AGGRESSIVE = "aggressive"  # Aggressively optimize, may remove non-essential data


class HistoryMode(Enum):
    """History deletion behavior."""
    ALL = "all"                # Delete all history
    NON_DEFORMER = "non_deformer"  # Delete only non-deformer history
    PRESERVE_DEFORMERS = "preserve_deformers"  # Keep deformer history


class ReferenceMode(Enum):
    """How to handle references."""
    PRESERVE = "preserve"      # Leave references untouched
    FLATTEN = "flatten"        # Flatten references
    IGNORE = "ignore"          # Skip referenced nodes in cleanup


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class CleanupResult:
    """Result of a single cleanup operation."""
    success: bool = True
    operation: str = ""
    items_deleted: int = 0
    items_fixed: int = 0
    items_skipped: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneCleanup:
    """Scene-level cleanup results."""
    deleted_nodes: int = 0
    removed_unknown: int = 0
    removed_orphan: int = 0
    removed_empty_groups: int = 0
    removed_empty_transforms: int = 0
    removed_empty_display_layers: int = 0
    removed_empty_render_layers: int = 0
    deleted_history: int = 0


@dataclass
class MeshCleanup:
    """Mesh cleanup results."""
    total_meshes: int = 0
    merged_vertices: int = 0
    deleted_history: int = 0
    fixed_non_manifold: int = 0
    deleted_lamina: int = 0
    deleted_unused_uv_sets: int = 0
    unlocked_normals: int = 0


@dataclass
class MaterialCleanup:
    """Material cleanup results."""
    removed_materials: int = 0
    removed_textures: int = 0
    removed_shading_groups: int = 0
    removed_file_nodes: int = 0


@dataclass
class AnimationCleanup:
    """Animation cleanup results."""
    removed_static_channels: int = 0
    removed_empty_curves: int = 0
    removed_animation_layers: int = 0
    removed_constraints: int = 0


@dataclass
class RigCleanup:
    """Rig cleanup results."""
    removed_unused_joints: int = 0
    removed_orphan_constraints: int = 0
    removed_orphan_controllers: int = 0
    invalid_display_layers: int = 0


@dataclass
class BlendshapeCleanup:
    """Blendshape cleanup results."""
    total_blendshapes: int = 0
    removed_targets: int = 0
    removed_empty_targets: int = 0
    removed_duplicates: int = 0


@dataclass
class NamespaceCleanup:
    """Namespace cleanup results."""
    removed_namespaces: int = 0
    merged_namespaces: int = 0
    flattened: int = 0


@dataclass
class CleanupReport:
    """Complete cleanup report."""
    success: bool = True
    type: CleanupType = CleanupType.SCENE
    mode: CleanupMode = CleanupMode.STANDARD
    scene: SceneCleanup = field(default_factory=SceneCleanup)
    mesh: MeshCleanup = field(default_factory=MeshCleanup)
    material: MaterialCleanup = field(default_factory=MaterialCleanup)
    animation: AnimationCleanup = field(default_factory=AnimationCleanup)
    rig: RigCleanup = field(default_factory=RigCleanup)
    blendshape: BlendshapeCleanup = field(default_factory=BlendshapeCleanup)
    namespace: NamespaceCleanup = field(default_factory=NamespaceCleanup)
    elapsed_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Cleanup Report - {self.type.value}")
        lines.append("=" * 60)
        lines.append(f"  Mode: {self.mode.value}")
        lines.append(f"  Duration: {self.elapsed_time_ms:.2f}ms")
        lines.append("")
        lines.append("  Cleanup Applied:")
        if self.scene.deleted_nodes:
            lines.append(f"    Scene: {self.scene.deleted_nodes} nodes deleted")
        if self.mesh.merged_vertices:
            lines.append(f"    Mesh: {self.mesh.merged_vertices} vertices merged")
        if self.material.removed_materials:
            lines.append(f"    Materials: {self.material.removed_materials} removed")
        if self.animation.removed_static_channels:
            lines.append(f"    Animation: {self.animation.removed_static_channels} static channels removed")
        if self.rig.removed_unused_joints:
            lines.append(f"    Rig: {self.rig.removed_unused_joints} joints removed")
        if self.blendshape.removed_targets:
            lines.append(f"    Blendshapes: {self.blendshape.removed_targets} targets removed")
        if self.namespace.removed_namespaces:
            lines.append(f"    Namespaces: {self.namespace.removed_namespaces} removed")
        if self.warnings:
            lines.append("")
            lines.append("  Warnings:")
            for w in self.warnings[:5]:
                lines.append(f"    - {w}")
        lines.append("=" * 60)
        return "\n".join(lines)