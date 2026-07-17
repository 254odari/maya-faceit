"""
blendshapes/arkit_mapper/presets.py

Preset management for the maya_faceit ARKit Mapper.

This module provides:

    • Built-in ARKit presets
    • User presets
    • Character presets
    • Preset registry
    • Loading / Saving
    • Validation
    • Version migration
    • Runtime preset management
    • Search and filtering
    • Diagnostics

The module is intentionally independent of Maya whenever
possible so that presets may be edited outside of Maya.
"""

from __future__ import annotations

# ============================================================
# Standard Library Imports
# ============================================================

import copy
import json
import logging
import os
import threading
import uuid

from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from dataclasses import is_dataclass

from datetime import datetime
from enum import Enum
from pathlib import Path

from typing import (
    Any,
    Dict,
    List,
    Set,
    Tuple,
    Optional,
    Iterable,
    Iterator,
    Sequence,
    Mapping,
    MutableMapping,
    Callable,
)

# ============================================================
# Local Imports
# ============================================================

from .exceptions import (
    PresetError,
    PresetAlreadyExistsError,
    PresetNotFoundError,
    PresetValidationError,
    VersionMismatchError,
)

from .statistics import (
    StatisticsCollector,
)

from .utils import (
    deep_copy,
    deep_merge,
    json_safe,
    content_hash,
    current_time,
)

from .io import (
    load_json,
    save_json,
)

# ============================================================
# Module Metadata
# ============================================================

MODULE_NAME = "arkit_mapper.presets"

MODULE_VERSION = "1.0.0"

LOGGER = logging.getLogger(MODULE_NAME)

# ============================================================
# Constants
# ============================================================

DEFAULT_PRESET_VERSION = "1.0"

DEFAULT_CATEGORY = "General"

DEFAULT_AUTHOR = "Unknown"

DEFAULT_DESCRIPTION = ""

DEFAULT_TAGS: Tuple[str, ...] = ()

DEFAULT_ICON = ""

DEFAULT_THUMBNAIL = ""

DEFAULT_CHARACTER = "Generic"

DEFAULT_LICENSE = "Internal"

DEFAULT_PRIORITY = 100

DEFAULT_WEIGHT = 1.0

# ------------------------------------------------------------

PRESET_FILE_EXTENSION = ".facepreset"

PRESET_FOLDER_NAME = "presets"

BUILTIN_FOLDER_NAME = "builtin"

USER_FOLDER_NAME = "user"

# ------------------------------------------------------------

SUPPORTED_PRESET_VERSIONS = {

    "1.0",

}

# ============================================================
# Enumerations
# ============================================================

class PresetType(Enum):
    """
    Types of presets.
    """

    BUILTIN = "builtin"

    USER = "user"

    PROJECT = "project"

    CHARACTER = "character"

    TEMPLATE = "template"


# ------------------------------------------------------------

class PresetStatus(Enum):
    """
    Runtime preset state.
    """

    ACTIVE = "active"

    DISABLED = "disabled"

    HIDDEN = "hidden"

    DEPRECATED = "deprecated"


# ------------------------------------------------------------

class PresetScope(Enum):
    """
    Where a preset belongs.
    """

    GLOBAL = "global"

    USER = "user"

    PROJECT = "project"


# ============================================================
# Type Aliases
# ============================================================

BlendshapeWeights = Dict[str, float]

PresetDictionary = Dict[str, Any]

PresetCollection = Dict[str, "Preset"]

# ============================================================
# Runtime Globals
# ============================================================

_PRESET_LOCK = threading.RLock()

_PRESET_CACHE: Dict[str, Any] = {}

_RUNTIME_REGISTRY: Dict[str, "Preset"] = OrderedDict()

# ============================================================
# Statistics
# ============================================================

STATISTICS = StatisticsCollector(
    "Preset Manager"
)

# ============================================================
# Helper Functions
# ============================================================

def generate_preset_uuid() -> str:
    """
    Generate a unique preset identifier.
    """

    return uuid.uuid4().hex


# ------------------------------------------------------------

def now() -> datetime:
    """
    Current timestamp.
    """

    return current_time()


# ------------------------------------------------------------

def preset_filename(
    name: str,
) -> str:
    """
    Convert a preset name into a filename.
    """

    filename = (

        name.strip()

        .replace(" ", "_")

        .lower()

    )

    if not filename.endswith(
        PRESET_FILE_EXTENSION
    ):

        filename += PRESET_FILE_EXTENSION

    return filename


# ------------------------------------------------------------

def is_supported_version(
    version: str,
) -> bool:
    """
    Check whether a preset version is supported.
    """

    return version in SUPPORTED_PRESET_VERSIONS


# ------------------------------------------------------------

def validate_version(
    version: str,
) -> None:
    """
    Validate preset version.
    """

    if not is_supported_version(version):

        raise VersionMismatchError(

            f"Unsupported preset version: "
            f"{version}"

        )


# ============================================================
# Module Initialization
# ============================================================

LOGGER.debug(

    "%s initialized (v%s)",

    MODULE_NAME,

    MODULE_VERSION,

)
# ============================================================
# Part 2 - Data Models
# ============================================================

# ------------------------------------------------------------
# Preset Metadata
# ------------------------------------------------------------

@dataclass(slots=True)
class PresetMetadata:
    """
    Descriptive information associated with a preset.
    """

    uuid: str = field(
        default_factory=generate_preset_uuid
    )

    name: str = "Unnamed Preset"

    version: str = DEFAULT_PRESET_VERSION

    author: str = DEFAULT_AUTHOR

    description: str = DEFAULT_DESCRIPTION

    category: str = DEFAULT_CATEGORY

    character: str = DEFAULT_CHARACTER

    preset_type: PresetType = PresetType.USER

    scope: PresetScope = PresetScope.USER

    status: PresetStatus = PresetStatus.ACTIVE

    icon: str = DEFAULT_ICON

    thumbnail: str = DEFAULT_THUMBNAIL

    license: str = DEFAULT_LICENSE

    tags: List[str] = field(
        default_factory=list
    )

    priority: int = DEFAULT_PRIORITY

    created: datetime = field(
        default_factory=now
    )

    modified: datetime = field(
        default_factory=now
    )

    # --------------------------------------------------------

    def touch(self) -> None:
        """
        Update the modification timestamp.
        """

        self.modified = now()

    # --------------------------------------------------------

    def validate(self) -> None:
        """
        Validate metadata.
        """

        if not self.name.strip():

            raise PresetValidationError(
                "Preset name cannot be empty."
            )

        validate_version(
            self.version
        )

    # --------------------------------------------------------

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        data = asdict(self)

        data["preset_type"] = (
            self.preset_type.value
        )

        data["scope"] = (
            self.scope.value
        )

        data["status"] = (
            self.status.value
        )

        data["created"] = (
            self.created.isoformat()
        )

        data["modified"] = (
            self.modified.isoformat()
        )

        return data

    # --------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> "PresetMetadata":

        metadata = cls(

            uuid=data.get(
                "uuid",
                generate_preset_uuid(),
            ),

            name=data.get(
                "name",
                "Unnamed Preset",
            ),

            version=data.get(
                "version",
                DEFAULT_PRESET_VERSION,
            ),

            author=data.get(
                "author",
                DEFAULT_AUTHOR,
            ),

            description=data.get(
                "description",
                "",
            ),

            category=data.get(
                "category",
                DEFAULT_CATEGORY,
            ),

            character=data.get(
                "character",
                DEFAULT_CHARACTER,
            ),

            preset_type=PresetType(
                data.get(
                    "preset_type",
                    PresetType.USER.value,
                )
            ),

            scope=PresetScope(
                data.get(
                    "scope",
                    PresetScope.USER.value,
                )
            ),

            status=PresetStatus(
                data.get(
                    "status",
                    PresetStatus.ACTIVE.value,
                )
            ),

            icon=data.get(
                "icon",
                "",
            ),

            thumbnail=data.get(
                "thumbnail",
                "",
            ),

            license=data.get(
                "license",
                DEFAULT_LICENSE,
            ),

            tags=list(
                data.get(
                    "tags",
                    [],
                )
            ),

            priority=int(
                data.get(
                    "priority",
                    DEFAULT_PRIORITY,
                )
            ),

        )

        if "created" in data:

            metadata.created = datetime.fromisoformat(
                data["created"]
            )

        if "modified" in data:

            metadata.modified = datetime.fromisoformat(
                data["modified"]
            )

        return metadata


# ------------------------------------------------------------
# Preset
# ------------------------------------------------------------

@dataclass(slots=True)
class Preset:
    """
    Complete preset definition.
    """

    metadata: PresetMetadata = field(
        default_factory=PresetMetadata
    )

    mapping: Dict[
        str,
        Dict[str, float]
    ] = field(
        default_factory=dict
    )

    settings: Dict[
        str,
        Any
    ] = field(
        default_factory=dict
    )

    notes: str = ""

    favorite: bool = False

    protected: bool = False

    # --------------------------------------------------------

    @property
    def uuid(self) -> str:

        return self.metadata.uuid

    # --------------------------------------------------------

    @property
    def name(self) -> str:

        return self.metadata.name

    # --------------------------------------------------------

    @property
    def category(self) -> str:

        return self.metadata.category

    # --------------------------------------------------------

    @property
    def type(self) -> PresetType:

        return self.metadata.preset_type

    # --------------------------------------------------------

    def copy(
        self,
    ) -> "Preset":
        """
        Deep copy the preset.
        """

        return copy.deepcopy(self)

    # --------------------------------------------------------

    def rename(
        self,
        name: str,
    ) -> None:
        """
        Rename the preset.
        """

        self.metadata.name = name

        self.metadata.touch()

    # --------------------------------------------------------

    def compute_hash(
        self,
    ) -> str:
        """
        Compute a content hash.
        """

        return content_hash(
            self.to_dict()
        )

    # --------------------------------------------------------

    def validate(
        self,
    ) -> None:
        """
        Validate preset integrity.
        """

        self.metadata.validate()

        if not isinstance(
            self.mapping,
            dict,
        ):

            raise PresetValidationError(
                "Mapping must be a dictionary."
            )

        for source, targets in self.mapping.items():

            if not isinstance(
                source,
                str,
            ):

                raise PresetValidationError(
                    "Invalid ARKit channel."
                )

            if not isinstance(
                targets,
                dict,
            ):

                raise PresetValidationError(
                    "Invalid mapping."
                )

    # --------------------------------------------------------

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "metadata":
                self.metadata.to_dict(),

            "mapping":
                deep_copy(
                    self.mapping
                ),

            "settings":
                deep_copy(
                    self.settings
                ),

            "notes":
                self.notes,

            "favorite":
                self.favorite,

            "protected":
                self.protected,

        }

    # --------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> "Preset":

        preset = cls(

            metadata=PresetMetadata.from_dict(

                data.get(
                    "metadata",
                    {},
                )

            ),

            mapping=deep_copy(

                data.get(
                    "mapping",
                    {},
                )

            ),

            settings=deep_copy(

                data.get(
                    "settings",
                    {},
                )

            ),

            notes=data.get(
                "notes",
                "",
            ),

            favorite=bool(

                data.get(
                    "favorite",
                    False,
                )

            ),

            protected=bool(

                data.get(
                    "protected",
                    False,
                )

            ),

        )

        return preset


