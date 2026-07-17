# -*- coding: utf-8 -*-
"""
tools/optimizer/settings.py

Configuration for the optimizer toolkit.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import OptimizationLevel, EvaluationMode


@dataclass
class OptimizationSettings:
    """Global settings for optimization operations."""

    # Level
    level: OptimizationLevel = OptimizationLevel.STANDARD

    # What to optimize
    optimize_scene: bool = True
    optimize_mesh: bool = True
    optimize_rig: bool = True
    optimize_blendshape: bool = True
    optimize_skin: bool = True
    optimize_deformer: bool = True
    optimize_animation: bool = True
    optimize_evaluation: bool = True

    # Evaluation
    evaluation_mode: EvaluationMode = EvaluationMode.AUTO
    use_cached_playback: bool = True
    enable_parallel_evaluation: bool = True
    gpu_override: bool = False

    # Mesh
    max_vertices_for_display_opt: int = 50000
    merge_vertex_tolerance: float = 0.001

    # Skin
    max_influences: int = 8

    # Animation
    simplify_curves: bool = True
    curve_tolerance: float = 0.001

    # Rig
    remove_unused_attributes: bool = True

    # Blendshape
    remove_zero_weights: bool = True
    enable_gpu_blendshapes: bool = True

    # Behavior
    auto_benchmark: bool = True
    verbose: bool = False
    undo_chunk_name: str = "Optimization Operation"


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_OPTIMIZATION_SETTINGS = OptimizationSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_optimization_settings() -> OptimizationSettings:
    """Get the default optimization settings."""
    return DEFAULT_OPTIMIZATION_SETTINGS


def create_optimization_settings(**kwargs) -> OptimizationSettings:
    """Create an OptimizationSettings instance with overrides."""
    settings = OptimizationSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings