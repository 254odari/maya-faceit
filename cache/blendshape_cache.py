"""
cache/blendshape_cache.py

Blendshape Runtime Cache System for Maya FaceIT.

This module caches every expensive blendshape-related computation so that
the plugin doesn't repeatedly query Maya's dependency graph or recalculate
deformation data. It serves as the primary data source for:
- Blendshape Manager
- Blendshape Builder
- ARKit
- Animation
- Correctives
- Inbetweens
- Drivers
- Exporters
- Validators

Responsibilities:
- Store and retrieve blendshape node information (targets, weights, aliases).
- Cache target metadata, indices, meshes, and topology.
- Cache current and default weights with locking states.
- Cache vertex deltas for targets.
- Cache corrective targets and their activation triggers.
- Cache inbetween targets and interpolation data.
- Cache ARKit mappings and 52-shape targets.
- Cache expression and viseme poses.
- Cache runtime evaluation data (frame-based weights).
- Invalidate and update cache entries when data changes.
- Provide statistics and diagnostics.

Dependencies:
- cache_base.py: BaseCache class.
- cache_utils.py: Key generation and utilities.
- cache_statistics.py: Statistics dataclass.
- blendshape_manager.py: For querying blendshape nodes.
- blendshape_delta.py: For vertex delta storage.
- blendshape_driver.py: For driver information.
- blendshape_correctives.py: For corrective data.
- blendshape_inbetweens.py: For inbetween data.
- blendshape_pose.py: For pose data.
- arkit/ (subpackage): ARKit definitions.

The module uses Maya's Python API and threading for thread safety.
"""

from __future__ import annotations

import copy
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Import base cache and utilities (with fallback)
try:
    from .cache_base import BaseCache, CacheSettings, CacheEntry, CacheMetadata, CacheStatus
    from .cache_utils import get_cache_key, hash_data, validate_cache_key, sanitize_key
    from .cache_statistics import CacheStatistics
except ImportError:
    # Minimal fallback
    class BaseCache:
        def __init__(self, name, cache_type, settings=None):
            self.name = name
            self.cache_type = cache_type
            self._storage = {}
            self._lock = threading.RLock()
        def store(self, key, value): pass
        def get(self, key): return None
        def delete(self, key): pass
        def clear(self): pass
        def contains(self, key): return False
        def size(self): return 0
        def statistics(self): return CacheStatistics()
        def memory_usage(self): return 0.0
    class CacheSettings: pass
    class CacheEntry: pass
    class CacheMetadata: pass
    class CacheStatus: pass
    def get_cache_key(*args, **kwargs): return str(args)
    def hash_data(data): return str(hash(str(data)))
    def validate_cache_key(key): return isinstance(key, str) and len(key) > 0
    def sanitize_key(key): return key.strip()
    class CacheStatistics:
        def __init__(self):
            self.hits = 0
            self.misses = 0
            self.hit_rate = 0.0
            self.memory_usage_mb = 0.0
            self.total_entries = 0
            self.by_type = {}
            self.invalidations = 0
            self.evictions = 0

# For Maya integration
try:
    import maya.cmds as cmds
    from maya.api import OpenMaya as om
except ImportError:
    # Dummy for testing
    class DummyMaya:
        pass
    cmds = DummyMaya()
    om = DummyMaya()

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class BlendshapeDataType(Enum):
    """Types of blendshape data that can be cached."""
    NODE = "node"
    TARGET = "target"
    WEIGHT = "weight"
    DELTA = "delta"
    CORRECTIVE = "corrective"
    INBETWEEN = "inbetween"
    POSE = "pose"
    DRIVER = "driver"
    ARKIT = "arkit"
    VISEME = "viseme"


class EvaluationMode(Enum):
    """Evaluation context for cached data."""
    STATIC = "static"
    LIVE = "live"
    ANIMATION = "animation"
    EXPORT = "export"
    PREVIEW = "preview"