# ------------------------------------------------------------
# Preset Summary
# ------------------------------------------------------------

@dataclass(slots=True)
class PresetSummary:
    """
    Lightweight preset representation used
    for listings and searches.
    """

    uuid: str

    name: str

    category: str

    character: str

    preset_type: PresetType

    version: str

    favorite: bool

    protected: bool

    # --------------------------------------------------------

    @classmethod
    def from_preset(
        cls,
        preset: Preset,
    ) -> "PresetSummary":

        return cls(

            uuid=preset.uuid,

            name=preset.name,

            category=preset.metadata.category,

            character=preset.metadata.character,

            preset_type=preset.metadata.preset_type,

            version=preset.metadata.version,

            favorite=preset.favorite,

            protected=preset.protected,

        )


# ------------------------------------------------------------
# Search Result
# ------------------------------------------------------------

@dataclass(slots=True)
class PresetSearchResult:
    """
    Result returned from preset searches.
    """

    preset: Preset

    score: float = 1.0

    matched_fields: List[str] = field(
        default_factory=list
    )


# ------------------------------------------------------------
# Runtime Cache Entry
# ------------------------------------------------------------

@dataclass(slots=True)
class PresetCacheEntry:
    """
    Cached preset information.
    """

    preset: Preset

    loaded: datetime = field(
        default_factory=now
    )

    accessed: datetime = field(
        default_factory=now
    )

    hit_count: int = 0

    # --------------------------------------------------------

    def touch(
        self,
    ) -> None:

        self.accessed = now()

        self.hit_count += 1


# ------------------------------------------------------------
# Registry Entry
# ------------------------------------------------------------

@dataclass(slots=True)
class RegistryEntry:
    """
    Entry stored by the runtime registry.
    """

    uuid: str

    name: str

    path: Optional[Path]

    preset_type: PresetType

    loaded: bool = False

    enabled: bool = True

    registered: datetime = field(
        default_factory=now
    )
# ============================================================
# Part 3 - Built-in Presets
# ============================================================

"""
This section defines the built-in presets shipped with the
ARKit Mapper. These presets are read-only templates that
serve as defaults and examples.

Additional presets may be registered at runtime by the
Preset Registry.
"""

# ------------------------------------------------------------
# Built-in Categories
# ------------------------------------------------------------

BUILTIN_CATEGORIES: Tuple[str, ...] = (
    "Apple ARKit",
    "FaceIt",
    "MetaHuman",
    "Character Creator",
    "Generic",
)

# ------------------------------------------------------------
# Built-in Preset Definitions
# ------------------------------------------------------------

_BUILTIN_PRESETS: Dict[str, Preset] = {}


# ------------------------------------------------------------
# Internal Builder
# ------------------------------------------------------------

def _create_builtin_preset(
    *,
    name: str,
    category: str,
    mapping: Mapping[str, Mapping[str, float]],
    description: str = "",
    character: str = DEFAULT_CHARACTER,
    author: str = "maya_faceit",
    version: str = DEFAULT_PRESET_VERSION,
    tags: Optional[Sequence[str]] = None,
) -> Preset:
    """
    Construct a read-only built-in preset.
    """

    metadata = PresetMetadata(

        name=name,

        version=version,

        author=author,

        description=description,

        category=category,

        character=character,

        preset_type=PresetType.BUILTIN,

        scope=PresetScope.GLOBAL,

        status=PresetStatus.ACTIVE,

        tags=list(tags or ()),

    )

    preset = Preset(

        metadata=metadata,

        mapping=deep_copy(mapping),

        protected=True,

    )

    preset.validate()

    return preset


# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

def register_builtin_preset(
    preset: Preset,
) -> None:
    """
    Register a built-in preset.

    Existing presets with the same UUID are
    replaced.
    """

    if preset.type != PresetType.BUILTIN:

        raise PresetValidationError(
            "Preset is not a built-in preset."
        )

    _BUILTIN_PRESETS[
        preset.uuid
    ] = preset


# ------------------------------------------------------------

def unregister_builtin_preset(
    preset_uuid: str,
) -> bool:
    """
    Remove a built-in preset.
    """

    return (

        _BUILTIN_PRESETS.pop(
            preset_uuid,
            None,
        )

        is not None

    )


# ------------------------------------------------------------
# Query Functions
# ------------------------------------------------------------

def builtin_presets() -> List[Preset]:
    """
    Return all built-in presets.
    """

    return [

        preset.copy()

        for preset

        in _BUILTIN_PRESETS.values()

    ]


# ------------------------------------------------------------

def builtin_preset(
    name: str,
) -> Preset:
    """
    Return a built-in preset by name.

    Raises
    ------
    PresetNotFoundError
    """

    for preset in _BUILTIN_PRESETS.values():

        if preset.name == name:

            return preset.copy()

    raise PresetNotFoundError(
        name
    )


# ------------------------------------------------------------

def builtin_categories() -> Tuple[str, ...]:
    """
    Return available built-in categories.
    """

    return BUILTIN_CATEGORIES


# ------------------------------------------------------------

def builtin_names() -> List[str]:
    """
    Return the names of all built-in presets.
    """

    return sorted(

        preset.name

        for preset

        in _BUILTIN_PRESETS.values()

    )


# ------------------------------------------------------------
# Default Presets
# ------------------------------------------------------------

EMPTY_PRESET = _create_builtin_preset(

    name="Empty",

    category="Generic",

    description=(
        "Blank preset containing no mappings."
    ),

    mapping={},

    tags=("empty",),

)

# ------------------------------------------------------------

IDENTITY_PRESET = _create_builtin_preset(

    name="Identity",

    category="Apple ARKit",

    description=(
        "One-to-one ARKit mapping."
    ),

    mapping={

        channel: {

            channel: 1.0

        }

        for channel

        in ARKIT_BLENDSHAPES

    },

    tags=(

        "arkit",

        "identity",

        "default",

    ),

)

# ------------------------------------------------------------

FACEIT_TEMPLATE_PRESET = _create_builtin_preset(

    name="FaceIt Template",

    category="FaceIt",

    description=(
        "Template preset for maya_faceit rigs."
    ),

    mapping={},

    character="FaceIt",

    tags=(

        "faceit",

        "template",

    ),

)

# ------------------------------------------------------------
# Initialization
# ------------------------------------------------------------

for preset in (

    EMPTY_PRESET,

    IDENTITY_PRESET,

    FACEIT_TEMPLATE_PRESET,

):

    register_builtin_preset(
        preset
    )


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def builtin_statistics() -> Dict[str, Any]:
    """
    Return statistics describing the built-in
    preset library.
    """

    categories: Dict[str, int] = {}

    for preset in _BUILTIN_PRESETS.values():

        category = preset.category

        categories[category] = (

            categories.get(
                category,
                0,
            )

            + 1

        )

    return {

        "count":
            len(
                _BUILTIN_PRESETS
            ),

        "categories":
            categories,

        "names":
            builtin_names(),

    }


# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

def validate_builtin_presets() -> None:
    """
    Validate every built-in preset.
    """

    for preset in _BUILTIN_PRESETS.values():

        preset.validate()

        if not preset.protected:

            raise PresetValidationError(

                f"{preset.name} must be protected."

            )


# ------------------------------------------------------------

LOGGER.debug(

    "Registered %d built-in presets.",

    len(_BUILTIN_PRESETS),

)
# ============================================================
# Part 4 - Preset Registry
# ============================================================

"""
Runtime registry responsible for tracking every preset
available to the ARKit mapper.

The registry stores built-in, user, project and temporary
presets and provides fast lookup by UUID and by name.
"""

# ------------------------------------------------------------
# Preset Registry
# ------------------------------------------------------------

