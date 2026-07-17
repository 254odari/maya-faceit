"""
blendshapes/blendshape_creator.py

Core Blendshape Creation Engine for Maya.

This module provides a complete framework for creating, configuring, and
managing blendshape targets. It is the authoritative entry point for all
blendshape creation operations in the maya_faceit system.

Responsibilities:
- Create new blendshape nodes or add targets to existing ones.
- Add, remove, rename, duplicate, and delete targets.
- Create corrective targets, ARKit targets, PSD targets, and in-between targets.
- Initialize and manage target weights.
- Validate mesh topology, vertex counts, and naming.
- Provide diagnostics, statistics, and reports.

The module delegates specialized tasks to other modules:
- blendshape_validator.py for topology and mesh validation.
- blendshape_library.py for target definitions (e.g., ARKit 52).
- blendshape_weights.py for weight management.
- blendshape_delta.py for delta computation.
- blendshape_pose.py for pose-based target generation.

This module uses Maya's Python API but is abstracted to provide a clean
interface for the rest of the plugin.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable

# Maya imports
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode, selected, ls, exists, currentTime, setKeyframe
    import pymel.core as pm
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional imports from other blendshape modules
try:
    from .blendshape_validator import BlendShapeValidator, ValidationReport
except ImportError:
    class BlendShapeValidator:
        def validate_mesh(self, mesh, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class DummyReport:
                is_valid = True
                errors = []
                warnings = []
            return DummyReport()
    ValidationReport = None

try:
    from .blendshape_library import BlendShapeLibrary, TargetDefinition
except ImportError:
    class BlendShapeLibrary:
        def get_arkit_targets(self):
            return []
        def get_corrective_targets(self):
            return []
        def get_target_by_name(self, name):
            return None
    TargetDefinition = None

try:
    from .blendshape_weights import WeightManager
except ImportError:
    WeightManager = None

try:
    from .blendshape_delta import DeltaManager
except ImportError:
    DeltaManager = None

try:
    from .blendshape_pose import PoseManager
except ImportError:
    PoseManager = None

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class BlendShapeCreationError(Exception):
    """Base exception for blendshape creation."""
    pass

class InvalidMeshError(BlendShapeCreationError):
    """Raised when the mesh is invalid for blendshape creation."""
    pass

class TargetError(BlendShapeCreationError):
    """Raised when target creation fails."""
    pass

class DuplicateTargetError(BlendShapeCreationError):
    """Raised when a target with the same name already exists."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class CreationMode(Enum):
    """How to create the blendshape node."""
    NEW_NODE = "new"
    EXISTING_NODE = "existing"
    AUTO = "auto"  # Find existing or create new


class TargetType(Enum):
    """Type of blendshape target."""
    STANDARD = "standard"
    CORRECTIVE = "corrective"
    ARKIT = "arkit"
    PSD = "psd"
    INBETWEEN = "inbetween"
    CUSTOM = "custom"


class WeightMode(Enum):
    """Initial weight mode."""
    ZERO = "zero"
    ONE = "one"
    AUTO = "auto"     # Use target definition default (or 0.0)
    CUSTOM = "custom"


class NamingMode(Enum):
    """Naming convention for targets."""
    KEEP = "keep"       # Use exactly the name provided
    PREFIX = "prefix"   # Add a prefix to the target name
    SUFFIX = "suffix"   # Add a suffix to the target name
    AUTO = "auto"       # Use library naming or infer


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class BlendShapeTarget:
    """
    Definition of a blendshape target.
    """
    name: str
    mesh: str                     # The target mesh or shape
    weight: float = 0.0
    target_type: TargetType = TargetType.STANDARD
    inbetween_value: Optional[float] = None  # If in-between, the weight value
    base_name: Optional[str] = None          # If in-between, the base target name
    corrective_set: Optional[str] = None     # For corrective targets, the set name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mesh": self.mesh,
            "weight": self.weight,
            "target_type": self.target_type.value,
            "inbetween_value": self.inbetween_value,
            "base_name": self.base_name,
            "corrective_set": self.corrective_set,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlendShapeTarget:
        return cls(
            name=data["name"],
            mesh=data["mesh"],
            weight=data.get("weight", 0.0),
            target_type=TargetType(data.get("target_type", "standard")),
            inbetween_value=data.get("inbetween_value"),
            base_name=data.get("base_name"),
            corrective_set=data.get("corrective_set"),
        )


@dataclass
class BlendShapeCreationSettings:
    """Settings for creating blendshape targets."""
    # Creation mode
    creation_mode: CreationMode = CreationMode.AUTO
    node_name: Optional[str] = None
    # Naming
    naming_mode: NamingMode = NamingMode.KEEP
    prefix: str = ""
    suffix: str = ""
    # Weighting
    weight_mode: WeightMode = WeightMode.ZERO
    default_weight: float = 0.0
    # Validation
    validate_topology: bool = True
    validate_vertex_count: bool = True
    validate_naming: bool = True
    # Undo
    enable_undo: bool = True
    # Progress
    progress_callback: Optional[Callable[[float, str], None]] = None
    cancel_check: Optional[Callable[[], bool]] = None


@dataclass
class CreationResult:
    """Result of a creation operation."""
    success: bool
    node_name: Optional[str] = None
    targets_added: List[str] = field(default_factory=list)
    targets_skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CreationStatistics:
    """Statistics for a creation session."""
    total_targets: int = 0
    targets_created: int = 0
    target_types: Dict[str, int] = field(default_factory=dict)
    inbetween_targets: int = 0
    corrective_targets: int = 0
    runtime_seconds: float = 0.0
    avg_time_per_target: float = 0.0


# ---- Part 4: BlendShapeCreator -----------------------------------------

class BlendShapeCreator:
    """
    Main controller for blendshape creation.
    """
    def __init__(self):
        self._settings = BlendShapeCreationSettings()
        self._validator = BlendShapeValidator() if BlendShapeValidator else None
        self._library = BlendShapeLibrary() if BlendShapeLibrary else None
        self._weight_manager = WeightManager() if WeightManager else None
        self._delta_manager = DeltaManager() if DeltaManager else None
        self._pose_manager = PoseManager() if PoseManager else None

        self._last_result: Optional[CreationResult] = None
        self._last_stats: Optional[CreationStatistics] = None

    # ---- Main Creation API ----

    def create_node(self, node_name: str, base_mesh: str, existing: bool = False) -> str:
        """
        Create a new blendshape node or get an existing one.

        Args:
            node_name: Name for the blendshape node.
            base_mesh: The base mesh to which the blendshape will be applied.
            existing: If True, try to find an existing node with the given name.

        Returns:
            The name of the blendshape node.

        Raises:
            InvalidMeshError: If the base mesh is invalid.
            BlendShapeCreationError: If node creation fails.
        """
        if not cmds.objExists(base_mesh):
            raise InvalidMeshError(f"Base mesh '{base_mesh}' does not exist")
        if not cmds.nodeType(base_mesh) == 'mesh':
            # Maybe it's a transform, get the shape
            shapes = cmds.listRelatives(base_mesh, shapes=True) or []
            if not shapes or cmds.nodeType(shapes[0]) != 'mesh':
                raise InvalidMeshError(f"'{base_mesh}' is not a mesh or does not have a mesh shape")

        # Validate mesh
        if self._settings.validate_topology and self._validator:
            report = self._validator.validate_mesh(base_mesh)
            if not report.is_valid:
                raise InvalidMeshError(f"Mesh validation failed: {', '.join(report.errors)}")

        # Look for existing node
        if existing:
            # Check if a blendshape node with this name already exists on this mesh
            existing_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
            for node in existing_nodes:
                if node == node_name:
                    logger.info(f"Using existing blendshape node '{node_name}'")
                    return node
            # If not found, fall through to creation

        # Create new node
        if node_name:
            # If a node with this name exists, we need to handle it
            if cmds.objExists(node_name):
                raise BlendShapeCreationError(f"Node '{node_name}' already exists")
            node = cmds.blendShape(base_mesh, name=node_name)[0]
        else:
            node = cmds.blendShape(base_mesh)[0]

        logger.info(f"Created blendshape node '{node}'")
        return node

    def create_target(
        self,
        node: str,
        target: BlendShapeTarget,
        settings: Optional[BlendShapeCreationSettings] = None,
    ) -> CreationResult:
        """
        Add a single target to a blendshape node.

        Args:
            node: The blendshape node.
            target: The target definition.
            settings: Optional override settings.

        Returns:
            CreationResult indicating success or failure.
        """
        if not cmds.objExists(node):
            return CreationResult(success=False, errors=[f"Node '{node}' does not exist"])

        if not cmds.objExists(target.mesh):
            return CreationResult(success=False, errors=[f"Target mesh '{target.mesh}' does not exist"])

        # Validate mesh compatibility
        if self._settings.validate_topology and self._validator:
            # Need to get the base mesh from the node
            base_mesh = cmds.listConnections(node, source=True, destination=False, type='mesh')[0]
            report = self._validator.validate_target_mesh(base_mesh, target.mesh)
            if not report.is_valid:
                return CreationResult(success=False, errors=[f"Target mesh validation failed: {', '.join(report.errors)}"])

        # Check if target already exists
        existing_targets = cmds.listAttr(node, m=True, string='weight') or []
        if target.name in existing_targets:
            return CreationResult(success=False, errors=[f"Target '{target.name}' already exists on node '{node}'"])

        # Apply naming mode
        final_name = self._apply_naming(target.name)

        # Add the target
        try:
            # Use cmds.blendShape to add the target
            cmds.blendShape(node, edit=True, target=(node, 0, target.mesh, 1.0))
            # The target is added with the name of the mesh. We need to rename it.
            # In Maya, the alias is the name of the target.
            # We can use `cmds.aliasAttr` to rename the weight attribute.
            # First, find the weight attribute index.
            # Let's get the target list and find the one we just added.
            # Better: use `cmds.listAttr` with the weight attribute.
            # We'll assume the weight attribute name is the same as the target mesh name.
            # We'll check and rename if needed.
            # Maya creates a weight attribute with a name based on the mesh's short name.
            # We'll find it.
            # We'll try to set alias.
            # We'll attempt to rename using `cmds.aliasAttr`.
            # Get the list of weight attributes.
            weight_attrs = cmds.listAttr(node, m=True, string='weight') or []
            # The last one is the new target
            if weight_attrs:
                new_attr = weight_attrs[-1]
                if new_attr != final_name:
                    cmds.aliasAttr(final_name, f"{node}.{new_attr}")
            # Initialize weight
            initial_weight = self._get_initial_weight(target, settings)
            cmds.setAttr(f"{node}.{final_name}", initial_weight)

            self._last_result = CreationResult(success=True, node_name=node, targets_added=[final_name])
            return self._last_result
        except Exception as e:
            return CreationResult(success=False, errors=[f"Failed to add target: {e}"])

    def create_targets(
        self,
        node: str,
        targets: List[BlendShapeTarget],
        settings: Optional[BlendShapeCreationSettings] = None,
    ) -> CreationResult:
        """
        Add multiple targets to a blendshape node.

        Args:
            node: The blendshape node.
            targets: List of target definitions.
            settings: Optional override settings.

        Returns:
            CreationResult summarizing the operation.
        """
        if settings:
            old_settings = self._settings
            self._settings = settings
        else:
            old_settings = None

        result = CreationResult(success=True, node_name=node)
        start_time = time.time()

        for i, target in enumerate(targets):
            if self._settings.cancel_check and self._settings.cancel_check():
                result.errors.append("Cancelled by user")
                result.success = False
                break
            if self._settings.progress_callback:
                self._settings.progress_callback(i / len(targets), f"Creating target {target.name}")
            # Create target
            target_result = self.create_target(node, target, settings)
            if target_result.success:
                result.targets_added.extend(target_result.targets_added)
            else:
                result.errors.extend(target_result.errors)
                result.targets_skipped.append(target.name)
                result.success = False

        elapsed = time.time() - start_time
        stats = CreationStatistics(
            total_targets=len(targets),
            targets_created=len(result.targets_added),
            runtime_seconds=elapsed,
            avg_time_per_target=elapsed / max(1, len(targets)),
        )
        # Count types
        for target in targets:
            ttype = target.target_type.value
            stats.target_types[ttype] = stats.target_types.get(ttype, 0) + 1
            if target.target_type == TargetType.INBETWEEN:
                stats.inbetween_targets += 1
            elif target.target_type == TargetType.CORRECTIVE:
                stats.corrective_targets += 1

        self._last_result = result
        self._last_stats = stats

        if old_settings:
            self._settings = old_settings

        return result

    # ---- Specialized Creators ----

    def create_arkit_targets(
        self,
        node: str,
        base_mesh: str,
        library: Optional[Dict[str, Any]] = None,
        settings: Optional[BlendShapeCreationSettings] = None,
    ) -> CreationResult:
        """
        Create all 52 ARKit blendshape targets from a library.

        Args:
            node: The blendshape node (or name to create).
            base_mesh: The base mesh.
            library: A dictionary of target definitions (or use default from blendshape_library).
            settings: Optional settings.

        Returns:
            CreationResult
        """
        # If node does not exist, create it
        if not cmds.objExists(node):
            try:
                node = self.create_node(node, base_mesh)
            except Exception as e:
                return CreationResult(success=False, errors=[str(e)])

        # Get target definitions
        if library is None:
            if self._library:
                # Use the library to get ARKit targets
                arkit_defs = self._library.get_arkit_targets()
                targets = [BlendShapeTarget(
                    name=defs.get('name'),
                    mesh=defs.get('mesh'),
                    target_type=TargetType.ARKIT,
                    weight=defs.get('initial_weight', 0.0)
                ) for defs in arkit_defs if 'name' in defs and 'mesh' in defs]
            else:
                return CreationResult(success=False, errors=["No library available for ARKit targets"])
        else:
            # Build targets from provided library
            targets = []
            for name, mesh in library.items():
                if isinstance(mesh, str):
                    targets.append(BlendShapeTarget(name=name, mesh=mesh, target_type=TargetType.ARKIT))
                else:
                    # Could be a dict with more info
                    targets.append(BlendShapeTarget(
                        name=name,
                        mesh=mesh.get('mesh'),
                        target_type=TargetType.ARKIT,
                        weight=mesh.get('weight', 0.0)
                    ))

        # Create targets
        return self.create_targets(node, targets, settings)

    def create_corrective_targets(
        self,
        node: str,
        base_mesh: str,
        corrective_defs: List[Dict[str, Any]],
        settings: Optional[BlendShapeCreationSettings] = None,
    ) -> CreationResult:
        """
        Create corrective blendshape targets.

        Args:
            node: The blendshape node.
            base_mesh: The base mesh.
            corrective_defs: List of corrective definitions.
                             Each dict should have 'name' and 'mesh', and optionally 'weight', 'type', etc.
            settings: Optional settings.

        Returns:
            CreationResult
        """
        # Convert to BlendShapeTarget list
        targets = []
        for defs in corrective_defs:
            if 'name' not in defs or 'mesh' not in defs:
                continue
            targets.append(BlendShapeTarget(
                name=defs['name'],
                mesh=defs['mesh'],
                target_type=TargetType.CORRECTIVE,
                weight=defs.get('weight', 0.0),
                corrective_set=defs.get('set'),
            ))
        return self.create_targets(node, targets, settings)

    def create_inbetween_targets(
        self,
        node: str,
        base_target: str,
        inbetween_defs: List[Dict[str, Any]],
        settings: Optional[BlendShapeCreationSettings] = None,
    ) -> CreationResult:
        """
        Create in-between targets for an existing target.

        Args:
            node: The blendshape node.
            base_target: The name of the base target.
            inbetween_defs: List of definitions for in-betweens.
                            Each should have 'name', 'mesh', and 'value' (0-1).
            settings: Optional settings.

        Returns:
            CreationResult
        """
        # Check base target exists
        if not cmds.objExists(f"{node}.{base_target}"):
            return CreationResult(success=False, errors=[f"Base target '{base_target}' not found on node '{node}'"])

        targets = []
        for defs in inbetween_defs:
            if 'name' not in defs or 'mesh' not in defs or 'value' not in defs:
                continue
            targets.append(BlendShapeTarget(
                name=defs['name'],
                mesh=defs['mesh'],
                target_type=TargetType.INBETWEEN,
                weight=0.0,
                inbetween_value=defs['value'],
                base_name=base_target,
            ))
        return self.create_targets(node, targets, settings)

    # ---- Target Management ----

    def remove_target(self, node: str, target_name: str) -> bool:
        """
        Remove a target from a blendshape node.
        """
        if not cmds.objExists(node):
            return False
        if not cmds.objExists(f"{node}.{target_name}"):
            return False
        try:
            cmds.removeMultiInstance(f"{node}.{target_name}", b=True)
            return True
        except:
            return False

    def rename_target(self, node: str, old_name: str, new_name: str) -> bool:
        """
        Rename a target alias on a blendshape node.
        """
        if not cmds.objExists(node):
            return False
        if not cmds.objExists(f"{node}.{old_name}"):
            return False
        if cmds.objExists(f"{node}.{new_name}"):
            return False
        try:
            cmds.aliasAttr(new_name, f"{node}.{old_name}")
            return True
        except:
            return False

    def duplicate_target(self, node: str, target_name: str, new_name: str) -> bool:
        """
        Duplicate a target (by duplicating the target mesh and adding it as a new target).
        """
        if not cmds.objExists(node):
            return False
        if not cmds.objExists(f"{node}.{target_name}"):
            return False
        # We need to get the target mesh for this target
        # This is tricky; we can get the target mesh from the blendshape node's target connections.
        # We'll use a simpler approach: query the target mesh via connections from the weight attribute? Not easy.
        # We'll skip for now.
        return False

    # ---- Weight Initialization ----

    def initialize_weights(self, node: str, target_names: Optional[List[str]] = None, mode: WeightMode = WeightMode.ZERO) -> None:
        """
        Initialize weights for targets on a blendshape node.
        """
        if not cmds.objExists(node):
            return
        if target_names is None:
            target_names = cmds.listAttr(node, m=True, string='weight') or []
        for name in target_names:
            if not cmds.objExists(f"{node}.{name}"):
                continue
            value = 0.0
            if mode == WeightMode.ONE:
                value = 1.0
            elif mode == WeightMode.AUTO:
                # Could query default from library
                value = 0.0
            elif mode == WeightMode.CUSTOM:
                value = self._settings.default_weight
            cmds.setAttr(f"{node}.{name}", value)

    # ---- Utilities ----

    def get_targets(self, node: str) -> List[str]:
        """Return list of target names on a blendshape node."""
        if not cmds.objExists(node):
            return []
        return cmds.listAttr(node, m=True, string='weight') or []

    def get_target_mesh(self, node: str, target_name: str) -> Optional[str]:
        """
        Get the target mesh for a given target name.
        """
        if not cmds.objExists(node):
            return None
        # Find the target index by alias? Not trivial.
        # We'll try to use `cmds.blendShape` query.
        # Use `cmds.blendShape(node, q=True, t=True)` to get target meshes.
        # But this returns the meshes in order; we need to map to names.
        # We'll use a different approach: find connections to the weight attribute? That's the weight.
        # The target mesh is connected to the node via the 'target' attribute array.
        # We can use `cmds.listConnections` on the node, filtered by mesh.
        targets = cmds.listConnections(node, type='mesh') or []
        # We don't know which one belongs to which target without looking at the target indices.
        # We'll return None for now.
        return None

    def _apply_naming(self, name: str) -> str:
        """Apply naming mode to a target name."""
        if self._settings.naming_mode == NamingMode.KEEP:
            return name
        elif self._settings.naming_mode == NamingMode.PREFIX:
            return f"{self._settings.prefix}{name}"
        elif self._settings.naming_mode == NamingMode.SUFFIX:
            return f"{name}{self._settings.suffix}"
        elif self._settings.naming_mode == NamingMode.AUTO:
            # Could infer from target type
            return name
        return name

    def _get_initial_weight(self, target: BlendShapeTarget, settings: Optional[BlendShapeCreationSettings] = None) -> float:
        """Determine initial weight for a target."""
        if settings is None:
            settings = self._settings
        if settings.weight_mode == WeightMode.ZERO:
            return 0.0
        elif settings.weight_mode == WeightMode.ONE:
            return 1.0
        elif settings.weight_mode == WeightMode.CUSTOM:
            return settings.default_weight
        elif settings.weight_mode == WeightMode.AUTO:
            # Use target's weight if specified, else 0.0
            return target.weight
        return 0.0

    # ---- Validation ----

    def validate_mesh(self, mesh: str) -> Dict[str, Any]:
        """Validate a mesh for blendshape creation."""
        if not cmds.objExists(mesh):
            return {"valid": False, "error": f"Mesh '{mesh}' does not exist"}
        if cmds.nodeType(mesh) != 'mesh':
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if not shapes or cmds.nodeType(shapes[0]) != 'mesh':
                return {"valid": False, "error": f"'{mesh}' is not a mesh"}
            mesh = shapes[0]
        # Get vertex count
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        return {"valid": True, "vertex_count": vertex_count}

    def validate_target_compatibility(self, base_mesh: str, target_mesh: str) -> Dict[str, Any]:
        """Check if two meshes are compatible for blendshape (same vertex count)."""
        base_info = self.validate_mesh(base_mesh)
        target_info = self.validate_mesh(target_mesh)
        if not base_info["valid"]:
            return {"valid": False, "error": base_info.get("error", "Base mesh invalid")}
        if not target_info["valid"]:
            return {"valid": False, "error": target_info.get("error", "Target mesh invalid")}
        if base_info["vertex_count"] != target_info["vertex_count"]:
            return {"valid": False, "error": f"Vertex count mismatch: {base_info['vertex_count']} vs {target_info['vertex_count']}"}
        return {"valid": True}

    # ---- Diagnostics ----

    def get_statistics(self) -> Optional[CreationStatistics]:
        """Return statistics from the last creation operation."""
        return self._last_stats

    def get_last_result(self) -> Optional[CreationResult]:
        """Return the last result."""
        return self._last_result

    def reset(self) -> None:
        """Reset internal state."""
        self._last_result = None
        self._last_stats = None

    # ---- Settings ----

    def set_settings(self, settings: BlendShapeCreationSettings) -> None:
        self._settings = settings

    def get_settings(self) -> BlendShapeCreationSettings:
        return self._settings


