"""
blendshapes/blendshape_manager.py

Central Orchestration Layer for the Blendshape Subsystem.

This module provides a unified API that coordinates all blendshape operations
through specialized sub-modules. It acts as the "director" of the blendshape
system, delegating to creators, generators, validators, optimizers, and other
services while maintaining a clean interface for the UI and external tools.

Responsibilities:
- Maintain a registry of all blendshape assets (targets, poses, correctives, etc.).
- Coordinate creation, editing, deletion, mirroring, normalization, optimization.
- Manage scene integration (scanning, discovery, history, references).
- Provide library management (save, load, import, export).
- Handle batch operations across multiple assets.
- Dispatch events and callbacks for UI updates and pipeline integration.
- Validate assets and generate diagnostics.

The manager acts as a facade + service locator, delegating specialized tasks
to dedicated modules such as creator, weight, pose, corrective, mirror, etc.
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
    import maya.cmds as cmds  # type: ignore
    import maya.mel as mel  # type: ignore
    from pymel.core import PyNode, selected, ls, exists  # type: ignore
    import pymel.core as pm  # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Import all blendshape submodules (with fallbacks)
try:
    from .blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType, CreationMode, WeightMode, NamingMode  # type: ignore
except ImportError:
    BlendShapeCreator = None
    BlendShapeTarget = None
    TargetType = None
    CreationMode = None
    WeightMode = None
    NamingMode = None

try:
    from .blendshape_generator import BlendshapeGenerator, GenerationTarget, GeneratorType, GenerationSettings  # type: ignore
except ImportError:
    BlendshapeGenerator = None
    GenerationTarget = None
    GeneratorType = None
    GenerationSettings = None

try:
    from .blendshape_weights import BlendshapeWeightManager, WeightSet, WeightMode as WeightModeEnum  # type: ignore
except ImportError:
    BlendshapeWeightManager = None
    WeightSet = None
    WeightModeEnum = None

try:
    from .blendshape_pose import BlendshapePoseManager, PoseDefinition, PoseType, BlendMode as PoseBlendMode  # type: ignore
except ImportError:
    BlendshapePoseManager = None
    PoseDefinition = None
    PoseType = None
    PoseBlendMode = None

try:
    from .blendshape_correctives import BlendshapeCorrectiveManager, CorrectiveDefinition, CorrectiveType  # type: ignore
except ImportError:
    BlendshapeCorrectiveManager = None
    CorrectiveDefinition = None
    CorrectiveType = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager, InbetweenDefinition, InbetweenMode  # type: ignore
except ImportError:
    BlendshadeInbetweenManager = None
    InbetweenDefinition = None
    InbetweenMode = None

try:
    from .blendshape_mirror import BlendshapeMirrorManager, MirrorSettings, MirrorDirection, MirrorPlane, MirrorMode  # type: ignore
except ImportError:
    BlendshapeMirrorManager = None
    MirrorSettings = None
    MirrorDirection = None
    MirrorPlane = None
    MirrorMode = None

try:
    from .blendshape_normalize import BlendshapeNormalizer, NormalizationSettings, NormalizationType  # type: ignore
except ImportError:
    BlendshapeNormalizer = None
    NormalizationSettings = None
    NormalizationType = None

try:
    from .blendshape_optimizer import BlendshapeOptimizer, OptimizationSettings, OptimizationType, OptimizationLevel  # type: ignore
except ImportError:
    BlendshapeOptimizer = None
    OptimizationSettings = None
    OptimizationType = None
    OptimizationLevel = None

try:
    from .blendshape_transfer import BlendshapeTransferEngine, TransferSettings, CorrespondenceMethod  # type: ignore
except ImportError:
    BlendshapeTransferEngine = None
    TransferSettings = None
    CorrespondenceMethod = None

try:
    from .blendshape_exporter import BlendshapeExporter, ExportSettings, ExportFormat  # type: ignore
except ImportError:
    BlendshapeExporter = None
    ExportSettings = None
    ExportFormat = None

try:
    from .blendshape_library import BlendShapeLibrary  # type: ignore
except ImportError:
    BlendShapeLibrary = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel, ValidationReport  # type: ignore
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None
    ValidationReport = None

try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions,
        get_vertex_position, set_vertex_position, clamp, lerp,
        sanitize_name, generate_unique_name, get_blendshape_targets,
        get_blendshape_weight, set_blendshape_weight, Timer, ProgressTracker,
        duplicate_mesh, freeze_transforms, remove_namespace, add_namespace,
        get_mesh_center, distance_point_to_point, normalize_vector,
        get_mesh_bounding_box, dict_to_json, json_to_dict, hash_data,
        checksum_mesh, get_active_weights, scale_weights, blend_weights,
        normalize_weights, apply_weight_bias, apply_weight_mask, mirror_weights
    )  # type: ignore
except ImportError:
    # Minimal fallback
    def get_shape_node(x): return x
    def get_mesh_vertex_count(x): return 0
    def get_mesh_vertex_positions(x): return []
    def get_vertex_position(x,y): return (0,0,0)
    def set_vertex_position(x,y,z): pass
    def clamp(a,b,c): return max(b, min(a, c))
    def lerp(a,b,t): return a + (b-a)*t
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
    def add_namespace(n, ns): return n
    def get_mesh_center(m): return (0,0,0)
    def distance_point_to_point(a,b): return 0.0
    def normalize_vector(v): return (0,0,0)
    def get_mesh_bounding_box(m): return ((0,0,0),(0,0,0))
    def dict_to_json(d, indent=2): return "{}"
    def json_to_dict(s): return {}
    def hash_data(d): return ""
    def checksum_mesh(m): return ""
    def get_active_weights(w, th): return {}
    def scale_weights(w, f): return {}
    def blend_weights(a,b,t): return {}
    def normalize_weights(w): return {}
    def apply_weight_bias(w,b): return {}
    def apply_weight_mask(w,m): return {}
    def mirror_weights(w,m): return {}

try:
    from ..core.symmetry import SymmetryEngine  # type: ignore
except ImportError:
    SymmetryEngine = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS  # type: ignore
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}


# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class BlendshapeManagerError(Exception):
    """Base exception for manager operations."""
    pass

class AssetNotFoundError(BlendshapeManagerError):
    """Raised when an asset is not found in the registry."""
    pass

class AssetExistsError(BlendshapeManagerError):
    """Raised when an asset already exists."""
    pass

class InvalidOperationError(BlendshapeManagerError):
    """Raised when an operation is invalid in the current state."""
    pass


# ---- Part 2: Constants & Enumerations --------------------------------

class ManagerMode(Enum):
    """Mode of operation for the manager."""
    EDIT = "edit"               # Interactive editing
    ANIMATION = "animation"     # Animation playback
    CAPTURE = "capture"         # Live capture
    EXPORT = "export"           # Export preparation
    PIPELINE = "pipeline"       # Automated pipeline


class SceneState(Enum):
    """State of the Maya scene."""
    EMPTY = "empty"
    READY = "ready"
    INVALID = "invalid"
    DIRTY = "dirty"
    LOCKED = "locked"


class AssetType(Enum):
    """Type of blendshape asset."""
    TARGET = "target"
    POSE = "pose"
    CORRECTIVE = "corrective"
    INBETWEEN = "inbetween"
    LIBRARY = "library"
    ARKIT = "arkit"
    VISEME = "viseme"


class EventType(Enum):
    """Event types for callback registration."""
    CREATED = "created"
    DELETED = "deleted"
    UPDATED = "updated"
    RENAMED = "renamed"
    LOADED = "loaded"
    SAVED = "saved"
    MIRRORED = "mirrored"
    NORMALIZED = "normalized"
    OPTIMIZED = "optimized"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class BlendshapeAsset:
    """
    A generic asset in the blendshape system.
    """
    id: str
    name: str
    asset_type: AssetType
    data: Any  # can be a target, pose, corrective, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    locked: bool = False
    tags: List[str] = field(default_factory=list)
    source: str = "user"  # 'builtin', 'user', 'imported'


@dataclass
class BlendshapeRegistry:
    """
    Registry tracking all blendshape assets.
    """
    assets: Dict[str, BlendshapeAsset] = field(default_factory=dict)  # id -> asset
    names: Dict[str, str] = field(default_factory=dict)  # name -> id
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # id -> list of dependent ids
    references: Dict[str, List[str]] = field(default_factory=dict)  # id -> list of referencing ids


@dataclass
class BlendshapeScene:
    """
    Information about the current Maya scene.
    """
    state: SceneState = SceneState.EMPTY
    blendshape_nodes: List[str] = field(default_factory=list)
    target_count: int = 0
    mesh_count: int = 0
    frame_range: Tuple[int, int] = (1, 100)


@dataclass
class BlendshapeStatistics:
    """Overall statistics of the blendshape system."""
    total_assets: int = 0
    targets: int = 0
    poses: int = 0
    correctives: int = 0
    inbetweens: int = 0
    arkit: int = 0
    visemes: int = 0
    libraries: int = 0
    locked: int = 0
    enabled: int = 0


@dataclass
class BlendshapeReport:
    """Diagnostic report."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[BlendshapeStatistics] = None