class PresetRegistry:
    """
    Runtime preset registry.

    Presets are indexed by UUID while an additional
    name index provides fast lookups.
    """

    # --------------------------------------------------------

    def __init__(self):

        self._presets: Dict[
            str,
            Preset,
        ] = OrderedDict()

        self._name_index: Dict[
            str,
            str,
        ] = {}

        self._lock = threading.RLock()

    # --------------------------------------------------------
    # Basic Properties
    # --------------------------------------------------------

    def __len__(self) -> int:

        return len(self._presets)

    # --------------------------------------------------------

    def __iter__(
        self,
    ) -> Iterator[Preset]:

        return iter(
            self._presets.values()
        )

    # --------------------------------------------------------

    def __contains__(
        self,
        uuid: str,
    ) -> bool:

        return uuid in self._presets

    # --------------------------------------------------------
    # Registration
    # --------------------------------------------------------

    def register(
        self,
        preset: Preset,
        *,
        overwrite: bool = False,
    ) -> None:
        """
        Register a preset.
        """

        preset.validate()

        with self._lock:

            if (

                not overwrite

                and preset.uuid in self._presets

            ):

                raise PresetAlreadyExistsError(

                    preset.uuid

                )

            existing = self._name_index.get(
                preset.name.lower()
            )

            if (

                existing

                and existing != preset.uuid

                and not overwrite

            ):

                raise PresetAlreadyExistsError(

                    preset.name

                )

            self._presets[
                preset.uuid
            ] = preset.copy()

            self._name_index[
                preset.name.lower()
            ] = preset.uuid

            STATISTICS.increment(
                "registered"
            )

    # --------------------------------------------------------

    def unregister(
        self,
        uuid: str,
    ) -> bool:
        """
        Remove a preset.
        """

        with self._lock:

            preset = self._presets.pop(
                uuid,
                None,
            )

            if preset is None:

                return False

            self._name_index.pop(
                preset.name.lower(),
                None,
            )

            STATISTICS.increment(
                "removed"
            )

            return True

    # --------------------------------------------------------
    # Lookup
    # --------------------------------------------------------

    def get(
        self,
        uuid: str,
    ) -> Preset:
        """
        Retrieve a preset by UUID.
        """

        try:

            return self._presets[
                uuid
            ].copy()

        except KeyError:

            raise PresetNotFoundError(
                uuid
            )

    # --------------------------------------------------------

    def get_by_name(
        self,
        name: str,
    ) -> Preset:
        """
        Retrieve a preset by name.
        """

        uuid = self._name_index.get(
            name.lower()
        )

        if uuid is None:

            raise PresetNotFoundError(
                name
            )

        return self.get(uuid)

    # --------------------------------------------------------

    def exists(
        self,
        uuid: str,
    ) -> bool:

        return uuid in self._presets

    # --------------------------------------------------------

    def name_exists(
        self,
        name: str,
    ) -> bool:

        return (

            name.lower()

            in self._name_index

        )

    # --------------------------------------------------------
    # Listing
    # --------------------------------------------------------

    def presets(
        self,
    ) -> List[Preset]:
        """
        Return every preset.
        """

        return [

            preset.copy()

            for preset

            in self._presets.values()

        ]

    # --------------------------------------------------------

    def summaries(
        self,
    ) -> List[PresetSummary]:
        """
        Return lightweight summaries.
        """

        return [

            PresetSummary.from_preset(
                preset
            )

            for preset

            in self._presets.values()

        ]

    # --------------------------------------------------------

    def names(
        self,
    ) -> List[str]:

        return sorted(

            self._name_index.keys()

        )

    # --------------------------------------------------------

    def uuids(
        self,
    ) -> List[str]:

        return list(
            self._presets.keys()
        )

    # --------------------------------------------------------
    # Filtering
    # --------------------------------------------------------

    def by_type(
        self,
        preset_type: PresetType,
    ) -> List[Preset]:

        return [

            preset.copy()

            for preset

            in self._presets.values()

            if (

                preset.type

                == preset_type

            )

        ]

    # --------------------------------------------------------

    def by_category(
        self,
        category: str,
    ) -> List[Preset]:

        return [

            preset.copy()

            for preset

            in self._presets.values()

            if (

                preset.category.lower()

                == category.lower()

            )

        ]

    # --------------------------------------------------------

    def favorites(
        self,
    ) -> List[Preset]:

        return [

            preset.copy()

            for preset

            in self._presets.values()

            if preset.favorite

        ]

    # --------------------------------------------------------
    # Maintenance
    # --------------------------------------------------------

    def clear(self) -> None:
        """
        Remove every preset.
        """

        with self._lock:

            self._presets.clear()

            self._name_index.clear()

    # --------------------------------------------------------

    def reload_builtin(
        self,
    ) -> None:
        """
        Reload built-in presets.
        """

        for preset in builtin_presets():

            self.register(

                preset,

                overwrite=True,

            )

    # --------------------------------------------------------

    def statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Registry statistics.
        """

        by_type: Dict[
            str,
            int,
        ] = {}

        by_category: Dict[
            str,
            int,
        ] = {}

        for preset in self._presets.values():

            preset_type = (
                preset.type.value
            )

            by_type[preset_type] = (

                by_type.get(
                    preset_type,
                    0,
                )

                + 1

            )

            category = (
                preset.category
            )

            by_category[category] = (

                by_category.get(
                    category,
                    0,
                )

                + 1

            )

        return {

            "total":

                len(
                    self
                ),

            "types":

                by_type,

            "categories":

                by_category,

            "favorites":

                len(
                    self.favorites()
                ),

        }


# ------------------------------------------------------------
# Global Runtime Registry
# ------------------------------------------------------------

PRESET_REGISTRY = PresetRegistry()

# ------------------------------------------------------------
# Register Built-ins
# ------------------------------------------------------------

PRESET_REGISTRY.reload_builtin()

# ------------------------------------------------------------
# Convenience Functions
# ------------------------------------------------------------

def register_preset(
    preset: Preset,
    *,
    overwrite: bool = False,
) -> None:
    """
    Register a preset in the global registry.
    """

    PRESET_REGISTRY.register(

        preset,

        overwrite=overwrite,

    )


# ------------------------------------------------------------

def unregister_preset(
    uuid: str,
) -> bool:

    return PRESET_REGISTRY.unregister(
        uuid
    )


# ------------------------------------------------------------

def get_preset(
    uuid: str,
) -> Preset:

    return PRESET_REGISTRY.get(
        uuid
    )


# ------------------------------------------------------------

def get_preset_by_name(
    name: str,
) -> Preset:

    return PRESET_REGISTRY.get_by_name(
        name
    )


# ------------------------------------------------------------

def registered_presets(
) -> List[Preset]:

    return PRESET_REGISTRY.presets()


# ------------------------------------------------------------

def preset_summaries(
) -> List[PresetSummary]:

    return PRESET_REGISTRY.summaries()


# ------------------------------------------------------------

def registry_statistics(
) -> Dict[str, Any]:

    return PRESET_REGISTRY.statistics()


# ------------------------------------------------------------

LOGGER.debug(

    "Preset registry initialized with %d presets.",

    len(PRESET_REGISTRY),

)
# ============================================================
# Part 5 - Preset Creation
# ============================================================

"""
Utilities for creating, cloning, modifying and generating
preset instances.

These helpers always return fully validated Preset objects.
"""

# ------------------------------------------------------------
# Internal Helpers
# ------------------------------------------------------------

def _default_metadata(
    name: str,
    *,
    author: str = DEFAULT_AUTHOR,
    description: str = DEFAULT_DESCRIPTION,
    category: str = DEFAULT_CATEGORY,
    character: str = DEFAULT_CHARACTER,
    preset_type: PresetType = PresetType.USER,
    scope: PresetScope = PresetScope.USER,
    tags: Optional[Iterable[str]] = None,
) -> PresetMetadata:
    """
    Build default metadata.
    """

    metadata = PresetMetadata(

        uuid=generate_preset_uuid(),

        name=name,

        version=DEFAULT_PRESET_VERSION,

        author=author,

        description=description,

        category=category,

        character=character,

        preset_type=preset_type,

        scope=scope,

        status=PresetStatus.ACTIVE,

        tags=list(tags or []),

    )

    metadata.validate()

    return metadata


# ------------------------------------------------------------
# Factory Functions
# ------------------------------------------------------------

def create_preset(
    name: str,
    *,
    mapping: Optional[
        Mapping[str, Mapping[str, float]]
    ] = None,
    settings: Optional[
        Mapping[str, Any]
    ] = None,
    notes: str = "",
    author: str = DEFAULT_AUTHOR,
    description: str = DEFAULT_DESCRIPTION,
    category: str = DEFAULT_CATEGORY,
    character: str = DEFAULT_CHARACTER,
    preset_type: PresetType = PresetType.USER,
    scope: PresetScope = PresetScope.USER,
    tags: Optional[
        Iterable[str]
    ] = None,
) -> Preset:
    """
    Create a new preset.
    """

    preset = Preset(

        metadata=_default_metadata(

            name,

            author=author,

            description=description,

            category=category,

            character=character,

            preset_type=preset_type,

            scope=scope,

            tags=tags,

        ),

        mapping=deep_copy(
            mapping or {}
        ),

        settings=deep_copy(
            settings or {}
        ),

        notes=notes,

    )

    preset.validate()

    return preset


# ------------------------------------------------------------

def create_empty_preset(
    name: str = "New Preset",
) -> Preset:
    """
    Create an empty user preset.
    """

    return create_preset(
        name
    )


# ------------------------------------------------------------

def create_identity_preset(
    name: str = "Identity",
) -> Preset:
    """
    Create a one-to-one ARKit preset.
    """

    mapping = {

        channel: {

            channel: 1.0

        }

        for channel

        in ARKIT_BLENDSHAPES

    }

    return create_preset(

        name,

        mapping=mapping,

        category="Apple ARKit",

    )


# ------------------------------------------------------------

def clone_preset(
    preset: Preset,
    *,
    new_name: Optional[str] = None,
) -> Preset:
    """
    Deep copy a preset.

    A new UUID is generated.
    """

    clone = preset.copy()

    clone.metadata.uuid = (
        generate_preset_uuid()
    )

    clone.metadata.created = now()

    clone.metadata.modified = now()

    if new_name:

        clone.metadata.name = new_name

    else:

        clone.metadata.name = (

            f"{preset.name} Copy"

        )

    clone.favorite = False

    clone.protected = False

    clone.validate()

    return clone


# ------------------------------------------------------------

def duplicate_preset(
    preset: Preset,
) -> Preset:
    """
    Alias for clone_preset().
    """

    return clone_preset(
        preset
    )


# ------------------------------------------------------------

def create_from_mapping(
    name: str,
    mapping: Mapping[
        str,
        Mapping[str, float]
    ],
) -> Preset:
    """
    Create a preset directly from a mapping.
    """

    return create_preset(

        name,

        mapping=mapping,

    )


# ------------------------------------------------------------
# Editing
# ------------------------------------------------------------

def rename_preset(
    preset: Preset,
    name: str,
) -> Preset:
    """
    Rename a preset.
    """

    preset.metadata.name = name

    preset.metadata.touch()

    preset.validate()

    return preset


# ------------------------------------------------------------

def set_description(
    preset: Preset,
    description: str,
) -> Preset:
    """
    Update preset description.
    """

    preset.metadata.description = (
        description
    )

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def set_category(
    preset: Preset,
    category: str,
) -> Preset:
    """
    Update category.
    """

    preset.metadata.category = (
        category
    )

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def set_character(
    preset: Preset,
    character: str,
) -> Preset:
    """
    Update character.
    """

    preset.metadata.character = (
        character
    )

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def add_tag(
    preset: Preset,
    tag: str,
) -> Preset:
    """
    Add a tag.
    """

    if tag not in preset.metadata.tags:

        preset.metadata.tags.append(
            tag
        )

        preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def remove_tag(
    preset: Preset,
    tag: str,
) -> Preset:
    """
    Remove a tag.
    """

    if tag in preset.metadata.tags:

        preset.metadata.tags.remove(
            tag
        )

        preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def clear_tags(
    preset: Preset,
) -> Preset:
    """
    Remove every tag.
    """

    preset.metadata.tags.clear()

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------
# Mapping Helpers
# ------------------------------------------------------------

def replace_mapping(
    preset: Preset,
    mapping: Mapping[
        str,
        Mapping[str, float]
    ],
) -> Preset:
    """
    Replace the entire mapping.
    """

    preset.mapping = deep_copy(
        mapping
    )

    preset.metadata.touch()

    preset.validate()

    return preset


# ------------------------------------------------------------

def update_mapping(
    preset: Preset,
    mapping: Mapping[
        str,
        Mapping[str, float]
    ],
) -> Preset:
    """
    Merge mapping values.
    """

    preset.mapping = deep_merge(

        preset.mapping,

        mapping,

    )

    preset.metadata.touch()

    preset.validate()

    return preset


# ------------------------------------------------------------

def clear_mapping(
    preset: Preset,
) -> Preset:
    """
    Remove every mapping.
    """

    preset.mapping.clear()

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------
# Settings Helpers
# ------------------------------------------------------------

def update_setting(
    preset: Preset,
    key: str,
    value: Any,
) -> Preset:
    """
    Set a runtime setting.
    """

    preset.settings[key] = value

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def remove_setting(
    preset: Preset,
    key: str,
) -> Preset:
    """
    Remove a runtime setting.
    """

    preset.settings.pop(
        key,
        None,
    )

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def clear_settings(
    preset: Preset,
) -> Preset:
    """
    Remove every runtime setting.
    """

    preset.settings.clear()

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------
# Flags
# ------------------------------------------------------------

def mark_favorite(
    preset: Preset,
    enabled: bool = True,
) -> Preset:
    """
    Toggle favorite state.
    """

    preset.favorite = enabled

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------

def protect_preset(
    preset: Preset,
    enabled: bool = True,
) -> Preset:
    """
    Toggle protection.
    """

    preset.protected = enabled

    preset.metadata.touch()

    return preset


# ------------------------------------------------------------
# Convenience
# ------------------------------------------------------------

def register_new_preset(
    name: str,
    **kwargs,
) -> Preset:
    """
    Create and register a preset.
    """

    preset = create_preset(
        name,
        **kwargs,
    )

    register_preset(
        preset
    )

    return preset


# ------------------------------------------------------------

LOGGER.debug(
    "Preset creation helpers initialized."
)
# ============================================================
# Part 6 - Loading & Saving
# ============================================================

"""
Persistence utilities for Preset objects.

These helpers serialize Preset instances to disk and restore
them while preserving metadata, mappings and settings.
"""

# ------------------------------------------------------------
# Internal Helpers
# ------------------------------------------------------------

def _normalize_preset_path(
    path: os.PathLike | str,
) -> Path:
    """
    Return a normalized preset path.

    If the filename has no extension, the default preset
    extension is appended automatically.
    """

    path = Path(path)

    if path.suffix.lower() != PRESET_FILE_EXTENSION:

        path = path.with_suffix(
            PRESET_FILE_EXTENSION
        )

    return path


# ------------------------------------------------------------

def _ensure_parent_directory(
    path: Path,
) -> None:
    """
    Create the parent directory if necessary.
    """

    path.parent.mkdir(

        parents=True,

        exist_ok=True,

    )


# ------------------------------------------------------------
# Serialization
# ------------------------------------------------------------

def serialize_preset(
    preset: Preset,
) -> Dict[str, Any]:
    """
    Convert a preset into a JSON-safe dictionary.
    """

    preset.validate()

    return json_safe(
        preset.to_dict()
    )


# ------------------------------------------------------------

def deserialize_preset(
    data: Mapping[str, Any],
) -> Preset:
    """
    Create a Preset from serialized data.
    """

    preset = Preset.from_dict(
        data
    )

    preset.validate()

    return preset


# ------------------------------------------------------------
# Saving
# ------------------------------------------------------------

def save_preset(
    preset: Preset,
    path: os.PathLike | str,
    *,
    overwrite: bool = True,
) -> Path:
    """
    Save a preset to disk.

    Returns
    -------
    pathlib.Path
        Saved file.
    """

    path = _normalize_preset_path(
        path
    )

    if (

        path.exists()

        and not overwrite

    ):

        raise PresetError(

            f"Preset already exists: {path}"

        )

    _ensure_parent_directory(
        path
    )

    save_json(

        serialize_preset(
            preset
        ),

        path,

    )

    STATISTICS.increment(
        "saved"
    )

    LOGGER.info(

        "Saved preset '%s' -> %s",

        preset.name,

        path,

    )

    return path


# ------------------------------------------------------------

def save_registry(
    directory: os.PathLike | str,
) -> int:
    """
    Save every registered preset.

    Returns
    -------
    int
        Number of presets written.
    """

    directory = Path(directory)

    directory.mkdir(

        parents=True,

        exist_ok=True,

    )

    count = 0

    for preset in registered_presets():

        filename = preset_filename(
            preset.name
        )

        save_preset(

            preset,

            directory / filename,

        )

        count += 1

    return count


# ------------------------------------------------------------
# Loading
# ------------------------------------------------------------

def load_preset(
    path: os.PathLike | str,
) -> Preset:
    """
    Load a preset from disk.
    """

    path = _normalize_preset_path(
        path
    )

    if not path.exists():

        raise PresetNotFoundError(
            str(path)
        )

    data = load_json(
        path
    )

    preset = deserialize_preset(
        data
    )

    STATISTICS.increment(
        "loaded"
    )

    LOGGER.info(

        "Loaded preset '%s'",

        preset.name,

    )

    return preset


# ------------------------------------------------------------

def load_directory(
    directory: os.PathLike | str,
    *,
    recursive: bool = False,
) -> List[Preset]:
    """
    Load every preset within a directory.
    """

    directory = Path(directory)

    if not directory.exists():

        return []

    pattern = (

        "**/*"

        if recursive

        else "*"

    )

    presets: List[
        Preset
    ] = []

    for path in directory.glob(pattern):

        if (

            path.is_file()

            and path.suffix.lower()

            == PRESET_FILE_EXTENSION

        ):

            try:

                presets.append(

                    load_preset(
                        path
                    )

                )

            except Exception as exc:

                LOGGER.warning(

                    "Unable to load %s (%s)",

                    path,

                    exc,

                )

    return presets


# ------------------------------------------------------------
# Registry Persistence
# ------------------------------------------------------------

def load_into_registry(
    directory: os.PathLike | str,
    *,
    overwrite: bool = False,
    recursive: bool = False,
) -> int:
    """
    Load every preset into the global registry.

    Returns
    -------
    int
        Number of presets successfully loaded.
    """

    loaded = 0

    for preset in load_directory(

        directory,

        recursive=recursive,

    ):

        try:

            register_preset(

                preset,

                overwrite=overwrite,

            )

            loaded += 1

        except PresetAlreadyExistsError:

            LOGGER.debug(

                "Skipping duplicate preset '%s'.",

                preset.name,

            )

    return loaded


# ------------------------------------------------------------
# Export
# ------------------------------------------------------------

def export_preset(
    preset: Preset,
    destination: os.PathLike | str,
) -> Path:
    """
    Export a preset.

    Alias for save_preset().
    """

    return save_preset(

        preset,

        destination,

    )


# ------------------------------------------------------------

def export_registry(
    directory: os.PathLike | str,
) -> int:
    """
    Export every registered preset.
    """

    return save_registry(
        directory
    )


# ------------------------------------------------------------
# Import
# ------------------------------------------------------------

def import_preset(
    path: os.PathLike | str,
    *,
    register: bool = True,
    overwrite: bool = False,
) -> Preset:
    """
    Import a preset from disk.
    """

    preset = load_preset(
        path
    )

    if register:

        register_preset(

            preset,

            overwrite=overwrite,

        )

    return preset


# ------------------------------------------------------------
# Convenience
# ------------------------------------------------------------

def builtin_directory() -> Path:
    """
    Default built-in preset directory.
    """

    return (

        Path(__file__).parent

        / BUILTIN_FOLDER_NAME

    )


# ------------------------------------------------------------

def user_directory() -> Path:
    """
    Default user preset directory.
    """

    return (

        Path.home()

        / ".maya_faceit"

        / PRESET_FOLDER_NAME

    )


# ------------------------------------------------------------

def ensure_user_directory() -> Path:
    """
    Ensure the user preset directory exists.
    """

    directory = user_directory()

    directory.mkdir(

        parents=True,

        exist_ok=True,

    )

    return directory


# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

def io_statistics() -> Dict[str, Any]:
    """
    Return I/O statistics.
    """

    return {

        "saved":

            STATISTICS.get(
                "saved",
                0,
            ),

        "loaded":

            STATISTICS.get(
                "loaded",
                0,
            ),

        "registered":

            len(
                PRESET_REGISTRY
            ),

    }


# ------------------------------------------------------------

LOGGER.debug(
    "Preset loading & saving initialized."
)
# ============================================================
# Part 7 - Validation
# ============================================================

"""
Validation utilities for preset integrity.

