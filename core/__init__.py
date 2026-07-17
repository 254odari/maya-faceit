"""
core/__init__.py

Core package for Maya Faceit.

This package contains the application framework, project management,
scene management, validation, logging, and the automatic facial rigging pipeline.
"""

# =============================================================================
# Application
# =============================================================================
from .app import FaceitApp, app

# =============================================================================
# Project Management
# =============================================================================
from .project import FaceitProject, project

# =============================================================================
# Preferences
# =============================================================================
from .preferences import Preferences, preferences

# =============================================================================
# Mesh Analysis
# =============================================================================
from .mesh_analyzer import MeshAnalyzer, mesh_analyzer

# =============================================================================
# Scene Management
# =============================================================================
from .scene.scene_manager import SceneManager, scene
from .scene.dependency_graph import DependencyGraph, dependency_graph
from .scene.hierarchy import HierarchyUtils
from .scene.references import ReferenceUtils

# =============================================================================
# Validation
# =============================================================================
from .validation.validation import Validator, validator
from .validation.topology_validator import TopologyValidator, topology_validator
from .validation.rig_validator import RigValidator, rig_validator
from .validation.mesh_validator import MeshValidator, mesh_validator
from .validation.scene_validator import SceneValidator, scene_validator

# =============================================================================
# Pipeline (Rig Building & Automatic Generation)
# =============================================================================
from .pipeline.rig_builder import RigBuilder, RigBuildResult, rig_builder
from .pipeline.rig_pipeline import RigPipeline, PipelineResult, rig_pipeline
from .pipeline.facial_template import (
    ControllerTemplate,
    JointTemplate,
    FacialRegion,
    FacialTemplate,
    create_default_template,
    facial_template,
)
from .pipeline.landmark_solver import Landmark, SolvedLandmarks, LandmarkSolver, landmark_solver

# =============================================================================
# Undo Management
# =============================================================================
from .undo.undo_manager import UndoManager, undo

# =============================================================================
# Logging
# =============================================================================
from .logging.logger import FaceitLogger, log, profile

# =============================================================================
# Naming Conventions
# =============================================================================
from .naming.naming import NamingConvention, naming, LEFT, RIGHT, CENTER, SUFFIX, VALID_SIDES

# =============================================================================
# Symmetry Engine
# =============================================================================
from .symmetry.symmetry import SymmetryEngine, SymmetrySettings, symmetry, AXIS_X, AXIS_Y, AXIS_Z, VALID_AXES

# =============================================================================
# Exceptions (for convenience)
# =============================================================================
from ..exceptions import FaceitError, ValidationError, RiggingError, ApplicationError


__all__ = [
    # App
    "FaceitApp",
    "app",

    # Project
    "FaceitProject",
    "project",

    # Preferences
    "Preferences",
    "preferences",

    # Mesh Analysis
    "MeshAnalyzer",
    "mesh_analyzer",

    # Scene
    "SceneManager",
    "scene",
    "DependencyGraph",
    "dependency_graph",
    "HierarchyUtils",
    "ReferenceUtils",

    # Validation
    "Validator",
    "validator",
    "TopologyValidator",
    "topology_validator",
    "RigValidator",
    "rig_validator",
    "MeshValidator",
    "mesh_validator",
    "SceneValidator",
    "scene_validator",

    # Pipeline
    "RigBuilder",
    "RigBuildResult",
    "rig_builder",
    "RigPipeline",
    "PipelineResult",
    "rig_pipeline",
    "ControllerTemplate",
    "JointTemplate",
    "FacialRegion",
    "FacialTemplate",
    "create_default_template",
    "facial_template",
    "Landmark",
    "SolvedLandmarks",
    "LandmarkSolver",
    "landmark_solver",

    # Undo
    "UndoManager",
    "undo",

    # Logging
    "FaceitLogger",
    "log",
    "profile",

    # Naming
    "NamingConvention",
    "naming",
    "LEFT",
    "RIGHT",
    "CENTER",
    "SUFFIX",
    "VALID_SIDES",

    # Symmetry
    "SymmetryEngine",
    "SymmetrySettings",
    "symmetry",
    "AXIS_X",
    "AXIS_Y",
    "AXIS_Z",
    "VALID_AXES",

    # Exceptions
    "FaceitError",
    "ValidationError",
    "RiggingError",
    "ApplicationError",
]