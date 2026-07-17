# -*- coding: utf-8 -*-
"""
tools/analysis
~~~~~~~~~~~~~~

Central analysis engine for Maya FaceIT.

Provides performance analysis, mesh analysis, rig analysis,
animation analysis, scene analysis, and dependency analysis.

Usage:
    from maya_faceit.tools.analysis import AnalysisEngine
    analysis = AnalysisEngine()
    report = analysis.analyze_scene()
    print(report.summary())
"""

from .types import (
    AnalysisScope,
    AnalysisCategory,
    AnalysisLevel,
    AnalysisResult,
    SceneStats,
    MeshStats,
    RigStats,
    AnimationStats,
    PerformanceStats,
    DependencyStats,
    AnalysisReport,
)
from .settings import AnalysisSettings, DEFAULT_ANALYSIS_SETTINGS
from .engine import AnalysisEngine, analysis
from .scene import SceneAnalyzer
from .mesh import MeshAnalyzer
from .rig import RigAnalyzer
from .animation import AnimationAnalyzer
from .performance import PerformanceAnalyzer
from .dependencies import DependencyAnalyzer
from .reporter import AnalysisReporter

__all__ = [
    # Types
    "AnalysisScope",
    "AnalysisCategory",
    "AnalysisLevel",
    "AnalysisResult",
    "SceneStats",
    "MeshStats",
    "RigStats",
    "AnimationStats",
    "PerformanceStats",
    "DependencyStats",
    "AnalysisReport",
    # Settings
    "AnalysisSettings",
    "DEFAULT_ANALYSIS_SETTINGS",
    # Engine
    "AnalysisEngine",
    "analysis",
    # Analyzers
    "SceneAnalyzer",
    "MeshAnalyzer",
    "RigAnalyzer",
    "AnimationAnalyzer",
    "PerformanceAnalyzer",
    "DependencyAnalyzer",
    # Reporter
    "AnalysisReporter",
]