"""
maya_faceit.expression.library

Expression Database.

This module provides a persistent repository for facial expression definitions,
with support for metadata, categories, tags, search, import/export, and
integration with the ExpressionGenerator and PoseLibrary.

The ExpressionLibrary acts as a central catalog for all expressions used
in the Faceit system.

Responsibilities:
- Store expression definitions with rich metadata (UUID, name, coefficients, tags, category, author, timestamps).
- CRUD operations: add, remove, update, get, list.
- Search by name, tags, category, author, date, or coefficient channels.
- Import/export to/from JSON format.
- Integration with ExpressionGenerator to install expressions.
- Integration with PoseLibrary to sync pose data.

Dependencies:
- expression.generator: ExpressionDefinition, ExpressionGenerator.
- expression.editor: ExpressionEditor.
- expression.presets: PresetManager.
- blendshape_utils: sanitize_name, normalize_weights.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Iterable, Callable

# Import dependencies (with fallbacks)
try:
    from .generator import ExpressionDefinition, ExpressionGenerator, ExpressionType
    from .editor import ExpressionEditor
    from .presets import PresetManager
    from ..blendshapes.blendshape_utils import sanitize_name, normalize_weights, clamp
    from ..blendshapes.blendshape_pose import PoseDefinition, BlendshapePoseManager
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionGenerator:
        def get_definition(self, name): return None
        def add_custom_expression(self, defn): pass
        def get_builtin_names(self): return []
    class ExpressionEditor: pass
    class PresetManager: pass
    def sanitize_name(name): return name
    def normalize_weights(weights): return weights
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    class PoseDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class BlendshapePoseManager:
        def get_pose(self, name): return None
        def _poses(self): return {}
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class ExpressionLibraryError(Exception):
    """Base exception for library operations."""
    pass

class ExpressionNotFoundError(ExpressionLibraryError):
    """Raised when an expression is not found in the library."""
    pass

class DuplicateExpressionError(ExpressionLibraryError):
    """Raised when adding an expression with a duplicate name or UUID."""
    pass

class LibraryIOError(ExpressionLibraryError):
    """Raised when file I/O fails."""
    pass


# ---- Data Models ----

@dataclass
class ExpressionMetadata:
    """
    Metadata for an expression entry in the library.
    """
    id: str  # UUID
    name: str
    created: str  # ISO timestamp
    modified: str  # ISO timestamp
    author: str = "unknown"
    tags: List[str] = field(default_factory=list)
    category: str = "Uncategorized"
    favorite: bool = False
    version: int = 1
    source: str = "user"  # "builtin", "user", "imported"
    notes: str = ""
    thumbnail_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpressionMetadata':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unnamed"),
            created=data.get("created", datetime.utcnow().isoformat()),
            modified=data.get("modified", datetime.utcnow().isoformat()),
            author=data.get("author", "unknown"),
            tags=data.get("tags", []),
            category=data.get("category", "Uncategorized"),
            favorite=data.get("favorite", False),
            version=data.get("version", 1),
            source=data.get("source", "user"),
            notes=data.get("notes", ""),
            thumbnail_path=data.get("thumbnail_path"),
        )

    def touch(self):
        """Update modification timestamp and increment version."""
        self.modified = datetime.utcnow().isoformat()
        self.version += 1


@dataclass
class ExpressionEntry:
    """
    A complete expression entry: definition plus metadata.
    """
    definition: ExpressionDefinition
    metadata: ExpressionMetadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definition": {
                "name": self.definition.name,
                "coefficients": self.definition.coefficients,
                "type": self.definition.expression_type.value if hasattr(self.definition.expression_type, 'value') else str(self.definition.expression_type),
                "description": self.definition.description,
                "tags": self.definition.tags,
                "metadata": self.definition.metadata,
            },
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpressionEntry':
        def_data = data["definition"]
        meta_data = data["metadata"]
        # Convert type string to ExpressionType if needed
        expr_type = def_data.get("type", "basic")
        from .generator import ExpressionType
        if isinstance(expr_type, str):
            try:
                expr_type = ExpressionType(expr_type)
            except ValueError:
                expr_type = ExpressionType.CUSTOM
        definition = ExpressionDefinition(
            name=def_data["name"],
            coefficients=def_data["coefficients"],
            expression_type=expr_type,
            description=def_data.get("description", ""),
            tags=def_data.get("tags", []),
            metadata=def_data.get("metadata", {}),
        )
        metadata = ExpressionMetadata.from_dict(meta_data)
        return cls(definition=definition, metadata=metadata)

    def clone(self) -> 'ExpressionEntry':
        return ExpressionEntry(
            definition=ExpressionDefinition(
                name=self.definition.name,
                coefficients=self.definition.coefficients.copy(),
                expression_type=self.definition.expression_type,
                description=self.definition.description,
                tags=self.definition.tags.copy(),
                metadata=self.definition.metadata.copy(),
            ),
            metadata=ExpressionMetadata.from_dict(self.metadata.to_dict()),
        )


# ---- ExpressionLibrary Class ----

class ExpressionLibrary:
    """
    Central database for facial expression definitions.

    Provides storage, organization, search, import/export, and integration
    with the ExpressionGenerator and PoseLibrary.
    """

    def __init__(
        self,
        generator: Optional[ExpressionGenerator] = None,
        editor: Optional[ExpressionEditor] = None,
        pose_manager: Optional[BlendshapePoseManager] = None,
        preset_manager: Optional[PresetManager] = None,
    ):
        """
        Initialize the expression library.

        Args:
            generator: ExpressionGenerator for installing expressions.
            editor: ExpressionEditor for editing.
            pose_manager: PoseManager for syncing poses.
            preset_manager: PresetManager for loading built-in presets.
        """
        self._generator = generator or ExpressionGenerator()
        self._editor = editor
        self._pose_manager = pose_manager or BlendshapePoseManager()
        self._preset_manager = preset_manager or PresetManager()

        # Internal storage
        self._entries: Dict[str, ExpressionEntry] = {}  # id -> entry
        self._name_to_id: Dict[str, str] = {}  # name -> id

        # Dirty flag
        self._dirty = False

        # Initialize built-in expressions from presets
        self._load_builtin_from_presets()

    # ---- Loading Built-in Expressions ----

    def _load_builtin_from_presets(self) -> None:
        """Load built-in expressions from the preset manager."""
        if self._preset_manager is None:
            return
        preset_names = self._preset_manager.list_presets()
        for name in preset_names:
            info = self._preset_manager.get_preset_info(name)
            if info is None:
                continue
            # Create entry
            defn = ExpressionDefinition(
                name=name,
                coefficients=info["coefficients"],
                expression_type=ExpressionType.BASIC,
                description=info.get("description", ""),
                tags=info.get("tags", []),
                metadata={"category": info.get("category", "Uncategorized")},
            )
            meta = ExpressionMetadata(
                id=str(uuid.uuid4()),
                name=name,
                created=datetime.utcnow().isoformat(),
                modified=datetime.utcnow().isoformat(),
                author="builtin",
                tags=info.get("tags", []),
                category=info.get("category", "Uncategorized"),
                source="builtin",
            )
            entry = ExpressionEntry(definition=defn, metadata=meta)
            self._add_entry(entry, skip_duplicate=True)

    # ---- Core Operations ----

    def add(
        self,
        definition: ExpressionDefinition,
        author: str = "unknown",
        tags: Optional[List[str]] = None,
        category: str = "Uncategorized",
        favorite: bool = False,
        source: str = "user",
        notes: str = "",
        skip_duplicate: bool = False,
    ) -> ExpressionEntry:
        """
        Add a new expression entry to the library.

        Args:
            definition: ExpressionDefinition to add.
            author: Author name.
            tags: List of tags.
            category: Category.
            favorite: Whether marked as favorite.
            source: Source (user, imported, etc.).
            notes: Additional notes.
            skip_duplicate: If True, update existing entry instead of raising error.

        Returns:
            The added ExpressionEntry.

        Raises:
            DuplicateExpressionError: If name already exists and skip_duplicate is False.
        """
        # Check for existing name
        if definition.name in self._name_to_id:
            if skip_duplicate:
                # Update the existing entry
                existing_id = self._name_to_id[definition.name]
                entry = self._entries[existing_id]
                entry.definition = definition
                entry.metadata.touch()
                self._dirty = True
                return entry
            else:
                raise DuplicateExpressionError(f"Expression '{definition.name}' already exists.")

        # Generate ID
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        metadata = ExpressionMetadata(
            id=entry_id,
            name=definition.name,
            created=now,
            modified=now,
            author=author,
            tags=tags or [],
            category=category,
            favorite=favorite,
            source=source,
            notes=notes,
        )
        entry = ExpressionEntry(definition=definition, metadata=metadata)
        self._add_entry(entry)
        self._dirty = True
        logger.info(f"Added expression '{definition.name}' to library.")
        return entry

    def _add_entry(self, entry: ExpressionEntry, skip_duplicate: bool = False) -> None:
        """Internal method to add an entry to storage."""
        if entry.metadata.id in self._entries:
            if skip_duplicate:
                # Update existing
                self._entries[entry.metadata.id] = entry
                self._name_to_id[entry.metadata.name] = entry.metadata.id
                return
            else:
                raise DuplicateExpressionError(f"Entry with ID '{entry.metadata.id}' already exists.")
        if entry.metadata.name in self._name_to_id and not skip_duplicate:
            raise DuplicateExpressionError(f"Expression '{entry.metadata.name}' already exists.")
        self._entries[entry.metadata.id] = entry
        self._name_to_id[entry.metadata.name] = entry.metadata.id

    def remove(self, identifier: Union[str, ExpressionDefinition]) -> bool:
        """
        Remove an expression from the library.

        Args:
            identifier: Either name (str) or ExpressionDefinition object.

        Returns:
            True if removed, False if not found.
        """
        if isinstance(identifier, ExpressionDefinition):
            name = identifier.name
        else:
            name = identifier

        if name not in self._name_to_id:
            return False
        entry_id = self._name_to_id.pop(name)
        del self._entries[entry_id]
        self._dirty = True
        logger.info(f"Removed expression '{name}' from library.")
        return True

    def get(self, identifier: Union[str, ExpressionDefinition]) -> Optional[ExpressionEntry]:
        """
        Retrieve an expression entry by name or definition.

        Args:
            identifier: Name (str) or ExpressionDefinition.

        Returns:
            ExpressionEntry or None.
        """
        if isinstance(identifier, ExpressionDefinition):
            name = identifier.name
        else:
            name = identifier
        if name not in self._name_to_id:
            return None
        entry_id = self._name_to_id[name]
        return self._entries.get(entry_id)

    def get_by_id(self, entry_id: str) -> Optional[ExpressionEntry]:
        """Retrieve an entry by UUID."""
        return self._entries.get(entry_id)

    def update(self, entry: ExpressionEntry) -> None:
        """
        Update an existing entry in the library.

        Args:
            entry: Updated ExpressionEntry (must have same ID and name).
        """
        if entry.metadata.id not in self._entries:
            raise ExpressionNotFoundError(f"Entry with ID '{entry.metadata.id}' not found.")
        old_name = self._entries[entry.metadata.id].metadata.name
        if old_name != entry.metadata.name:
            # Update name mapping
            self._name_to_id.pop(old_name, None)
            self._name_to_id[entry.metadata.name] = entry.metadata.id
        self._entries[entry.metadata.id] = entry
        entry.metadata.touch()
        self._dirty = True

    def list_entries(self) -> List[ExpressionEntry]:
        """Return all entries."""
        return list(self._entries.values())

    def list_names(self) -> List[str]:
        """Return all expression names."""
        return list(self._name_to_id.keys())

    def count(self) -> int:
        """Return the number of entries."""
        return len(self._entries)

    # ---- Search and Filtering ----

    def search(self, query: str, case_sensitive: bool = False) -> List[ExpressionEntry]:
        """
        Search expressions by name, tags, category, description, or author.

        Args:
            query: Search string.
            case_sensitive: If True, case-sensitive search.

        Returns:
            List of matching entries.
        """
        if not query:
            return self.list_entries()
        results = []
        q = query if case_sensitive else query.lower()
        for entry in self._entries.values():
            match = False
            # Check name
            name = entry.metadata.name if case_sensitive else entry.metadata.name.lower()
            if q in name:
                match = True
            if not match:
                # Check tags
                for tag in entry.metadata.tags:
                    tag_str = tag if case_sensitive else tag.lower()
                    if q in tag_str:
                        match = True
                        break
            if not match:
                # Check category
                cat = entry.metadata.category if case_sensitive else entry.metadata.category.lower()
                if q in cat:
                    match = True
            if not match:
                # Check description
                desc = entry.definition.description if case_sensitive else entry.definition.description.lower()
                if q in desc:
                    match = True
            if not match:
                # Check author
                auth = entry.metadata.author if case_sensitive else entry.metadata.author.lower()
                if q in auth:
                    match = True
            if not match:
                # Check coefficient channel names
                for ch in entry.definition.coefficients.keys():
                    ch_str = ch if case_sensitive else ch.lower()
                    if q in ch_str:
                        match = True
                        break
            if match:
                results.append(entry)
        return results

    def filter_by_tags(self, tags: List[str], match_all: bool = True) -> List[ExpressionEntry]:
        """Filter entries that have the given tags."""
        if not tags:
            return self.list_entries()
        results = []
        for entry in self._entries.values():
            entry_tags = set(entry.metadata.tags)
            if match_all:
                if all(t in entry_tags for t in tags):
                    results.append(entry)
            else:
                if any(t in entry_tags for t in tags):
                    results.append(entry)
        return results

    def filter_by_category(self, category: str) -> List[ExpressionEntry]:
        """Filter entries by exact category match."""
        return [e for e in self._entries.values() if e.metadata.category == category]

    def filter_by_author(self, author: str) -> List[ExpressionEntry]:
        """Filter entries by author."""
        return [e for e in self._entries.values() if e.metadata.author == author]

    def filter_by_favorite(self) -> List[ExpressionEntry]:
        """Return favorite entries."""
        return [e for e in self._entries.values() if e.metadata.favorite]

    def filter_by_source(self, source: str) -> List[ExpressionEntry]:
        """Filter entries by source (builtin, user, imported)."""
        return [e for e in self._entries.values() if e.metadata.source == source]

    def filter_by_date_range(self, start: Optional[str] = None, end: Optional[str] = None) -> List[ExpressionEntry]:
        """Filter entries by creation date range (ISO strings)."""
        results = []
        for entry in self._entries.values():
            if start and entry.metadata.created < start:
                continue
            if end and entry.metadata.created > end:
                continue
            results.append(entry)
        return results

    # ---- Categories and Tags ----

    def get_all_categories(self) -> List[str]:
        """Return all categories used in the library."""
        cats = set()
        for entry in self._entries.values():
            cats.add(entry.metadata.category)
        return sorted(cats)

    def get_all_tags(self) -> List[str]:
        """Return all tags used in the library."""
        tags = set()
        for entry in self._entries.values():
            tags.update(entry.metadata.tags)
        return sorted(tags)

    def add_tag(self, name: str, tag: str) -> bool:
        """Add a tag to an expression."""
        entry = self.get(name)
        if entry is None:
            return False
        if tag not in entry.metadata.tags:
            entry.metadata.tags.append(tag)
            entry.metadata.touch()
            self._dirty = True
        return True

    def remove_tag(self, name: str, tag: str) -> bool:
        """Remove a tag from an expression."""
        entry = self.get(name)
        if entry is None:
            return False
        if tag in entry.metadata.tags:
            entry.metadata.tags.remove(tag)
            entry.metadata.touch()
            self._dirty = True
        return True

    def set_category(self, name: str, category: str) -> bool:
        """Set the category of an expression."""
        entry = self.get(name)
        if entry is None:
            return False
        if entry.metadata.category != category:
            entry.metadata.category = category
            entry.metadata.touch()
            self._dirty = True
        return True

    def set_favorite(self, name: str, favorite: bool = True) -> bool:
        """Mark/unmark an expression as favorite."""
        entry = self.get(name)
        if entry is None:
            return False
        if entry.metadata.favorite != favorite:
            entry.metadata.favorite = favorite
            entry.metadata.touch()
            self._dirty = True
        return True

    # ---- Integration with Generator ----

    def install_to_generator(self, name: str) -> bool:
        """
        Install an expression from the library into the ExpressionGenerator.

        Args:
            name: Expression name.

        Returns:
            True if installed successfully.
        """
        entry = self.get(name)
        if entry is None:
            return False
        if self._generator:
            # Add as custom expression (overrides built-in if any)
            self._generator.add_custom_expression(entry.definition)
            return True
        return False

    def install_all_to_generator(self) -> int:
        """Install all expressions into the generator."""
        count = 0
        for entry in self._entries.values():
            if self.install_to_generator(entry.metadata.name):
                count += 1
        return count

    def sync_with_pose_library(self) -> None:
        """
        Sync entries with the PoseLibrary: create/update poses.
        """
        if self._pose_manager is None:
            return
        for entry in self._entries.values():
            # Skip built-ins if desired? We'll sync all.
            pose_name = entry.metadata.name
            # Create a PoseDefinition
            pose_def = PoseDefinition(
                name=pose_name,
                weights=entry.definition.coefficients.copy(),
                pose_type="expression",
                metadata={
                    "source": "expression_library",
                    "id": entry.metadata.id,
                    "category": entry.metadata.category,
                    "tags": entry.metadata.tags,
                },
                tags=entry.metadata.tags,
                category=entry.metadata.category,
            )
            # Add or update in pose manager
            # The pose manager may not have a direct update; we'll use its internal dict
            if hasattr(self._pose_manager, '_poses'):
                self._pose_manager._poses[pose_name] = pose_def
        logger.info(f"Synced {len(self._entries)} expressions to pose library.")

    # ---- Export / Import ----

    def export_to_file(self, filepath: Union[str, Path], include_builtin: bool = False) -> None:
        """
        Export library entries to a JSON file.

        Args:
            filepath: Path to JSON file.
            include_builtin: If True, include built-in entries.
        """
        path = Path(filepath)
        data = []
        for entry in self._entries.values():
            if not include_builtin and entry.metadata.source == "builtin":
                continue
            data.append(entry.to_dict())
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported {len(data)} expressions to {path}")
        except Exception as e:
            raise LibraryIOError(f"Failed to export library: {e}")

    def import_from_file(self, filepath: Union[str, Path], source: str = "imported", overwrite: bool = False) -> int:
        """
        Import expressions from a JSON file.

        Args:
            filepath: Path to JSON file.
            source: Source label for imported entries.
            overwrite: If True, overwrite existing entries with same name.

        Returns:
            Number of entries imported.
        """
        path = Path(filepath)
        if not path.exists():
            raise LibraryIOError(f"File not found: {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise LibraryIOError(f"Failed to read file: {e}")
        count = 0
        for item in data:
            entry = ExpressionEntry.from_dict(item)
            # Set source
            entry.metadata.source = source
            # Check if name exists
            if entry.metadata.name in self._name_to_id:
                if overwrite:
                    # Remove existing
                    self.remove(entry.metadata.name)
                else:
                    # Skip or raise? We'll skip.
                    logger.warning(f"Expression '{entry.metadata.name}' already exists; skipping.")
                    continue
            self._add_entry(entry)
            count += 1
        self._dirty = True
        logger.info(f"Imported {count} expressions from {path}")
        return count

    def export_to_generator(self, name: str) -> bool:
        """
        Export an expression from library to the generator (same as install).
        """
        return self.install_to_generator(name)

    # ---- Utility ----

    def clear(self) -> None:
        """Remove all user/imported entries, keeping built-ins if desired."""
        to_remove = [name for name, entry in self._entries.items() if entry.metadata.source != "builtin"]
        for name in to_remove:
            self.remove(name)

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    def get_statistics(self) -> Dict[str, Any]:
        """Return statistics about the library."""
        stats = {
            "total_entries": len(self._entries),
            "builtin_count": sum(1 for e in self._entries.values() if e.metadata.source == "builtin"),
            "user_count": sum(1 for e in self._entries.values() if e.metadata.source == "user"),
            "imported_count": sum(1 for e in self._entries.values() if e.metadata.source == "imported"),
            "favorite_count": sum(1 for e in self._entries.values() if e.metadata.favorite),
            "categories": self.get_all_categories(),
            "tags": self.get_all_tags(),
        }
        return stats


# ---- Public API ----

__all__ = [
    "ExpressionLibrary",
    "ExpressionEntry",
    "ExpressionMetadata",
    "ExpressionLibraryError",
    "ExpressionNotFoundError",
    "DuplicateExpressionError",
    "LibraryIOError",
]