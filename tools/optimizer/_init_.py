# -*- coding: utf-8 -*-
"""
tools/optimizer
~~~~~~~~~~~~~~~

Performance optimization engine for Maya FaceIT.

Provides scene, mesh, rig, blendshape, skin, deformer, animation, and
evaluation optimization.

Usage:
    from maya_faceit.tools.optimizer import OptimizerEngine
    opt = OptimizerEngine()
    report = opt.optimize_scene()
    print(report.summary())
"""

from .types import (
    OptimizationType,
    OptimizationLevel,
    EvaluationMode,
    GPUCompatibility,
    OptimizationResult,
    SceneOptimization,
    MeshOptimization,
    RigOptimization,
    BlendshapeOptimization,
    SkinOptimization,
    DeformerOptimization,
    AnimationOptimization,
    EvaluationOptimization,
    OptimizationReport,
)
from .settings import OptimizationSettings, DEFAULT_OPTIMIZATION_SETTINGS
from .engine import OptimizerEngine, optimizer
from .scene import SceneOptimizer
from .mesh import MeshOptimizer
from .rig import RigOptimizer
from .blendshape import BlendshapeOptimizer
from .skin import SkinOptimizer
from .deformer import DeformerOptimizer
from .animation import AnimationOptimizer
from .evaluation import EvaluationOptimizer
from .reporter import OptimizationReporter

__all__ = [
    # Types
    "OptimizationType",
    "OptimizationLevel",
    "EvaluationMode",
    "GPUCompatibility",
    "OptimizationResult",
    "SceneOptimization",
    "MeshOptimization",
    "RigOptimization",
    "BlendshapeOptimization",
    "SkinOptimization",
    "DeformerOptimization",
    "AnimationOptimization",
    "EvaluationOptimization",
    "OptimizationReport",
    # Settings
    "OptimizationSettings",
    "DEFAULT_OPTIMIZATION_SETTINGS",
    # Engine
    "OptimizerEngine",
    "optimizer",
    # Subsystems
    "SceneOptimizer",
    "MeshOptimizer",
    "RigOptimizer",
    "BlendshapeOptimizer",
    "SkinOptimizer",
    "DeformerOptimizer",
    "AnimationOptimizer",
    "EvaluationOptimizer",
    "OptimizationReporter",
]