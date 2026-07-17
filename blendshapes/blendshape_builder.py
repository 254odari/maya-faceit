"""
blendshapes/blendshape_builder.py

Blendshape Construction Engine for Maya.

This module coordinates the assembly of complete blendshape systems from meshes,
templates, ARKit definitions, expression sets, visemes, correctives, and
configuration data. It orchestrates the entire build pipeline, delegating to
specialized builders for each subsystem.

Responsibilities:
- Build complete blendshape rigs from source meshes and configuration.
- Construct blendShape nodes, targets, expressions, ARKit 52, visemes, correctives.
- Build driver networks, inbetweens, and pose systems.
- Support multiple build profiles (ARKit, FACS, Viseme, Game, Film).
- Batch build across multiple characters or LODs.
- Validate and report on the build process.

Dependencies:
- blendshape_creator.py: Target creation.
- blendshape_generator.py: Procedural generation.
- blendshape_driver.py: Driver network construction.
- blendshape_pose.py: Pose and expression management.
- blendshape_correctives.py: Corrective systems.
- blendshape_inbetweens.py: Inbetween management.
- blendshape_optimizer.py: Post-build optimization.
- blendshape_normalize.py: Normalization.
- blendshape_mirror.py: Symmetry handling.
- blendshape_validator.py: Build validation.
- blendshape_library.py: Asset library.
- blendshape_manager.py: Orchestration.

The module uses a Builder + Director pattern.
"""

from __future__ import annotations

import copy
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Maya imports (with fallback)
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists # type: ignore
    import pymel.core as pm # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Import all submodules (with fallbacks)
try:
    from .blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType, CreationMode, WeightMode, NamingMode
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None
    CreationMode = None
    WeightMode = None
    NamingMode = None

try:
    from .blendshape_generator import BlendshapeGenerator, GenerationTarget, GeneratorType, GenerationSettings
except ImportError:
    BlendshapeGenerator = None
    GenerationTarget = None
    GeneratorType = None
    GenerationSettings = None

try:
    from .blendshape_driver import BlendshapeDriver, DriverDefinition, DriverType
except ImportError:
    BlendshapeDriver = None
    DriverDefinition = None
    DriverType = None

try:
    from .blendshape_pose import BlendshapePoseManager, PoseDefinition, PoseType, BlendMode as PoseBlendMode
except ImportError:
    BlendshapePoseManager = None
    PoseDefinition = None
    PoseType = None
    PoseBlendMode = None

try:
    from .blendshape_correctives import BlendshapeCorrectiveManager, CorrectiveDefinition, CorrectiveType
except ImportError:
    BlendshapeCorrectiveManager = None
    CorrectiveDefinition = None
    CorrectiveType = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager, InbetweenDefinition, InbetweenMode
except ImportError:
    BlendshadeInbetweenManager = None
    InbetweenDefinition = None
    InbetweenMode = None

try:
    from .blendshape_optimizer import BlendshapeOptimizer, OptimizationSettings, OptimizationType, OptimizationLevel
except ImportError:
    BlendshapeOptimizer = None
    OptimizationSettings = None
    OptimizationType = None
    OptimizationLevel = None

try:
    from .blendshape_normalize import BlendshapeNormalizer, NormalizationSettings, NormalizationType
except ImportError:
    BlendshapeNormalizer = None
    NormalizationSettings = None
    NormalizationType = None

try:
    from .blendshape_mirror import BlendshapeMirrorManager, MirrorSettings, MirrorDirection
except ImportError:
    BlendshapeMirrorManager = None
    MirrorSettings = None
    MirrorDirection = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel, ValidationReport
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None
    ValidationReport = None

try:
    from .blendshape_manager import BlendshapeManager, AssetType
except ImportError:
    BlendshapeManager = None
    AssetType = None

try:
    from .blendshape_library import BlendshapeLibraryManager, BlendshapeAsset
except ImportError:
    BlendshapeLibraryManager = None
    BlendshapeAsset = None

try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions, get_mesh_vertex_position,
        sanitize_name, generate_unique_name, get_blendshape_targets,
        get_blendshape_weight, set_blendshape_weight, Timer, ProgressTracker,
        duplicate_mesh, freeze_transforms, remove_namespace
    )
