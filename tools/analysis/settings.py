# -*- coding: utf-8 -*-
"""
tools/analysis/settings.py

Configuration for analysis operations.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from .types import AnalysisLevel, AnalysisScope


@dataclass
class AnalysisSettings:
    """Global settings for analysis operations."""

    # Analysis level
    level: AnalysisLevel = AnalysisLevel.STANDARD
    scope: AnalysisScope = AnalysisScope.SCENE

    # What to analyze
    analyze_scene: bool = True
    analyze_mesh: bool = True
    analyze_rig: bool = True
    analyze_animation: bool = True
    analyze_performance: bool = True
    analyze_dependencies: bool = True

    # Performance benchmarking
    benchmark_frames: int = 10
    benchmark_timeout: float = 5.0

    # Caching
    cache_enabled: bool = True
    cache_directory: Optional[str] = None

    # Reporting
    verbose: bool = False
    include_details: bool = True


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_ANALYSIS_SETTINGS = AnalysisSettings()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_analysis_settings() -> AnalysisSettings:
    """Get the default analysis settings."""
    return DEFAULT_ANALYSIS_SETTINGS


def create_analysis_settings(**kwargs) -> AnalysisSettings:
    """Create an AnalysisSettings instance with overrides."""
    settings = AnalysisSettings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings