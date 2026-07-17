# -*- coding: utf-8 -*-
"""
tools/optimizer/types.py

Enums and dataclasses for the optimizer toolkit.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# =============================================================================
# ENUMS
# =============================================================================

class OptimizationType(Enum):
    """Type of optimization operation."""
    SCENE = "scene"
    MESH = "mesh"
    RIG = "rig"
    BLENDSHAPE = "blendshape"
    SKIN = "skin"
    DEFORMER = "deformer"
    ANIMATION = "animation"
    EVALUATION = "evaluation"


class OptimizationLevel(Enum):
    """Optimization aggressiveness."""
    SAFE = "safe"              # Only safe, non-destructive optimizations
    STANDARD = "standard"      # Balanced optimizations
    AGGRESSIVE = "aggressive"  # Maximum performance, may remove non-essential data


class EvaluationMode(Enum):
    """Maya evaluation mode."""
    DG = "dg"                  # Legacy Dependency Graph
    SERIAL = "serial"          # Serial evaluation
    PARALLEL = "parallel"      # Parallel evaluation
    GPU = "gpu"                # GPU evaluation
    AUTO = "auto"              # Automatically choose best mode


class GPUCompatibility(Enum):
    """GPU compatibility status."""
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class OptimizationResult:
    """Result of a single optimization operation."""
    success: bool = True
    operation: str = ""
    items_processed: int = 0
    items_optimized: int = 0
    items_skipped: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneOptimization:
    """Scene-level optimization results."""
    optimized_nodes: int = 0
    deleted_history: int = 0
    removed_unknown: int = 0
    removed_empty_groups: int = 0
    removed_empty_transforms: int = 0
    evaluation_mode: str = ""
    cached_playback_enabled: bool = False


@dataclass
class MeshOptimization:
    """Mesh optimization results."""
    total_meshes: int = 0
    merged_vertices: int = 0
    deleted_history: int = 0
    optimized_display: int = 0
    optimized_uvs: int = 0


@dataclass
class RigOptimization:
    """Rig optimization results."""
    total_controllers: int = 0
    optimized_controllers: int = 0
    removed_unused_attrs: int = 0
    optimized_shapes: int = 0


@dataclass
class BlendshapeOptimization:
    """Blendshape optimization results."""
    total_blendshapes: int = 0
    optimized_blendshapes: int = 0
    removed_targets: int = 0
    gpu_enabled: int = 0


@dataclass
class SkinOptimization:
    """SkinCluster optimization results."""
    total_skins: int = 0
    optimized_skins: int = 0
    max_influences_set: int = 0
    gpu_enabled: int = 0
    removed_influences: int = 0


@dataclass
class DeformerOptimization:
    """Deformer optimization results."""
    total_deformers: int = 0
    optimized_deformers: int = 0
    deleted_history: int = 0


@dataclass
class AnimationOptimization:
    """Animation optimization results."""
    total_curves: int = 0
    simplified_curves: int = 0
    cached_playback_enabled: bool = False


@dataclass
class EvaluationOptimization:
    """Evaluation manager optimization results."""
    evaluation_mode: str = ""
    gpu_override: bool = False
    parallel_evaluation: bool = False
    cached_playback: bool = False


@dataclass
class OptimizationReport:
    """Complete optimization report."""
    success: bool = True
    type: OptimizationType = OptimizationType.SCENE
    level: OptimizationLevel = OptimizationLevel.STANDARD
    scene: SceneOptimization = field(default_factory=SceneOptimization)
    mesh: MeshOptimization = field(default_factory=MeshOptimization)
    rig: RigOptimization = field(default_factory=RigOptimization)
    blendshape: BlendshapeOptimization = field(default_factory=BlendshapeOptimization)
    skin: SkinOptimization = field(default_factory=SkinOptimization)
    deformer: DeformerOptimization = field(default_factory=DeformerOptimization)
    animation: AnimationOptimization = field(default_factory=AnimationOptimization)
    evaluation: EvaluationOptimization = field(default_factory=EvaluationOptimization)
    fps_before: float = 0.0
    fps_after: float = 0.0
    memory_saved_mb: float = 0.0
    elapsed_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Optimization Report - {self.type.value}")
        lines.append("=" * 60)
        lines.append(f"  Level: {self.level.value}")
        lines.append(f"  Duration: {self.elapsed_time_ms:.2f}ms")
        if self.fps_before > 0 and self.fps_after > 0:
            lines.append(f"  FPS Improvement: {self.fps_before:.1f} → {self.fps_after:.1f}")
        if self.memory_saved_mb > 0:
            lines.append(f"  Memory Saved: {self.memory_saved_mb:.1f} MB")
        lines.append("")
        lines.append("  Optimizations Applied:")
        if self.scene.optimized_nodes:
            lines.append(f"    Scene: {self.scene.optimized_nodes} nodes")
        if self.mesh.merged_vertices:
            lines.append(f"    Mesh: {self.mesh.merged_vertices} vertices merged")
        if self.rig.optimized_controllers:
            lines.append(f"    Rig: {self.rig.optimized_controllers} controllers")
        if self.blendshape.optimized_blendshapes:
            lines.append(f"    Blendshapes: {self.blendshape.optimized_blendshapes} nodes")
        if self.skin.optimized_skins:
            lines.append(f"    Skin: {self.skin.optimized_skins} clusters")
        if self.animation.simplified_curves:
            lines.append(f"    Animation: {self.animation.simplified_curves} curves simplified")
        if self.evaluation.evaluation_mode:
            lines.append(f"    Evaluation Mode: {self.evaluation.evaluation_mode}")
        lines.append("=" * 60)
        return "\n".join(lines)