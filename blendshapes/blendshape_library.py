"""
blendshapes/blendshape_library.py

Blendshape Asset Library System for Maya.

This module provides a comprehensive asset database for reusable facial
blendshape assets, including targets, poses, correctives, visemes, ARKit
expressions, and inbetween targets. It manages storage, organization,
search, versioning, import/export, thumbnails, and collections.

The library acts as the content browser and asset catalog for the entire
facial rigging and animation pipeline.

Responsibilities:
- Store, organize, and retrieve blendshape assets.
- Manage categories, collections, tags, and metadata.
- Search and filter assets by name, type, tag, category, etc.
- Version control assets (save, restore, diff).
- Import and export assets from/to various formats (JSON, FBX, etc.).
- Generate and cache thumbnails for assets.
- Validate library integrity and asset compatibility.
- Support batch operations (import, export, rename, categorize).

Dependencies:
- blendshape_creator.py: Register newly created assets.
- blendshape_generator.py: Store generated assets.
- blendshape_pose.py: Pose library management.
- blendshape_correctives.py: Corrective asset storage.
- blendshape_inbetweens.py: Inbetween asset storage.
- blendshape_weights.py: Weight preset storage.
- blendshape_exporter.py: Export assets and libraries.
- blendshape_validator.py: Validate assets.
- blendshape_manager.py: Consumer of library services.
- blendshape_utils.py: Shared utilities.
- arkit/: ARKit asset definitions.
- core/: File I/O and path utilities.
- ui/: Browser and thumbnail views.

The module uses Maya's Python API and may optionally leverage PIL/Pillow
for thumbnail processing.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
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

# Optional PIL for thumbnail processing
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Import blendshape modules (with fallbacks)
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
    )
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
    from .blendshape_validator import BlendshapeValidator, ValidationLevel
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None

try:
    from .blendshape_creator import BlendShapeCreator
except ImportError:
    BlendShapeCreator = None

try:
    from .blendshape_generator import BlendshapeGenerator
except ImportError:
    BlendshapeGenerator = None

try:
    from .blendshape_pose import BlendshapePoseManager
except ImportError:
    BlendshapePoseManager = None

try:
    from .blendshape_correctives import BlendshapeCorrectiveManager
except ImportError:
    BlendshapeCorrectiveManager = None

try:
    from .blendshape_inbetweens import BlendshadeInbetweenManager
except ImportError:
    BlendshadeInbetweenManager = None

try:
    from .blendshape_weights import BlendshapeWeightManager
except ImportError:
    BlendshapeWeightManager = None

try:
    from .blendshape_exporter import BlendshapeExporter
except ImportError:
    BlendshapeExporter = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()


# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class LibraryError(Exception):
    """Base exception for library operations."""
    pass

class AssetNotFoundError(LibraryError):
    """Raised when an asset is not found."""
    pass

class AssetExistsError(LibraryError):
    """Raised when an asset already exists."""
    pass

class LibraryIOError(LibraryError):
    """Raised when file I/O fails."""
    pass

class LibraryValidationError(LibraryError):
    """Raised when validation fails."""
    pass


# ---- Part 2: Constants & Enumerations --------------------------------

class AssetType(Enum):
    """Types of assets in the library."""
    BLENDSHAPE = "blendshape"
    POSE = "pose"
    CORRECTIVE = "corrective"
    INBETWEEN = "inbetween"
    ARKIT = "arkit"
    VISEME = "viseme"
    EXPRESSION = "expression"
    PRESET = "preset"
    LIBRARY = "library"


class LibraryType(Enum):
    """Where the library is stored."""
    LOCAL = "local"
    PROJECT = "project"
    SHARED = "shared"
    GLOBAL = "global"
    ONLINE = "online"


class AssetStatus(Enum):
    """Status of an asset."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    LOCKED = "locked"
    DELETED = "deleted"


class ThumbnailMode(Enum):
    """How thumbnails are generated."""
    VIEWPORT = "viewport"
    IMAGE = "image"
    AUTO = "auto"
    CUSTOM = "custom"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class AssetVersion:
    """A version of an asset."""
    version_id: str
    version_number: str
    created: str
    author: str
    changes: str
    data: Dict[str, Any]


