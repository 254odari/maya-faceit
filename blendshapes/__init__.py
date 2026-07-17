"""
blendshapes/__init__.py

Blendshape Package for Maya FaceIT.

This package provides a comprehensive system for creating, managing, driving,
optimizing, and exporting blendshapes for facial rigging and animation.

Submodules:
- blendshape_creator.py   : Create and configure blendshape targets and nodes.
- blendshape_generator.py : Procedural generation of blendshape targets.
- blendshape_driver.py    : Connect blendshapes to controllers, joints, ARKit, etc.
- blendshape_pose.py      : Manage facial poses and expression libraries.
- blendshape_correctives.py: Generate and manage corrective blendshapes.
- blendshape_inbetweens.py: Manage intermediate inbetween targets.
- blendshape_optimizer.py : Optimize blendshapes for runtime performance.
- blendshape_normalize.py : Normalize weights, deltas, and poses.
- blendshape_mirror.py    : Mirror blendshapes across symmetry planes.
- blendshape_validator.py : Validate blendshape data and rigs.
- blendshape_library.py   : Asset library for blendshapes.
- blendshape_manager.py   : Orchestrate all blendshape operations.
- blendshape_builder.py   : Assemble complete blendshape systems.
- blendshape_exporter.py  : Export blendshapes to various formats.
- blendshape_transfer.py  : Transfer blendshapes between meshes.
- blendshape_combiner.py  : Combine multiple blendshapes.
- blendshape_delta.py     : Compute and store vertex deltas.
- arkit_mapper/           : ARKit to blendshape mapping.

All public APIs are re‑exported from this module for convenient access.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

# ---- Part 1: Version & Metadata -----------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"
__license__ = "MIT"

PACKAGE_NAME = "maya_faceit.blendshapes"
VERSION = __version__
AUTHOR = __author__
LICENSE = __license__

# ---- Part 2: Configure Logging ------------------------------------------

logger = logging.getLogger(__name__)

# ---- Part 3: Public Imports ---------------------------------------------

# 3.1 Blendshape Creator
from .blendshape_creator import (
    BlendShapeCreator,
    BlendShapeTarget,
    TargetType as CreatorTargetType,
    CreationMode,
    WeightMode,
    NamingMode,
    CreationResult,
    CreationStatistics,
)

# 3.2 Blendshape Generator
from .blendshape_generator import (
    BlendshapeGenerator,
    GenerationTarget,
    GeneratorType,
    GenerationSettings,
    GenerationResult,
    GenerationStatistics,
    GenerationReport,
)

# 3.3 Blendshape Driver
from .blendshape_driver import (
    BlendshapeDriver,
    DriverDefinition,
    DriverConnection,
    DriverNetwork,
    DriverType,
    EvaluationMode as DriverEvaluationMode,
    DriverSpace,
    BlendMode as DriverBlendMode,
)

# 3.4 Blendshape Pose
from .blendshape_pose import (
    BlendshapePoseManager,
    PoseDefinition,
    PoseType,
    PoseFrame,
    PoseLayer,
    PoseLibrary,
    PosePreset,
    PoseStatistics,
    PoseReport,
    BlendMode as PoseBlendMode,
    MirrorMode as PoseMirrorMode,
    PoseSpace,
)

# 3.5 Blendshape Correctives
from .blendshape_correctives import (
    BlendshapeCorrectiveManager,
    CorrectiveDefinition,
    CorrectiveTarget,
    CorrectivePose,
    CorrectiveRule,
    CorrectiveType,
    TriggerType,
    SolverMode,
    EvaluationMode as CorrectiveEvaluationMode,
)

# 3.6 Blendshape Inbetweens
from .blendshape_inbetweens import (
    BlendshadeInbetweenManager,
    InbetweenDefinition,
    InbetweenPose,
    InterpolationCurve,
    InbetweenMode,
    EvaluationMode as InbetweenEvaluationMode,
    InterpolationType,
    BlendPolicy,
)

# 3.7 Blendshape Optimizer
from .blendshape_optimizer import (
    BlendshapeOptimizer,
    OptimizationSettings,
    OptimizationType,
    OptimizationLevel,
    RuntimeTarget,
    CompressionMode as OptimizerCompressionMode,
)

# 3.8 Blendshape Normalizer
from .blendshape_normalize import (
    BlendshapeNormalizer,
    NormalizationSettings,
    NormalizationType,
    NormalizationMode,
    RangePolicy,
    SymmetryMode as NormalizerSymmetryMode,
)

# 3.9 Blendshape Mirror
from .blendshape_mirror import (
    BlendshapeMirrorManager,
    MirrorSettings,
    MirrorPair,
    VertexMap,
    MirrorDirection,
    MirrorPlane,
    SymmetryMode as MirrorSymmetryMode,
    NamingConvention,
)

# 3.10 Blendshape Validator
from .blendshape_validator import (
    BlendshapeValidator,
    ValidationLevel,
    ValidationReport,
    ValidationIssue,
    MeshValidation,
    TopologyValidation,
    BlendshapeValidation,
    WeightValidation,
    ARKitValidation,
    SceneValidation,
    ValidationStatistics,
)

# 3.11 Blendshape Library
from .blendshape_library import (
    BlendshapeLibraryManager,
    BlendshapeLibrary,
    BlendshapeAsset,
    AssetMetadata,
    AssetCategory,
    AssetCollection,
    AssetVersion,
    LibraryStatistics,
    LibraryReport,
    AssetType as LibraryAssetType,
    LibraryType,
    AssetStatus,
    ThumbnailMode,
)

# 3.12 Blendshape Manager
from .blendshape_manager import (
    BlendshapeManager,
    BlendshapeRegistry,
    BlendshapeScene,
    ManagerMode,
    SceneState,
    AssetType as ManagerAssetType,
    EventType,
)

# 3.13 Blendshape Builder
from .blendshape_builder import (
    BlendshapeBuilder,
    BuildSettings,
    BuildProfile,
    BuildResult,
    BuildStatistics,
    BuildReport,
    BuildMode,
    BuildStrategy,
    BuildTarget,
    BuildStatus,
)

# 3.14 Blendshape Exporter
from .blendshape_exporter import (
    BlendshapeExporter,
    ExportSettings,
    ExportManifest,
    ExportStatistics,
    ExportReport,
    ExportFormat,
    Compression as ExporterCompression,
    MetadataLevel,
    ExportScope,
)

# 3.15 Blendshape Transfer
from .blendshape_transfer import (
    BlendshapeTransferEngine,
    CorrespondenceMap,
    TransferSettings,
    TransferResult,
    TransferStatistics,
    CorrespondenceMethod,
    TransferMode,
)

# 3.16 Blendshape Combiner
from .blendshape_combiner import (
    BlendshapeCombiner,
    BlendshapeCombination,
    CombinationSettings,
    CombinationResult,
    CombinationStatistics,
    CombinationMode,
    BlendMode as CombinerBlendMode,
    CorrectiveMode as CombinerCorrectiveMode,
    ConflictPolicy,
)

# 3.17 Blendshape Delta
from .blendshape_delta import (
    BlendshapeDeltaEngine,
    BlendshapeDelta,
    VertexDelta,
    SparseDelta,
    CompressedDelta,
    DeltaStatistics,
    DeltaReport,
    DeltaFormat,
    CompressionMode as DeltaCompressionMode,
    MirrorMode as DeltaMirrorMode,
    BlendMode as DeltaBlendMode,
)

# 3.18 ARKit Mapper (subpackage)
from .arkit_mapper import (
    ARKitChannel,
    RigTarget,
    ARKitMapping,
    MappingResult,
    ARKitMapper,
    arkit_mapper,
)

# ---- Part 4: Factory Functions (optional) -----------------------------

def create_manager() -> BlendshapeManager:
    """Create a new BlendshapeManager instance."""
    return BlendshapeManager()


def create_builder() -> BlendshapeBuilder:
    """Create a new BlendshapeBuilder instance."""
    return BlendshapeBuilder()


def create_library() -> BlendshapeLibraryManager:
    """Create a new BlendshapeLibraryManager instance."""
    return BlendshapeLibraryManager()


def create_validator() -> BlendshapeValidator:
    """Create a new BlendshapeValidator instance."""
    return BlendshapeValidator()


def create_optimizer() -> BlendshapeOptimizer:
    """Create a new BlendshapeOptimizer instance."""
    return BlendshapeOptimizer()


def create_mirror() -> BlendshapeMirrorManager:
    """Create a new BlendshapeMirrorManager instance."""
    return BlendshapeMirrorManager()


def create_normalizer() -> BlendshapeNormalizer:
    """Create a new BlendshapeNormalizer instance."""
    return BlendshapeNormalizer()


# ---- Part 5: Package Information ---------------------------------------

def package_info() -> Dict[str, Any]:
    """
    Return package metadata and environment information.
    """
    import maya.cmds as cmds
    maya_version = cmds.about(version=True) if hasattr(cmds, 'about') else "Unknown"
    return {
        "package": PACKAGE_NAME,
        "version": VERSION,
        "author": AUTHOR,
        "license": LICENSE,
        "maya_version": maya_version,
        "submodules": [
            "blendshape_creator",
            "blendshape_generator",
            "blendshape_driver",
            "blendshape_pose",
            "blendshape_correctives",
            "blendshape_inbetweens",
            "blendshape_optimizer",
            "blendshape_normalize",
            "blendshape_mirror",
            "blendshape_validator",
            "blendshape_library",
            "blendshape_manager",
            "blendshape_builder",
            "blendshape_exporter",
            "blendshape_transfer",
            "blendshape_combiner",
            "blendshape_delta",
            "arkit_mapper",
        ],
    }


# ---- Part 6: Public API (__all__) ---------------------------------------

__all__ = [
    # ---- Managers ----
    "BlendshapeManager",
    "BlendshapeBuilder",
    "BlendshapeLibraryManager",
    "BlendshapeValidator",
    "BlendshapeOptimizer",
    "BlendshapeMirrorManager",
    "BlendshapeNormalizer",
    "BlendshapeDriver",
    "BlendshapePoseManager",
    "BlendshapeCorrectiveManager",
    "BlendshadeInbetweenManager",
    "BlendshapeTransferEngine",
    "BlendshapeCombiner",
    "BlendshapeDeltaEngine",
    "BlendshapeExporter",
    "BlendshapeGenerator",
    "BlendShapeCreator",

    # ---- Creator ----
    "BlendShapeTarget",
    "CreatorTargetType",
    "CreationMode",
    "WeightMode",
    "NamingMode",
    "CreationResult",
    "CreationStatistics",

    # ---- Generator ----
    "GenerationTarget",
    "GeneratorType",
    "GenerationSettings",
    "GenerationResult",
    "GenerationStatistics",
    "GenerationReport",

    # ---- Driver ----
    "DriverDefinition",
    "DriverConnection",
    "DriverNetwork",
    "DriverType",
    "DriverEvaluationMode",
    "DriverSpace",
    "DriverBlendMode",

    # ---- Pose ----
    "PoseDefinition",
    "PoseType",
    "PoseFrame",
    "PoseLayer",
    "PoseLibrary",
    "PosePreset",
    "PoseStatistics",
    "PoseReport",
    "PoseBlendMode",
    "PoseMirrorMode",
    "PoseSpace",

    # ---- Correctives ----
    "CorrectiveDefinition",
    "CorrectiveTarget",
    "CorrectivePose",
    "CorrectiveRule",
    "CorrectiveType",
    "TriggerType",
    "SolverMode",
    "CorrectiveEvaluationMode",

    # ---- Inbetweens ----
    "InbetweenDefinition",
    "InbetweenPose",
    "InterpolationCurve",
    "InbetweenMode",
    "InbetweenEvaluationMode",
    "InterpolationType",
    "BlendPolicy",

    # ---- Optimizer ----
    "OptimizationSettings",
    "OptimizationType",
    "OptimizationLevel",
    "RuntimeTarget",
    "OptimizerCompressionMode",

    # ---- Normalizer ----
    "NormalizationSettings",
    "NormalizationType",
    "NormalizationMode",
    "RangePolicy",
    "NormalizerSymmetryMode",

    # ---- Mirror ----
    "MirrorSettings",
    "MirrorPair",
    "VertexMap",
    "MirrorDirection",
    "MirrorPlane",
    "MirrorSymmetryMode",
    "NamingConvention",

    # ---- Validator ----
    "ValidationLevel",
    "ValidationReport",
    "ValidationIssue",
    "MeshValidation",
    "TopologyValidation",
    "BlendshapeValidation",
    "WeightValidation",
    "ARKitValidation",
    "SceneValidation",
    "ValidationStatistics",

    # ---- Library ----
    "BlendshapeLibrary",
    "BlendshapeAsset",
    "AssetMetadata",
    "AssetCategory",
    "AssetCollection",
    "AssetVersion",
    "LibraryStatistics",
    "LibraryReport",
    "LibraryAssetType",
    "LibraryType",
    "AssetStatus",
    "ThumbnailMode",

    # ---- Manager ----
    "BlendshapeRegistry",
    "BlendshapeScene",
    "ManagerMode",
    "SceneState",
    "ManagerAssetType",
    "EventType",

    # ---- Builder ----
    "BuildSettings",
    "BuildProfile",
    "BuildResult",
    "BuildStatistics",
    "BuildReport",
    "BuildMode",
    "BuildStrategy",
    "BuildTarget",
    "BuildStatus",

    # ---- Exporter ----
    "ExportSettings",
    "ExportManifest",
    "ExportStatistics",
    "ExportReport",
    "ExportFormat",
    "ExporterCompression",
    "MetadataLevel",
    "ExportScope",

    # ---- Transfer ----
    "CorrespondenceMap",
    "TransferSettings",
    "TransferResult",
    "TransferStatistics",
    "CorrespondenceMethod",
    "TransferMode",

    # ---- Combiner ----
    "BlendshapeCombination",
    "CombinationSettings",
    "CombinationResult",
    "CombinationStatistics",
    "CombinationMode",
    "CombinerBlendMode",
    "CombinerCorrectiveMode",
    "ConflictPolicy",

    # ---- Delta ----
    "BlendshapeDelta",
    "VertexDelta",
    "SparseDelta",
    "CompressedDelta",
    "DeltaStatistics",
    "DeltaReport",
    "DeltaFormat",
    "DeltaCompressionMode",
    "DeltaMirrorMode",
    "DeltaBlendMode",

    # ---- ARKit Mapper ----
    "ARKitChannel",
    "RigTarget",
    "ARKitMapping",
    "MappingResult",
    "ARKitMapper",
    "arkit_mapper",

    # ---- Factories ----
    "create_manager",
    "create_builder",
    "create_library",
    "create_validator",
    "create_optimizer",
    "create_mirror",
    "create_normalizer",

    # ---- Package info ----
    "package_info",

    # ---- Metadata ----
    "PACKAGE_NAME",
    "VERSION",
    "AUTHOR",
    "LICENSE",
]

# ---- Part 7: Module Initialization ------------------------------------

logger.debug("blendshapes package loaded")