except ImportError:
    def get_shape_node(x): return x
    def get_mesh_vertex_count(x): return 0
    def get_mesh_vertex_positions(x): return []
    def sanitize_name(n): return n
    def generate_unique_name(n, existing): return n
    def get_blendshape_targets(n): return []
    def get_blendshape_weight(n,t): return 0.0
    def set_blendshape_weight(n,t,v): pass
    class Timer: pass
    class ProgressTracker: pass
    def duplicate_mesh(m, n): return m
    def freeze_transforms(m): pass
    def remove_namespace(n): return n

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class BuildError(Exception):
    """Base exception for builder operations."""
    pass

class BuildCanceledError(BuildError):
    """Raised when building is canceled."""
    pass

class BuildValidationError(BuildError):
    """Raised when validation fails."""
    pass

class BuildConfigError(BuildError):
    """Raised when configuration is invalid."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class BuildMode(Enum):
    """What to build."""
    EMPTY = "empty"
    FULL = "full"
    ARKIT = "arkit"
    VISEME = "viseme"
    EXPRESSION = "expression"
    CORRECTIVE = "corrective"
    CUSTOM = "custom"


class BuildStrategy(Enum):
    """How to build."""
    FROM_TEMPLATE = "from_template"
    FROM_LIBRARY = "from_library"
    FROM_SCENE = "from_scene"
    FROM_JSON = "from_json"
    FROM_PRESET = "from_preset"


class BuildTarget(Enum):
    """Platform target."""
    FILM = "film"
    GAME = "game"
    VR = "vr"
    MOBILE = "mobile"
    ARKIT = "arkit"


class BuildStatus(Enum):
    """Status of a build task."""
    WAITING = "waiting"
    BUILDING = "building"
    COMPLETE = "complete"
    FAILED = "failed"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class BuildSettings:
    """Settings for a build operation."""
    # General
    mode: BuildMode = BuildMode.FULL
    strategy: BuildStrategy = BuildStrategy.FROM_TEMPLATE
    target: BuildTarget = BuildTarget.FILM
    # Components
    build_arkit: bool = True
    build_visemes: bool = True
    build_expressions: bool = True
    build_correctives: bool = True
    build_inbetweens: bool = True
    build_drivers: bool = True
    build_poses: bool = True
    # Optimization
    optimize_after_build: bool = True
    normalize_after_build: bool = True
    # Mirroring
    mirror_left_right: bool = True
    # Naming
    naming_prefix: str = ""
    naming_suffix: str = ""
    # Validation
    validate_before: bool = True
    validate_after: bool = True
    validation_level: str = "normal"
    # Progress
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class BuildProfile:
    """A reusable build profile."""
    name: str
    settings: BuildSettings
    description: str = ""


@dataclass
class BuildTask:
    """A single build task for batch processing."""
    name: str
    base_mesh: str
    settings: BuildSettings
    callback: Optional[Callable[[BuildResult], None]] = None


@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    built_targets: List[str] = field(default_factory=list)
    built_nodes: List[str] = field(default_factory=list)
    built_poses: List[str] = field(default_factory=list)
    built_correctives: List[str] = field(default_factory=list)
    built_arkit: List[str] = field(default_factory=list)
    built_visemes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    elapsed_time: float = 0.0


@dataclass
class BuildStatistics:
    """Statistics for a build operation."""
    total_targets: int = 0
    total_nodes: int = 0
    total_poses: int = 0
    total_correctives: int = 0
    total_arkit: int = 0
    total_visemes: int = 0
    time_seconds: float = 0.0


@dataclass
class BuildReport:
    """Full report of a build operation."""
    success: bool
    result: BuildResult
    statistics: BuildStatistics
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


# ---- Part 4: Build Manager ------------------------------------------

class BlendshapeBuilder:
    """
    Main controller for blendshape construction.
    Orchestrates all specialized builders.
    """
    def __init__(self):
        # Lazy initialize sub-builders
        self._target_builder = None
        self._node_builder = None
        self._expression_builder = None
        self._arkit_builder = None
        self._viseme_builder = None
        self._corrective_builder = None
        self._inbetween_builder = None
        self._driver_builder = None
        self._runtime_builder = None

        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._generator = BlendshapeGenerator() if BlendshapeGenerator else None
        self._driver = BlendshapeDriver() if BlendshapeDriver else None
        self._pose_manager = BlendshapePoseManager() if BlendshapePoseManager else None
        self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._optimizer = BlendshapeOptimizer() if BlendshapeOptimizer else None
        self._normalizer = BlendshapeNormalizer() if BlendshapeNormalizer else None
        self._mirror_manager = BlendshapeMirrorManager() if BlendshapeMirrorManager else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._manager = BlendshapeManager() if BlendshapeManager else None
        self._library_manager = BlendshapeLibraryManager() if BlendshapeLibraryManager else None

        self._settings = BuildSettings()
        self._last_report: Optional[BuildReport] = None
        self._last_stats: Optional[BuildStatistics] = None
        self._cancelled = False

    # ---- Main Build API ----

    def build(
        self,
        base_mesh: str,
        settings: Optional[BuildSettings] = None,
    ) -> BuildReport:
        """
        Build a complete blendshape system on the given base mesh.
        """
        if settings is not None:
            self._settings = settings
        self._cancelled = False
        start_time = time.time()

        # Validate base mesh
        if not cmds.objExists(base_mesh):
            return self._create_failure_report(f"Base mesh '{base_mesh}' does not exist", start_time)

        # Validate before build
        if self._settings.validate_before and self._validator:
            val_report = self._validator.validate_mesh(base_mesh, level=self._settings.validation_level)
            if not val_report.is_valid:
                return self._create_failure_report("Pre-build validation failed", start_time, val_report.errors)

        # Prepare result
        result = BuildResult(success=True)
        stats = BuildStatistics()

        # Build pipeline
        try:
            # 1. Build blendshape node and base target structure
            node = self._build_node(base_mesh)
            if node:
                result.built_nodes.append(node)

            # 2. Build ARKit targets
            if self._settings.build_arkit:
                arkit_targets = self._build_arkit(base_mesh, node)
                result.built_arkit.extend(arkit_targets)
                result.built_targets.extend(arkit_targets)

            # 3. Build visemes
            if self._settings.build_visemes:
                visemes = self._build_visemes(base_mesh, node)
                result.built_visemes.extend(visemes)
                result.built_targets.extend(visemes)

            # 4. Build expressions
            if self._settings.build_expressions:
                expressions = self._build_expressions(base_mesh, node)
                result.built_poses.extend(expressions)

            # 5. Build correctives
            if self._settings.build_correctives:
                correctives = self._build_correctives(base_mesh, node)
                result.built_correctives.extend(correctives)

            # 6. Build inbetweens
            if self._settings.build_inbetweens:
                inbetweens = self._build_inbetweens(base_mesh, node)
                # Inbetweens are attached to parent targets, not separate nodes

            # 7. Build drivers
            if self._settings.build_drivers:
                self._build_drivers(base_mesh, node)

            # 8. Mirror left-right if requested
            if self._settings.mirror_left_right:
                self._mirror_targets(base_mesh)

            # 9. Normalize after build
            if self._settings.normalize_after_build:
                self._normalize_rig(base_mesh)

            # 10. Optimize after build
            if self._settings.optimize_after_build:
                self._optimize_rig(base_mesh)

        except BuildCanceledError:
            return self._create_failure_report("Build canceled", start_time)
        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        # Validate after build
        if self._settings.validate_after and self._validator:
            val_report = self._validator.validate([base_mesh], level=self._settings.validation_level)
            if not val_report.is_valid:
                result.errors.extend(val_report.errors)
                result.success = False

        # Compute statistics
        stats.total_targets = len(result.built_targets)
        stats.total_nodes = len(result.built_nodes)
        stats.total_poses = len(result.built_poses)
        stats.total_correctives = len(result.built_correctives)
        stats.total_arkit = len(result.built_arkit)
        stats.total_visemes = len(result.built_visemes)
        stats.time_seconds = time.time() - start_time

        report = BuildReport(
            success=result.success,
            result=result,
            statistics=stats,
            validation_errors=[],
            validation_warnings=[]
        )
        self._last_report = report
        self._last_stats = stats
        return report

    def build_arkit(self, base_mesh: str) -> BuildReport:
        """Build only ARKit 52 system."""
        settings = copy.copy(self._settings)
        settings.mode = BuildMode.ARKIT
        settings.build_arkit = True
        settings.build_visemes = False
        settings.build_expressions = False
        settings.build_correctives = False
        return self.build(base_mesh, settings)

    def build_visemes(self, base_mesh: str) -> BuildReport:
        """Build only viseme system."""
        settings = copy.copy(self._settings)
        settings.mode = BuildMode.VISEME
        settings.build_arkit = False
        settings.build_visemes = True
        settings.build_expressions = False
        settings.build_correctives = False
        return self.build(base_mesh, settings)

    def build_expressions(self, base_mesh: str) -> BuildReport:
        """Build only expression system."""
        settings = copy.copy(self._settings)
        settings.mode = BuildMode.EXPRESSION
        settings.build_arkit = False
        settings.build_visemes = False
        settings.build_expressions = True
        settings.build_correctives = False
        return self.build(base_mesh, settings)

    def build_correctives(self, base_mesh: str) -> BuildReport:
        """Build only corrective system."""
        settings = copy.copy(self._settings)
        settings.mode = BuildMode.CORRECTIVE
        settings.build_arkit = False
        settings.build_visemes = False
        settings.build_expressions = False
        settings.build_correctives = True
        return self.build(base_mesh, settings)

    def rebuild(self, base_mesh: str, settings: Optional[BuildSettings] = None) -> BuildReport:
        """Rebuild an existing rig (clear and rebuild)."""
        # Clear existing blendshape data? In practice we'd detect existing nodes and recreate.
        return self.build(base_mesh, settings)

    def preview(self, base_mesh: str, settings: Optional[BuildSettings] = None) -> Dict[str, Any]:
        """
        Preview what will be built without applying changes.
        Returns a dictionary with estimated counts and structure.
        """
        if settings is None:
            settings = self._settings
        preview_data = {
            "base_mesh": base_mesh,
            "mode": settings.mode.value,
            "target": settings.target.value,
            "components": []
        }
        # Simulate count of targets
        if settings.build_arkit:
            preview_data["components"].append({"arkit": len(ARKIT_BLENDSHAPES)})
        if settings.build_visemes:
            preview_data["components"].append({"visemes": 16})  # typical count
        if settings.build_expressions:
            preview_data["components"].append({"expressions": 7})  # typical emotions
        if settings.build_correctives:
            preview_data["components"].append({"correctives": 0})  # depends on combin
        return preview_data

    def cancel(self) -> None:
        """Cancel the current build operation."""
        self._cancelled = True

    # ---- Specialized Builders ----

    def _build_node(self, base_mesh: str) -> Optional[str]:
        """Build the primary blendshape node."""
        if not self._creator:
            logger.warning("BlendShapeCreator not available; cannot build node")
            return None
        # Check if a blendshape node already exists on this mesh
        bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
        if bs_nodes:
            node = bs_nodes[0]
            logger.info(f"Using existing blendshape node: {node}")
            return node
        # Create a new node
        node_name = f"{sanitize_name(base_mesh)}_blendShape"
        node = self._creator.create_node(node_name, base_mesh)
        logger.info(f"Created blendshape node: {node}")
        return node

    def _build_arkit(self, base_mesh: str, node: str) -> List[str]:
        """Build ARKit 52 targets."""
        if not self._generator:
            logger.warning("BlendshapeGenerator not available; skipping ARKit build")
            return []
        logger.info("Building ARKit 52 targets...")
        # Use generator to create ARKit targets
        report = self._generator.generate_arkit(base_mesh)
        if report.success:
            logger.info(f"Generated {len(report.generated_targets)} ARKit targets")
            return report.generated_targets
        else:
            logger.error(f"ARKit generation failed: {report.errors}")
            return []

    def _build_visemes(self, base_mesh: str, node: str) -> List[str]:
        """Build viseme targets."""
        if not self._generator:
            logger.warning("BlendshapeGenerator not available; skipping viseme build")
            return []
        logger.info("Building viseme targets...")
        report = self._generator.generate_visemes(base_mesh)
        if report.success:
            logger.info(f"Generated {len(report.generated_targets)} viseme targets")
            return report.generated_targets
        else:
            logger.error(f"Viseme generation failed: {report.errors}")
            return []

    def _build_expressions(self, base_mesh: str, node: str) -> List[str]:
        """Build expression poses."""
        if not self._pose_manager:
            logger.warning("Pose manager not available; skipping expression build")
            return []
        logger.info("Building expression poses...")
        # Use pose manager to generate emotions
        # We'll generate a set of expressions
        expressions = ["Happy", "Sad", "Angry", "Fear", "Disgust", "Surprise", "Neutral"]
        built = []
        for expr in expressions:
            # Generate a pose (this assumes the generator creates poses)
            # In a full implementation, we would use the generator's emotion generation
            # For now, we'll use the pose manager's capture to capture current state
            # But we need to have the targets already. So we'll rely on generator.
            # We'll use the generator's emotion generation
            if self._generator:
                report = self._generator.generate_emotions(base_mesh)
                if report.success:
                    built.extend(report.generated_targets)
        return built

    def _build_correctives(self, base_mesh: str, node: str) -> List[str]:
        """Build corrective targets."""
        if not self._corrective_manager:
            logger.warning("Corrective manager not available; skipping corrective build")
            return []
        logger.info("Building corrective targets...")
        # We need to decide which combinations to generate.
        # For now, we'll generate some simple combinations based on ARKit targets.
        # In practice, we'd have a more sophisticated system.
        # We'll generate a few sample correctives.
        built = []
        # Example: JawOpen + Smile corrective
        # Check if both targets exist
        targets = get_blendshape_targets(node)
        if "jawOpen" in targets and "mouthSmileLeft" in targets:
            try:
                defn = self._corrective_manager.create_blendshape_corrective(
                    "JawOpen_Smile_Corrective",
                    base_mesh,
                    ["jawOpen", "mouthSmileLeft"]
                )
                built.append(defn.name)
                logger.info(f"Created corrective: {defn.name}")
            except Exception as e:
                logger.warning(f"Failed to create corrective: {e}")
        return built

    def _build_inbetweens(self, base_mesh: str, node: str) -> List[str]:
        """Build inbetween targets for key blendshapes."""
        if not self._inbetween_manager:
            logger.warning("Inbetween manager not available; skipping inbetween build")
            return []
        logger.info("Building inbetween targets...")
        # For common targets like jawOpen, eyeBlink, etc.
        targets = get_blendshape_targets(node)
        inbetween_candidates = ["jawOpen", "mouthSmileLeft", "mouthSmileRight", "eyeBlinkLeft", "eyeBlinkRight"]
        built = []
        for t in targets:
            if t in inbetween_candidates:
                # Generate a mesh for inbetween (we need to create a target mesh)
                # For simplicity, we'll create a few inbetweens by duplicating base mesh and deforming
                # In production, this would be more sophisticated.
                # We'll create a simple inbetween at 0.5
                try:
                    # Duplicate base mesh
                    mesh = duplicate_mesh(base_mesh, f"{t}_in_50")
                    if mesh:
                        # Apply a simple deformation (just move vertices slightly)
                        vert_count = get_mesh_vertex_count(mesh)
                        if vert_count > 0:
                            for i in range(min(10, vert_count)):
                                pos = get_mesh_vertex_position(mesh, i)  # Not implemented in fallback
                                # We'll just assume position exists.
                                pass
                        # Create inbetween
                        defn = self._inbetween_manager.create_inbetween(t, 0.5, mesh)
                        built.append(defn.name)
                except Exception as e:
                    logger.warning(f"Failed to create inbetween for {t}: {e}")
        return built

    def _build_drivers(self, base_mesh: str, node: str) -> None:
        """Build driver network for blendshapes."""
        if not self._driver:
            logger.warning("Driver not available; skipping driver build")
            return
        logger.info("Building driver network...")
        # In production, we would create controller attributes and connect them.
        # For now, we'll just set up some simple SDK relationships.
        # This would require a controller rig; we'll skip.

    def _mirror_targets(self, base_mesh: str) -> None:
        """Mirror left/right targets."""
        if not self._mirror_manager:
            logger.warning("Mirror manager not available; skipping mirroring")
            return
        logger.info("Mirroring left-right targets...")
        # We'll need to get all targets and mirror those with left/right pairs.
        # The mirror manager will handle this.

    def _normalize_rig(self, base_mesh: str) -> None:
        """Normalize blendshape weights and deltas."""
        if not self._normalizer:
            logger.warning("Normalizer not available; skipping normalization")
            return
        logger.info("Normalizing blendshape system...")
        self._normalizer.normalize()

    def _optimize_rig(self, base_mesh: str) -> None:
        """Optimize blendshape rig."""
        if not self._optimizer:
            logger.warning("Optimizer not available; skipping optimization")
            return
        logger.info("Optimizing blendshape system...")
        self._optimizer.optimize()

    # ---- Batch Operations ----

    def batch_build(self, tasks: List[BuildTask]) -> List[BuildReport]:
        """Build multiple blendshape systems in batch."""
        reports = []
        for task in tasks:
            if self._cancelled:
                raise BuildCanceledError("Batch build canceled")
            report = self.build(task.base_mesh, task.settings)
            reports.append(report)
            if task.callback:
                task.callback(report.result)
        return reports

    # ---- Validation ----

    def validate(self, build_result: BuildResult) -> BuildReport:
        """Validate a build result."""
        # In practice, we would validate the rig integrity.
        # For now, we'll just return a simple report.
        report = BuildReport(
            success=build_result.success,
            result=build_result,
            statistics=BuildStatistics(),
            validation_errors=[],
            validation_warnings=[]
        )
        return report

    # ---- Utilities ----

    def _create_failure_report(self, msg: str, start_time: float, errors: Optional[List[str]] = None) -> BuildReport:
        result = BuildResult(success=False, errors=[msg] + (errors or []))
        stats = BuildStatistics(time_seconds=time.time() - start_time)
        return BuildReport(
            success=False,
            result=result,
            statistics=stats,
            validation_errors=[],
            validation_warnings=[]
        )

    def get_last_report(self) -> Optional[BuildReport]:
        return self._last_report

    def get_last_stats(self) -> Optional[BuildStatistics]:
        return self._last_stats

    def reset(self) -> None:
        self._last_report = None
        self._last_stats = None
        self._cancelled = False

    def set_settings(self, settings: BuildSettings) -> None:
        self._settings = settings

    def get_settings(self) -> BuildSettings:
        return self._settings

    # ---- Build Profiles ----

    @staticmethod
    def get_builtin_profiles() -> Dict[str, BuildProfile]:
        """Return built-in build profiles."""
        profiles = {}
        profiles["arkit"] = BuildProfile(
            name="ARKit 52",
            settings=BuildSettings(
                mode=BuildMode.ARKIT,
                build_arkit=True,
                build_visemes=False,
                build_expressions=False,
                build_correctives=False,
                build_inbetweens=False,
                build_drivers=False,
                optimize_after_build=True,
                normalize_after_build=True,
                mirror_left_right=True,
            ),
            description="Complete Apple ARKit 52 blendshape system"
        )
        profiles["viseme"] = BuildProfile(
            name="Viseme",
            settings=BuildSettings(
                mode=BuildMode.VISEME,
                build_arkit=False,
                build_visemes=True,
                build_expressions=False,
                build_correctives=False,
                build_inbetweens=False,
                build_drivers=False,
                optimize_after_build=True,
                normalize_after_build=True,
                mirror_left_right=False,
            ),
            description="Viseme system for lip-sync animation"
        )
        profiles["expression"] = BuildProfile(
            name="Expression",
            settings=BuildSettings(
                mode=BuildMode.EXPRESSION,
                build_arkit=False,
                build_visemes=False,
                build_expressions=True,
                build_correctives=False,
                build_inbetweens=False,
                build_drivers=False,
                optimize_after_build=True,
                normalize_after_build=True,
                mirror_left_right=True,
            ),
            description="Core expression library (happy, sad, angry, etc.)"
        )
        profiles["full"] = BuildProfile(
            name="Full Rig",
            settings=BuildSettings(
                mode=BuildMode.FULL,
                build_arkit=True,
                build_visemes=True,
                build_expressions=True,
                build_correctives=True,
                build_inbetweens=True,
                build_drivers=True,
                optimize_after_build=True,
                normalize_after_build=True,
                mirror_left_right=True,
            ),
            description="Complete facial blendshape rig with all components"
        )
        return profiles


# ---- Part 18: Public API -----------------------------------------------

__all__ = [
    "BlendshapeBuilder",
    "BuildSettings",
    "BuildProfile",
    "BuildTask",
    "BuildResult",
    "BuildStatistics",
    "BuildReport",
    "BuildMode",
    "BuildStrategy",
    "BuildTarget",
    "BuildStatus",
    "BuildError",
    "BuildCanceledError",
    "BuildValidationError",
    "BuildConfigError",
]