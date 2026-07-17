# -*- coding: utf-8 -*-
"""
tools/analysis/types.py

Enums and dataclasses for analysis results.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


# =============================================================================
# ENUMS
# =============================================================================

class AnalysisScope(Enum):
    """Scope of analysis."""
    SCENE = "scene"
    SELECTION = "selection"
    OBJECT = "object"
    REGION = "region"
    CUSTOM = "custom"


class AnalysisCategory(Enum):
    """Category of analysis."""
    SCENE = "scene"
    MESH = "mesh"
    RIG = "rig"
    ANIMATION = "animation"
    PERFORMANCE = "performance"
    DEPENDENCIES = "dependencies"


class AnalysisLevel(Enum):
    """Level of detail for analysis."""
    QUICK = "quick"          # Fast, high-level summary
    STANDARD = "standard"    # Full analysis
    DEEP = "deep"            # Comprehensive, may be slower


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SceneStats:
    """Statistics about the overall scene."""
    total_nodes: int = 0
    total_transforms: int = 0
    total_meshes: int = 0
    total_joints: int = 0
    total_controllers: int = 0
    total_constraints: int = 0
    total_skin_clusters: int = 0
    total_blendshapes: int = 0
    total_references: int = 0
    total_namespaces: int = 0
    total_display_layers: int = 0
    total_render_layers: int = 0
    unknown_nodes: int = 0
    empty_groups: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshStats:
    """Statistics about meshes."""
    total_meshes: int = 0
    total_vertices: int = 0
    total_edges: int = 0
    total_faces: int = 0
    total_triangles: int = 0
    total_ngons: int = 0
    non_manifold_edges: int = 0
    lamina_faces: int = 0
    open_borders: int = 0
    average_vertex_count: float = 0.0
    average_face_count: float = 0.0
    max_vertex_count: int = 0
    max_face_count: int = 0
    meshes_with_history: int = 0
    meshes_with_uvs: int = 0
    meshes_with_normals: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RigStats:
    """Statistics about rigs."""
    total_controllers: int = 0
    total_joints: int = 0
    total_constraints: int = 0
    total_skin_clusters: int = 0
    total_blendshape_nodes: int = 0
    total_blendshape_targets: int = 0
    locked_controllers: int = 0
    hidden_controllers: int = 0
    controllers_with_animation: int = 0
    joints_with_animation: int = 0
    orphan_joints: int = 0
    orphan_controllers: int = 0
    invalid_constraints: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnimationStats:
    """Statistics about animation."""
    total_animated_objects: int = 0
    total_animated_attributes: int = 0
    total_keyframes: int = 0
    total_animation_curves: int = 0
    total_animation_layers: int = 0
    static_channels: int = 0
    empty_curves: int = 0
    time_range_start: float = 0.0
    time_range_end: float = 0.0
    fps: float = 24.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Statistics about performance."""
    fps: float = 0.0
    evaluation_time_ms: float = 0.0
    viewport_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    evaluation_mode: str = "DG"
    gpu_compatible: bool = False
    gpu_enabled: bool = False
    cached_playback_enabled: bool = False
    parallel_evaluation_enabled: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyStats:
    """Statistics about dependencies."""
    total_connections: int = 0
    total_cycles: int = 0
    max_depth: int = 0
    average_depth: float = 0.0
    isolated_nodes: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """A single analysis result."""
    category: AnalysisCategory
    name: str
    value: Any
    level: AnalysisLevel = AnalysisLevel.STANDARD
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    """Complete analysis report."""
    scope: AnalysisScope = AnalysisScope.SCENE
    level: AnalysisLevel = AnalysisLevel.STANDARD
    scene: SceneStats = field(default_factory=SceneStats)
    mesh: MeshStats = field(default_factory=MeshStats)
    rig: RigStats = field(default_factory=RigStats)
    animation: AnimationStats = field(default_factory=AnimationStats)
    performance: PerformanceStats = field(default_factory=PerformanceStats)
    dependencies: DependencyStats = field(default_factory=DependencyStats)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Analysis Report - {self.scope.value}")
        lines.append("=" * 60)
        lines.append(f"  Duration: {self.duration_ms:.2f}ms")
        lines.append(f"  Level: {self.level.value}")
        lines.append("")
        lines.append("  Scene:")
        lines.append(f"    Nodes: {self.scene.total_nodes}")
        lines.append(f"    Meshes: {self.scene.total_meshes}")
        lines.append(f"    Joints: {self.scene.total_joints}")
        lines.append(f"    Controllers: {self.scene.total_controllers}")
        lines.append("")
        lines.append("  Meshes:")
        lines.append(f"    Vertices: {self.mesh.total_vertices:,}")
        lines.append(f"    Faces: {self.mesh.total_faces:,}")
        if self.mesh.total_ngons:
            lines.append(f"    N-Gons: {self.mesh.total_ngons} (!)")
        if self.mesh.non_manifold_edges:
            lines.append(f"    Non-Manifold: {self.mesh.non_manifold_edges} (!)")
        lines.append("")
        lines.append("  Rig:")
        lines.append(f"    Controllers: {self.rig.total_controllers}")
        lines.append(f"    Joints: {self.rig.total_joints}")
        lines.append(f"    Blendshapes: {self.rig.total_blendshape_nodes}")
        lines.append("")
        lines.append("  Animation:")
        lines.append(f"    Animated Objects: {self.animation.total_animated_objects}")
        lines.append(f"    Keyframes: {self.animation.total_keyframes:,}")
        lines.append(f"    Time Range: {self.animation.time_range_start:.1f} - {self.animation.time_range_end:.1f}")
        lines.append("")
        if self.performance.fps > 0:
            lines.append("  Performance:")
            lines.append(f"    FPS: {self.performance.fps:.1f}")
            lines.append(f"    Evaluation Mode: {self.performance.evaluation_mode}")
        if self.warnings:
            lines.append("")
            lines.append("  Warnings:")
            for w in self.warnings[:5]:
                lines.append(f"    - {w}")
        lines.append("=" * 60)
        return "\n".join(lines)