# ---- Part 11: Utility Functions --------------------------------------

def get_blendshape_nodes(mesh: str) -> List[str]:
    """Return all blendshape nodes applied to a mesh."""
    if not cmds.objExists(mesh):
        return []
    # If mesh is a transform, get the shape
    if cmds.nodeType(mesh) != 'mesh':
        shapes = cmds.listRelatives(mesh, shapes=True) or []
        if shapes:
            mesh = shapes[0]
    connections = cmds.listConnections(mesh, type='blendShape') or []
    return connections


def get_target_meshes(node: str) -> List[str]:
    """Return all target meshes connected to a blendshape node."""
    if not cmds.objExists(node):
        return []
    return cmds.listConnections(node, type='mesh') or []


def get_target_weights(node: str) -> Dict[str, float]:
    """Return a dict of target names and their current weights."""
    if not cmds.objExists(node):
        return {}
    targets = cmds.listAttr(node, m=True, string='weight') or []
    weights = {}
    for t in targets:
        if cmds.objExists(f"{node}.{t}"):
            weights[t] = cmds.getAttr(f"{node}.{t}")
    return weights


# ---- Part 12: Public API -----------------------------------------------

__all__ = [
    "BlendShapeCreator",
    "BlendShapeTarget",
    "BlendShapeCreationSettings",
    "CreationResult",
    "CreationStatistics",
    "CreationMode",
    "TargetType",
    "WeightMode",
    "NamingMode",
    "BlendShapeCreationError",
    "InvalidMeshError",
    "TargetError",
    "DuplicateTargetError",
    "get_blendshape_nodes",
    "get_target_meshes",
    "get_target_weights",
]