class BlendshapeState(Enum):
    """State of a blendshape cache entry."""
    UNKNOWN = "unknown"
    READY = "ready"
    DIRTY = "dirty"
    INVALID = "invalid"
    DELETED = "deleted"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class BlendshapeNodeInfo:
    """Information about a blendshape node."""
    node_name: str
    base_mesh: str
    target_count: int
    target_names: List[str]
    target_indices: Dict[str, int]  # name -> index
    alias_table: Dict[str, str]  # alias -> target name
    input_connections: List[str]
    output_connections: List[str]
    uuid: str = ""


@dataclass
class TargetInfo:
    """Information about a specific target."""
    name: str
    index: int
    mesh: str
    vertex_count: int
    topology_hash: str
    bounding_box: Optional[Tuple[float, float, float, float, float, float]] = None
    default_weight: float = 0.0
    current_weight: float = 0.0
    locked: bool = False
    state: BlendshapeState = BlendshapeState.READY


@dataclass
class WeightInfo:
    """Weight information for a target."""
    target: str
    current: float
    default: float
    min: float = 0.0
    max: float = 1.0
    locked: bool = False
    animated: bool = False


@dataclass
class DeltaInfo:
    """Delta (vertex displacement) information for a target."""
    target: str
    vertex_count: int
    deltas: Optional[List[Tuple[int, Tuple[float, float, float]]]] = None
    sparse: bool = False
    changed_vertices: Optional[List[int]] = None
    magnitude_sum: float = 0.0
    last_updated: float = 0.0


@dataclass
class CorrectiveInfo:
    """Information about a corrective target."""
    name: str
    triggers: List[str]  # target names or joint names
    weight: float = 1.0
    activation_threshold: float = 0.5
    solver: str = "linear"
    affected_vertices: Optional[List[int]] = None


@dataclass
class InbetweenInfo:
    """Information about an inbetween target."""
    parent_target: str
    weight: float
    mesh: str
    interpolation_type: str = "linear"
    order: int = 0


@dataclass
class ARKitInfo:
    """Information about ARKit mapping."""
    arkit_channel: str
    target: str
    multiplier: float = 1.0
    offset: float = 0.0
    calibrated: bool = False


@dataclass
class PoseInfo:
    """Information about a facial pose."""
    name: str
    weights: Dict[str, float]  # target -> weight
    pose_type: str = "custom"
    tags: List[str] = field(default_factory=list)


@dataclass
class RuntimeInfo:
    """Runtime evaluation data for a frame."""
    frame_number: int
    time: float
    weights: Dict[str, float]
    evaluation_mode: EvaluationMode = EvaluationMode.LIVE
    dirty: bool = False


@dataclass
class BlendshapeStatistics:
    """Statistics for the blendshape cache."""
    total_nodes: int = 0
    total_targets: int = 0
    total_weights: int = 0
    total_deltas: int = 0
    total_correctives: int = 0
    total_inbetweens: int = 0
    total_poses: int = 0
    total_arkit: int = 0
    total_runtime_frames: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    memory_usage_mb: float = 0.0