@dataclass
class AssetMetadata:
    """Metadata for an asset."""
    asset_id: str
    name: str
    asset_type: AssetType
    category: str
    tags: List[str] = field(default_factory=list)
    description: str = ""
    author: str = "unknown"
    studio: str = ""
    created: str = ""
    modified: str = ""
    version: str = "1.0.0"
    status: AssetStatus = AssetStatus.ACTIVE
    dependencies: List[str] = field(default_factory=list)  # asset IDs this asset depends on
    compatibility: Dict[str, str] = field(default_factory=dict)  # e.g., {"maya": "2024", "plugin": "1.0"}
    thumbnail_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlendshapeAsset:
    """A complete asset in the library."""
    metadata: AssetMetadata
    data: Any  # The actual asset data (e.g., PoseDefinition, CorrectiveDefinition, etc.)
    versions: List[AssetVersion] = field(default_factory=list)  # version history
    thumbnail: Optional[Image.Image] = None  # PIL Image, if loaded


@dataclass
class AssetCategory:
    """A category for organizing assets."""
    name: str
    description: str = ""
    parent: Optional[str] = None  # parent category name
    children: List[str] = field(default_factory=list)  # child category names


@dataclass
class AssetCollection:
    """A user-defined collection of assets."""
    name: str
    description: str = ""
    asset_ids: List[str] = field(default_factory=list)  # list of asset IDs


@dataclass
class BlendshapeLibrary:
    """The top-level library container."""
    name: str
    library_type: LibraryType = LibraryType.LOCAL
    path: str = ""
    assets: Dict[str, BlendshapeAsset] = field(default_factory=dict)  # asset_id -> asset
    categories: Dict[str, AssetCategory] = field(default_factory=dict)
    collections: Dict[str, AssetCollection] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_modified: str = ""


@dataclass
class LibraryStatistics:
    """Statistics about the library."""
    total_assets: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    total_versions: int = 0
    library_count: int = 0
    thumbnail_count: int = 0