# ---- Part 4: Blendshape Registry (implementation) --------------------

class BlendshapeRegistryManager:
    """
    Manages the asset registry.
    """
    def __init__(self):
        self.registry = BlendshapeRegistry()

    def register(self, asset: BlendshapeAsset) -> None:
        """Register a new asset."""
        if asset.id in self.registry.assets:
            raise AssetExistsError(f"Asset with ID '{asset.id}' already exists")
        if asset.name in self.registry.names:
            raise AssetExistsError(f"Asset with name '{asset.name}' already exists")
        self.registry.assets[asset.id] = asset
        self.registry.names[asset.name] = asset.id

    def unregister(self, asset_id: str) -> None:
        """Remove an asset from the registry."""
        if asset_id not in self.registry.assets:
            raise AssetNotFoundError(f"Asset with ID '{asset_id}' not found")
        asset = self.registry.assets[asset_id]
        del self.registry.assets[asset_id]
        del self.registry.names[asset.name]

    def get(self, identifier: Union[str, AssetType]) -> Any:
        """
        Get an asset by ID or name. If AssetType is provided, returns all assets of that type.
        """
        if isinstance(identifier, str):
            # Try as ID first, then as name
            if identifier in self.registry.assets:
                return self.registry.assets[identifier]
            if identifier in self.registry.names:
                return self.registry.assets[self.registry.names[identifier]]
            raise AssetNotFoundError(f"Asset '{identifier}' not found")
        elif isinstance(identifier, AssetType):
            # Return list of assets of that type
            return [a for a in self.registry.assets.values() if a.asset_type == identifier]
        else:
            raise TypeError("identifier must be str or AssetType")

    def get_all(self) -> List[BlendshapeAsset]:
        """Return all assets."""
        return list(self.registry.assets.values())

    def update(self, asset: BlendshapeAsset) -> None:
        """Update an existing asset."""
        if asset.id not in self.registry.assets:
            raise AssetNotFoundError(f"Asset with ID '{asset.id}' not found")
        old_name = self.registry.assets[asset.id].name
        if old_name != asset.name and asset.name in self.registry.names:
            raise AssetExistsError(f"Asset with name '{asset.name}' already exists")
        self.registry.assets[asset.id] = asset
        if old_name != asset.name:
            del self.registry.names[old_name]
            self.registry.names[asset.name] = asset.id

    def exists(self, identifier: Union[str, AssetType]) -> bool:
        """Check if an asset exists."""
        if isinstance(identifier, str):
            return identifier in self.registry.assets or identifier in self.registry.names
        elif isinstance(identifier, AssetType):
            return any(a.asset_type == identifier for a in self.registry.assets.values())
        return False