@dataclass
class BlendshapeReport:
    """Diagnostic report for the blendshape cache."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[BlendshapeStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Blendshape Cache Manager ---------------------------------

class BlendshapeCache(BaseCache):
    """
    Blendshape Runtime Cache.

    Caches all blendshape-related data: nodes, targets, weights, deltas,
    correctives, inbetweens, drivers, ARKit mappings, poses, and runtime state.
    """

    def __init__(self, name: str = "blendshape_cache", settings: Optional[CacheSettings] = None):
        super().__init__(name=name, cache_type="blendshape", settings=settings)

        # Internal storage for each data category
        self._nodes: Dict[str, BlendshapeNodeInfo] = {}  # node_name -> info
        self._targets: Dict[str, TargetInfo] = {}  # target_name -> info
        self._weights: Dict[str, WeightInfo] = {}  # target -> weight info
        self._deltas: Dict[str, DeltaInfo] = {}  # target -> delta info
        self._correctives: Dict[str, CorrectiveInfo] = {}  # corrective_name -> info
        self._inbetweens: Dict[str, InbetweenInfo] = {}  # inbetween_name -> info
        self._poses: Dict[str, PoseInfo] = {}  # pose_name -> info
        self._arkit: Dict[str, ARKitInfo] = {}  # arkit_channel -> info
        self._runtime: Dict[int, RuntimeInfo] = {}  # frame_number -> runtime info

        # Lookup maps
        self._node_to_targets: Dict[str, List[str]] = {}  # node_name -> target names
        self._target_to_node: Dict[str, str] = {}  # target_name -> node_name
        self._alias_to_target: Dict[str, str] = {}  # alias -> target_name

        # Dirty tracking
        self._dirty_targets: Set[str] = set()
        self._dirty_nodes: Set[str] = set()

        self._lock = threading.RLock()

    # ---- Node Cache ----

    def store_node(self, node_info: BlendshapeNodeInfo) -> None:
        """Store a blendshape node information."""
        with self._lock:
            self._nodes[node_info.node_name] = node_info
            self._node_to_targets[node_info.node_name] = node_info.target_names
            for target in node_info.target_names:
                self._target_to_node[target] = node_info.node_name
            for alias, target in node_info.alias_table.items():
                self._alias_to_target[alias] = target
            # Store in base cache
            key = f"node_{node_info.node_name}"
            self.store(key, node_info)
            logger.debug(f"Stored blendshape node: {node_info.node_name}")

    def get_node(self, node_name: str) -> Optional[BlendshapeNodeInfo]:
        """Get node information by name."""
        with self._lock:
            # Check base cache first
            key = f"node_{node_name}"
            node = self.get(key)
            if node:
                self._update_hit()
                return node
            # Check internal dict
            node = self._nodes.get(node_name)
            if node:
                self.store(key, node)  # cache in base
                self._update_hit()
            else:
                self._update_miss()
            return node

    def list_nodes(self) -> List[str]:
        """Return all node names."""
        with self._lock:
            return list(self._nodes.keys())

    def get_targets_for_node(self, node_name: str) -> List[str]:
        """Return targets belonging to a node."""
        with self._lock:
            return self._node_to_targets.get(node_name, [])

    def get_node_for_target(self, target: str) -> Optional[str]:
        """Return the node that contains a target."""
        with self._lock:
            return self._target_to_node.get(target)

    def get_alias_target(self, alias: str) -> Optional[str]:
        """Resolve an alias to a target name."""
        with self._lock:
            return self._alias_to_target.get(alias)

    # ---- Target Cache ----

    def store_target(self, target_info: TargetInfo) -> None:
        """Store target information."""
        with self._lock:
            self._targets[target_info.name] = target_info
            # Also store weight info if not exists
            if target_info.name not in self._weights:
                self._weights[target_info.name] = WeightInfo(
                    target=target_info.name,
                    current=target_info.current_weight,
                    default=target_info.default_weight
                )
            # Store in base cache
            key = f"target_{target_info.name}"
            self.store(key, target_info)
            logger.debug(f"Stored target: {target_info.name}")

    def get_target(self, target_name: str) -> Optional[TargetInfo]:
        """Get target information."""
        with self._lock:
            key = f"target_{target_name}"
            target = self.get(key)
            if target:
                self._update_hit()
                return target
            target = self._targets.get(target_name)
            if target:
                self.store(key, target)
                self._update_hit()
            else:
                self._update_miss()
            return target

    def get_target_index(self, target_name: str) -> Optional[int]:
        """Get the index of a target."""
        target = self.get_target(target_name)
        return target.index if target else None

    def get_target_mesh(self, target_name: str) -> Optional[str]:
        """Get the target mesh for a target."""
        target = self.get_target(target_name)
        return target.mesh if target else None

    def get_target_vertex_count(self, target_name: str) -> Optional[int]:
        """Get the vertex count of the target."""
        target = self.get_target(target_name)
        return target.vertex_count if target else None

    def get_all_targets(self) -> List[str]:
        """Return all target names."""
        with self._lock:
            return list(self._targets.keys())

    # ---- Weight Cache ----

    def store_weight(self, weight_info: WeightInfo) -> None:
        """Store weight information."""
        with self._lock:
            self._weights[weight_info.target] = weight_info
            # Also update target's current weight if target exists
            if weight_info.target in self._targets:
                self._targets[weight_info.target].current_weight = weight_info.current
            # Store in base cache
            key = f"weight_{weight_info.target}"
            self.store(key, weight_info)

    def get_weight(self, target_name: str) -> Optional[WeightInfo]:
        """Get weight information for a target."""
        with self._lock:
            key = f"weight_{target_name}"
            weight = self.get(key)
            if weight:
                self._update_hit()
                return weight
            weight = self._weights.get(target_name)
            if weight:
                self.store(key, weight)
                self._update_hit()
            else:
                self._update_miss()
            return weight

    def get_current_weight(self, target_name: str) -> float:
        """Get the current weight of a target."""
        info = self.get_weight(target_name)
        return info.current if info else 0.0

    def set_current_weight(self, target_name: str, value: float) -> None:
        """Update the current weight of a target."""
        with self._lock:
            if target_name in self._weights:
                self._weights[target_name].current = value
                # Update target info
                if target_name in self._targets:
                    self._targets[target_name].current_weight = value
                # Mark as dirty
                self._dirty_targets.add(target_name)
                # Store update
                key = f"weight_{target_name}"
                self.store(key, self._weights[target_name])
            else:
                raise KeyError(f"Target '{target_name}' not found in weight cache")

    def lock_weight(self, target_name: str) -> None:
        """Lock a weight."""
        with self._lock:
            if target_name in self._weights:
                self._weights[target_name].locked = True
                # Update target info
                if target_name in self._targets:
                    self._targets[target_name].locked = True
            else:
                raise KeyError(f"Target '{target_name}' not found in weight cache")

    def unlock_weight(self, target_name: str) -> None:
        """Unlock a weight."""
        with self._lock:
            if target_name in self._weights:
                self._weights[target_name].locked = False
                if target_name in self._targets:
                    self._targets[target_name].locked = False
            else:
                raise KeyError(f"Target '{target_name}' not found in weight cache")

    def get_all_weights(self) -> Dict[str, float]:
        """Get a dictionary of all current weights."""
        with self._lock:
            return {t: info.current for t, info in self._weights.items()}

    # ---- Delta Cache ----

    def store_delta(self, delta_info: DeltaInfo) -> None:
        """Store delta information for a target."""
        with self._lock:
            self._deltas[delta_info.target] = delta_info
            # Store in base cache
            key = f"delta_{delta_info.target}"
            self.store(key, delta_info)
            logger.debug(f"Stored delta for target: {delta_info.target}")

    def get_delta(self, target_name: str) -> Optional[DeltaInfo]:
        """Get delta information for a target."""
        with self._lock:
            key = f"delta_{target_name}"
            delta = self.get(key)
            if delta:
                self._update_hit()
                return delta
            delta = self._deltas.get(target_name)
            if delta:
                self.store(key, delta)
                self._update_hit()
            else:
                self._update_miss()
            return delta

    def get_delta_deltas(self, target_name: str) -> Optional[List[Tuple[int, Tuple[float, float, float]]]]:
        """Get the actual vertex deltas for a target."""
        info = self.get_delta(target_name)
        return info.deltas if info else None

    def get_changed_vertices(self, target_name: str) -> Optional[List[int]]:
        """Get the list of vertices that are affected by a target."""
        info = self.get_delta(target_name)
        return info.changed_vertices if info else None

    # ---- Corrective Cache ----

    def store_corrective(self, corrective_info: CorrectiveInfo) -> None:
        """Store corrective information."""
        with self._lock:
            self._correctives[corrective_info.name] = corrective_info
            key = f"corrective_{corrective_info.name}"
            self.store(key, corrective_info)

    def get_corrective(self, name: str) -> Optional[CorrectiveInfo]:
        """Get corrective information by name."""
        with self._lock:
            key = f"corrective_{name}"
            corr = self.get(key)
            if corr:
                self._update_hit()
                return corr
            corr = self._correctives.get(name)
            if corr:
                self.store(key, corr)
                self._update_hit()
            else:
                self._update_miss()
            return corr

    def get_correctives_for_target(self, target_name: str) -> List[str]:
        """Get corrective names that affect a target (by trigger list)."""
        with self._lock:
            result = []
            for name, corr in self._correctives.items():
                if target_name in corr.triggers:
                    result.append(name)
            return result

    # ---- Inbetween Cache ----

    def store_inbetween(self, inbetween_info: InbetweenInfo) -> None:
        """Store inbetween information."""
        with self._lock:
            self._inbetweens[inbetween_info.parent_target] = inbetween_info
            key = f"inbetween_{inbetween_info.parent_target}"
            self.store(key, inbetween_info)

    def get_inbetween(self, parent_target: str) -> Optional[InbetweenInfo]:
        """Get inbetween information for a parent target."""
        with self._lock:
            key = f"inbetween_{parent_target}"
            inb = self.get(key)
            if inb:
                self._update_hit()
                return inb
            inb = self._inbetweens.get(parent_target)
            if inb:
                self.store(key, inb)
                self._update_hit()
            else:
                self._update_miss()
            return inb

    # ---- ARKit Cache ----

    def store_arkit(self, arkit_info: ARKitInfo) -> None:
        """Store ARKit mapping information."""
        with self._lock:
            self._arkit[arkit_info.arkit_channel] = arkit_info
            key = f"arkit_{arkit_info.arkit_channel}"
            self.store(key, arkit_info)

    def get_arkit(self, arkit_channel: str) -> Optional[ARKitInfo]:
        """Get ARKit mapping for a channel."""
        with self._lock:
            key = f"arkit_{arkit_channel}"
            info = self.get(key)
            if info:
                self._update_hit()
                return info
            info = self._arkit.get(arkit_channel)
            if info:
                self.store(key, info)
                self._update_hit()
            else:
                self._update_miss()
            return info

    def get_arkit_target(self, arkit_channel: str) -> Optional[str]:
        """Get the target associated with an ARKit channel."""
        info = self.get_arkit(arkit_channel)
        return info.target if info else None

    def get_all_arkit_mappings(self) -> Dict[str, str]:
        """Get all ARKit channel to target mappings."""
        with self._lock:
            return {ch: info.target for ch, info in self._arkit.items()}

    # ---- Pose Cache ----

    def store_pose(self, pose_info: PoseInfo) -> None:
        """Store pose information."""
        with self._lock:
            self._poses[pose_info.name] = pose_info
            key = f"pose_{pose_info.name}"
            self.store(key, pose_info)

    def get_pose(self, pose_name: str) -> Optional[PoseInfo]:
        """Get pose information by name."""
        with self._lock:
            key = f"pose_{pose_name}"
            pose = self.get(key)
            if pose:
                self._update_hit()
                return pose
            pose = self._poses.get(pose_name)
            if pose:
                self.store(key, pose)
                self._update_hit()
            else:
                self._update_miss()
            return pose

    def get_pose_weights(self, pose_name: str) -> Optional[Dict[str, float]]:
        """Get the weights of a pose."""
        pose = self.get_pose(pose_name)
        return pose.weights if pose else None

    def list_poses(self) -> List[str]:
        """List all pose names."""
        with self._lock:
            return list(self._poses.keys())

    # ---- Runtime Cache ----

    def store_runtime(self, runtime_info: RuntimeInfo) -> None:
        """Store runtime evaluation data for a frame."""
        with self._lock:
            self._runtime[runtime_info.frame_number] = runtime_info
            key = f"runtime_{runtime_info.frame_number}"
            self.store(key, runtime_info)

    def get_runtime(self, frame_number: int) -> Optional[RuntimeInfo]:
        """Get runtime data for a frame."""
        with self._lock:
            key = f"runtime_{frame_number}"
            runtime = self.get(key)
            if runtime:
                self._update_hit()
                return runtime
            runtime = self._runtime.get(frame_number)
            if runtime:
                self.store(key, runtime)
                self._update_hit()
            else:
                self._update_miss()
            return runtime

    def get_latest_runtime(self) -> Optional[RuntimeInfo]:
        """Get the most recent runtime data."""
        with self._lock:
            if not self._runtime:
                return None
            # Get the frame with the highest frame number
            max_frame = max(self._runtime.keys())
            return self._runtime[max_frame]

    def clear_runtime(self) -> None:
        """Clear all runtime data."""
        with self._lock:
            self._runtime.clear()
            # Remove from base cache
            for key in list(self._storage.keys()):
                if key.startswith("runtime_"):
                    self.delete(key)

    # ---- Invalidation ----

    def invalidate_target(self, target_name: str) -> None:
        """Invalidate a specific target."""
        with self._lock:
            self._dirty_targets.add(target_name)
            # Invalidate related caches
            self._deltas.pop(target_name, None)
            self._weights.pop(target_name, None)
            # Remove from base cache
            for prefix in ["target_", "weight_", "delta_"]:
                key = f"{prefix}{target_name}"
                self.delete(key)
            # Also invalidate correctives that depend on this target
            for corr_name, corr in list(self._correctives.items()):
                if target_name in corr.triggers:
                    self._correctives.pop(corr_name, None)
                    self.delete(f"corrective_{corr_name}")
            # Remove runtime data
            self.clear_runtime()

    def invalidate_node(self, node_name: str) -> None:
        """Invalidate a node and all its targets."""
        with self._lock:
            self._dirty_nodes.add(node_name)
            targets = self._node_to_targets.get(node_name, [])
            for target in targets:
                self.invalidate_target(target)
            # Remove node data
            self._nodes.pop(node_name, None)
            self._node_to_targets.pop(node_name, None)
            self.delete(f"node_{node_name}")

    def invalidate_all(self) -> None:
        """Invalidate all cached blendshape data."""
        with self._lock:
            self.clear()
            self._nodes.clear()
            self._targets.clear()
            self._weights.clear()
            self._deltas.clear()
            self._correctives.clear()
            self._inbetweens.clear()
            self._poses.clear()
            self._arkit.clear()
            self._runtime.clear()
            self._node_to_targets.clear()
            self._target_to_node.clear()
            self._alias_to_target.clear()
            self._dirty_targets.clear()
            self._dirty_nodes.clear()

    # ---- Validation ----

    def validate_node(self, node_name: str) -> List[str]:
        """Validate a node's cache integrity."""
        errors = []
        node = self.get_node(node_name)
        if not node:
            errors.append(f"Node '{node_name}' not found in cache")
        else:
            # Check targets exist
            for target in node.target_names:
                if target not in self._targets:
                    errors.append(f"Target '{target}' referenced by node '{node_name}' but not cached")
            # Check aliases
            for alias, target in node.alias_table.items():
                if target not in self._targets:
                    errors.append(f"Alias '{alias}' points to uncached target '{target}'")
        return errors

    def validate_all(self) -> BlendshapeReport:
        """Validate the entire blendshape cache."""
        report = BlendshapeReport(success=True)
        for node_name in self._nodes:
            errors = self.validate_node(node_name)
            if errors:
                report.errors.extend([f"Node {node_name}: {e}" for e in errors])
                report.success = False
        # Check for orphaned targets (not in any node)
        all_targets = set(self._targets.keys())
        node_targets = set()
        for targets in self._node_to_targets.values():
            node_targets.update(targets)
        orphans = all_targets - node_targets
        if orphans:
            report.warnings.append(f"Orphaned targets (not in any node): {list(orphans)}")
        # Check runtime consistency
        if self._runtime and self._weights:
            # Check if runtime weights match current weights for latest frame
            latest = self.get_latest_runtime()
            if latest:
                for target, weight in latest.weights.items():
                    current = self.get_current_weight(target)
                    if abs(weight - current) > 1e-6:
                        report.warnings.append(f"Runtime weight mismatch for '{target}': cache={current}, runtime={weight}")
        return report

    # ---- Statistics ----

    def statistics(self) -> CacheStatistics:
        """Return aggregated cache statistics."""
        stats = super().statistics()
        # Augment with blendshape-specific counts
        stats.total_entries = len(self._nodes) + len(self._targets) + len(self._weights) + len(self._deltas) + len(self._correctives)
        stats.by_type["nodes"] = len(self._nodes)
        stats.by_type["targets"] = len(self._targets)
        stats.by_type["weights"] = len(self._weights)
        stats.by_type["deltas"] = len(self._deltas)
        stats.by_type["correctives"] = len(self._correctives)
        stats.by_type["inbetweens"] = len(self._inbetweens)
        stats.by_type["poses"] = len(self._poses)
        stats.by_type["arkit"] = len(self._arkit)
        stats.by_type["runtime"] = len(self._runtime)
        return stats

    def get_blendshape_statistics(self) -> BlendshapeStatistics:
        """Get detailed blendshape statistics."""
        with self._lock:
            bs_stats = BlendshapeStatistics()
            bs_stats.total_nodes = len(self._nodes)
            bs_stats.total_targets = len(self._targets)
            bs_stats.total_weights = len(self._weights)
            bs_stats.total_deltas = len(self._deltas)
            bs_stats.total_correctives = len(self._correctives)
            bs_stats.total_inbetweens = len(self._inbetweens)
            bs_stats.total_poses = len(self._poses)
            bs_stats.total_arkit = len(self._arkit)
            bs_stats.total_runtime_frames = len(self._runtime)
            if self._statistics:
                bs_stats.cache_hits = self._statistics.hits
                bs_stats.cache_misses = self._statistics.misses
                total = bs_stats.cache_hits + bs_stats.cache_misses
                if total > 0:
                    bs_stats.hit_rate = bs_stats.cache_hits / total
            bs_stats.memory_usage_mb = self.memory_usage()
            return bs_stats

    # ---- Dirty Tracking ----

    def is_dirty(self, target_name: str) -> bool:
        """Check if a target is marked as dirty."""
        return target_name in self._dirty_targets

    def mark_clean(self, target_name: str) -> None:
        """Mark a target as clean (not dirty)."""
        self._dirty_targets.discard(target_name)

    def mark_clean_all(self) -> None:
        """Mark all targets as clean."""
        self._dirty_targets.clear()
        self._dirty_nodes.clear()

    # ---- Utility ----

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            super().clear()
            self._nodes.clear()
            self._targets.clear()
            self._weights.clear()
            self._deltas.clear()
            self._correctives.clear()
            self._inbetweens.clear()
            self._poses.clear()
            self._arkit.clear()
            self._runtime.clear()
            self._node_to_targets.clear()
            self._target_to_node.clear()
            self._alias_to_target.clear()
            self._dirty_targets.clear()
            self._dirty_nodes.clear()

    def prune_runtime(self, max_frames: int) -> int:
        """Remove old runtime frames to keep cache size under max_frames."""
        with self._lock:
            if len(self._runtime) <= max_frames:
                return 0
            sorted_frames = sorted(self._runtime.keys())
            to_remove = len(self._runtime) - max_frames
            removed = 0
            for frame_num in sorted_frames[:to_remove]:
                self._runtime.pop(frame_num, None)
                self.delete(f"runtime_{frame_num}")
                removed += 1
            return removed

    # ---- Hit/Miss Tracking ----

    def _update_hit(self):
        if self._statistics:
            self._statistics.hits += 1

    def _update_miss(self):
        if self._statistics:
            self._statistics.misses += 1