These helpers verify that presets are structurally correct,
contain valid metadata, supported versions, and consistent
ARKit mappings before being registered or saved.
"""

# ------------------------------------------------------------
# Metadata Validation
# ------------------------------------------------------------

def validate_metadata(
    metadata: PresetMetadata,
) -> None:
    """
    Validate preset metadata.
    """

    if not isinstance(
        metadata,
        PresetMetadata,
    ):
        raise PresetValidationError(
            "Invalid preset metadata."
        )

    metadata.validate()


# ------------------------------------------------------------

def validate_name(
    name: str,
) -> None:
    """
    Validate a preset name.
    """

    if not isinstance(name, str):

        raise PresetValidationError(
            "Preset name must be a string."
        )

    if not name.strip():

        raise PresetValidationError(
            "Preset name cannot be empty."
        )


# ------------------------------------------------------------

def validate_mapping(
    mapping: Mapping[
        str,
        Mapping[str, float]
    ],
) -> None:
    """
    Validate an ARKit mapping.
    """

    if not isinstance(mapping, Mapping):

        raise PresetValidationError(
            "Mapping must be a dictionary."
        )

    for arkit_channel, targets in mapping.items():

        if not isinstance(
            arkit_channel,
            str,
        ):

            raise PresetValidationError(
                "Invalid ARKit channel."
            )

        if not isinstance(
            targets,
            Mapping,
        ):

            raise PresetValidationError(
                f"'{arkit_channel}' must map "
                "to a dictionary."
            )

        for target, weight in targets.items():

            if not isinstance(
                target,
                str,
            ):

                raise PresetValidationError(
                    "Invalid driven channel."
                )

            if not isinstance(
                weight,
                (int, float),
            ):

                raise PresetValidationError(
                    f"Invalid weight for "
                    f"{target}."
                )


# ------------------------------------------------------------

def validate_settings(
    settings: Mapping[
        str,
        Any,
    ],
) -> None:
    """
    Validate runtime settings.
    """

    if not isinstance(
        settings,
        Mapping,
    ):

        raise PresetValidationError(
            "Settings must be a dictionary."
        )


# ------------------------------------------------------------
# Preset Validation
# ------------------------------------------------------------

def validate_preset(
    preset: Preset,
) -> None:
    """
    Validate an entire preset.
    """

    if not isinstance(
        preset,
        Preset,
    ):

        raise PresetValidationError(
            "Object is not a Preset."
        )

    validate_metadata(
        preset.metadata
    )

    validate_mapping(
        preset.mapping
    )

    validate_settings(
        preset.settings
    )

    preset.validate()


# ------------------------------------------------------------

def validate_collection(
    presets: Iterable[
        Preset
    ],
) -> None:
    """
    Validate multiple presets.
    """

    names: Set[str] = set()

    uuids: Set[str] = set()

    for preset in presets:

        validate_preset(
            preset
        )

        if preset.uuid in uuids:

            raise PresetValidationError(

                f"Duplicate UUID: "
                f"{preset.uuid}"

            )

        if preset.name.lower() in names:

            raise PresetValidationError(

                f"Duplicate preset name: "
                f"{preset.name}"

            )

        uuids.add(
            preset.uuid
        )

        names.add(
            preset.name.lower()
        )


# ------------------------------------------------------------
# Registry Validation
# ------------------------------------------------------------

def validate_registry() -> None:
    """
    Validate the runtime registry.
    """

    validate_collection(
        PRESET_REGISTRY.presets()
    )


# ------------------------------------------------------------
# Compatibility
# ------------------------------------------------------------

def validate_version_compatibility(
    preset: Preset,
) -> None:
    """
    Validate preset version support.
    """

    validate_version(
        preset.metadata.version
    )


# ------------------------------------------------------------

def validate_character(
    preset: Preset,
    character: str,
) -> bool:
    """
    Check whether a preset is intended for the
    specified character.

    Returns
    -------
    bool
    """

    return (

        preset.metadata.character.lower()

        == character.lower()

    )


# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

@dataclass(slots=True)
class ValidationResult:
    """
    Validation report.
    """

    valid: bool

    errors: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    # --------------------------------------------------------

    def add_error(
        self,
        message: str,
    ) -> None:

        self.valid = False

        self.errors.append(
            message
        )

    # --------------------------------------------------------

    def add_warning(
        self,
        message: str,
    ) -> None:

        self.warnings.append(
            message
        )


# ------------------------------------------------------------

def validation_report(
    preset: Preset,
) -> ValidationResult:
    """
    Produce a validation report instead of
    raising exceptions.
    """

    report = ValidationResult(
        valid=True
    )

    try:

        validate_preset(
            preset
        )

    except Exception as exc:

        report.add_error(
            str(exc)
        )

    if not preset.mapping:

        report.add_warning(
            "Preset contains no mappings."
        )

    if not preset.metadata.tags:

        report.add_warning(
            "Preset has no tags."
        )

    if not preset.metadata.description:

        report.add_warning(
            "Preset has no description."
        )

    return report


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def is_valid_preset(
    preset: Preset,
) -> bool:
    """
    Return True if the preset is valid.
    """

    try:

        validate_preset(
            preset
        )

        return True

    except Exception:

        return False


# ------------------------------------------------------------

LOGGER.debug(
    "Preset validation subsystem initialized."
)
# ============================================================
# Part 8 - Search & Filtering
# ============================================================

"""
Search and filtering utilities for preset collections and
the runtime registry.

These helpers provide name searches, category filtering,
tag filtering, character matching, and custom predicate
queries.
"""

from fnmatch import fnmatch

# ------------------------------------------------------------
# Internal Helper
# ------------------------------------------------------------

def _match_text(
    value: str,
    query: str,
    *,
    case_sensitive: bool = False,
) -> bool:
    """
    Perform a substring match.
    """

    if not case_sensitive:

        value = value.lower()

        query = query.lower()

    return query in value


# ------------------------------------------------------------
# Name Search
# ------------------------------------------------------------

def find_by_name(
    query: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
    *,
    case_sensitive: bool = False,
) -> List[Preset]:
    """
    Search presets by name.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if _match_text(

            preset.name,

            query,

            case_sensitive=case_sensitive,

        )

    ]


# ------------------------------------------------------------
# Description Search
# ------------------------------------------------------------

def find_by_description(
    query: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Search descriptions.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if _match_text(

            preset.metadata.description,

            query,

        )

    ]


# ------------------------------------------------------------
# Category Filtering
# ------------------------------------------------------------

def filter_by_category(
    category: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Filter presets by category.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if (

            preset.category.lower()

            == category.lower()

        )

    ]


# ------------------------------------------------------------
# Character Filtering
# ------------------------------------------------------------

def filter_by_character(
    character: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Filter presets by character.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if (

            preset.metadata.character.lower()

            == character.lower()

        )

    ]


# ------------------------------------------------------------
# Type Filtering
# ------------------------------------------------------------

def filter_by_type(
    preset_type: PresetType,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Filter by preset type.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if preset.type == preset_type

    ]


# ------------------------------------------------------------
# Tag Filtering
# ------------------------------------------------------------

