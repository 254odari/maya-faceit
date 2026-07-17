# -*- coding: utf-8 -*-
"""
tools/relax
~~~~~~~~~~~

Dedicated relaxation engine for Maya FaceIT.

Reduces unwanted deformation, smooths noise, and improves distribution
of geometry, weights, and surfaces while preserving overall shape.

Usage:
    from maya_faceit.tools.relax import RelaxTools
    relax = RelaxTools()
    report = relax.mesh("pCube1")
    print(report.summary())
"""

from .types import (
    RelaxMode,
    RelaxAlgorithm,
    FalloffMode,
    WeightType,
    RelaxSettings,
    RelaxReport,
    ValidationResult,
)
from .settings import DEFAULT_RELAX_SETTINGS
from .engine import RelaxEngine
from .mesh import MeshRelaxer
from .vertex import VertexRelaxer
from .surface import SurfaceRelaxer
from .weight import WeightRelaxer
from .uv import UVRelaxer
from .region import RegionRelaxer
from .validation import RelaxValidator
from .utils import RelaxUtils
from .reporter import RelaxReporter

# Main facade
from .relax_tools import RelaxTools, get_relax_tools

# Convenience functions (backward compatibility)
from .relax_tools import (
    relax_mesh,
    relax_vertices,
    relax_surface,
    relax_skin_weights,
    relax_blendshape_weights,
    relax_uvs,
    relax_region,
    set_relax_settings,
)

__all__ = [
    # Types
    "RelaxMode",
    "RelaxAlgorithm",
    "FalloffMode",
    "WeightType",
    "RelaxSettings",
    "RelaxReport",
    "ValidationResult",
    # Settings
    "DEFAULT_RELAX_SETTINGS",
    # Core
    "RelaxEngine",
    # Relaxers
    "MeshRelaxer",
    "VertexRelaxer",
    "SurfaceRelaxer",
    "WeightRelaxer",
    "UVRelaxer",
    "RegionRelaxer",
    # Validation
    "RelaxValidator",
    # Utils
    "RelaxUtils",
    # Reporter
    "RelaxReporter",
    # Main facade
    "RelaxTools",
    "get_relax_tools",
    # Convenience
    "relax_mesh",
    "relax_vertices",
    "relax_surface",
    "relax_skin_weights",
    "relax_blendshape_weights",
    "relax_uvs",
    "relax_region",
    "set_relax_settings",
]