# ---- Part 17: Utilities ----------------------------------------------

def get_blendshape_cache() -> BlendshapeCache:
    """
    Get the global blendshape cache instance (singleton).
    """
    # Using a global variable or a registry pattern; for simplicity, we create a new one.
    # In production, you'd have a cache manager that provides this.
    return BlendshapeCache()


def invalidate_blendshape_cache() -> None:
    """Convenience function to invalidate the entire blendshape cache."""
    cache = get_blendshape_cache()
    cache.invalidate_all()


def get_cached_weight(target: str) -> float:
    """Convenience function to get a weight from the cache."""
    cache = get_blendshape_cache()
    return cache.get_current_weight(target)


def set_cached_weight(target: str, value: float) -> None:
    """Convenience function to set a weight in the cache."""
    cache = get_blendshape_cache()
    cache.set_current_weight(target, value)


# ---- Part 18: Public API -----------------------------------------------

__all__ = [
    "BlendshapeCache",
    "BlendshapeNodeInfo",
    "TargetInfo",
    "WeightInfo",
    "DeltaInfo",
    "CorrectiveInfo",
    "InbetweenInfo",
    "ARKitInfo",
    "PoseInfo",
    "RuntimeInfo",
    "BlendshapeStatistics",
    "BlendshapeReport",
    "BlendshapeDataType",
    "EvaluationMode",
    "BlendshapeState",
    "get_blendshape_cache",
    "invalidate_blendshape_cache",
    "get_cached_weight",
    "set_cached_weight",
]