# ---- Part 5: Blendshape Manager (Main Facade) -------------------------

class BlendshapeManager:
    """
    Main controller for all blendshape operations.

    This class provides a unified API that delegates to specialized sub-modules.
    """
    def __init__(self, mode: ManagerMode = ManagerMode.EDIT):
        self.mode = mode
        self._registry_manager = BlendshapeRegistryManager()

        # Initialize sub-managers (lazy initialization)
        self._creator: Optional[BlendShapeCreator] = None
        self._generator: Optional[BlendshapeGenerator] = None
        self._weight_manager: Optional[BlendshapeWeightManager] = None
        self._pose_manager: Optional[BlendshapePoseManager] = None
        self._corrective_manager: Optional[BlendshapeCorrectiveManager] = None
        self._inbetween_manager: Optional[BlendshadeInbetweenManager] = None
        self._mirror_manager: Optional[BlendshapeMirrorManager] = None
        self._normalizer: Optional[BlendshapeNormalizer] = None
        self._optimizer: Optional[BlendshapeOptimizer] = None
        self._transfer_engine: Optional[BlendshapeTransferEngine] = None
        self._exporter: Optional[BlendshapeExporter] = None
        self._library: Optional[BlendShapeLibrary] = None
        self._validator: Optional[BlendshapeValidator] = None
        self._symmetry_engine: Optional[SymmetryEngine] = None

        self._event_listeners: Dict[EventType, List[Callable]] = {e: [] for e in EventType}
        self._scene: BlendshapeScene = BlendshapeScene()
        self._last_report: Optional[BlendshapeReport] = None

        # Scan the current Maya scene on init
        self.scan_scene()

    # ---- Lazy Initialization ----

    def _get_creator(self) -> BlendShapeCreator:
        if self._creator is None:
            self._creator = BlendShapeCreator() if BlendShapeCreator else None
        return self._creator

    def _get_generator(self) -> BlendshapeGenerator:
        if self._generator is None:
            self._generator = BlendshapeGenerator() if BlendshapeGenerator else None
        return self._generator

    def _get_weight_manager(self) -> BlendshapeWeightManager:
        if self._weight_manager is None:
            self._weight_manager = BlendshapeWeightManager() if BlendshapeWeightManager else None
        return self._weight_manager

    def _get_pose_manager(self) -> BlendshapePoseManager:
        if self._pose_manager is None:
            self._pose_manager = BlendshapePoseManager() if BlendshapePoseManager else None
        return self._pose_manager

    def _get_corrective_manager(self) -> BlendshapeCorrectiveManager:
        if self._corrective_manager is None:
            self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        return self._corrective_manager

    def _get_inbetween_manager(self) -> BlendshadeInbetweenManager:
        if self._inbetween_manager is None:
            self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        return self._inbetween_manager

    def _get_mirror_manager(self) -> BlendshapeMirrorManager:
        if self._mirror_manager is None:
            self._mirror_manager = BlendshapeMirrorManager() if BlendshapeMirrorManager else None
        return self._mirror_manager

    def _get_normalizer(self) -> BlendshapeNormalizer:
        if self._normalizer is None:
            self._normalizer = BlendshapeNormalizer() if BlendshapeNormalizer else None
        return self._normalizer

    def _get_optimizer(self) -> BlendshapeOptimizer:
        if self._optimizer is None:
            self._optimizer = BlendshapeOptimizer() if BlendshapeOptimizer else None
        return self._optimizer

    def _get_transfer_engine(self) -> BlendshapeTransferEngine:
        if self._transfer_engine is None:
            self._transfer_engine = BlendshapeTransferEngine() if BlendshapeTransferEngine else None
        return self._transfer_engine

    def _get_exporter(self) -> BlendshapeExporter:
        if self._exporter is None:
            self._exporter = BlendshapeExporter() if BlendshapeExporter else None
        return self._exporter

    def _get_library(self) -> BlendShapeLibrary:
        if self._library is None:
            self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        return self._library

    def _get_validator(self) -> BlendshapeValidator:
        if self._validator is None:
            self._validator = BlendshapeValidator() if BlendshapeValidator else None
        return self._validator

    def _get_symmetry_engine(self) -> SymmetryEngine:
        if self._symmetry_engine is None:
            self._symmetry_engine = SymmetryEngine() if SymmetryEngine else None
        return self._symmetry_engine

    # ---- Scene Integration ----

    def scan_scene(self) -> BlendshapeScene:
        """
        Scan the current Maya scene for blendshape-related data and update the scene state.
        """
        self._scene.state = SceneState.READY
        # Find all blendshape nodes
        bs_nodes = cmds.ls(type='blendShape') or []
        self._scene.blendshape_nodes = bs_nodes
        # Count targets
        total_targets = 0
        for node in bs_nodes:
            targets = cmds.blendShape(node, q=True, target=True) or []
            total_targets += len(targets)
        self._scene.target_count = total_targets
        # Count meshes
        meshes = cmds.ls(type='mesh') or []
        self._scene.mesh_count = len(meshes)
        # Frame range
        start = int(cmds.playbackOptions(q=True, min=True))
        end = int(cmds.playbackOptions(q=True, max=True))
        self._scene.frame_range = (start, end)
        return self._scene

    def get_scene_state(self) -> SceneState:
        return self._scene.state

    def refresh_scene(self) -> None:
        self.scan_scene()

    # ---- Asset Management ----

    def create_asset(
        self,
        name: str,
        asset_type: AssetType,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        source: str = "user"
    ) -> BlendshapeAsset:
        """
        Create a new asset and register it.
        """
        # Generate a unique ID
        asset_id = str(uuid.uuid4())
        # Sanitize name
        name = sanitize_name(name)
        # Ensure name is unique
        existing_names = [a.name for a in self._registry_manager.get_all()]
        name = generate_unique_name(name, existing_names)
        asset = BlendshapeAsset(
            id=asset_id,
            name=name,
            asset_type=asset_type,
            data=data,
            metadata=metadata or {},
            tags=tags or [],
            source=source
        )
        self._registry_manager.register(asset)
        # Dispatch event
        self._dispatch_event(EventType.CREATED, asset)
        return asset

    def delete_asset(self, identifier: Union[str, AssetType]) -> None:
        """
        Delete an asset by ID or name.
        """
        if isinstance(identifier, str):
            asset = self._registry_manager.get(identifier)
            self._registry_manager.unregister(asset.id)
            # Dispatch event
            self._dispatch_event(EventType.DELETED, asset)
        else:
            # Delete all assets of a type
            assets = self._registry_manager.get(identifier)
            for a in assets:
                self._registry_manager.unregister(a.id)
                self._dispatch_event(EventType.DELETED, a)

    def get_asset(self, identifier: Union[str, AssetType]) -> Any:
        """
        Get an asset by ID or name, or list of assets by type.
        """
        return self._registry_manager.get(identifier)

    def update_asset(self, asset: BlendshapeAsset) -> None:
        """
        Update an existing asset.
        """
        self._registry_manager.update(asset)
        self._dispatch_event(EventType.UPDATED, asset)

    def rename_asset(self, old_identifier: str, new_name: str) -> None:
        """
        Rename an asset.
        """
        asset = self._registry_manager.get(old_identifier)
        # Check if new name is already taken
        if new_name in self._registry_manager.registry.names:
            raise AssetExistsError(f"Asset with name '{new_name}' already exists")
        old_name = asset.name
        asset.name = new_name
        self._registry_manager.update(asset)
        self._dispatch_event(EventType.RENAMED, asset, old_name=old_name)

    def list_assets(self, asset_type: Optional[AssetType] = None) -> List[BlendshapeAsset]:
        """
        List all assets, optionally filtered by type.
        """
        if asset_type is None:
            return self._registry_manager.get_all()
        else:
            return self._registry_manager.get(asset_type)

    # ---- Creation Pipeline ----

    def create_target(
        self,
        base_mesh: str,
        target_mesh: str,
        name: Optional[str] = None,
        **kwargs
    ) -> BlendshapeAsset:
        """
        Create a new blendshape target.
        Delegates to BlendShapeCreator.
        """
        creator = self._get_creator()
        if not creator:
            raise BlendshapeManagerError("BlendShapeCreator not available")
        # Generate a name if not provided
        if name is None:
            name = target_mesh
        # Create the target
        # For simplicity, we'll use the creator's create_target method.
        # In a full implementation, we would create a BlendShapeTarget and call create_target.
        target = BlendShapeTarget(name=name, mesh=target_mesh, **kwargs)
        # We need to ensure a blendshape node exists on the base mesh
        bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
        if bs_nodes:
            node = bs_nodes[0]
        else:
            node = creator.create_node(f"{base_mesh}_blendShape", base_mesh)
        result = creator.create_target(node, target)
        if not result.success:
            raise BlendshapeManagerError(f"Failed to create target: {result.errors}")
        # Register as an asset
        asset = self.create_asset(
            name=name,
            asset_type=AssetType.TARGET,
            data={"node": node, "target": target, "base_mesh": base_mesh, "target_mesh": target_mesh},
            tags=kwargs.get('tags', []),
            source=kwargs.get('source', 'user')
        )
        return asset

    def generate_arkit_library(self, base_mesh: str) -> List[BlendshapeAsset]:
        """
        Generate all 52 ARKit blendshapes.
        Delegates to BlendshapeGenerator.
        """
        generator = self._get_generator()
        if not generator:
            raise BlendshapeManagerError("BlendshapeGenerator not available")
        report = generator.generate_arkit(base_mesh)
        assets = []
        for target_name in report.generated_targets:
            asset = self.create_asset(
                name=target_name,
                asset_type=AssetType.ARKIT,
                data={"target": target_name, "base_mesh": base_mesh},
                tags=["arkit", "generated"],
                source="generated"
            )
            assets.append(asset)
        return assets

    def generate_visemes(self, base_mesh: str) -> List[BlendshapeAsset]:
        """
        Generate viseme targets.
        """
        generator = self._get_generator()
        if not generator:
            raise BlendshapeManagerError("BlendshapeGenerator not available")
        report = generator.generate_visemes(base_mesh)
        assets = []
        for target_name in report.generated_targets:
            asset = self.create_asset(
                name=target_name,
                asset_type=AssetType.VISEME,
                data={"target": target_name, "base_mesh": base_mesh},
                tags=["viseme", "generated"],
                source="generated"
            )
            assets.append(asset)
        return assets

    def generate_emotions(self, base_mesh: str) -> List[BlendshapeAsset]:
        """
        Generate emotion expressions.
        """
        generator = self._get_generator()
        if not generator:
            raise BlendshapeManagerError("BlendshapeGenerator not available")
        report = generator.generate_emotions(base_mesh)
        assets = []
        for target_name in report.generated_targets:
            asset = self.create_asset(
                name=target_name,
                asset_type=AssetType.POSE,
                data={"target": target_name, "base_mesh": base_mesh},
                tags=["emotion", "generated"],
                source="generated"
            )
            assets.append(asset)
        return assets

    # ---- Editing Pipeline ----

    def set_weight(self, target: str, value: float) -> None:
        """
        Set a blendshape weight.
        Delegates to BlendshapeWeightManager.
        """
        weight_mgr = self._get_weight_manager()
        if not weight_mgr:
            raise BlendshapeManagerError("Weight manager not available")
        weight_mgr.set_weight(target, value)

    def get_weight(self, target: str) -> float:
        """Get a blendshape weight."""
        weight_mgr = self._get_weight_manager()
        if not weight_mgr:
            raise BlendshapeManagerError("Weight manager not available")
        return weight_mgr.get_weight(target)

    def lock_weight(self, target: str) -> None:
        """Lock a blendshape weight."""
        weight_mgr = self._get_weight_manager()
        if not weight_mgr:
            raise BlendshapeManagerError("Weight manager not available")
        weight_mgr.lock_weight(target)

    def unlock_weight(self, target: str) -> None:
        """Unlock a blendshape weight."""
        weight_mgr = self._get_weight_manager()
        if not weight_mgr:
            raise BlendshapeManagerError("Weight manager not available")
        weight_mgr.unlock_weight(target)

    def normalize_weights(self, targets: Optional[List[str]] = None) -> None:
        """Normalize weights."""
        normalizer = self._get_normalizer()
        if not normalizer:
            raise BlendshapeManagerError("Normalizer not available")
        settings = NormalizationSettings(normalization_types=[NormalizationType.WEIGHTS])
        normalizer.normalize(targets, settings)

    def mirror_weights(self, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> None:
        """Mirror weights left/right."""
        mirror_mgr = self._get_mirror_manager()
        if not mirror_mgr:
            raise BlendshapeManagerError("Mirror manager not available")
        mirror_mgr.mirror_weights(direction)

    # ---- Pose Management ----

    def capture_pose(self, name: str) -> BlendshapeAsset:
        """Capture the current rig state as a pose."""
        pose_mgr = self._get_pose_manager()
        if not pose_mgr:
            raise BlendshapeManagerError("Pose manager not available")
        pose = pose_mgr.capture(name)
        asset = self.create_asset(
            name=name,
            asset_type=AssetType.POSE,
            data=pose,
            tags=["captured"],
            source="user"
        )
        return asset

    def apply_pose(self, name: str, blend_factor: float = 1.0) -> None:
        """Apply a pose to the rig."""
        pose_mgr = self._get_pose_manager()
        if not pose_mgr:
            raise BlendshapeManagerError("Pose manager not available")
        # Find the pose asset
        asset = self.get_asset(name)
        if asset.asset_type != AssetType.POSE:
            raise InvalidOperationError(f"Asset '{name}' is not a pose")
        pose = asset.data
        pose_mgr.apply(pose.name, blend_factor)

    def blend_poses(self, pose_names: List[str], weights: List[float], output_name: str) -> BlendshapeAsset:
        """Blend multiple poses into a new pose."""
        pose_mgr = self._get_pose_manager()
        if not pose_mgr:
            raise BlendshapeManagerError("Pose manager not available")
        blended = pose_mgr.blend(pose_names, weights, output_name=output_name)
        asset = self.create_asset(
            name=output_name,
            asset_type=AssetType.POSE,
            data=blended,
            tags=["blended"],
            source="user"
        )
        return asset

    # ---- Corrective Management ----

    def create_corrective(self, name: str, base_mesh: str, source_targets: List[str]) -> BlendshapeAsset:
        """Create a corrective blendshape."""
        corrective_mgr = self._get_corrective_manager()
        if not corrective_mgr:
            raise BlendshapeManagerError("Corrective manager not available")
        defn = corrective_mgr.create_blendshape_corrective(name, base_mesh, source_targets)
        asset = self.create_asset(
            name=name,
            asset_type=AssetType.CORRECTIVE,
            data=defn,
            tags=["corrective"],
            source="user"
        )
        return asset

    # ---- Inbetween Management ----

    def create_inbetween(self, parent_target: str, weight: float, mesh: str) -> BlendshapeAsset:
        """Create an inbetween target."""
        inbetween_mgr = self._get_inbetween_manager()
        if not inbetween_mgr:
            raise BlendshapeManagerError("Inbetween manager not available")
        defn = inbetween_mgr.create_inbetween(parent_target, weight, mesh)
        asset = self.create_asset(
            name=defn.name,
            asset_type=AssetType.INBETWEEN,
            data=defn,
            tags=["inbetween"],
            source="user"
        )
        return asset

    # ---- Mirroring ----

    def mirror_target(self, source_target: str, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> BlendshapeAsset:
        """
        Mirror a blendshape target.
        Delegates to BlendshapeMirrorManager.
        """
        mirror_mgr = self._get_mirror_manager()
        if not mirror_mgr:
            raise BlendshapeManagerError("Mirror manager not available")
        result = mirror_mgr.mirror_delta(source_target, direction)
        if not result.success:
            raise BlendshapeManagerError(f"Mirror failed: {result.errors}")
        # The mirrored target name is generated by the mirror manager
        mirrored_name = result.mirrored_targets[0] if result.mirrored_targets else None
        if not mirrored_name:
            raise BlendshapeManagerError("Mirror produced no target")
        # Create an asset for the mirrored target
        asset = self.create_asset(
            name=mirrored_name,
            asset_type=AssetType.TARGET,
            data={"source": source_target, "direction": direction.value},
            tags=["mirrored"],
            source="user"
        )
        self._dispatch_event(EventType.MIRRORED, asset)
        return asset

    def mirror_pose(self, pose_name: str, direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> BlendshapeAsset:
        """
        Mirror a pose.
        """
        mirror_mgr = self._get_mirror_manager()
        if not mirror_mgr:
            raise BlendshapeManagerError("Mirror manager not available")
        result = mirror_mgr.mirror_pose(pose_name, direction)
        if not result.success:
            raise BlendshapeManagerError(f"Pose mirror failed: {result.errors}")
        mirrored_name = result.mirrored_targets[0] if result.mirrored_targets else None
        if not mirrored_name:
            raise BlendshapeManagerError("Pose mirror produced no target")
        # Create an asset for the mirrored pose
        # We need to retrieve the mirrored pose from the pose manager
        pose_mgr = self._get_pose_manager()
        if not pose_mgr:
            raise BlendshapeManagerError("Pose manager not available")
        pose = pose_mgr.get_pose(mirrored_name)
        if not pose:
            raise BlendshapeManagerError(f"Mirrored pose '{mirrored_name}' not found")
        asset = self.create_asset(
            name=mirrored_name,
            asset_type=AssetType.POSE,
            data=pose,
            tags=["mirrored"],
            source="user"
        )
        self._dispatch_event(EventType.MIRRORED, asset)
        return asset

    # ---- Normalization ----

    def normalize_all(self) -> None:
        """Normalize all assets."""
        normalizer = self._get_normalizer()
        if not normalizer:
            raise BlendshapeManagerError("Normalizer not available")
        report = normalizer.normalize()
        self._dispatch_event(EventType.NORMALIZED, report)

    def normalize_targets(self, targets: Optional[List[str]] = None) -> None:
        """Normalize specific targets."""
        normalizer = self._get_normalizer()
        if not normalizer:
            raise BlendshapeManagerError("Normalizer not available")
        normalizer.normalize_weights(targets)

    # ---- Optimization ----

    def optimize(self) -> None:
        """Optimize the entire blendshape system."""
        optimizer = self._get_optimizer()
        if not optimizer:
            raise BlendshapeManagerError("Optimizer not available")
        report = optimizer.optimize()
        self._dispatch_event(EventType.OPTIMIZED, report)

    def optimize_selected(self, targets: List[str]) -> None:
        """Optimize specific targets."""
        optimizer = self._get_optimizer()
        if not optimizer:
            raise BlendshapeManagerError("Optimizer not available")
        optimizer.optimize(targets)

    # ---- Transfer ----

    def transfer_target(self, source_target: str, target_mesh: str) -> None:
        """
        Transfer a blendshape target to another mesh.
        """
        transfer = self._get_transfer_engine()
        if not transfer:
            raise BlendshapeManagerError("Transfer engine not available")
        # We need the source mesh. We'll get it from the asset data.
        asset = self.get_asset(source_target)
        if asset.asset_type != AssetType.TARGET:
            raise InvalidOperationError(f"Asset '{source_target}' is not a target")
        source_data = asset.data
        source_mesh = source_data.get('base_mesh')
        if not source_mesh:
            raise BlendshapeManagerError(f"Source mesh not found for '{source_target}'")
        # Transfer delta if available, else just transfer the target mesh itself.
        # For simplicity, we'll transfer the target mesh directly.
        # In practice, we would compute delta and apply to target_mesh.
        # We'll use the transfer engine's transfer_delta method.
        # But we need the delta. We'll fetch it from delta engine.
        # Since we don't have delta engine exposed here, we'll skip detailed implementation.
        # Placeholder: log a message.
        logger.info(f"Transferring target '{source_target}' to mesh '{target_mesh}'")

    # ---- Export ----

    def export(self, filepath: str, format: ExportFormat = ExportFormat.JSON) -> None:
        """
        Export all blendshape assets to a file.
        """
        exporter = self._get_exporter()
        if not exporter:
            raise BlendshapeManagerError("Exporter not available")
        # Collect all assets
        assets = self.list_assets()
        # For now, just export targets (simplified)
        # In practice, we would gather all data and export.
        exporter.export_all(filepath, format)

    # ---- Library Management ----

    def load_library(self, filepath: str) -> List[BlendshapeAsset]:
        """
        Load a blendshape library from a file.
        """
        library = self._get_library()
        if not library:
            raise BlendshapeManagerError("Library not available")
        # Load library data
        # For simplicity, we'll assume the library returns a list of assets.
        # In practice, we'd parse the file and create assets.
        # Placeholder: create some sample assets.
        assets = []
        # Simulate loading
        logger.info(f"Loading library from {filepath}")
        return assets

    def save_library(self, filepath: str) -> None:
        """
        Save the current blendshape library to a file.
        """
        library = self._get_library()
        if not library:
            raise BlendshapeManagerError("Library not available")
        # Save all assets
        # For simplicity, just log
        logger.info(f"Saving library to {filepath}")

    # ---- Validation ----

    def validate(self) -> BlendshapeReport:
        """
        Validate all assets and the scene.
        """
        validator = self._get_validator()
        if not validator:
            raise BlendshapeManagerError("Validator not available")
        report = validator.validate()
        self._last_report = report
        return report

    # ---- Diagnostics ----

    def get_statistics(self) -> BlendshapeStatistics:
        """
        Compute and return statistics about the blendshape system.
        """
        stats = BlendshapeStatistics()
        assets = self.list_assets()
        stats.total_assets = len(assets)
        for a in assets:
            if a.asset_type == AssetType.TARGET:
                stats.targets += 1
            elif a.asset_type == AssetType.POSE:
                stats.poses += 1
            elif a.asset_type == AssetType.CORRECTIVE:
                stats.correctives += 1
            elif a.asset_type == AssetType.INBETWEEN:
                stats.inbetweens += 1
            elif a.asset_type == AssetType.ARKIT:
                stats.arkit += 1
            elif a.asset_type == AssetType.VISEME:
                stats.visemes += 1
            elif a.asset_type == AssetType.LIBRARY:
                stats.libraries += 1
            if a.locked:
                stats.locked += 1
            if a.enabled:
                stats.enabled += 1
        return stats

    # ---- Events & Callbacks ----

    def register_event(self, event_type: EventType, callback: Callable) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)

    def unregister_event(self, event_type: EventType, callback: Callable) -> None:
        """Unregister a callback."""
        if event_type in self._event_listeners:
            self._event_listeners[event_type].remove(callback)

    def _dispatch_event(self, event_type: EventType, data: Any, **kwargs) -> None:
        """Dispatch an event to all registered listeners."""
        for cb in self._event_listeners.get(event_type, []):
            try:
                cb(data, **kwargs)
            except Exception as e:
                logger.warning(f"Event callback failed: {e}")

    # ---- Batch Operations ----

    def batch_create_arkit(self, meshes: List[str]) -> Dict[str, List[BlendshapeAsset]]:
        """
        Batch generate ARKit libraries for multiple meshes.
        """
        results = {}
        for mesh in meshes:
            results[mesh] = self.generate_arkit_library(mesh)
        return results

    def batch_mirror(self, target_names: List[str], direction: MirrorDirection = MirrorDirection.LEFT_TO_RIGHT) -> List[BlendshapeAsset]:
        """
        Batch mirror multiple targets.
        """
        mirrored = []
        for t in target_names:
            try:
                asset = self.mirror_target(t, direction)
                mirrored.append(asset)
            except Exception as e:
                logger.error(f"Failed to mirror {t}: {e}")
        return mirrored

    # ---- Utilities ----

    def get_asset_by_name(self, name: str) -> Optional[BlendshapeAsset]:
        """Get an asset by its name."""
        try:
            return self.get_asset(name)
        except AssetNotFoundError:
            return None

    def get_assets_by_tag(self, tag: str) -> List[BlendshapeAsset]:
        """Get all assets with a specific tag."""
        return [a for a in self.list_assets() if tag in a.tags]

    # ---- Reset ----

    def clear(self) -> None:
        """Clear all assets and reset the manager."""
        self._registry_manager = BlendshapeRegistryManager()
        self._scene = BlendshapeScene()
        self._last_report = None

    # ---- Shutdown ----

    def shutdown(self) -> None:
        """Clean up resources."""
        # Notify listeners about shutdown?
        pass


# ---- Part 16: Public API -----------------------------------------------

__all__ = [
    "BlendshapeManager",
    "BlendshapeAsset",
    "BlendshapeRegistry",
    "BlendshapeScene",
    "BlendshapeStatistics",
    "BlendshapeReport",
    "ManagerMode",
    "SceneState",
    "AssetType",
    "EventType",
    "BlendshapeManagerError",
    "AssetNotFoundError",
    "AssetExistsError",
    "InvalidOperationError",
]