def filter_by_tag(
    tag: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Return presets containing a tag.
    """

    presets = presets or registered_presets()

    tag = tag.lower()

    return [

        preset.copy()

        for preset in presets

        if any(

            existing.lower() == tag

            for existing

            in preset.metadata.tags

        )

    ]


# ------------------------------------------------------------
# Wildcard Search
# ------------------------------------------------------------

def wildcard_search(
    pattern: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Wildcard search using shell-style patterns.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if fnmatch(

            preset.name,

            pattern,

        )

    ]


# ------------------------------------------------------------
# Favorites
# ------------------------------------------------------------

def favorite_presets(
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Return favorite presets.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if preset.favorite

    ]


# ------------------------------------------------------------
# Custom Filtering
# ------------------------------------------------------------

def filter_presets(
    predicate: Callable[
        [Preset],
        bool,
    ],
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[Preset]:
    """
    Filter using a callable predicate.
    """

    presets = presets or registered_presets()

    return [

        preset.copy()

        for preset in presets

        if predicate(preset)

    ]


# ------------------------------------------------------------
# Multi-field Search
# ------------------------------------------------------------

def search_presets(
    query: str,
    presets: Optional[
        Iterable[Preset]
    ] = None,
) -> List[PresetSearchResult]:
    """
    Search multiple preset fields.

    Matches:

        • Name
        • Description
        • Category
        • Character
        • Tags
    """

    presets = presets or registered_presets()

    results: List[
        PresetSearchResult
    ] = []

    query_lower = query.lower()

    for preset in presets:

        score = 0.0

        matched: List[str] = []

        if query_lower in preset.name.lower():

            score += 5

            matched.append("name")

        if query_lower in (

            preset.metadata.description.lower()

        ):

            score += 2

            matched.append("description")

        if query_lower in (

            preset.category.lower()

        ):

            score += 2

            matched.append("category")

        if query_lower in (

            preset.metadata.character.lower()

        ):

            score += 2

            matched.append("character")

        for tag in preset.metadata.tags:

            if query_lower in tag.lower():

                score += 1

                matched.append("tag")

                break

        if score:

            results.append(

                PresetSearchResult(

                    preset=preset.copy(),

                    score=score,

                    matched_fields=matched,

                )

            )

    results.sort(

        key=lambda item: item.score,

        reverse=True,

    )

    return results


# ------------------------------------------------------------
# Sorting
# ------------------------------------------------------------

def sort_presets(
    presets: Iterable[
        Preset
    ],
    *,
    key: str = "name",
    reverse: bool = False,
) -> List[Preset]:
    """
    Sort presets.

    Supported keys:

        name
        category
        character
        created
        modified
        priority
    """

    presets = list(presets)

    lookup = {

        "name":
            lambda p: p.name.lower(),

        "category":
            lambda p: p.category.lower(),

        "character":
            lambda p: (
                p.metadata.character.lower()
            ),

        "created":
            lambda p: p.metadata.created,

        "modified":
            lambda p: p.metadata.modified,

        "priority":
            lambda p: p.metadata.priority,

    }

    sorter = lookup.get(

        key,

        lookup["name"],

    )

    presets.sort(

        key=sorter,

        reverse=reverse,

    )

    return [

        preset.copy()

        for preset in presets

    ]


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def search_statistics() -> Dict[str, Any]:
    """
    Statistics describing the registered presets.
    """

    presets = registered_presets()

    return {

        "total":

            len(presets),

        "favorites":

            len(

                favorite_presets(
                    presets
                )

            ),

        "categories":

            len({

                preset.category

                for preset

                in presets

            }),

        "characters":

            len({

                preset.metadata.character

                for preset

                in presets

            }),

        "types":

            len({

                preset.type

                for preset

                in presets

            }),

    }


# ------------------------------------------------------------

LOGGER.debug(
    "Preset search & filtering initialized."
)
# ============================================================
# Part 9 - Runtime Preset Manager
# ============================================================

"""
Runtime preset management.

This layer is responsible for:

    • Active preset management
    • Loading/unloading presets
    • Runtime cache
    • Recently used presets
    • Session state
    • Default preset selection
    • Activation callbacks

The RuntimePresetManager operates on the global
PRESET_REGISTRY but maintains its own runtime state.
"""

# ------------------------------------------------------------
# Runtime Preset Manager
# ------------------------------------------------------------

class RuntimePresetManager:
    """
    Runtime manager responsible for activating and
    switching presets.
    """

    MAX_RECENT = 20

    # --------------------------------------------------------

    def __init__(self):

        self._active_uuid: Optional[str] = None

        self._default_uuid: Optional[str] = None

        self._cache: Dict[
            str,
            PresetCacheEntry
        ] = {}

        self._recent: List[str] = []

        self._callbacks: List[
            Callable[[Preset], None]
        ] = []

        self._lock = threading.RLock()

    # --------------------------------------------------------
    # Active Preset
    # --------------------------------------------------------

    @property
    def active_uuid(self) -> Optional[str]:

        return self._active_uuid

    # --------------------------------------------------------

    @property
    def active_preset(self) -> Optional[Preset]:

        if self._active_uuid is None:

            return None

        return self.get_cached(
            self._active_uuid
        )

    # --------------------------------------------------------

    def activate(
        self,
        preset: Preset | str,
    ) -> Preset:
        """
        Activate a preset.
        """

        with self._lock:

            if isinstance(
                preset,
                Preset,
            ):

                uuid = preset.uuid

            else:

                uuid = preset

            preset = PRESET_REGISTRY.get(
                uuid
            )

            self._active_uuid = uuid

            self._cache_preset(
                preset
            )

            self._add_recent(
                uuid
            )

            self._emit(
                preset
            )

            LOGGER.info(
                "Activated preset '%s'.",
                preset.name,
            )

            return preset.copy()

    # --------------------------------------------------------

    def deactivate(self) -> None:
        """
        Clear the active preset.
        """

        self._active_uuid = None

    # --------------------------------------------------------

    def is_active(
        self,
        preset: Preset | str,
    ) -> bool:

        uuid = (

            preset.uuid

            if isinstance(
                preset,
                Preset,
            )

            else preset

        )

        return uuid == self._active_uuid

    # --------------------------------------------------------
    # Default Preset
    # --------------------------------------------------------

    def set_default(
        self,
        preset: Preset | str,
    ) -> None:

        self._default_uuid = (

            preset.uuid

            if isinstance(
                preset,
                Preset,
            )

            else preset

        )

    # --------------------------------------------------------

    def default_preset(
        self,
    ) -> Optional[Preset]:

        if self._default_uuid is None:

            return None

        return PRESET_REGISTRY.get(
            self._default_uuid
        )

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    def _cache_preset(
        self,
        preset: Preset,
    ) -> None:

        self._cache[
            preset.uuid
        ] = PresetCacheEntry(

            preset.copy()

        )

    # --------------------------------------------------------

    def get_cached(
        self,
        uuid: str,
    ) -> Optional[Preset]:

        entry = self._cache.get(
            uuid
        )

        if entry is None:

            try:

                preset = PRESET_REGISTRY.get(
                    uuid
                )

            except Exception:

                return None

            self._cache_preset(
                preset
            )

            entry = self._cache[
                uuid
            ]

        entry.touch()

        return entry.preset.copy()

    # --------------------------------------------------------

    def clear_cache(
        self,
    ) -> None:

        self._cache.clear()

    # --------------------------------------------------------

    def cache_statistics(
        self,
    ) -> Dict[str, Any]:

        return {

            "entries":
                len(
                    self._cache
                ),

            "hits":

                sum(

                    item.hit_count

                    for item

                    in self._cache.values()

                ),

        }

    # --------------------------------------------------------
    # Recent Presets
    # --------------------------------------------------------

    def _add_recent(
        self,
        uuid: str,
    ) -> None:

        if uuid in self._recent:

            self._recent.remove(
                uuid
            )

        self._recent.insert(
            0,
            uuid,
        )

        self._recent = self._recent[
            : self.MAX_RECENT
        ]

    # --------------------------------------------------------

    def recent_presets(
        self,
    ) -> List[Preset]:

        result = []

        for uuid in self._recent:

            try:

                result.append(

                    PRESET_REGISTRY.get(
                        uuid
                    )

                )

            except Exception:

                pass

        return result

    # --------------------------------------------------------

    def clear_recent(
        self,
    ) -> None:

        self._recent.clear()

    # --------------------------------------------------------
    # Callbacks
    # --------------------------------------------------------

    def register_callback(
        self,
        callback: Callable[
            [Preset],
            None,
        ],
    ) -> None:

        if callback not in self._callbacks:

            self._callbacks.append(
                callback
            )

    # --------------------------------------------------------

    def unregister_callback(
        self,
        callback: Callable,
    ) -> None:

        if callback in self._callbacks:

            self._callbacks.remove(
                callback
            )

    # --------------------------------------------------------

    def _emit(
        self,
        preset: Preset,
    ) -> None:

        for callback in list(
            self._callbacks
        ):

            try:

                callback(
                    preset.copy()
                )

            except Exception:

                LOGGER.exception(
                    "Preset callback failed."
                )

    # --------------------------------------------------------
    # Session
    # --------------------------------------------------------

    def session_state(
        self,
    ) -> Dict[str, Any]:

        return {

            "active":

                self._active_uuid,

            "default":

                self._default_uuid,

            "recent":

                list(
                    self._recent
                ),

            "cache":

                len(
                    self._cache
                ),

        }

    # --------------------------------------------------------

    def restore_session(
        self,
        state: Mapping[
            str,
            Any,
        ],
    ) -> None:

        self._active_uuid = state.get(
            "active"
        )

        self._default_uuid = state.get(
            "default"
        )

        self._recent = list(

            state.get(
                "recent",
                [],
            )

        )

    # --------------------------------------------------------

    def reset(
        self,
    ) -> None:

        self.deactivate()

        self.clear_cache()

        self.clear_recent()

        self._default_uuid = None


# ------------------------------------------------------------
# Global Runtime Manager
# ------------------------------------------------------------

RUNTIME_PRESETS = RuntimePresetManager()


# ------------------------------------------------------------
# Convenience API
# ------------------------------------------------------------

def activate_preset(
    preset: Preset | str,
) -> Preset:

    return RUNTIME_PRESETS.activate(
        preset
    )


# ------------------------------------------------------------

def active_preset(
) -> Optional[Preset]:

    return RUNTIME_PRESETS.active_preset


# ------------------------------------------------------------

def deactivate_preset(
) -> None:

    RUNTIME_PRESETS.deactivate()


# ------------------------------------------------------------

def recent_presets(
) -> List[Preset]:

    return RUNTIME_PRESETS.recent_presets()


# ------------------------------------------------------------

def runtime_statistics(
) -> Dict[str, Any]:
    """
    Runtime manager statistics.
    """

    return {

        "active":

            RUNTIME_PRESETS.active_uuid,

        "cache":

            RUNTIME_PRESETS.cache_statistics(),

        "recent":

            len(
                RUNTIME_PRESETS._recent
            ),

        "callbacks":

            len(
                RUNTIME_PRESETS._callbacks
            ),

    }


# ------------------------------------------------------------

LOGGER.debug(
    "Runtime preset manager initialized."
)
# ============================================================
# Part 10 - User Presets
# ============================================================

"""
User preset management.

This section manages presets created by end users,
including storage, editing, favorites, import/export,
and synchronization with the runtime registry.
"""

# ------------------------------------------------------------
# User Preset Manager
# ------------------------------------------------------------

class UserPresetManager:
    """
    Manager responsible for user-created presets.
    """

    # --------------------------------------------------------

    def __init__(self):

        self._directory = ensure_user_directory()

        self._favorites: Set[str] = set()

        self._lock = threading.RLock()

    # --------------------------------------------------------
    # Properties
    # --------------------------------------------------------

    @property
    def directory(self) -> Path:
        """
        User preset directory.
        """

        return self._directory

    # --------------------------------------------------------

    def set_directory(
        self,
        directory: os.PathLike | str,
    ) -> None:
        """
        Change the user preset directory.
        """

        directory = Path(directory)

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._directory = directory

    # --------------------------------------------------------
    # Preset Creation
    # --------------------------------------------------------

    def create(
        self,
        name: str,
        **kwargs,
    ) -> Preset:
        """
        Create a new user preset.
        """

        preset = create_preset(

            name,

            preset_type=PresetType.USER,

            scope=PresetScope.USER,

            **kwargs,

        )

        register_preset(
            preset
        )

        return preset

    # --------------------------------------------------------

    def clone(
        self,
        preset: Preset,
        *,
        new_name: Optional[str] = None,
    ) -> Preset:
        """
        Clone an existing preset.
        """

        clone = clone_preset(

            preset,

            new_name=new_name,

        )

        clone.metadata.preset_type = (
            PresetType.USER
        )

        clone.metadata.scope = (
            PresetScope.USER
        )

        register_preset(
            clone
        )

        return clone

    # --------------------------------------------------------
    # Saving
    # --------------------------------------------------------

    def save(
        self,
        preset: Preset,
    ) -> Path:
        """
        Save a preset into the user directory.
        """

        filename = preset_filename(
            preset.name
        )

        return save_preset(

            preset,

            self.directory / filename,

        )

    # --------------------------------------------------------

    def save_all(
        self,
    ) -> int:
        """
        Save every registered user preset.
        """

        count = 0

        for preset in filter_by_type(
            PresetType.USER
        ):

            self.save(
                preset
            )

            count += 1

        return count

    # --------------------------------------------------------
    # Loading
    # --------------------------------------------------------

    def load_all(
        self,
        *,
        overwrite: bool = False,
    ) -> int:
        """
        Load every user preset from disk.
        """

        return load_into_registry(

            self.directory,

            overwrite=overwrite,

        )

    # --------------------------------------------------------

    def reload(
        self,
    ) -> int:
        """
        Reload all user presets.
        """

        return self.load_all(
            overwrite=True
        )

    # --------------------------------------------------------
    # Removal
    # --------------------------------------------------------

    def delete(
        self,
        preset: Preset | str,
    ) -> bool:
        """
        Delete a user preset.
        """

        if isinstance(
            preset,
            Preset,
        ):

            preset = preset.uuid

        try:

            existing = get_preset(
                preset
            )

        except Exception:

            return False

        path = (

            self.directory /

            preset_filename(
                existing.name
            )

        )

        if path.exists():

            path.unlink()

        unregister_preset(
            preset
        )

        self._favorites.discard(
            preset
        )

        return True

    # --------------------------------------------------------
    # Favorites
    # --------------------------------------------------------

    def add_favorite(
        self,
        preset: Preset | str,
    ) -> None:
        """
        Mark a preset as favorite.
        """

        if isinstance(
            preset,
            Preset,
        ):

            preset.favorite = True

            preset = preset.uuid

        self._favorites.add(
            preset
        )

    # --------------------------------------------------------

    def remove_favorite(
        self,
        preset: Preset | str,
    ) -> None:
        """
        Remove favorite.
        """

        if isinstance(
            preset,
            Preset,
        ):

            preset.favorite = False

            preset = preset.uuid

        self._favorites.discard(
            preset
        )

    # --------------------------------------------------------

    def favorites(
        self,
    ) -> List[Preset]:
        """
        Return favorite presets.
        """

        result: List[
            Preset
        ] = []

        for uuid in sorted(
            self._favorites
        ):

            try:

                result.append(

                    get_preset(
                        uuid
                    )

                )

            except Exception:

                pass

        return result

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    def presets(
        self,
    ) -> List[Preset]:
        """
        Return all registered user presets.
        """

        return filter_by_type(
            PresetType.USER
        )

    # --------------------------------------------------------

    def names(
        self,
    ) -> List[str]:
        """
        Return user preset names.
        """

        return sorted(

            preset.name

            for preset

            in self.presets()

        )

    # --------------------------------------------------------

    def count(
        self,
    ) -> int:

        return len(
            self.presets()
        )

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    def statistics(
        self,
    ) -> Dict[str, Any]:
        """
        Return user preset statistics.
        """

        return {

            "directory":

                str(
                    self.directory
                ),

            "count":

                self.count(),

            "favorites":

                len(
                    self._favorites
                ),

            "registered":

                len(
                    PRESET_REGISTRY
                ),

        }


# ------------------------------------------------------------
# Global User Manager
# ------------------------------------------------------------

USER_PRESETS = UserPresetManager()

# ------------------------------------------------------------
# Convenience API
# ------------------------------------------------------------

def create_user_preset(
    name: str,
    **kwargs,
) -> Preset:
    """
    Create and register a user preset.
    """

    return USER_PRESETS.create(
        name,
        **kwargs,
    )


# ------------------------------------------------------------

def save_user_presets(
) -> int:
    """
    Save every user preset.
    """

    return USER_PRESETS.save_all()


# ------------------------------------------------------------

def load_user_presets(
    *,
    overwrite: bool = False,
) -> int:
    """
    Load all user presets.
    """

    return USER_PRESETS.load_all(
        overwrite=overwrite
    )


# ------------------------------------------------------------

def favorite_user_preset(
    preset: Preset | str,
) -> None:
    """
    Mark a user preset as favorite.
    """

    USER_PRESETS.add_favorite(
        preset
    )


# ------------------------------------------------------------

def user_preset_statistics(
) -> Dict[str, Any]:
    """
    User preset statistics.
    """

    return USER_PRESETS.statistics()


# ------------------------------------------------------------

LOGGER.debug(
    "User preset manager initialized."
)
# ============================================================
# Part 11 - Versioning & Migration
# ============================================================

"""
Versioning and migration support.

This subsystem allows preset files created with older
versions of maya_faceit to be upgraded automatically to the
current preset schema.

Migration functions are registered by source version and are
executed sequentially until the target version is reached.
"""

# ------------------------------------------------------------
# Version Constants
# ------------------------------------------------------------

CURRENT_PRESET_VERSION = DEFAULT_PRESET_VERSION

# ------------------------------------------------------------
# Migration Registry
# ------------------------------------------------------------

_MIGRATIONS: Dict[
    Tuple[str, str],
    Callable[[Dict[str, Any]], Dict[str, Any]],
] = OrderedDict()


# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

def register_migration(
    source_version: str,
    target_version: str,
    migration: Callable[
        [Dict[str, Any]],
        Dict[str, Any],
    ],
) -> None:
    """
    Register a migration function.
    """

    key = (
        source_version,
        target_version,
    )

    _MIGRATIONS[key] = migration

    LOGGER.info(

        "Registered preset migration %s -> %s",

        source_version,

        target_version,

    )


# ------------------------------------------------------------

def unregister_migration(
    source_version: str,
    target_version: str,
) -> bool:
    """
    Remove a migration.
    """

    return (

        _MIGRATIONS.pop(

            (
                source_version,
                target_version,
            ),

            None,

        )

        is not None

    )


# ------------------------------------------------------------
# Query
# ------------------------------------------------------------

def available_migrations(
) -> List[Tuple[str, str]]:
    """
    Return registered migrations.
    """

    return list(
        _MIGRATIONS.keys()
    )


# ------------------------------------------------------------

def has_migration(
    source_version: str,
    target_version: str,
) -> bool:
    """
    Return True if a migration exists.
    """

    return (

        source_version,
        target_version,

    ) in _MIGRATIONS


# ------------------------------------------------------------
# Migration Engine
# ------------------------------------------------------------

def migrate_dictionary(
    data: Mapping[str, Any],
    *,
    target_version: str = CURRENT_PRESET_VERSION,
) -> Dict[str, Any]:
    """
    Migrate serialized preset data.
    """

    data = deep_copy(data)

    metadata = data.setdefault(
        "metadata",
        {},
    )

    version = metadata.get(
        "version",
        "1.0",
    )

    if version == target_version:

        return data

    visited: Set[str] = set()

    while version != target_version:

        if version in visited:

            raise VersionMismatchError(

                "Migration loop detected."

            )

        visited.add(
            version
        )

        migrated = False

        for (

            source,

            target,

        ), function in _MIGRATIONS.items():

            if source != version:

                continue

            LOGGER.info(

                "Migrating preset %s -> %s",

                source,

                target,

            )

            data = function(data)

            metadata = data.setdefault(
                "metadata",
                {},
            )

            metadata["version"] = target

            version = target

            migrated = True

            break

        if not migrated:

            raise VersionMismatchError(

                f"No migration path from "
                f"{version} to "
                f"{target_version}"

            )

    return data


# ------------------------------------------------------------

def migrate_preset(
    preset: Preset,
    *,
    target_version: str = CURRENT_PRESET_VERSION,
) -> Preset:
    """
    Migrate a Preset object.
    """

    data = migrate_dictionary(

        preset.to_dict(),

        target_version=target_version,

    )

    migrated = Preset.from_dict(
        data
    )

    migrated.validate()

    return migrated


# ------------------------------------------------------------
# Compatibility
# ------------------------------------------------------------

def is_compatible(
    version: str,
) -> bool:
    """
    Return True if the version is directly
    supported without migration.
    """

    return (

        version

        == CURRENT_PRESET_VERSION

    )


# ------------------------------------------------------------

def requires_migration(
    version: str,
) -> bool:
    """
    Determine whether migration is required.
    """

    return not is_compatible(
        version
    )


# ------------------------------------------------------------

def ensure_latest(
    preset: Preset,
) -> Preset:
    """
    Upgrade a preset if required.
    """

    version = preset.metadata.version

    if is_compatible(version):

        return preset

    return migrate_preset(
        preset
    )


# ------------------------------------------------------------
# Default Migration
# ------------------------------------------------------------

def _migration_100_to_100(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Identity migration.

    Serves as the default migration for the
    initial preset format.
    """

    return deep_copy(data)


register_migration(

    "1.0",

    "1.0",

    _migration_100_to_100,

)

# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

def migration_statistics(
) -> Dict[str, Any]:
    """
    Return migration statistics.
    """

    return {

        "current_version":

            CURRENT_PRESET_VERSION,

        "supported_versions":

            sorted(
                SUPPORTED_PRESET_VERSIONS
            ),

        "registered_migrations":

            len(
                _MIGRATIONS
            ),

        "migration_paths":

            [

                f"{src}->{dst}"

                for (

                    src,

                    dst,

                )

                in _MIGRATIONS

            ],

    }


# ------------------------------------------------------------

def validate_migrations(
) -> None:
    """
    Validate the migration registry.
    """

    for (

        source,

        target,

    ), function in _MIGRATIONS.items():

        if not callable(
            function
        ):

            raise PresetValidationError(

                f"Migration "
                f"{source}->{target} "
                f"is not callable."

            )


# ------------------------------------------------------------

LOGGER.debug(
    "Preset migration subsystem initialized."
)
# ============================================================
# Part 12 - Statistics & Diagnostics
# ============================================================

"""
Statistics and diagnostics for the preset subsystem.

Provides:

    • Registry statistics
    • Runtime statistics
    • User preset statistics
    • Built-in preset statistics
    • Migration statistics
    • Health checks
    • Integrity verification
    • Diagnostic reports
"""

# ------------------------------------------------------------
# Statistics Collector
# ------------------------------------------------------------

@dataclass(slots=True)
class PresetStatistics:
    """
    Overall preset statistics.
    """

    total: int = 0

    builtin: int = 0

    user: int = 0

    project: int = 0

    template: int = 0

    character: int = 0

    favorites: int = 0

    active: int = 0

    categories: int = 0

    characters: int = 0

    mappings: int = 0

    created: datetime = field(
        default_factory=now
    )

    # --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:

        return {

            "total": self.total,

            "builtin": self.builtin,

            "user": self.user,

            "project": self.project,

            "template": self.template,

            "character": self.character,

            "favorites": self.favorites,

            "active": self.active,

            "categories": self.categories,

            "characters": self.characters,

            "mappings": self.mappings,

            "created": self.created.isoformat(),

        }


# ------------------------------------------------------------
# Registry Statistics
# ------------------------------------------------------------

def collect_statistics() -> PresetStatistics:
    """
    Collect runtime statistics.
    """

    presets = PRESET_REGISTRY.presets()

    stats = PresetStatistics()

    stats.total = len(presets)

    stats.active = (
        1 if RUNTIME_PRESETS.active_uuid else 0
    )

    categories = set()

    characters = set()

    mapping_count = 0

    for preset in presets:

        categories.add(
            preset.category
        )

        characters.add(
            preset.metadata.character
        )

        mapping_count += len(
            preset.mapping
        )

        if preset.favorite:
            stats.favorites += 1

        if preset.type == PresetType.BUILTIN:
            stats.builtin += 1

        elif preset.type == PresetType.USER:
            stats.user += 1

        elif preset.type == PresetType.PROJECT:
            stats.project += 1

        elif preset.type == PresetType.TEMPLATE:
            stats.template += 1

        elif preset.type == PresetType.CHARACTER:
            stats.character += 1

    stats.categories = len(categories)

    stats.characters = len(characters)

    stats.mappings = mapping_count

    return stats


# ------------------------------------------------------------
# Health Check
# ------------------------------------------------------------

def preset_health() -> Dict[str, Any]:
    """
    Perform a quick health check.
    """

    issues = []

    try:

        validate_registry()

    except Exception as exc:

        issues.append(str(exc))

    return {

        "healthy":

            len(issues) == 0,

        "issues":

            issues,

        "registry_size":

            len(PRESET_REGISTRY),

        "cache_size":

            len(
                RUNTIME_PRESETS._cache
            ),

        "user_directory":

            str(
                USER_PRESETS.directory
            ),

    }


# ------------------------------------------------------------
# Integrity Check
# ------------------------------------------------------------

def verify_integrity() -> List[str]:
    """
    Verify all registered presets.
    """

    errors: List[str] = []

    for preset in registered_presets():

        try:

            validate_preset(
                preset
            )

        except Exception as exc:

            errors.append(

                f"{preset.name}: {exc}"

            )

    return errors


# ------------------------------------------------------------
# Diagnostics Report
# ------------------------------------------------------------

def diagnostics_report() -> Dict[str, Any]:
    """
    Produce a complete diagnostics report.
    """

    return {

        "module":

            MODULE_NAME,

        "version":

            MODULE_VERSION,

        "statistics":

            collect_statistics().to_dict(),

        "registry":

            registry_statistics(),

        "runtime":

            runtime_statistics(),

        "user":

            user_preset_statistics(),

        "builtin":

            builtin_statistics(),

        "migration":

            migration_statistics(),

        "io":

            io_statistics(),

        "health":

            preset_health(),

    }


# ------------------------------------------------------------
# Console Report
# ------------------------------------------------------------

def print_diagnostics() -> None:
    """
    Print a readable diagnostics report.
    """

    report = diagnostics_report()

    print("=" * 70)
    print("Preset Diagnostics")
    print("=" * 70)

    for section, values in report.items():

        print()

        print(f"[{section}]")

        if isinstance(values, Mapping):

            for key, value in values.items():

                print(f"{key}: {value}")

        else:

            print(values)

    print("=" * 70)


# ------------------------------------------------------------
# Export Report
# ------------------------------------------------------------

def export_diagnostics(
    path: os.PathLike | str,
) -> Path:
    """
    Export diagnostics as JSON.
    """

    path = Path(path)

    save_json(

        diagnostics_report(),

        path,

    )

    return path


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

def preset_summary() -> Dict[str, Any]:
    """
    Lightweight summary.
    """

    stats = collect_statistics()

    return {

        "total":

            stats.total,

        "builtin":

            stats.builtin,

        "user":

            stats.user,

        "favorites":

            stats.favorites,

        "active":

            bool(
                RUNTIME_PRESETS.active_uuid
            ),

    }


# ------------------------------------------------------------
# Logger
# ------------------------------------------------------------

LOGGER.info(

    "Preset subsystem initialized "

    "(%d registered presets).",

    len(PRESET_REGISTRY),

)

LOGGER.debug(
    "Statistics & diagnostics initialized."
)
# ============================================================
# Part 13 - Public API
# ============================================================

"""
Public API for the ARKit preset management subsystem.

Only symbols listed in __all__ are considered part of the
stable public interface. Internal helpers should remain
private and may change without notice.
"""

# ------------------------------------------------------------
# Module Information
# ------------------------------------------------------------

__title__ = "maya_faceit ARKit Preset Manager"

__description__ = (
    "Preset management system for the maya_faceit "
    "ARKit mapper."
)

__author__ = "OpenAI"

__license__ = "MIT"

try:
    __version__ = MODULE_VERSION
except NameError:
    __version__ = "1.0.0"

# ------------------------------------------------------------
# Public Exports
# ------------------------------------------------------------

__all__ = [

    # ========================================================
    # Foundation
    # ========================================================

    "MODULE_NAME",
    "MODULE_VERSION",
    "CURRENT_PRESET_VERSION",
    "PRESET_FILE_EXTENSION",
    "PRESET_FOLDER_NAME",
    "BUILTIN_FOLDER_NAME",
    "USER_FOLDER_NAME",

    "PresetType",
    "PresetStatus",
    "PresetScope",

    # ========================================================
    # Data Models
    # ========================================================

    "PresetMetadata",
    "Preset",
    "PresetSummary",
    "PresetSearchResult",
    "PresetCacheEntry",
    "RegistryEntry",
    "PresetStatistics",
    "ValidationResult",

    # ========================================================
    # Built-in Presets
    # ========================================================

    "EMPTY_PRESET",
    "IDENTITY_PRESET",
    "FACEIT_TEMPLATE_PRESET",

    "builtin_presets",
    "builtin_preset",
    "builtin_categories",
    "builtin_names",
    "builtin_statistics",
    "validate_builtin_presets",

    # ========================================================
    # Registry
    # ========================================================

    "PresetRegistry",
    "PRESET_REGISTRY",

    "register_preset",
    "unregister_preset",
    "registered_presets",
    "get_preset",
    "get_preset_by_name",
    "preset_summaries",
    "registry_statistics",

    # ========================================================
    # Preset Creation
    # ========================================================

    "create_preset",
    "create_empty_preset",
    "create_identity_preset",
    "clone_preset",
    "duplicate_preset",
    "create_from_mapping",
    "rename_preset",
    "replace_mapping",
    "update_mapping",
    "clear_mapping",
    "update_setting",
    "remove_setting",
    "clear_settings",
    "mark_favorite",
    "protect_preset",
    "register_new_preset",

    # ========================================================
    # Loading / Saving
    # ========================================================

    "serialize_preset",
    "deserialize_preset",
    "save_preset",
    "load_preset",
    "save_registry",
    "load_directory",
    "load_into_registry",
    "export_preset",
    "export_registry",
    "import_preset",
    "builtin_directory",
    "user_directory",
    "ensure_user_directory",
    "io_statistics",

    # ========================================================
    # Validation
    # ========================================================

    "validate_metadata",
    "validate_name",
    "validate_mapping",
    "validate_settings",
    "validate_preset",
    "validate_collection",
    "validate_registry",
    "validate_version_compatibility",
    "validate_character",
    "validation_report",
    "is_valid_preset",

    # ========================================================
    # Search & Filtering
    # ========================================================

    "find_by_name",
    "find_by_description",
    "filter_by_category",
    "filter_by_character",
    "filter_by_type",
    "filter_by_tag",
    "wildcard_search",
    "favorite_presets",
    "filter_presets",
    "search_presets",
    "sort_presets",
    "search_statistics",

    # ========================================================
    # Runtime Manager
    # ========================================================

    "RuntimePresetManager",
    "RUNTIME_PRESETS",
    "activate_preset",
    "active_preset",
    "deactivate_preset",
    "recent_presets",
    "runtime_statistics",

    # ========================================================
    # User Presets
    # ========================================================

    "UserPresetManager",
    "USER_PRESETS",
    "create_user_preset",
    "save_user_presets",
    "load_user_presets",
    "favorite_user_preset",
    "user_preset_statistics",

    # ========================================================
    # Versioning & Migration
    # ========================================================

    "register_migration",
    "unregister_migration",
    "available_migrations",
    "has_migration",
    "migrate_dictionary",
    "migrate_preset",
    "is_compatible",
    "requires_migration",
    "ensure_latest",
    "migration_statistics",
    "validate_migrations",

    # ========================================================
    # Statistics & Diagnostics
    # ========================================================

    "collect_statistics",
    "preset_health",
    "verify_integrity",
    "diagnostics_report",
    "print_diagnostics",
    "export_diagnostics",
    "preset_summary",
]

# ------------------------------------------------------------
# Initialization
# ------------------------------------------------------------

def initialize() -> None:
    """
    Initialize the preset subsystem.
    Safe to call multiple times.
    """

    validate_builtin_presets()

    validate_migrations()

    LOGGER.info(
        "%s v%s initialized.",
        MODULE_NAME,
        MODULE_VERSION,
    )


# ------------------------------------------------------------

def shutdown() -> None:
    """
    Shut down the preset subsystem and clear
    runtime-only state.
    """

    RUNTIME_PRESETS.reset()

    LOGGER.info(
        "%s shutdown complete.",
        MODULE_NAME,
    )


# ------------------------------------------------------------
# Automatic Initialization
# ------------------------------------------------------------

try:

    initialize()

except Exception:

    LOGGER.exception(
        "Failed to initialize preset subsystem."
    )

# ------------------------------------------------------------

LOGGER.debug(
    "Public API initialized."
)