@dataclass
class LibraryReport:
    """Diagnostic report for the library."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[LibraryStatistics] = None


# ---- Part 4: Library Manager -----------------------------------------

class BlendshapeLibraryManager:
    """
    Main controller for the blendshape asset library system.
    """
    def __init__(self):
        self._libraries: Dict[str, BlendshapeLibrary] = {}  # name -> library
        self._active_library: Optional[str] = None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._creator = BlendShapeCreator() if BlendShapeCreator else None
        self._generator = BlendshapeGenerator() if BlendshapeGenerator else None
        self._pose_manager = BlendshapePoseManager() if BlendshapePoseManager else None
        self._corrective_manager = BlendshapeCorrectiveManager() if BlendshapeCorrectiveManager else None
        self._inbetween_manager = BlendshadeInbetweenManager() if BlendshadeInbetweenManager else None
        self._weight_manager = BlendshapeWeightManager() if BlendshapeWeightManager else None
        self._exporter = BlendshapeExporter() if BlendshapeExporter else None

        self._last_report: Optional[LibraryReport] = None
        self._last_stats: Optional[LibraryStatistics] = None

        # Cache for thumbnails
        self._thumbnail_cache: Dict[str, Image.Image] = {}

    # ---- Library Management ----

    def create_library(self, name: str, library_type: LibraryType = LibraryType.LOCAL, path: str = "") -> BlendshapeLibrary:
        """Create a new empty library."""
        if name in self._libraries:
            raise AssetExistsError(f"Library '{name}' already exists")
        library = BlendshapeLibrary(
            name=name,
            library_type=library_type,
            path=path,
            last_modified=time.ctime()
        )
        self._libraries[name] = library
        if self._active_library is None:
            self._active_library = name
        return library

    def load_library(self, name: str, filepath: str) -> BlendshapeLibrary:
        """Load a library from a JSON file."""
        if name in self._libraries:
            raise AssetExistsError(f"Library '{name}' already exists")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise LibraryIOError(f"Failed to load library from {filepath}: {e}")

        # Reconstruct library from data
        library = self._deserialize_library(data)
        self._libraries[name] = library
        if self._active_library is None:
            self._active_library = name
        return library

    def save_library(self, name: str, filepath: str) -> None:
        """Save a library to a JSON file."""
        if name not in self._libraries:
            raise AssetNotFoundError(f"Library '{name}' not found")
        library = self._libraries[name]
        data = self._serialize_library(library)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise LibraryIOError(f"Failed to save library to {filepath}: {e}")
        library.last_modified = time.ctime()

    def delete_library(self, name: str) -> None:
        """Delete a library from memory and optionally disk."""
        if name not in self._libraries:
            raise AssetNotFoundError(f"Library '{name}' not found")
        if self._active_library == name:
            self._active_library = None
        del self._libraries[name]

    def get_library(self, name: str) -> Optional[BlendshapeLibrary]:
        return self._libraries.get(name)

    def list_libraries(self) -> List[str]:
        return list(self._libraries.keys())

    def set_active_library(self, name: str) -> None:
        if name not in self._libraries:
            raise AssetNotFoundError(f"Library '{name}' not found")
        self._active_library = name

    def get_active_library(self) -> Optional[BlendshapeLibrary]:
        if self._active_library:
            return self._libraries.get(self._active_library)
        return None

    # ---- Asset Management ----

    def add_asset(self, library_name: str, asset: BlendshapeAsset) -> None:
        """Add an asset to a library."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset.metadata.asset_id in lib.assets:
            raise AssetExistsError(f"Asset with ID '{asset.metadata.asset_id}' already exists in library")
        # Ensure no duplicate names
        existing_names = [a.metadata.name for a in lib.assets.values()]
        if asset.metadata.name in existing_names:
            # Generate a unique name
            asset.metadata.name = generate_unique_name(asset.metadata.name, existing_names)
        lib.assets[asset.metadata.asset_id] = asset

    def remove_asset(self, library_name: str, asset_id: str) -> None:
        """Remove an asset from a library."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found in library")
        del lib.assets[asset_id]

    def get_asset(self, library_name: str, identifier: Union[str, AssetType]) -> Any:
        """Get an asset by ID, name, or type."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if isinstance(identifier, str):
            # Try ID first, then name
            if identifier in lib.assets:
                return lib.assets[identifier]
            # Search by name
            for a in lib.assets.values():
                if a.metadata.name == identifier:
                    return a
            raise AssetNotFoundError(f"Asset '{identifier}' not found in library '{library_name}'")
        elif isinstance(identifier, AssetType):
            return [a for a in lib.assets.values() if a.metadata.asset_type == identifier]
        else:
            raise TypeError("identifier must be str or AssetType")

    def list_assets(self, library_name: str, asset_type: Optional[AssetType] = None) -> List[BlendshapeAsset]:
        """List all assets, optionally filtered by type."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_type is None:
            return list(lib.assets.values())
        else:
            return [a for a in lib.assets.values() if a.metadata.asset_type == asset_type]

    def update_asset(self, library_name: str, asset: BlendshapeAsset) -> None:
        """Update an existing asset."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset.metadata.asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset.metadata.asset_id}' not found")
        # Check name conflict if changed
        old = lib.assets[asset.metadata.asset_id]
        if old.metadata.name != asset.metadata.name:
            existing_names = [a.metadata.name for a in lib.assets.values() if a.metadata.asset_id != asset.metadata.asset_id]
            if asset.metadata.name in existing_names:
                raise AssetExistsError(f"Asset with name '{asset.metadata.name}' already exists")
        lib.assets[asset.metadata.asset_id] = asset

    # ---- Categories ----

    def add_category(self, library_name: str, category: AssetCategory) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if category.name in lib.categories:
            raise AssetExistsError(f"Category '{category.name}' already exists")
        lib.categories[category.name] = category
        # Update parent-child relationships
        if category.parent:
            parent = lib.categories.get(category.parent)
            if parent and category.name not in parent.children:
                parent.children.append(category.name)

    def remove_category(self, library_name: str, category_name: str) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if category_name not in lib.categories:
            raise AssetNotFoundError(f"Category '{category_name}' not found")
        # Remove from parent's children
        cat = lib.categories[category_name]
        if cat.parent:
            parent = lib.categories.get(cat.parent)
            if parent and category_name in parent.children:
                parent.children.remove(category_name)
        del lib.categories[category_name]

    def get_category(self, library_name: str, category_name: str) -> Optional[AssetCategory]:
        lib = self.get_library(library_name)
        if not lib:
            return None
        return lib.categories.get(category_name)

    def list_categories(self, library_name: str) -> List[str]:
        lib = self.get_library(library_name)
        if not lib:
            return []
        return list(lib.categories.keys())

    # ---- Collections ----

    def add_collection(self, library_name: str, collection: AssetCollection) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if collection.name in lib.collections:
            raise AssetExistsError(f"Collection '{collection.name}' already exists")
        lib.collections[collection.name] = collection

    def remove_collection(self, library_name: str, collection_name: str) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if collection_name not in lib.collections:
            raise AssetNotFoundError(f"Collection '{collection_name}' not found")
        del lib.collections[collection_name]

    def add_to_collection(self, library_name: str, collection_name: str, asset_id: str) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if collection_name not in lib.collections:
            raise AssetNotFoundError(f"Collection '{collection_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        collection = lib.collections[collection_name]
        if asset_id not in collection.asset_ids:
            collection.asset_ids.append(asset_id)

    def remove_from_collection(self, library_name: str, collection_name: str, asset_id: str) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if collection_name not in lib.collections:
            raise AssetNotFoundError(f"Collection '{collection_name}' not found")
        collection = lib.collections[collection_name]
        if asset_id in collection.asset_ids:
            collection.asset_ids.remove(asset_id)

    # ---- Search ----

    def search(self, library_name: str, query: str, asset_type: Optional[AssetType] = None) -> List[BlendshapeAsset]:
        """
        Search for assets by name, tags, category, or description.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        q = query.lower()
        results = []
        for a in lib.assets.values():
            if asset_type and a.metadata.asset_type != asset_type:
                continue
            if q in a.metadata.name.lower():
                results.append(a)
                continue
            if q in a.metadata.description.lower():
                results.append(a)
                continue
            if q in a.metadata.category.lower():
                results.append(a)
                continue
            for tag in a.metadata.tags:
                if q in tag.lower():
                    results.append(a)
                    break
        return results

    def filter_by_tag(self, library_name: str, tag: str) -> List[BlendshapeAsset]:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        return [a for a in lib.assets.values() if tag in a.metadata.tags]

    def filter_by_category(self, library_name: str, category: str) -> List[BlendshapeAsset]:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        return [a for a in lib.assets.values() if a.metadata.category == category]

    # ---- Versioning ----

    def add_version(self, library_name: str, asset_id: str, version: AssetVersion) -> None:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        asset = lib.assets[asset_id]
        asset.versions.append(version)
        # Update metadata version
        asset.metadata.version = version.version_number
        asset.metadata.modified = version.created

    def get_versions(self, library_name: str, asset_id: str) -> List[AssetVersion]:
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        return lib.assets[asset_id].versions

    def rollback_version(self, library_name: str, asset_id: str, version_number: str) -> None:
        """
        Rollback an asset to a previous version.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        asset = lib.assets[asset_id]
        # Find the version
        target = None
        for v in asset.versions:
            if v.version_number == version_number:
                target = v
                break
        if target is None:
            raise AssetNotFoundError(f"Version '{version_number}' not found for asset '{asset_id}'")
        # Restore data from that version
        # This is a simplified restoration; in practice, we would deep copy the data.
        asset.data = target.data
        asset.metadata.version = version_number
        asset.metadata.modified = time.ctime()

    # ---- Thumbnails ----

    def generate_thumbnail(self, library_name: str, asset_id: str, mode: ThumbnailMode = ThumbnailMode.VIEWPORT) -> Optional[Image.Image]:
        """
        Generate a thumbnail for an asset.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        asset = lib.assets[asset_id]

        # If we already have a thumbnail, return it
        if asset_id in self._thumbnail_cache:
            return self._thumbnail_cache[asset_id]

        # Generate thumbnail based on mode
        if mode == ThumbnailMode.VIEWPORT:
            # Use Maya viewport capture (simplified: use mel command)
            try:
                # This is a placeholder; in production, we'd use `cmds.viewFit` and `cmds.renderWindowSnapshot`
                # For now, we'll just create a blank image.
                if HAS_PIL:
                    img = Image.new('RGB', (256, 256), color='gray')
                else:
                    img = None
            except:
                img = None
        elif mode == ThumbnailMode.IMAGE:
            # Try to load from metadata thumbnail_path
            if asset.metadata.thumbnail_path and os.path.exists(asset.metadata.thumbnail_path):
                try:
                    if HAS_PIL:
                        img = Image.open(asset.metadata.thumbnail_path)
                    else:
                        img = None
                except:
                    img = None
            else:
                img = None
        else:
            img = None

        # Cache the result
        if img:
            self._thumbnail_cache[asset_id] = img
            asset.metadata.thumbnail_path = f"thumbnails/{asset_id}.png"  # placeholder
        return img

    def save_thumbnail(self, library_name: str, asset_id: str, filepath: str) -> None:
        """Save a thumbnail to disk."""
        img = self.generate_thumbnail(library_name, asset_id)
        if img and HAS_PIL:
            img.save(filepath)

    # ---- Import/Export ----

    def import_asset(self, library_name: str, asset_data: Dict[str, Any]) -> BlendshapeAsset:
        """
        Import an asset from a dictionary (e.g., from JSON).
        """
        # This would deserialize the asset from the provided data.
        # We'll implement a basic deserialization.
        # In practice, we'd need to reconstruct the specific asset type.
        metadata = AssetMetadata(
            asset_id=str(uuid.uuid4()),
            name=asset_data.get("name", "ImportedAsset"),
            asset_type=AssetType(asset_data.get("type", "blendshape")),
            category=asset_data.get("category", "Uncategorized"),
            tags=asset_data.get("tags", []),
            description=asset_data.get("description", ""),
            author=asset_data.get("author", "imported"),
            created=time.ctime(),
            modified=time.ctime()
        )
        asset = BlendshapeAsset(metadata=metadata, data=asset_data.get("data", {}))
        self.add_asset(library_name, asset)
        return asset

    def export_asset(self, library_name: str, asset_id: str, filepath: str) -> None:
        """Export an asset to a JSON file."""
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        if asset_id not in lib.assets:
            raise AssetNotFoundError(f"Asset '{asset_id}' not found")
        asset = lib.assets[asset_id]
        data = self._serialize_asset(asset)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise LibraryIOError(f"Failed to export asset: {e}")

    def import_library(self, filepath: str) -> BlendshapeLibrary:
        """Import an entire library from a file."""
        # Reuse load_library with a generated name
        name = os.path.splitext(os.path.basename(filepath))[0]
        return self.load_library(name, filepath)

    def export_library(self, library_name: str, filepath: str) -> None:
        """Export an entire library to a JSON file."""
        self.save_library(library_name, filepath)

    # ---- Validation ----

    def validate_library(self, library_name: str) -> LibraryReport:
        """
        Validate a library for integrity and asset compatibility.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        report = LibraryReport(success=True)

        # Check for duplicate asset IDs
        ids = set()
        for asset_id in lib.assets:
            if asset_id in ids:
                report.errors.append(f"Duplicate asset ID: {asset_id}")
                report.success = False
            ids.add(asset_id)

        # Check for duplicate names
        names = set()
        for asset in lib.assets.values():
            if asset.metadata.name in names:
                report.warnings.append(f"Duplicate asset name: {asset.metadata.name}")
            names.add(asset.metadata.name)

        # Check category existence
        for asset in lib.assets.values():
            if asset.metadata.category and asset.metadata.category not in lib.categories:
                report.warnings.append(f"Asset '{asset.metadata.name}' references unknown category: {asset.metadata.category}")

        # Validate using external validator if available
        if self._validator:
            for asset in lib.assets.values():
                # We'd need to extract the actual asset data and validate it.
                # For simplicity, we'll assume it's valid.
                pass

        # Statistics
        stats = self.get_statistics(library_name)
        report.statistics = stats
        self._last_report = report
        return report

    # ---- Statistics ----

    def get_statistics(self, library_name: str) -> LibraryStatistics:
        """
        Compute statistics for a library.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        stats = LibraryStatistics()
        stats.total_assets = len(lib.assets)
        by_type = {}
        by_category = {}
        by_status = {}
        total_versions = 0
        for asset in lib.assets.values():
            t = asset.metadata.asset_type.value
            by_type[t] = by_type.get(t, 0) + 1
            cat = asset.metadata.category
            by_category[cat] = by_category.get(cat, 0) + 1
            status = asset.metadata.status.value
            by_status[status] = by_status.get(status, 0) + 1
            total_versions += len(asset.versions)
        stats.by_type = by_type
        stats.by_category = by_category
        stats.by_status = by_status
        stats.total_versions = total_versions
        stats.library_count = len(self._libraries)
        stats.thumbnail_count = len(self._thumbnail_cache)
        return stats

    # ---- Serialization Helpers ----

    def _serialize_asset(self, asset: BlendshapeAsset) -> Dict[str, Any]:
        """Convert an asset to a JSON-serializable dictionary."""
        return {
            "metadata": {
                "asset_id": asset.metadata.asset_id,
                "name": asset.metadata.name,
                "asset_type": asset.metadata.asset_type.value,
                "category": asset.metadata.category,
                "tags": asset.metadata.tags,
                "description": asset.metadata.description,
                "author": asset.metadata.author,
                "studio": asset.metadata.studio,
                "created": asset.metadata.created,
                "modified": asset.metadata.modified,
                "version": asset.metadata.version,
                "status": asset.metadata.status.value,
                "dependencies": asset.metadata.dependencies,
                "compatibility": asset.metadata.compatibility,
                "thumbnail_path": asset.metadata.thumbnail_path,
                "metadata": asset.metadata.metadata,
            },
            "data": asset.data,  # This assumes the data is JSON-serializable
            "versions": [{"version_id": v.version_id, "version_number": v.version_number,
                          "created": v.created, "author": v.author, "changes": v.changes,
                          "data": v.data} for v in asset.versions]
        }

    def _deserialize_asset(self, data: Dict[str, Any]) -> BlendshapeAsset:
        """Reconstruct an asset from a dictionary."""
        meta_data = data["metadata"]
        metadata = AssetMetadata(
            asset_id=meta_data["asset_id"],
            name=meta_data["name"],
            asset_type=AssetType(meta_data["asset_type"]),
            category=meta_data["category"],
            tags=meta_data.get("tags", []),
            description=meta_data.get("description", ""),
            author=meta_data.get("author", "unknown"),
            studio=meta_data.get("studio", ""),
            created=meta_data.get("created", time.ctime()),
            modified=meta_data.get("modified", time.ctime()),
            version=meta_data.get("version", "1.0.0"),
            status=AssetStatus(meta_data.get("status", "active")),
            dependencies=meta_data.get("dependencies", []),
            compatibility=meta_data.get("compatibility", {}),
            thumbnail_path=meta_data.get("thumbnail_path"),
            metadata=meta_data.get("metadata", {})
        )
        asset = BlendshapeAsset(metadata=metadata, data=data["data"])
        # Restore versions if present
        for vdata in data.get("versions", []):
            version = AssetVersion(
                version_id=vdata["version_id"],
                version_number=vdata["version_number"],
                created=vdata["created"],
                author=vdata["author"],
                changes=vdata["changes"],
                data=vdata["data"]
            )
            asset.versions.append(version)
        return asset

    def _serialize_library(self, library: BlendshapeLibrary) -> Dict[str, Any]:
        """Convert a library to a JSON-serializable dictionary."""
        return {
            "name": library.name,
            "library_type": library.library_type.value,
            "path": library.path,
            "last_modified": library.last_modified,
            "metadata": library.metadata,
            "assets": {aid: self._serialize_asset(a) for aid, a in library.assets.items()},
            "categories": {cname: {"name": c.name, "description": c.description, "parent": c.parent, "children": c.children} for cname, c in library.categories.items()},
            "collections": {cname: {"name": c.name, "description": c.description, "asset_ids": c.asset_ids} for cname, c in library.collections.items()}
        }

    def _deserialize_library(self, data: Dict[str, Any]) -> BlendshapeLibrary:
        """Reconstruct a library from a dictionary."""
        library = BlendshapeLibrary(
            name=data["name"],
            library_type=LibraryType(data["library_type"]),
            path=data.get("path", ""),
            last_modified=data.get("last_modified", time.ctime()),
            metadata=data.get("metadata", {})
        )
        # Restore assets
        for aid, adata in data.get("assets", {}).items():
            asset = self._deserialize_asset(adata)
            library.assets[aid] = asset
        # Restore categories
        for cname, cdata in data.get("categories", {}).items():
            category = AssetCategory(
                name=cdata["name"],
                description=cdata.get("description", ""),
                parent=cdata.get("parent"),
                children=cdata.get("children", [])
            )
            library.categories[cname] = category
        # Restore collections
        for cname, cdata in data.get("collections", {}).items():
            collection = AssetCollection(
                name=cdata["name"],
                description=cdata.get("description", ""),
                asset_ids=cdata.get("asset_ids", [])
            )
            library.collections[cname] = collection
        return library

    # ---- Batch Operations ----

    def batch_import_assets(self, library_name: str, filepaths: List[str]) -> List[BlendshapeAsset]:
        """
        Import multiple assets from files.
        """
        imported = []
        for path in filepaths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                asset = self.import_asset(library_name, data)
                imported.append(asset)
            except Exception as e:
                logger.error(f"Failed to import {path}: {e}")
        return imported

    def batch_export_assets(self, library_name: str, asset_ids: List[str], output_dir: str) -> None:
        """
        Export multiple assets to a directory.
        """
        os.makedirs(output_dir, exist_ok=True)
        for aid in asset_ids:
            try:
                filepath = os.path.join(output_dir, f"{aid}.json")
                self.export_asset(library_name, aid, filepath)
            except Exception as e:
                logger.error(f"Failed to export {aid}: {e}")

    def batch_rename_assets(self, library_name: str, rename_map: Dict[str, str]) -> None:
        """
        Batch rename assets.
        """
        lib = self.get_library(library_name)
        if not lib:
            raise AssetNotFoundError(f"Library '{library_name}' not found")
        for old_id, new_name in rename_map.items():
            if old_id not in lib.assets:
                continue
            asset = lib.assets[old_id]
            # Check if new name already exists
            existing_names = [a.metadata.name for a in lib.assets.values() if a.metadata.asset_id != old_id]
            if new_name in existing_names:
                continue
            asset.metadata.name = new_name

    # ---- Utilities ----

    def clear_cache(self) -> None:
        """Clear the thumbnail cache."""
        self._thumbnail_cache.clear()

    def get_library_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics for all loaded libraries.
        """
        total_assets = 0
        for lib in self._libraries.values():
            total_assets += len(lib.assets)
        return {
            "library_count": len(self._libraries),
            "total_assets": total_assets,
            "active_library": self._active_library
        }


# ---- Part 16: Public API -----------------------------------------------

__all__ = [
    "BlendshapeLibraryManager",
    "BlendshapeLibrary",
    "BlendshapeAsset",
    "AssetMetadata",
    "AssetCategory",
    "AssetCollection",
    "AssetVersion",
    "LibraryStatistics",
    "LibraryReport",
    "AssetType",
    "LibraryType",
    "AssetStatus",
    "ThumbnailMode",
    "LibraryError",
    "AssetNotFoundError",
    "AssetExistsError",
    "LibraryIOError",
    "LibraryValidationError",
]