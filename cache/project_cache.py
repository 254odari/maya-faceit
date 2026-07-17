"""
cache/project_cache.py

Project Cache System for Maya FaceIT.

This module represents the entire state of a Faceit project, allowing quick
restoration of working sessions without reanalyzing meshes, rebuilding rigs,
reloading ARKit mappings, or regenerating blendshape data.

It aggregates references to specialized caches (MeshCache, BlendshapeCache,
LandmarkCache) and adds project-level metadata, character data, rig data,
animation data, preferences, and UI state.

Responsibilities:
- Load, save, close, and reload Faceit projects.
- Manage project metadata, characters, rigs, animation, preferences, UI state.
- Integrate with MeshCache, BlendshapeCache, and LandmarkCache.
- Provide snapshot-based persistence (JSON, binary, compressed).
- Support autosave, backups, and crash recovery.
- Validate project integrity and cache compatibility.
- Provide diagnostics and statistics.

Dependencies:
- cache_base.py: BaseCache class.
- cache_manager.py: CacheManager for accessing specialized caches.
- mesh_cache.py, blendshape_cache.py, landmark_cache.py: Specialized caches.
- cache_utils.py: Utilities for serialization, hashing, etc.
- cache_statistics.py: Statistics dataclass.
- maya.cmds: For scene information.

The module uses Maya's Python API and threading for thread safety.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import shutil
import threading
import time
import uuid
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

# Maya imports
try:
    import maya.cmds as cmds
except ImportError:
    class DummyMaya:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyMaya()

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class ProjectState(Enum):
    """State of the project in the cache."""
    NEW = "new"
    OPEN = "open"
    MODIFIED = "modified"
    SAVED = "saved"
    CLOSED = "closed"
    CORRUPTED = "corrupted"


class SaveMode(Enum):
    """Mode for saving the project."""
    FULL = "full"
    INCREMENTAL = "incremental"
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    BACKUP = "backup"


class CacheVersionState(Enum):
    """Compatibility of cached project with current plugin version."""
    CURRENT = "current"
    OUTDATED = "outdated"
    INCOMPATIBLE = "incompatible"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class VersionInfo:
    """Version information for the project cache."""
    plugin_version: str
    cache_version: str
    maya_version: str
    schema_version: int = 1


@dataclass
class ProjectMetadata:
    """Metadata for a Faceit project."""
    project_id: str
    name: str
    created: str
    last_modified: str
    author: str = ""
    scene_file: str = ""
    description: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)


@dataclass
class CharacterData:
    """Data for a character in the project."""
    name: str
    namespace: str = ""
    meshes: List[str] = field(default_factory=list)  # mesh names or UUIDs
    blendshape_node: str = ""
    arkit_mapping: Dict[str, str] = field(default_factory=dict)  # arkit_channel -> target
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RigData:
    """Data for the facial rig."""
    controllers: List[str] = field(default_factory=list)  # controller names
    joints: List[str] = field(default_factory=list)       # joint names
    driver_network: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    spaces: Dict[str, Any] = field(default_factory=dict)
    control_shapes: Dict[str, str] = field(default_factory=dict)  # controller -> shape
    display_layers: List[str] = field(default_factory=list)


@dataclass
class AnimationData:
    """Data for animation."""
    timeline_start: int = 1
    timeline_end: int = 100
    animation_layers: List[str] = field(default_factory=list)
    keyframes: Dict[str, Any] = field(default_factory=dict)  # target -> keyframes
    curves: Dict[str, Any] = field(default_factory=dict)
    baked_data: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreferencesData:
    """Plugin preferences."""
    solver_settings: Dict[str, Any] = field(default_factory=dict)
    mirror_options: Dict[str, Any] = field(default_factory=dict)
    export_settings: Dict[str, Any] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    language: str = "en_US"


@dataclass
class UIStateData:
    """UI state for the project."""
    window_positions: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict)
    docked_windows: List[str] = field(default_factory=list)
    expanded_panels: List[str] = field(default_factory=list)
    selected_tabs: Dict[str, str] = field(default_factory=dict)
    selection: List[str] = field(default_factory=list)
    viewport_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectCacheEntry:
    """Complete project state."""
    metadata: ProjectMetadata
    characters: List[CharacterData]
    rig: RigData
    animation: AnimationData
    preferences: PreferencesData
    ui_state: UIStateData
    version: VersionInfo
    mesh_cache_snapshot: Optional[Dict[str, Any]] = None   # serialized mesh cache
    blendshape_cache_snapshot: Optional[Dict[str, Any]] = None
    landmark_cache_snapshot: Optional[Dict[str, Any]] = None
    validation_reports: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    state: ProjectState = ProjectState.NEW
    last_saved: str = ""
    autosave_timestamp: str = ""


# ---- Part 4: Project Cache Manager ------------------------------------

class ProjectCache(BaseCache):
    """
    Project-level cache that aggregates all project state and specialized caches.

    Provides a single API for loading, saving, and managing Faceit projects.
    """

    def __init__(self, name: str = "project_cache", settings: Optional[CacheSettings] = None):
        super().__init__(name=name, cache_type="project", settings=settings)

        # Current project entry
        self._current_project: Optional[ProjectCacheEntry] = None
        self._project_path: str = ""

        # References to specialized caches (set by cache manager)
        self._mesh_cache = None
        self._blendshape_cache = None
        self._landmark_cache = None

        # Lock for thread safety
        self._project_lock = threading.RLock()

        # Autosave timer
        self._autosave_interval = 300  # seconds
        self._last_autosave = time.time()
        self._autosave_enabled = True

        # Backup management
        self._backup_dir = ""
        self._max_backups = 10

        logger.debug("ProjectCache initialized")

    # ---- Integration with Specialized Caches ----

    def set_mesh_cache(self, mesh_cache) -> None:
        """Set the mesh cache reference."""
        self._mesh_cache = mesh_cache

    def set_blendshape_cache(self, blendshape_cache) -> None:
        """Set the blendshape cache reference."""
        self._blendshape_cache = blendshape_cache

    def set_landmark_cache(self, landmark_cache) -> None:
        """Set the landmark cache reference."""
        self._landmark_cache = landmark_cache

    # ---- Project Lifecycle ----

    def create_project(self, name: str, author: str = "") -> ProjectCacheEntry:
        """
        Create a new Faceit project.
        """
        with self._project_lock:
            project_id = str(uuid.uuid4())
            now = time.ctime()
            metadata = ProjectMetadata(
                project_id=project_id,
                name=name,
                created=now,
                last_modified=now,
                author=author
            )
            version = self._get_version_info()

            entry = ProjectCacheEntry(
                metadata=metadata,
                characters=[],
                rig=RigData(),
                animation=AnimationData(),
                preferences=PreferencesData(),
                ui_state=UIStateData(),
                version=version,
                state=ProjectState.NEW,
                last_saved=now
            )
            self._current_project = entry
            self._project_path = ""
            logger.info(f"Created new project: {name} ({project_id})")
            return entry

    def load_project(self, filepath: str) -> ProjectCacheEntry:
        """
        Load a project from disk.
        """
        with self._project_lock:
            # Load from disk
            entry = self._load_from_disk(filepath)
            if entry is None:
                raise IOError(f"Failed to load project from {filepath}")

            # Validate compatibility
            version_state = self._check_version_compatibility(entry.version)
            if version_state == CacheVersionState.INCOMPATIBLE:
                logger.warning(f"Project version {entry.version.cache_version} is incompatible with current version")
                entry.state = ProjectState.CORRUPTED
                self._current_project = entry
                self._project_path = filepath
                return entry

            # Restore specialized caches from snapshots if available
            if self._mesh_cache and entry.mesh_cache_snapshot:
                try:
                    self._mesh_cache.import_data(entry.mesh_cache_snapshot)
                    logger.debug("Restored mesh cache from snapshot")
                except Exception as e:
                    logger.warning(f"Failed to restore mesh cache: {e}")

            if self._blendshape_cache and entry.blendshape_cache_snapshot:
                try:
                    self._blendshape_cache.import_data(entry.blendshape_cache_snapshot)
                    logger.debug("Restored blendshape cache from snapshot")
                except Exception as e:
                    logger.warning(f"Failed to restore blendshape cache: {e}")

            if self._landmark_cache and entry.landmark_cache_snapshot:
                try:
                    self._landmark_cache.import_data(entry.landmark_cache_snapshot)
                    logger.debug("Restored landmark cache from snapshot")
                except Exception as e:
                    logger.warning(f"Failed to restore landmark cache: {e}")

            entry.state = ProjectState.OPEN
            self._current_project = entry
            self._project_path = filepath
            logger.info(f"Loaded project from {filepath}")
            return entry

    def save_project(self, filepath: str = "", mode: SaveMode = SaveMode.FULL) -> bool:
        """
        Save the current project to disk.
        """
        with self._project_lock:
            if self._current_project is None:
                logger.error("No project to save")
                return False

            # Use provided path or existing path
            if filepath:
                self._project_path = filepath
            elif not self._project_path:
                logger.error("No filepath specified and no existing project path")
                return False

            # Update metadata
            self._current_project.metadata.last_modified = time.ctime()
            self._current_project.last_saved = time.ctime()
            self._current_project.state = ProjectState.SAVED

            # Capture snapshots from specialized caches
            if mode == SaveMode.FULL:
                self._capture_snapshots()

            # Save to disk
            success = self._save_to_disk(self._project_path, mode)
            if success:
                logger.info(f"Saved project to {self._project_path}")
                return True
            else:
                logger.error(f"Failed to save project to {self._project_path}")
                return False

    def close_project(self) -> None:
        """Close the current project without saving (will prompt user)."""
        with self._project_lock:
            if self._current_project:
                self._current_project.state = ProjectState.CLOSED
                self._current_project = None
                self._project_path = ""
                logger.info("Closed project")

    def reload_project(self) -> Optional[ProjectCacheEntry]:
        """
        Reload the current project from disk (discarding unsaved changes).
        """
        if not self._project_path:
            logger.error("No project path to reload")
            return None
        return self.load_project(self._project_path)

    # ---- Backup and Autosave ----

    def backup(self, backup_path: Optional[str] = None) -> str:
        """
        Create a backup of the current project.
        """
        if self._current_project is None:
            logger.error("No project to backup")
            return ""

        if backup_path is None:
            backup_dir = self._backup_dir or os.path.dirname(self._project_path)
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{os.path.splitext(os.path.basename(self._project_path))[0]}_backup_{timestamp}.faceit"
            backup_path = os.path.join(backup_dir, backup_name)

        # Save a copy
        old_path = self._project_path
        self.save_project(backup_path, SaveMode.FULL)
        self._project_path = old_path  # restore original path

        logger.info(f"Created backup at {backup_path}")
        return backup_path

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore from a backup file.
        """
        try:
            self.load_project(backup_path)
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def autosave(self) -> None:
        """Perform an autosave if enabled and time interval has passed."""
        if not self._autosave_enabled:
            return
        if self._current_project is None:
            return
        now = time.time()
        if now - self._last_autosave >= self._autosave_interval:
            if self._project_path:
                # Save to autosave file
                autosave_dir = os.path.join(os.path.dirname(self._project_path), "autosave")
                os.makedirs(autosave_dir, exist_ok=True)
                autosave_file = os.path.join(autosave_dir, f"{os.path.splitext(os.path.basename(self._project_path))[0]}_autosave.faceit")
                self._current_project.autosave_timestamp = time.ctime()
                self.save_project(autosave_file, SaveMode.AUTOMATIC)
                self._last_autosave = now
                logger.debug("Autosaved project")

    # ---- Project Query ----

    def get_project(self) -> Optional[ProjectCacheEntry]:
        """Return the current project entry."""
        with self._project_lock:
            return self._current_project

    def get_metadata(self) -> Optional[ProjectMetadata]:
        """Return project metadata."""
        entry = self.get_project()
        return entry.metadata if entry else None

    def get_characters(self) -> List[CharacterData]:
        """Return character data."""
        entry = self.get_project()
        return entry.characters if entry else []

    def get_rig_data(self) -> Optional[RigData]:
        """Return rig data."""
        entry = self.get_project()
        return entry.rig if entry else None

    def get_animation_data(self) -> Optional[AnimationData]:
        """Return animation data."""
        entry = self.get_project()
        return entry.animation if entry else None

    def get_preferences(self) -> Optional[PreferencesData]:
        """Return preferences."""
        entry = self.get_project()
        return entry.preferences if entry else None

    def get_ui_state(self) -> Optional[UIStateData]:
        """Return UI state."""
        entry = self.get_project()
        return entry.ui_state if entry else None

    # ---- Project Modification ----

    def add_character(self, character: CharacterData) -> None:
        """Add a character to the project."""
        with self._project_lock:
            if self._current_project is None:
                raise RuntimeError("No project loaded")
            self._current_project.characters.append(character)
            self._current_project.state = ProjectState.MODIFIED

    def remove_character(self, name: str) -> bool:
        """Remove a character by name."""
        with self._project_lock:
            if self._current_project is None:
                return False
            for i, char in enumerate(self._current_project.characters):
                if char.name == name:
                    del self._current_project.characters[i]
                    self._current_project.state = ProjectState.MODIFIED
                    return True
            return False

    def update_character(self, character: CharacterData) -> bool:
        """Update an existing character."""
        with self._project_lock:
            if self._current_project is None:
                return False
            for i, char in enumerate(self._current_project.characters):
                if char.name == character.name:
                    self._current_project.characters[i] = character
                    self._current_project.state = ProjectState.MODIFIED
                    return True
            return False

    def update_rig_data(self, rig_data: RigData) -> None:
        """Update rig data."""
        with self._project_lock:
            if self._current_project is None:
                raise RuntimeError("No project loaded")
            self._current_project.rig = rig_data
            self._current_project.state = ProjectState.MODIFIED

    def update_animation_data(self, animation_data: AnimationData) -> None:
        """Update animation data."""
        with self._project_lock:
            if self._current_project is None:
                raise RuntimeError("No project loaded")
            self._current_project.animation = animation_data
            self._current_project.state = ProjectState.MODIFIED

    def update_preferences(self, preferences: PreferencesData) -> None:
        """Update preferences."""
        with self._project_lock:
            if self._current_project is None:
                raise RuntimeError("No project loaded")
            self._current_project.preferences = preferences
            self._current_project.state = ProjectState.MODIFIED

    def update_ui_state(self, ui_state: UIStateData) -> None:
        """Update UI state."""
        with self._project_lock:
            if self._current_project is None:
                raise RuntimeError("No project loaded")
            self._current_project.ui_state = ui_state
            self._current_project.state = ProjectState.MODIFIED

    # ---- Persistence ----

    def _capture_snapshots(self) -> None:
        """Capture snapshots of specialized caches into the project entry."""
        if self._current_project is None:
            return

        if self._mesh_cache:
            self._current_project.mesh_cache_snapshot = self._mesh_cache.export_data()
        if self._blendshape_cache:
            self._current_project.blendshape_cache_snapshot = self._blendshape_cache.export_data()
        if self._landmark_cache:
            self._current_project.landmark_cache_snapshot = self._landmark_cache.export_data()

    def _save_to_disk(self, filepath: str, mode: SaveMode) -> bool:
        """Serialize project entry to disk."""
        if self._current_project is None:
            return False

        # Update version info
        self._current_project.version = self._get_version_info()

        # Serialize to dict
        data = self._serialize_project_entry(self._current_project)

        # Determine format based on file extension
        if filepath.endswith('.faceit'):
            # Use JSON with optional compression
            try:
                import gzip
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                return True
            except:
                # Fallback to plain JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                return True
        elif filepath.endswith('.json'):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        else:
            # Try plain JSON with .faceit extension
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True

    def _load_from_disk(self, filepath: str) -> Optional[ProjectCacheEntry]:
        """Deserialize project entry from disk."""
        try:
            if filepath.endswith('.faceit'):
                import gzip
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            return self._deserialize_project_entry(data)
        except Exception as e:
            logger.error(f"Failed to load project from {filepath}: {e}")
            return None

    def _serialize_project_entry(self, entry: ProjectCacheEntry) -> Dict[str, Any]:
        """Convert a ProjectCacheEntry to a JSON-serializable dict."""
        return {
            "metadata": entry.metadata.__dict__,
            "characters": [c.__dict__ for c in entry.characters],
            "rig": entry.rig.__dict__,
            "animation": entry.animation.__dict__,
            "preferences": entry.preferences.__dict__,
            "ui_state": entry.ui_state.__dict__,
            "version": entry.version.__dict__,
            "mesh_cache_snapshot": entry.mesh_cache_snapshot,
            "blendshape_cache_snapshot": entry.blendshape_cache_snapshot,
            "landmark_cache_snapshot": entry.landmark_cache_snapshot,
            "validation_reports": entry.validation_reports,
            "statistics": entry.statistics,
            "state": entry.state.value,
            "last_saved": entry.last_saved,
            "autosave_timestamp": entry.autosave_timestamp,
        }

    def _deserialize_project_entry(self, data: Dict[str, Any]) -> ProjectCacheEntry:
        """Reconstruct a ProjectCacheEntry from a dict."""
        # Reconstruct metadata
        metadata = ProjectMetadata(**data["metadata"])
        characters = [CharacterData(**c) for c in data.get("characters", [])]
        rig = RigData(**data["rig"])
        animation = AnimationData(**data["animation"])
        preferences = PreferencesData(**data["preferences"])
        ui_state = UIStateData(**data["ui_state"])
        version = VersionInfo(**data["version"])
        entry = ProjectCacheEntry(
            metadata=metadata,
            characters=characters,
            rig=rig,
            animation=animation,
            preferences=preferences,
            ui_state=ui_state,
            version=version,
            mesh_cache_snapshot=data.get("mesh_cache_snapshot"),
            blendshape_cache_snapshot=data.get("blendshape_cache_snapshot"),
            landmark_cache_snapshot=data.get("landmark_cache_snapshot"),
            validation_reports=data.get("validation_reports", []),
            statistics=data.get("statistics", {}),
            state=ProjectState(data.get("state", "new")),
            last_saved=data.get("last_saved", ""),
            autosave_timestamp=data.get("autosave_timestamp", "")
        )
        return entry

    def _get_version_info(self) -> VersionInfo:
        """Get current version information."""
        import sys
        maya_version = cmds.about(version=True) if hasattr(cmds, 'about') else "Unknown"
        return VersionInfo(
            plugin_version="1.0.0",
            cache_version="1.0",
            maya_version=maya_version,
            schema_version=1
        )

    def _check_version_compatibility(self, version: VersionInfo) -> CacheVersionState:
        """Check compatibility of cached project with current plugin version."""
        # For now, assume compatible if schema_version matches
        current = self._get_version_info()
        if version.schema_version == current.schema_version:
            return CacheVersionState.CURRENT
        elif version.schema_version < current.schema_version:
            # Could implement migration
            return CacheVersionState.OUTDATED
        else:
            return CacheVersionState.INCOMPATIBLE

    # ---- Validation ----

    def validate_project(self) -> Dict[str, Any]:
        """
        Validate the current project integrity.
        """
        report = {"success": True, "errors": [], "warnings": []}
        if self._current_project is None:
            report["errors"].append("No project loaded")
            report["success"] = False
            return report

        # Check basic fields
        if not self._current_project.metadata.project_id:
            report["errors"].append("Missing project ID")
            report["success"] = False
        if not self._current_project.metadata.name:
            report["warnings"].append("Project has no name")

        # Check characters
        for char in self._current_project.characters:
            if not char.name:
                report["warnings"].append("Character has no name")
            if not char.meshes:
                report["warnings"].append(f"Character '{char.name}' has no meshes")

        # Validate against Maya scene? Could check if mesh exists etc.
        # Not necessary here.

        # Check version compatibility
        version_state = self._check_version_compatibility(self._current_project.version)
        if version_state == CacheVersionState.INCOMPATIBLE:
            report["errors"].append(f"Project version {self._current_project.version.cache_version} is incompatible")
            report["success"] = False
        elif version_state == CacheVersionState.OUTDATED:
            report["warnings"].append(f"Project version {self._current_project.version.cache_version} is outdated, consider migrating")

        return report

    # ---- Statistics ----

    def statistics(self) -> CacheStatistics:
        """Return cache statistics with project-specific data."""
        stats = super().statistics()
        if self._current_project:
            stats.total_entries = 1
            stats.by_type["project"] = 1
            stats.by_type["characters"] = len(self._current_project.characters)
            stats.by_type["mesh_snapshot"] = 1 if self._current_project.mesh_cache_snapshot else 0
            stats.by_type["blendshape_snapshot"] = 1 if self._current_project.blendshape_cache_snapshot else 0
            stats.by_type["landmark_snapshot"] = 1 if self._current_project.landmark_cache_snapshot else 0
        return stats

    def get_project_statistics(self) -> Dict[str, Any]:
        """Get detailed project statistics."""
        if self._current_project is None:
            return {}
        entry = self._current_project
        stats = {
            "project_name": entry.metadata.name,
            "project_id": entry.metadata.project_id,
            "characters": len(entry.characters),
            "has_mesh_snapshot": entry.mesh_cache_snapshot is not None,
            "has_blendshape_snapshot": entry.blendshape_cache_snapshot is not None,
            "has_landmark_snapshot": entry.landmark_cache_snapshot is not None,
            "validation_reports": len(entry.validation_reports),
            "state": entry.state.value,
            "last_saved": entry.last_saved,
            "autosave_timestamp": entry.autosave_timestamp,
        }
        return stats

    # ---- Utility ----

    def clear(self) -> None:
        """Clear the project cache."""
        with self._project_lock:
            super().clear()
            self._current_project = None
            self._project_path = ""

    def is_modified(self) -> bool:
        """Check if the current project has unsaved modifications."""
        if self._current_project is None:
            return False
        return self._current_project.state == ProjectState.MODIFIED

    def set_autosave_interval(self, seconds: int) -> None:
        """Set the autosave interval in seconds."""
        self._autosave_interval = seconds

    def enable_autosave(self, enabled: bool) -> None:
        """Enable or disable autosave."""
        self._autosave_enabled = enabled

    def set_backup_dir(self, directory: str) -> None:
        """Set the directory for backups."""
        self._backup_dir = directory

    def set_max_backups(self, count: int) -> None:
        """Set the maximum number of backups to keep."""
        self._max_backups = count

    def prune_backups(self) -> int:
        """Remove old backups beyond the maximum limit."""
        if not self._backup_dir or not os.path.exists(self._backup_dir):
            return 0
        backups = [f for f in os.listdir(self._backup_dir) if f.endswith('.faceit') and 'backup' in f]
        if len(backups) <= self._max_backups:
            return 0
        backups.sort(key=lambda f: os.path.getmtime(os.path.join(self._backup_dir, f)))
        to_delete = backups[:-self._max_backups]
        for f in to_delete:
            os.remove(os.path.join(self._backup_dir, f))
        return len(to_delete)


# ---- Part 17: Utilities ----------------------------------------------

def get_project_cache() -> ProjectCache:
    """Get the global project cache instance."""
    # In production, this would be managed by the CacheManager.
    # For simplicity, we create a new instance.
    return ProjectCache()


# ---- Part 18: Public API -----------------------------------------------

__all__ = [
    "ProjectCache",
    "ProjectCacheEntry",
    "ProjectMetadata",
    "CharacterData",
    "RigData",
    "AnimationData",
    "PreferencesData",
    "UIStateData",
    "VersionInfo",
    "ProjectState",
    "SaveMode",
    "CacheVersionState",
    "get_project_cache",
]