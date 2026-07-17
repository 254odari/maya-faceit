"""
tools/mesh/__init__.py

Mesh Processing Package for maya_faceit
Provides a high-level, unified API for all mesh operations.
"""

from __future__ import annotations

# Import core types
from .types import (
    # Enums
    MeshOperation,
    NormalMode,
    UVProjection,
    ComponentType,
    IssueSeverity,
    
    # Data Models
    MeshSettings,
    MeshStatistics,
    MeshIssue,
    MeshReport,
    TopologyFingerprint,
    
    # Type aliases
    MeshSelection,
    ComponentSelection,
)

# Import settings
from .settings import (
    MeshOperationProfiles,
    DEFAULT_MESH_SETTINGS,
    get_settings_for_operation,
    validate_settings,
)

# Import main classes (lazy import in __getattr__ for performance)
__all__ = [
    # Main Public API
    "MeshTools",
    "MeshEngine",
    
    # Types
    "MeshOperation",
    "NormalMode",
    "UVProjection",
    "ComponentType",
    "IssueSeverity",
    "MeshSettings",
    "MeshStatistics",
    "MeshIssue",
    "MeshReport",
    "TopologyFingerprint",
    
    # Settings
    "MeshOperationProfiles",
    "DEFAULT_MESH_SETTINGS",
    "get_settings_for_operation",
    "validate_settings",
    
    # Convenience
    "mesh",           # Global singleton instance
]

# =============================================================================
# LAZY IMPORTS (Prevents circular imports and improves load time)
# =============================================================================

def __getattr__(name: str):
    """Lazy loading of heavy classes."""
    if name == "MeshEngine":
        from .core.engine import MeshEngine
        return MeshEngine
    elif name == "MeshTools":
        from .core.engine import MeshTools
        return MeshTools
    elif name == "mesh":
        from .core.engine import mesh
        return mesh
    
    # Optional: expose submodules
    elif name in {"core", "components", "mapping", "operations", 
                  "analysis", "validation", "repair", "utils"}:
        import importlib
        return importlib.import_module(f".{name}", package=__name__)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# =============================================================================
# PACKAGE METADATA
# =============================================================================

__version__ = "1.0.0"
__author__ = "maya_faceit"
__description__ = "High-performance mesh processing library for Maya"


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

# Allow direct access to common submodules
from . import core
from . import components
from . import mapping
from . import operations
from . import analysis
from . import validation
from . import repair
from . import utils

# Quick access to frequently used classes
try:
    from .components.vertices import VertexTools
    from .components.edges import EdgeTools
    from .components.faces import FaceTools
    from .mapping.uvs import UVTools
    from .mapping.normals import NormalTools
    from .operations.retopology import RetopologyTools
    from .analysis.analyzer import MeshAnalyzer
    from .validation.validator import MeshValidator
    from .repair.repair import MeshRepair
    
    __all__.extend([
        "VertexTools", "EdgeTools", "FaceTools",
        "UVTools", "NormalTools", "RetopologyTools",
        "MeshAnalyzer", "MeshValidator", "MeshRepair"
    ])
except ImportError:
    # Submodules may not be implemented yet - graceful fallback
    pass