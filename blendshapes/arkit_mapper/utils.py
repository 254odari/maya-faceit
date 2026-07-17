# ============================================================
# blendshapes/arkit_mapper/utils.py
# Part 1.0 - Foundation
# ============================================================

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import os
import platform
import re
import statistics
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    DefaultDict,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# ------------------------------------------------------------
# Optional Dependencies
# ------------------------------------------------------------

try:
    import numpy as np

    HAS_NUMPY = True

except ImportError:

    np = None

    HAS_NUMPY = False

try:
    import maya.cmds as cmds

    HAS_MAYA = True

except Exception:

    cmds = None

    HAS_MAYA = False

# ------------------------------------------------------------
# Module Information
# ------------------------------------------------------------

MODULE_NAME = "maya_faceit.blendshapes.arkit_mapper.utils"

MODULE_VERSION = "1.0.0"

MODULE_AUTHOR = "OpenAI"

SUPPORTED_ARKIT_VERSION = "52"

# ------------------------------------------------------------
# Generic Type Variables
# ------------------------------------------------------------

T = TypeVar("T")

KT = TypeVar("KT")

VT = TypeVar("VT")

Number = Union[int, float]

PathLike = Union[str, Path]

JsonValue = Union[
    None,
    bool,
    int,
    float,
    str,
    List[Any],
    Dict[str, Any],
]

BlendshapeDict = Dict[str, float]

MappingDict = Dict[str, BlendshapeDict]

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

EPSILON = 1e-8

DEFAULT_PRECISION = 6

DEFAULT_BATCH_SIZE = 128

DEFAULT_TIMER_NAME = "default"

MAX_BLENDSHAPE_VALUE = 1.0

MIN_BLENDSHAPE_VALUE = 0.0

# ------------------------------------------------------------
# Common ARKit Defaults
# ------------------------------------------------------------

EMPTY_BLENDSHAPES: BlendshapeDict = {}

EMPTY_MAPPING: MappingDict = {}

# ------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------

class UtilsError(Exception):
    """
    Base utility exception.
    """
    pass


class ValidationError(UtilsError):
    """
    Raised when validation fails.
    """
    pass


class SerializationError(UtilsError):
    """
    Raised during serialization failures.
    """
    pass


class TimerError(UtilsError):
    """
    Raised by timing utilities.
    """
    pass


class MayaUnavailableError(UtilsError):
    """
    Raised when Maya functionality
    is requested outside Maya.
    """
    pass


# ------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------

@dataclass(slots=True)
class TimerResult:
    """
    Timing result.
    """

    name: str

    start_time: float

    end_time: float

    elapsed: float

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(slots=True)
class Report:
    """
    Generic utility report.
    """

    title: str

    created: datetime = field(
        default_factory=datetime.now
    )

    entries: Dict[str, Any] = field(
        default_factory=dict
    )

    warnings: List[str] = field(
        default_factory=list
    )

    errors: List[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class UtilityStatistics:
    """
    Runtime statistics shared across
    utility helpers.
    """

    calls: int = 0

    failures: int = 0

    elapsed_time: float = 0.0

    last_call: Optional[datetime] = None


# ------------------------------------------------------------
# Utility Registry
# ------------------------------------------------------------

class UtilityRegistry:
    """
    Registry for reusable helper functions.
    """

    def __init__(self):

        self._registry: Dict[
            str,
            Callable[..., Any]
        ] = {}

    # -----------------------------------------------------

    def register(
        self,
        name: str,
        function: Callable[..., Any],
    ) -> None:
        """
        Register a helper function.
        """

        self._registry[name] = function

    # -----------------------------------------------------

    def unregister(
        self,
        name: str,
    ) -> None:
        """
        Remove a registered helper.
        """

        self._registry.pop(
            name,
            None,
        )

    # -----------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:
        """
        Check whether a helper exists.
        """

        return name in self._registry

    # -----------------------------------------------------

    def get(
        self,
        name: str,
    ) -> Callable[..., Any]:
        """
        Retrieve a registered helper.
        """

        try:

            return self._registry[name]

        except KeyError as exc:

            raise UtilsError(

                f"Unknown utility: {name}"

            ) from exc

    # -----------------------------------------------------

    def names(
        self,
    ) -> List[str]:
        """
        Return registered names.
        """

        return sorted(
            self._registry.keys()
        )

    # -----------------------------------------------------

    def clear(
        self,
    ) -> None:
        """
        Remove all registered helpers.
        """

        self._registry.clear()

    # -----------------------------------------------------

    def __contains__(
        self,
        name: str,
    ) -> bool:

        return self.exists(name)

    # -----------------------------------------------------

    def __len__(
        self,
    ) -> int:

        return len(
            self._registry
        )

    # -----------------------------------------------------

    def __iter__(
        self,
    ) -> Iterator[str]:

        return iter(
            self.names()
        )


# ------------------------------------------------------------
# Global Registry
# ------------------------------------------------------------

UTILITY_REGISTRY = UtilityRegistry()

UTILITY_STATISTICS = UtilityStatistics()

# ------------------------------------------------------------
# Module Information Helpers
# ------------------------------------------------------------

def module_information() -> Dict[str, Any]:
    """
    Return module metadata.
    """

    return {

        "module":
            MODULE_NAME,

        "version":
            MODULE_VERSION,

        "author":
            MODULE_AUTHOR,

        "python":
            platform.python_version(),

        "platform":
            platform.platform(),

        "maya":
            HAS_MAYA,

        "numpy":
            HAS_NUMPY,

    }


def module_ready() -> bool:
    """
    Basic module health check.
    """

    return True


def reset_statistics() -> None:
    """
    Reset shared runtime statistics.
    """

    global UTILITY_STATISTICS

    UTILITY_STATISTICS = UtilityStatistics()
# ============================================================
# Part 2 - Dictionary Utilities
# ============================================================

# ------------------------------------------------------------
# Basic Dictionary Operations
# ------------------------------------------------------------

def deep_copy_dict(
    data: Mapping[KT, VT],
) -> Dict[KT, VT]:
    """
    Return a deep copy of a mapping.
    """

    return copy.deepcopy(data)


# ------------------------------------------------------------

def deep_merge(
    base: MutableMapping[str, Any],
    update: Mapping[str, Any],
    *,
    overwrite: bool = True,
) -> MutableMapping[str, Any]:
    """
    Recursively merge two dictionaries.
    """

    for key, value in update.items():

        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, Mapping)
        ):

            deep_merge(
                base[key],
                value,
                overwrite=overwrite,
            )

        else:

            if overwrite or key not in base:

                base[key] = copy.deepcopy(value)

    return base


# ------------------------------------------------------------

def shallow_merge(
    *mappings: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Perform a shallow merge.
    """

    merged: Dict[str, Any] = {}

    for mapping in mappings:

        merged.update(mapping)

    return merged


# ------------------------------------------------------------
# Nested Lookup
# ------------------------------------------------------------

def nested_get(
    mapping: Mapping[str, Any],
    path: Union[str, Sequence[str]],
    default: Any = None,
) -> Any:
    """
    Retrieve a nested value.

    Examples
    --------
    nested_get(data, "a.b.c")
    nested_get(data, ["a", "b", "c"])
    """

    if isinstance(path, str):

        path = path.split(".")

    current = mapping

    for key in path:

        if (
            not isinstance(current, Mapping)
            or key not in current
        ):
            return default

        current = current[key]

    return current


# ------------------------------------------------------------

def nested_set(
    mapping: MutableMapping[str, Any],
    path: Union[str, Sequence[str]],
    value: Any,
) -> MutableMapping[str, Any]:
    """
    Set a nested value, creating
    intermediate dictionaries.
    """

    if isinstance(path, str):

        path = path.split(".")

    current = mapping

    for key in path[:-1]:

        current = current.setdefault(
            key,
            {},
        )

    current[path[-1]] = value

    return mapping


# ------------------------------------------------------------

def nested_exists(
    mapping: Mapping[str, Any],
    path: Union[str, Sequence[str]],
) -> bool:
    """
    Check whether a nested key exists.
    """

    sentinel = object()

    return (

        nested_get(
            mapping,
            path,
            sentinel,
        )

        is not sentinel

    )


# ------------------------------------------------------------

def nested_delete(
    mapping: MutableMapping[str, Any],
    path: Union[str, Sequence[str]],
) -> bool:
    """
    Delete a nested key.
    """

    if isinstance(path, str):

        path = path.split(".")

    current = mapping

    for key in path[:-1]:

        if key not in current:

            return False

        current = current[key]

    return (

        current.pop(
            path[-1],
            None,
        )

        is not None

    )


# ------------------------------------------------------------
# Flatten / Unflatten
# ------------------------------------------------------------

def flatten_dict(
    mapping: Mapping[str, Any],
    *,
    separator: str = ".",
    parent_key: str = "",
) -> Dict[str, Any]:
    """
    Flatten nested dictionaries.
    """

    items: Dict[str, Any] = {}

    for key, value in mapping.items():

        full_key = (

            key

            if not parent_key

            else f"{parent_key}{separator}{key}"

        )

        if isinstance(value, Mapping):

            items.update(

                flatten_dict(

                    value,

                    separator=separator,

                    parent_key=full_key,

                )

            )

        else:

            items[full_key] = value

    return items


# ------------------------------------------------------------

def unflatten_dict(
    mapping: Mapping[str, Any],
    *,
    separator: str = ".",
) -> Dict[str, Any]:
    """
    Restore a flattened dictionary.
    """

    result: Dict[str, Any] = {}

    for key, value in mapping.items():

        nested_set(

            result,

            key.split(separator),

            value,

        )

    return result


# ------------------------------------------------------------
# Filtering
# ------------------------------------------------------------

def filter_keys(
    mapping: Mapping[str, Any],
    keys: Iterable[str],
) -> Dict[str, Any]:
    """
    Keep only specified keys.
    """

    keys = set(keys)

    return {

        k: copy.deepcopy(v)

        for k, v in mapping.items()

        if k in keys

    }


# ------------------------------------------------------------

def exclude_keys(
    mapping: Mapping[str, Any],
    keys: Iterable[str],
) -> Dict[str, Any]:
    """
    Remove specified keys.
    """

    keys = set(keys)

    return {

        k: copy.deepcopy(v)

        for k, v in mapping.items()

        if k not in keys

    }


# ------------------------------------------------------------

def filter_values(
    mapping: Mapping[str, Any],
    predicate: Callable[[Any], bool],
) -> Dict[str, Any]:
    """
    Keep values matching a predicate.
    """

    return {

        k: copy.deepcopy(v)

        for k, v in mapping.items()

        if predicate(v)

    }


# ------------------------------------------------------------
# Safe Updates
# ------------------------------------------------------------

def safe_update(
    mapping: MutableMapping[str, Any],
    updates: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Update only existing keys.
    """

    for key, value in updates.items():

        if key in mapping:

            mapping[key] = value

    return mapping


# ------------------------------------------------------------

def update_if_missing(
    mapping: MutableMapping[str, Any],
    defaults: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Insert only missing keys.
    """

    for key, value in defaults.items():

        mapping.setdefault(

            key,

            copy.deepcopy(value),

        )

    return mapping


# ------------------------------------------------------------
# Dictionary Comparison
# ------------------------------------------------------------

def dictionary_difference(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> Dict[str, Tuple[Any, Any]]:
    """
    Compare two dictionaries.

    Returns
    -------
    {
        key:
            (left_value, right_value)
    }
    """

    differences = {}

    keys = set(left) | set(right)

    for key in keys:

        lv = left.get(key)

        rv = right.get(key)

        if lv != rv:

            differences[key] = (

                lv,

                rv,

            )

    return differences


# ------------------------------------------------------------

def dictionary_equal(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    """
    Deep dictionary equality.
    """

    return copy.deepcopy(left) == copy.deepcopy(right)


# ------------------------------------------------------------

def dictionary_size(
    mapping: Mapping[str, Any],
) -> int:
    """
    Number of keys including nested keys.
    """

    count = 0

    for value in mapping.values():

        count += 1

        if isinstance(value, Mapping):

            count += dictionary_size(
                value
            )

    return count
# ============================================================
# Part 3 - Numeric Utilities
# ============================================================

# ------------------------------------------------------------
# Clamp & Range Helpers
# ------------------------------------------------------------

def clamp(
    value: Number,
    minimum: Number = MIN_BLENDSHAPE_VALUE,
    maximum: Number = MAX_BLENDSHAPE_VALUE,
) -> Number:
    """
    Clamp a numeric value to a range.
    """

    if minimum > maximum:
        raise ValueError(
            "minimum cannot be greater than maximum."
        )

    return max(minimum, min(maximum, value))


# ------------------------------------------------------------

def saturate(value: Number) -> float:
    """
    Clamp to the range [0, 1].
    """

    return float(clamp(value, 0.0, 1.0))


# ------------------------------------------------------------

def in_range(
    value: Number,
    minimum: Number,
    maximum: Number,
    *,
    inclusive: bool = True,
) -> bool:
    """
    Test whether a value lies within a range.
    """

    if inclusive:
        return minimum <= value <= maximum

    return minimum < value < maximum


# ------------------------------------------------------------
# Normalization & Remapping
# ------------------------------------------------------------

def normalize(
    value: Number,
    minimum: Number,
    maximum: Number,
) -> float:
    """
    Normalize a value into the range [0, 1].
    """

    if math.isclose(
        minimum,
        maximum,
        abs_tol=EPSILON,
    ):
        return 0.0

    return (value - minimum) / (maximum - minimum)


# ------------------------------------------------------------

def denormalize(
    normalized: Number,
    minimum: Number,
    maximum: Number,
) -> float:
    """
    Convert a normalized value back into a range.
    """

    return (
        minimum +
        float(normalized) *
        (maximum - minimum)
    )


# ------------------------------------------------------------

def remap(
    value: Number,
    source_min: Number,
    source_max: Number,
    target_min: Number,
    target_max: Number,
    *,
    clamp_output: bool = False,
) -> float:
    """
    Remap a value from one range to another.
    """

    t = normalize(
        value,
        source_min,
        source_max,
    )

    result = denormalize(
        t,
        target_min,
        target_max,
    )

    if clamp_output:
        result = clamp(
            result,
            target_min,
            target_max,
        )

    return float(result)


# ------------------------------------------------------------
# Interpolation
# ------------------------------------------------------------

def lerp(
    start: Number,
    end: Number,
    alpha: float,
) -> float:
    """
    Linear interpolation.
    """

    return (
        float(start) +
        (float(end) - float(start)) *
        alpha
    )


# ------------------------------------------------------------

def inverse_lerp(
    start: Number,
    end: Number,
    value: Number,
) -> float:
    """
    Inverse linear interpolation.
    """

    return normalize(
        value,
        start,
        end,
    )


# ------------------------------------------------------------

def smoothstep(
    edge0: Number,
    edge1: Number,
    value: Number,
) -> float:
    """
    Smooth interpolation using the
    smoothstep function.
    """

    t = saturate(
        normalize(
            value,
            edge0,
            edge1,
        )
    )

    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------

def smootherstep(
    edge0: Number,
    edge1: Number,
    value: Number,
) -> float:
    """
    Higher-order smooth interpolation.
    """

    t = saturate(
        normalize(
            value,
            edge0,
            edge1,
        )
    )

    return (
        t**3 *
        (t * (6 * t - 15) + 10)
    )


# ------------------------------------------------------------
# Averaging
# ------------------------------------------------------------

def average(
    values: Sequence[Number],
) -> float:
    """
    Arithmetic mean.
    """

    if not values:
        return 0.0

    return float(
        statistics.mean(values)
    )


# ------------------------------------------------------------

def weighted_average(
    values: Sequence[Number],
    weights: Sequence[Number],
) -> float:
    """
    Weighted average.
    """

    if len(values) != len(weights):
        raise ValueError(
            "values and weights must have equal length."
        )

    total = sum(weights)

    if math.isclose(
        total,
        0.0,
        abs_tol=EPSILON,
    ):
        return 0.0

    return float(

        sum(
            v * w
            for v, w
            in zip(values, weights)
        ) / total

    )


# ------------------------------------------------------------

def moving_average(
    values: Sequence[Number],
    window: int = 5,
) -> List[float]:
    """
    Compute a moving average.
    """

    if window <= 0:
        raise ValueError(
            "window must be positive."
        )

    results: List[float] = []

    history: Deque[float] = deque(
        maxlen=window
    )

    for value in values:

        history.append(float(value))

        results.append(

            sum(history) /
            len(history)

        )

    return results


# ------------------------------------------------------------
# Precision
# ------------------------------------------------------------

def round_value(
    value: Number,
    precision: int = DEFAULT_PRECISION,
) -> float:
    """
    Round to a fixed precision.
    """

    return round(
        float(value),
        precision,
    )


# ------------------------------------------------------------

def almost_equal(
    a: Number,
    b: Number,
    *,
    tolerance: float = EPSILON,
) -> bool:
    """
    Floating-point comparison.
    """

    return math.isclose(
        float(a),
        float(b),
        abs_tol=tolerance,
    )


# ------------------------------------------------------------

def snap(
    value: Number,
    increment: Number,
) -> float:
    """
    Snap a value to the nearest increment.
    """

    if increment == 0:
        return float(value)

    return round(
        float(value) / increment
    ) * increment


# ------------------------------------------------------------
# Blendshape Helpers
# ------------------------------------------------------------

def clamp_blendshape(
    value: Number,
) -> float:
    """
    Clamp a blendshape value into the
    valid ARKit range.
    """

    return float(
        clamp(
            value,
            MIN_BLENDSHAPE_VALUE,
            MAX_BLENDSHAPE_VALUE,
        )
    )


# ------------------------------------------------------------

def normalize_blendshape(
    value: Number,
) -> float:
    """
    Normalize and clamp a blendshape value.
    """

    return saturate(value)


# ------------------------------------------------------------

def normalize_blendshape_dict(
    values: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Normalize all blendshape values in a
    dictionary.
    """

    return {

        key: normalize_blendshape(value)

        for key, value in values.items()

    }


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def minimum(
    values: Sequence[Number],
) -> float:
    """
    Minimum value.
    """

    return float(min(values)) if values else 0.0


# ------------------------------------------------------------

def maximum(
    values: Sequence[Number],
) -> float:
    """
    Maximum value.
    """

    return float(max(values)) if values else 0.0


# ------------------------------------------------------------

def variance(
    values: Sequence[Number],
) -> float:
    """
    Population variance.
    """

    if len(values) < 2:
        return 0.0

    return float(
        statistics.pvariance(values)
    )


# ------------------------------------------------------------

def standard_deviation(
    values: Sequence[Number],
) -> float:
    """
    Population standard deviation.
    """

    if len(values) < 2:
        return 0.0

    return float(
        statistics.pstdev(values)
    )
# ============================================================
# Part 4 - Blendshape Utilities
# ============================================================

# ------------------------------------------------------------
# Blendshape Dictionary Creation
# ------------------------------------------------------------

def zero_blendshapes(
    channels: Iterable[str],
) -> BlendshapeDict:
    """
    Create a blendshape dictionary with all
    values initialized to 0.0.
    """

    return {
        channel: 0.0
        for channel in channels
    }


# ------------------------------------------------------------

def constant_blendshapes(
    channels: Iterable[str],
    value: Number,
) -> BlendshapeDict:
    """
    Create a blendshape dictionary using
    the same value for every channel.
    """

    value = clamp_blendshape(value)

    return {
        channel: value
        for channel in channels
    }


# ------------------------------------------------------------

def copy_blendshapes(
    blendshapes: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Deep-copy a blendshape dictionary.
    """

    return {
        key: float(value)
        for key, value in blendshapes.items()
    }


# ------------------------------------------------------------
# Normalization
# ------------------------------------------------------------

def normalize_blendshapes(
    blendshapes: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Clamp every blendshape value to the
    valid ARKit range.
    """

    return {

        channel: clamp_blendshape(value)

        for channel, value
        in blendshapes.items()

    }


# ------------------------------------------------------------

def normalize_missing_channels(
    blendshapes: MutableMapping[str, Number],
    channels: Iterable[str],
    *,
    default: float = 0.0,
) -> BlendshapeDict:
    """
    Ensure every required channel exists.
    """

    result = copy_blendshapes(
        blendshapes
    )

    for channel in channels:

        result.setdefault(
            channel,
            default,
        )

    return normalize_blendshapes(
        result
    )


# ------------------------------------------------------------
# Filtering
# ------------------------------------------------------------

def filter_blendshapes(
    blendshapes: Mapping[str, Number],
    channels: Iterable[str],
) -> BlendshapeDict:
    """
    Keep only the requested channels.
    """

    allowed = set(channels)

    return {

        channel: float(value)

        for channel, value
        in blendshapes.items()

        if channel in allowed

    }


# ------------------------------------------------------------

def remove_zero_blendshapes(
    blendshapes: Mapping[str, Number],
    *,
    tolerance: float = EPSILON,
) -> BlendshapeDict:
    """
    Remove channels whose value is
    effectively zero.
    """

    return {

        channel: float(value)

        for channel, value
        in blendshapes.items()

        if abs(value) > tolerance

    }


# ------------------------------------------------------------

def active_blendshapes(
    blendshapes: Mapping[str, Number],
    *,
    threshold: float = 0.001,
) -> BlendshapeDict:
    """
    Return only active blendshapes.
    """

    return {

        channel: float(value)

        for channel, value
        in blendshapes.items()

        if value >= threshold

    }


# ------------------------------------------------------------
# Scaling
# ------------------------------------------------------------

def scale_blendshapes(
    blendshapes: Mapping[str, Number],
    factor: Number,
) -> BlendshapeDict:
    """
    Multiply all blendshape values by a
    scale factor.
    """

    return {

        channel: clamp_blendshape(
            value * factor
        )

        for channel, value
        in blendshapes.items()

    }


# ------------------------------------------------------------

def offset_blendshapes(
    blendshapes: Mapping[str, Number],
    offset: Number,
) -> BlendshapeDict:
    """
    Add a constant offset to every channel.
    """

    return {

        channel: clamp_blendshape(
            value + offset
        )

        for channel, value
        in blendshapes.items()

    }


# ------------------------------------------------------------
# Mirroring
# ------------------------------------------------------------

_LEFT_PATTERN = re.compile(
    r"(^L_|_L$|Left)",
    re.IGNORECASE,
)

_RIGHT_PATTERN = re.compile(
    r"(^R_|_R$|Right)",
    re.IGNORECASE,
)


def mirrored_channel_name(
    name: str,
) -> str:
    """
    Return the mirrored channel name.
    """

    if _LEFT_PATTERN.search(name):

        return _LEFT_PATTERN.sub(
            lambda m: (
                "Right"
                if m.group().lower() == "left"
                else m.group().replace(
                    "L",
                    "R"
                ).replace(
                    "l",
                    "r"
                )
            ),
            name,
        )

    if _RIGHT_PATTERN.search(name):

        return _RIGHT_PATTERN.sub(
            lambda m: (
                "Left"
                if m.group().lower() == "right"
                else m.group().replace(
                    "R",
                    "L"
                ).replace(
                    "r",
                    "l"
                )
            ),
            name,
        )

    return name


# ------------------------------------------------------------

def mirror_blendshapes(
    blendshapes: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Mirror left/right blendshape channels.
    """

    mirrored = {}

    for channel, value in blendshapes.items():

        mirrored[
            mirrored_channel_name(channel)
        ] = float(value)

    return mirrored


# ------------------------------------------------------------
# Combination Utilities
# ------------------------------------------------------------

def merge_blendshapes(
    *blendshape_sets: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Merge multiple blendshape dictionaries.
    Later dictionaries override earlier ones.
    """

    merged: BlendshapeDict = {}

    for data in blendshape_sets:

        for key, value in data.items():

            merged[key] = clamp_blendshape(
                value
            )

    return merged


# ------------------------------------------------------------

def blendshape_difference(
    source: Mapping[str, Number],
    target: Mapping[str, Number],
) -> BlendshapeDict:
    """
    Compute channel differences.
    """

    channels = set(source) | set(target)

    return {

        channel:

        float(
            target.get(channel, 0.0)
            -
            source.get(channel, 0.0)
        )

        for channel in channels

    }


# ------------------------------------------------------------

def interpolate_blendshapes(
    start: Mapping[str, Number],
    end: Mapping[str, Number],
    alpha: float,
) -> BlendshapeDict:
    """
    Interpolate between two blendshape poses.
    """

    channels = set(start) | set(end)

    result = {}

    for channel in channels:

        result[channel] = clamp_blendshape(

            lerp(

                start.get(channel, 0.0),

                end.get(channel, 0.0),

                alpha,

            )

        )

    return result


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def validate_blendshapes(
    blendshapes: Mapping[str, Number],
) -> bool:
    """
    Validate a blendshape dictionary.
    """

    for channel, value in blendshapes.items():

        if not isinstance(
            channel,
            str,
        ):
            return False

        if not isinstance(
            value,
            (int, float),
        ):
            return False

    return True


# ------------------------------------------------------------

def blendshape_statistics(
    blendshapes: Mapping[str, Number],
) -> Dict[str, Any]:
    """
    Generate simple statistics for a
    blendshape dictionary.
    """

    values = list(blendshapes.values())

    return {

        "count":
            len(values),

        "active":
            len(
                active_blendshapes(
                    blendshapes
                )
            ),

        "minimum":
            minimum(values),

        "maximum":
            maximum(values),

        "average":
            average(values),

        "variance":
            variance(values),

        "standard_deviation":
            standard_deviation(values),

    }
# ============================================================
# Part 5 - Collection Utilities
# ============================================================

# ------------------------------------------------------------
# Chunking
# ------------------------------------------------------------

def chunked(
    iterable: Iterable[T],
    size: int,
) -> Iterator[List[T]]:
    """
    Yield successive chunks from an iterable.

    Parameters
    ----------
    iterable
        Source iterable.
    size
        Maximum chunk size.
    """

    if size <= 0:
        raise ValueError(
            "Chunk size must be greater than zero."
        )

    chunk: List[T] = []

    for item in iterable:

        chunk.append(item)

        if len(chunk) >= size:

            yield chunk

            chunk = []

    if chunk:

        yield chunk


# ------------------------------------------------------------

def batched(
    iterable: Iterable[T],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[List[T]]:
    """
    Split an iterable into batches.
    """

    return list(
        chunked(
            iterable,
            batch_size,
        )
    )


# ------------------------------------------------------------
# Grouping
# ------------------------------------------------------------

def group_by(
    iterable: Iterable[T],
    key: Callable[[T], Any],
) -> Dict[Any, List[T]]:
    """
    Group items using a key function.
    """

    groups: DefaultDict[
        Any,
        List[T],
    ] = defaultdict(list)

    for item in iterable:

        groups[key(item)].append(item)

    return dict(groups)


# ------------------------------------------------------------

def group_by_attribute(
    iterable: Iterable[Any],
    attribute: str,
) -> Dict[Any, List[Any]]:
    """
    Group objects by an attribute.
    """

    return group_by(
        iterable,
        lambda obj: getattr(
            obj,
            attribute,
            None,
        ),
    )


# ------------------------------------------------------------
# Filtering
# ------------------------------------------------------------

def unique(
    iterable: Iterable[T],
) -> List[T]:
    """
    Preserve order while removing duplicates.
    """

    seen: Set[Any] = set()

    result: List[T] = []

    for item in iterable:

        if item in seen:

            continue

        seen.add(item)

        result.append(item)

    return result


# ------------------------------------------------------------

def unique_by(
    iterable: Iterable[T],
    key: Callable[[T], Any],
) -> List[T]:
    """
    Remove duplicates using a key function.
    """

    seen: Set[Any] = set()

    result: List[T] = []

    for item in iterable:

        identifier = key(item)

        if identifier in seen:

            continue

        seen.add(identifier)

        result.append(item)

    return result


# ------------------------------------------------------------

def flatten(
    iterable: Iterable[Iterable[T]],
) -> List[T]:
    """
    Flatten one level of nesting.
    """

    return [

        item

        for collection in iterable

        for item in collection

    ]


# ------------------------------------------------------------

def compact(
    iterable: Iterable[T],
) -> List[T]:
    """
    Remove None values.
    """

    return [

        item

        for item in iterable

        if item is not None

    ]


# ------------------------------------------------------------
# Sorting
# ------------------------------------------------------------

def sorted_by(
    iterable: Iterable[T],
    key: Callable[[T], Any],
    *,
    reverse: bool = False,
) -> List[T]:
    """
    Return a sorted list.
    """

    return sorted(
        iterable,
        key=key,
        reverse=reverse,
    )


# ------------------------------------------------------------

def sort_dictionary(
    mapping: Mapping[KT, VT],
    *,
    by_value: bool = False,
    reverse: bool = False,
) -> Dict[KT, VT]:
    """
    Return a sorted dictionary.
    """

    items = mapping.items()

    if by_value:

        items = sorted(

            items,

            key=lambda item: item[1],

            reverse=reverse,

        )

    else:

        items = sorted(

            items,

            key=lambda item: item[0],

            reverse=reverse,

        )

    return dict(items)


# ------------------------------------------------------------
# Collection Statistics
# ------------------------------------------------------------

def count_if(
    iterable: Iterable[T],
    predicate: Callable[[T], bool],
) -> int:
    """
    Count items matching a predicate.
    """

    return sum(

        1

        for item in iterable

        if predicate(item)

    )


# ------------------------------------------------------------

def frequencies(
    iterable: Iterable[T],
) -> Dict[T, int]:
    """
    Count occurrences of each value.
    """

    counts: Dict[T, int] = {}

    for item in iterable:

        counts[item] = (

            counts.get(item, 0) + 1

        )

    return counts


# ------------------------------------------------------------

def partition(
    iterable: Iterable[T],
    predicate: Callable[[T], bool],
) -> Tuple[List[T], List[T]]:
    """
    Split a collection into matching and
    non-matching items.
    """

    passed: List[T] = []

    failed: List[T] = []

    for item in iterable:

        if predicate(item):

            passed.append(item)

        else:

            failed.append(item)

    return passed, failed


# ------------------------------------------------------------

def pairwise(
    iterable: Iterable[T],
) -> Iterator[Tuple[T, T]]:
    """
    Yield consecutive pairs.

    Example
    -------
    [A, B, C] ->
        (A, B), (B, C)
    """

    iterator = iter(iterable)

    try:

        previous = next(iterator)

    except StopIteration:

        return

    for current in iterator:

        yield previous, current

        previous = current


# ------------------------------------------------------------
# Dictionary Helpers
# ------------------------------------------------------------

def invert_dictionary(
    mapping: Mapping[KT, VT],
) -> Dict[VT, KT]:
    """
    Swap dictionary keys and values.

    Values must be hashable.
    """

    return {

        value: key

        for key, value

        in mapping.items()

    }


# ------------------------------------------------------------

def dictionary_keys_union(
    *mappings: Mapping[Any, Any],
) -> Set[Any]:
    """
    Return the union of dictionary keys.
    """

    result: Set[Any] = set()

    for mapping in mappings:

        result.update(mapping.keys())

    return result


# ------------------------------------------------------------

def dictionary_keys_intersection(
    *mappings: Mapping[Any, Any],
) -> Set[Any]:
    """
    Return the intersection of dictionary keys.
    """

    if not mappings:

        return set()

    result = set(mappings[0].keys())

    for mapping in mappings[1:]:

        result.intersection_update(
            mapping.keys()
        )

    return result


# ------------------------------------------------------------
# Miscellaneous
# ------------------------------------------------------------

def first(
    iterable: Iterable[T],
    default: Optional[T] = None,
) -> Optional[T]:
    """
    Return the first item.
    """

    return next(
        iter(iterable),
        default,
    )


# ------------------------------------------------------------

def last(
    iterable: Iterable[T],
    default: Optional[T] = None,
) -> Optional[T]:
    """
    Return the last item.
    """

    items = list(iterable)

    if not items:

        return default

    return items[-1]


# ------------------------------------------------------------

def take(
    iterable: Iterable[T],
    count: int,
) -> List[T]:
    """
    Take the first N items.
    """

    if count <= 0:

        return []

    result: List[T] = []

    for item in iterable:

        result.append(item)

        if len(result) >= count:

            break

    return result


# ------------------------------------------------------------

def drop(
    iterable: Iterable[T],
    count: int,
) -> List[T]:
    """
    Skip the first N items.
    """

    if count <= 0:

        return list(iterable)

    iterator = iter(iterable)

    for _ in range(count):

        try:

            next(iterator)

        except StopIteration:

            return []

    return list(iterator)
# ============================================================
# Part 6 - String & Naming Utilities
# ============================================================

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)

_NON_ALNUM_PATTERN = re.compile(
    r"[^A-Za-z0-9_]+"
)

_CAMEL_BOUNDARY_PATTERN = re.compile(
    r"(?<!^)(?=[A-Z])"
)

_MULTIPLE_UNDERSCORE_PATTERN = re.compile(
    r"_+"
)

_LEFT_NAME_PATTERN = re.compile(
    r"(?:^L_|_L$|Left)",
    re.IGNORECASE,
)

_RIGHT_NAME_PATTERN = re.compile(
    r"(?:^R_|_R$|Right)",
    re.IGNORECASE,
)

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def is_valid_identifier(
    name: str,
) -> bool:
    """
    Determine whether a string is a valid
    Python/Maya-style identifier.
    """

    if not isinstance(name, str):

        return False

    return bool(
        _IDENTIFIER_PATTERN.match(name)
    )


# ------------------------------------------------------------

def validate_identifier(
    name: str,
) -> str:
    """
    Validate an identifier.

    Raises
    ------
    ValidationError
    """

    if not is_valid_identifier(name):

        raise ValidationError(
            f"Invalid identifier: {name!r}"
        )

    return name


# ------------------------------------------------------------
# Sanitizing
# ------------------------------------------------------------

def safe_identifier(
    text: str,
    *,
    replacement: str = "_",
) -> str:
    """
    Convert arbitrary text into a valid
    identifier.
    """

    text = _NON_ALNUM_PATTERN.sub(
        replacement,
        text.strip(),
    )

    text = _MULTIPLE_UNDERSCORE_PATTERN.sub(
        "_",
        text,
    )

    text = text.strip("_")

    if not text:

        text = "unnamed"

    if text[0].isdigit():

        text = "_" + text

    return text


# ------------------------------------------------------------

def slugify(
    text: str,
) -> str:
    """
    Create a filesystem-friendly slug.
    """

    slug = safe_identifier(
        text.lower()
    )

    return slug.replace(
        "_",
        "-",
    )


# ------------------------------------------------------------
# Case Conversion
# ------------------------------------------------------------

def snake_case(
    text: str,
) -> str:
    """
    Convert CamelCase to snake_case.
    """

    text = _CAMEL_BOUNDARY_PATTERN.sub(
        "_",
        text,
    )

    return safe_identifier(
        text.lower()
    )


# ------------------------------------------------------------

def camel_case(
    text: str,
) -> str:
    """
    Convert snake_case to camelCase.
    """

    parts = snake_case(
        text
    ).split("_")

    if not parts:

        return ""

    return (
        parts[0]
        +
        "".join(
            word.capitalize()
            for word in parts[1:]
        )
    )


# ------------------------------------------------------------

def pascal_case(
    text: str,
) -> str:
    """
    Convert text to PascalCase.
    """

    return "".join(

        word.capitalize()

        for word in snake_case(
            text
        ).split("_")

    )


# ------------------------------------------------------------
# Prefix / Suffix
# ------------------------------------------------------------

def add_prefix(
    name: str,
    prefix: str,
) -> str:
    """
    Add a prefix if missing.
    """

    if name.startswith(prefix):

        return name

    return prefix + name


# ------------------------------------------------------------

def add_suffix(
    name: str,
    suffix: str,
) -> str:
    """
    Add a suffix if missing.
    """

    if name.endswith(suffix):

        return name

    return name + suffix


# ------------------------------------------------------------

def remove_prefix(
    name: str,
    prefix: str,
) -> str:
    """
    Remove a prefix if present.
    """

    if name.startswith(prefix):

        return name[len(prefix):]

    return name


# ------------------------------------------------------------

def remove_suffix(
    name: str,
    suffix: str,
) -> str:
    """
    Remove a suffix if present.
    """

    if suffix and name.endswith(suffix):

        return name[:-len(suffix)]

    return name


# ------------------------------------------------------------
# Left / Right Naming
# ------------------------------------------------------------

def is_left_name(
    name: str,
) -> bool:
    """
    Determine whether a name belongs to
    the left side.
    """

    return bool(
        _LEFT_NAME_PATTERN.search(name)
    )


# ------------------------------------------------------------

def is_right_name(
    name: str,
) -> bool:
    """
    Determine whether a name belongs to
    the right side.
    """

    return bool(
        _RIGHT_NAME_PATTERN.search(name)
    )


# ------------------------------------------------------------

def opposite_side_name(
    name: str,
) -> str:
    """
    Convert a left-side name to right,
    or vice versa.
    """

    if is_left_name(name):

        return mirrored_channel_name(
            name
        )

    if is_right_name(name):

        return mirrored_channel_name(
            name
        )

    return name


# ------------------------------------------------------------
# Formatting
# ------------------------------------------------------------

def title_case(
    text: str,
) -> str:
    """
    Convert text to title case.
    """

    return snake_case(
        text
    ).replace(
        "_",
        " ",
    ).title()


# ------------------------------------------------------------

def sentence_case(
    text: str,
) -> str:
    """
    Convert text to sentence case.
    """

    text = text.strip()

    if not text:

        return ""

    return (
        text[0].upper()
        +
        text[1:].lower()
    )


# ------------------------------------------------------------

def truncate(
    text: str,
    length: int,
    *,
    suffix: str = "...",
) -> str:
    """
    Truncate a string.
    """

    if len(text) <= length:

        return text

    usable = max(
        0,
        length - len(suffix),
    )

    return text[:usable] + suffix


# ------------------------------------------------------------
# Number Formatting
# ------------------------------------------------------------

def format_percentage(
    value: Number,
    precision: int = 2,
) -> str:
    """
    Format a percentage.
    """

    return (
        f"{value * 100:.{precision}f}%"
    )


# ------------------------------------------------------------

def format_float(
    value: Number,
    precision: int = DEFAULT_PRECISION,
) -> str:
    """
    Format a floating-point number.
    """

    return (
        f"{float(value):.{precision}f}"
    )


# ------------------------------------------------------------
# Miscellaneous
# ------------------------------------------------------------

def random_identifier(
    prefix: str = "id",
) -> str:
    """
    Generate a random identifier.
    """

    return (

        safe_identifier(prefix)

        + "_"

        + uuid.uuid4().hex[:8]

    )


# ------------------------------------------------------------

def unique_name(
    base: str,
    existing: Iterable[str],
) -> str:
    """
    Generate a unique name.
    """

    existing = set(existing)

    if base not in existing:

        return base

    index = 1

    while True:

        candidate = f"{base}_{index}"

        if candidate not in existing:

            return candidate

        index += 1


# ------------------------------------------------------------

def common_prefix(
    strings: Sequence[str],
) -> str:
    """
    Return the longest common prefix.
    """

    if not strings:

        return ""

    return os.path.commonprefix(
        strings
    )


# ------------------------------------------------------------

def common_suffix(
    strings: Sequence[str],
) -> str:
    """
    Return the longest common suffix.
    """

    if not strings:

        return ""

    reversed_strings = [

        s[::-1]

        for s in strings

    ]

    suffix = os.path.commonprefix(
        reversed_strings
    )

    return suffix[::-1]
# ============================================================
# Part 7 - Time & Performance Utilities
# ============================================================

# ------------------------------------------------------------
# High Resolution Timing
# ------------------------------------------------------------

def current_time() -> datetime:
    """
    Return the current local datetime.
    """

    return datetime.now()


# ------------------------------------------------------------

def timestamp() -> float:
    """
    Return a high-resolution timestamp.
    """

    return time.perf_counter()


# ------------------------------------------------------------

def unix_timestamp() -> float:
    """
    Return the current Unix timestamp.
    """

    return time.time()


# ------------------------------------------------------------
# Stopwatch
# ------------------------------------------------------------

class Stopwatch:
    """
    High-resolution stopwatch.

    Example
    -------
    >>> sw = Stopwatch()
    >>> sw.start()
    >>> ...
    >>> sw.stop()
    >>> print(sw.elapsed)
    """

    def __init__(self):

        self.reset()

    # -----------------------------------------------------

    def start(self) -> None:

        if self._running:
            return

        self._start = time.perf_counter()
        self._running = True

    # -----------------------------------------------------

    def stop(self) -> float:

        if not self._running:
            return self.elapsed

        self._elapsed += (
            time.perf_counter()
            - self._start
        )

        self._running = False

        return self.elapsed

    # -----------------------------------------------------

    def restart(self) -> None:

        self.reset()
        self.start()

    # -----------------------------------------------------

    def reset(self) -> None:

        self._start = 0.0
        self._elapsed = 0.0
        self._running = False

    # -----------------------------------------------------

    @property
    def elapsed(self) -> float:

        if self._running:

            return (

                self._elapsed

                +

                (
                    time.perf_counter()
                    - self._start
                )

            )

        return self._elapsed

    # -----------------------------------------------------

    @property
    def running(self) -> bool:

        return self._running


# ------------------------------------------------------------
# Timer Context Manager
# ------------------------------------------------------------

class Timer:
    """
    Timing context manager.

    Example
    -------
    >>> with Timer("Conversion"):
    >>>     convert()
    """

    def __init__(
        self,
        name: str = DEFAULT_TIMER_NAME,
    ):

        self.name = name

        self.result: Optional[
            TimerResult
        ] = None

    # -----------------------------------------------------

    def __enter__(self):

        self._start = time.perf_counter()

        return self

    # -----------------------------------------------------

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        end = time.perf_counter()

        elapsed = end - self._start

        self.result = TimerResult(

            name=self.name,

            start_time=self._start,

            end_time=end,

            elapsed=elapsed,

        )

        UTILITY_STATISTICS.calls += 1

        UTILITY_STATISTICS.elapsed_time += elapsed

        UTILITY_STATISTICS.last_call = (
            datetime.now()
        )

        return False


# ------------------------------------------------------------
# Decorators
# ------------------------------------------------------------

def timed(
    name: Optional[str] = None,
):
    """
    Decorator that measures execution time.
    """

    def decorator(function):

        timer_name = (
            name
            or function.__name__
        )

        @functools.wraps(function)
        def wrapper(
            *args,
            **kwargs,
        ):

            start = time.perf_counter()

            try:

                return function(
                    *args,
                    **kwargs,
                )

            finally:

                elapsed = (
                    time.perf_counter()
                    - start
                )

                UTILITY_STATISTICS.calls += 1

                UTILITY_STATISTICS.elapsed_time += (
                    elapsed
                )

                UTILITY_STATISTICS.last_call = (
                    datetime.now()
                )

        return wrapper

    return decorator


# ------------------------------------------------------------

def profile(
    function: Callable,
):
    """
    Simple profiling decorator.
    """

    @functools.wraps(function)
    def wrapper(
        *args,
        **kwargs,
    ):

        sw = Stopwatch()

        sw.start()

        try:

            return function(
                *args,
                **kwargs,
            )

        finally:

            sw.stop()

            print(
                f"{function.__name__}: "
                f"{sw.elapsed:.6f}s"
            )

    return wrapper


# ------------------------------------------------------------

def retry(
    attempts: int = 3,
    delay: float = 0.0,
    exceptions=Exception,
):
    """
    Retry decorator.

    Parameters
    ----------
    attempts
        Maximum retry attempts.
    delay
        Delay between attempts.
    """

    def decorator(function):

        @functools.wraps(function)
        def wrapper(
            *args,
            **kwargs,
        ):

            last_error = None

            for _ in range(attempts):

                try:

                    return function(
                        *args,
                        **kwargs,
                    )

                except exceptions as exc:

                    last_error = exc

                    if delay > 0.0:

                        time.sleep(delay)

            raise last_error

        return wrapper

    return decorator


# ------------------------------------------------------------
# Performance Helpers
# ------------------------------------------------------------

def benchmark(
    function: Callable,
    *args,
    repeats: int = 10,
    **kwargs,
) -> Dict[str, float]:
    """
    Benchmark a callable.
    """

    samples = []

    for _ in range(repeats):

        start = time.perf_counter()

        function(
            *args,
            **kwargs,
        )

        samples.append(

            time.perf_counter()
            - start

        )

    return {

        "minimum":
            min(samples),

        "maximum":
            max(samples),

        "average":
            statistics.mean(samples),

        "total":
            sum(samples),

        "runs":
            repeats,

    }


# ------------------------------------------------------------

def measure(
    function: Callable,
    *args,
    **kwargs,
) -> float:
    """
    Measure a single execution.
    """

    start = time.perf_counter()

    function(
        *args,
        **kwargs,
    )

    return (
        time.perf_counter()
        - start
    )


# ------------------------------------------------------------

def fps(
    frame_time: float,
) -> float:
    """
    Frames per second from frame time.
    """

    if frame_time <= 0.0:

        return 0.0

    return 1.0 / frame_time


# ------------------------------------------------------------

def milliseconds(
    seconds: float,
) -> float:
    """
    Convert seconds to milliseconds.
    """

    return seconds * 1000.0


# ------------------------------------------------------------

def seconds(
    milliseconds_value: float,
) -> float:
    """
    Convert milliseconds to seconds.
    """

    return milliseconds_value / 1000.0


# ------------------------------------------------------------
# Runtime Statistics
# ------------------------------------------------------------

def performance_statistics() -> Dict[str, Any]:
    """
    Return utility performance statistics.
    """

    average_time = 0.0

    if UTILITY_STATISTICS.calls:

        average_time = (

            UTILITY_STATISTICS.elapsed_time

            /

            UTILITY_STATISTICS.calls

        )

    return {

        "calls":
            UTILITY_STATISTICS.calls,

        "failures":
            UTILITY_STATISTICS.failures,

        "total_time":
            UTILITY_STATISTICS.elapsed_time,

        "average_time":
            average_time,

        "last_call":
            UTILITY_STATISTICS.last_call,

    }


# ------------------------------------------------------------

def reset_performance_statistics() -> None:
    """
    Reset runtime timing statistics.
    """

    reset_statistics()
# ============================================================
# Part 8 - Serialization Helpers
# ============================================================

# ------------------------------------------------------------
# JSON-safe Conversion
# ------------------------------------------------------------

def json_safe(
    value: Any,
) -> JsonValue:
    """
    Recursively convert an object into a JSON-safe
    representation.
    """

    if value is None:
        return None

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if is_dataclass(value):
        return json_safe(asdict(value))

    if isinstance(value, Mapping):

        return {

            str(key): json_safe(item)

            for key, item in value.items()

        }

    if isinstance(value, (list, tuple, set, frozenset)):

        return [

            json_safe(item)

            for item in value

        ]

    if HAS_NUMPY:

        if isinstance(value, np.ndarray):

            return value.tolist()

        if isinstance(value, np.generic):

            return value.item()

    return str(value)


# ------------------------------------------------------------

def deep_serialize(
    value: Any,
) -> Any:
    """
    Alias for json_safe() used throughout the
    ARKit mapper.
    """

    return json_safe(value)


# ------------------------------------------------------------
# Dataclass Helpers
# ------------------------------------------------------------

def dataclass_to_dict(
    instance: Any,
) -> Dict[str, Any]:
    """
    Convert a dataclass to a dictionary.
    """

    if not is_dataclass(instance):

        raise SerializationError(
            "Object is not a dataclass."
        )

    return asdict(instance)


# ------------------------------------------------------------

def object_to_dict(
    obj: Any,
) -> Dict[str, Any]:
    """
    Convert an arbitrary object to a dictionary.
    """

    if is_dataclass(obj):

        return asdict(obj)

    if hasattr(obj, "__dict__"):

        return {

            key: value

            for key, value

            in vars(obj).items()

            if not key.startswith("_")

        }

    raise SerializationError(
        f"Cannot serialize object of type "
        f"{type(obj).__name__}."
    )


# ------------------------------------------------------------
# NumPy Helpers
# ------------------------------------------------------------

def numpy_to_list(
    value: Any,
) -> Any:
    """
    Convert NumPy arrays/scalars into native
    Python types.
    """

    if not HAS_NUMPY:

        return value

    if isinstance(value, np.ndarray):

        return value.tolist()

    if isinstance(value, np.generic):

        return value.item()

    return value


# ------------------------------------------------------------

def list_to_numpy(
    value: Any,
):
    """
    Convert nested sequences into a NumPy array.

    If NumPy is unavailable, the original value
    is returned.
    """

    if not HAS_NUMPY:

        return value

    return np.asarray(value)


# ------------------------------------------------------------
# Hash Helpers
# ------------------------------------------------------------

def md5_hash(
    value: Any,
) -> str:
    """
    Compute an MD5 hash of serialized data.
    """

    encoded = json.dumps(

        json_safe(value),

        sort_keys=True,

        separators=(",", ":"),

    ).encode("utf-8")

    return hashlib.md5(
        encoded
    ).hexdigest()


# ------------------------------------------------------------

def sha1_hash(
    value: Any,
) -> str:
    """
    Compute a SHA-1 hash.
    """

    encoded = json.dumps(

        json_safe(value),

        sort_keys=True,

        separators=(",", ":"),

    ).encode("utf-8")

    return hashlib.sha1(
        encoded
    ).hexdigest()


# ------------------------------------------------------------

def sha256_hash(
    value: Any,
) -> str:
    """
    Compute a SHA-256 hash.
    """

    encoded = json.dumps(

        json_safe(value),

        sort_keys=True,

        separators=(",", ":"),

    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


# ------------------------------------------------------------

def content_hash(
    value: Any,
    algorithm: str = "sha256",
) -> str:
    """
    Compute a content hash using the requested
    algorithm.
    """

    algorithm = algorithm.lower()

    if algorithm == "md5":

        return md5_hash(value)

    if algorithm == "sha1":

        return sha1_hash(value)

    if algorithm == "sha256":

        return sha256_hash(value)

    raise SerializationError(
        f"Unsupported hash algorithm: "
        f"{algorithm}"
    )


# ------------------------------------------------------------
# Serialization Validation
# ------------------------------------------------------------

def is_json_serializable(
    value: Any,
) -> bool:
    """
    Determine whether an object can be
    serialized to JSON.
    """

    try:

        json.dumps(
            json_safe(value)
        )

        return True

    except Exception:

        return False


# ------------------------------------------------------------

def serialization_size(
    value: Any,
) -> int:
    """
    Return the serialized size in bytes.
    """

    encoded = json.dumps(

        json_safe(value),

        separators=(",", ":"),

        sort_keys=True,

    ).encode("utf-8")

    return len(encoded)


# ------------------------------------------------------------

def pretty_json(
    value: Any,
    *,
    indent: int = 4,
) -> str:
    """
    Pretty-print JSON.
    """

    return json.dumps(

        json_safe(value),

        indent=indent,

        sort_keys=True,

        ensure_ascii=False,

    )


# ------------------------------------------------------------

def compact_json(
    value: Any,
) -> str:
    """
    Compact JSON representation.
    """

    return json.dumps(

        json_safe(value),

        separators=(",", ":"),

        sort_keys=True,

    )


# ------------------------------------------------------------
# Binary Helpers
# ------------------------------------------------------------

def serialize_bytes(
    value: Any,
) -> bytes:
    """
    Serialize an object to UTF-8 JSON bytes.
    """

    return compact_json(
        value
    ).encode("utf-8")


# ------------------------------------------------------------

def deserialize_bytes(
    data: bytes,
) -> Any:
    """
    Deserialize UTF-8 JSON bytes.
    """

    return json.loads(
        data.decode("utf-8")
    )


# ------------------------------------------------------------
# Reports
# ------------------------------------------------------------

def serialization_report(
    value: Any,
) -> Dict[str, Any]:
    """
    Generate a serialization report.
    """

    return {

        "serializable":
            is_json_serializable(value),

        "size_bytes":
            serialization_size(value),

        "md5":
            md5_hash(value),

        "sha1":
            sha1_hash(value),

        "sha256":
            sha256_hash(value),

    }
# ============================================================
# Part 9 - Maya Utilities
# ============================================================

# ------------------------------------------------------------
# Maya Environment
# ------------------------------------------------------------

def maya_available() -> bool:
    """
    Return True if running inside Autodesk Maya.
    """

    return HAS_MAYA


# ------------------------------------------------------------

def require_maya() -> None:
    """
    Raise an exception if Maya is unavailable.
    """

    if not HAS_MAYA:
        raise MayaUnavailableError(
            "This operation requires Autodesk Maya."
        )


# ------------------------------------------------------------

def maya_version() -> Optional[int]:
    """
    Return the Maya version as an integer.

    Returns
    -------
    Optional[int]
        Maya version (e.g. 2026), or None if
        Maya is unavailable.
    """

    if not HAS_MAYA:
        return None

    try:
        return int(cmds.about(version=True))
    except Exception:
        return None


# ------------------------------------------------------------

def api_version() -> Optional[int]:
    """
    Return the Maya API version.
    """

    if not HAS_MAYA:
        return None

    try:
        return int(cmds.about(apiVersion=True))
    except Exception:
        return None


# ------------------------------------------------------------
# Node Utilities
# ------------------------------------------------------------

def node_exists(
    node: str,
) -> bool:
    """
    Test whether a Maya node exists.
    """

    if not HAS_MAYA:
        return False

    return cmds.objExists(node)


# ------------------------------------------------------------

def ensure_node_exists(
    node: str,
) -> str:
    """
    Validate that a node exists.
    """

    require_maya()

    if not cmds.objExists(node):
        raise ValidationError(
            f"Node does not exist: {node}"
        )

    return node


# ------------------------------------------------------------

def node_type(
    node: str,
) -> Optional[str]:
    """
    Return the Maya node type.
    """

    if not node_exists(node):
        return None

    return cmds.nodeType(node)


# ------------------------------------------------------------

def list_nodes(
    node_type_name: Optional[str] = None,
) -> List[str]:
    """
    List Maya nodes.

    Parameters
    ----------
    node_type_name
        Optional node type filter.
    """

    if not HAS_MAYA:
        return []

    if node_type_name:

        return cmds.ls(
            type=node_type_name
        ) or []

    return cmds.ls() or []


# ------------------------------------------------------------
# Selection Utilities
# ------------------------------------------------------------

def current_selection() -> List[str]:
    """
    Return the current Maya selection.
    """

    if not HAS_MAYA:
        return []

    return cmds.ls(
        selection=True,
        long=True,
    ) or []


# ------------------------------------------------------------

def select_nodes(
    nodes: Iterable[str],
    *,
    replace: bool = True,
) -> None:
    """
    Select nodes.
    """

    require_maya()

    cmds.select(
        list(nodes),
        replace=replace,
    )


# ------------------------------------------------------------

class PreserveSelection:
    """
    Context manager that restores the
    current Maya selection.

    Example
    -------
    with PreserveSelection():
        cmds.select(...)
    """

    def __enter__(self):

        self._selection = current_selection()

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        if HAS_MAYA:

            cmds.select(
                self._selection,
                replace=True,
            )

        return False


# ------------------------------------------------------------
# Undo Utilities
# ------------------------------------------------------------

class UndoChunk:
    """
    Context manager for Maya undo chunks.

    Example
    -------
    with UndoChunk():
        ...
    """

    def __enter__(self):

        require_maya()

        cmds.undoInfo(
            openChunk=True
        )

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        cmds.undoInfo(
            closeChunk=True
        )

        return False


# ------------------------------------------------------------
# Attribute Utilities
# ------------------------------------------------------------

def attribute_exists(
    attribute: str,
) -> bool:
    """
    Determine whether an attribute exists.
    """

    if not HAS_MAYA:
        return False

    try:

        return cmds.objExists(attribute)

    except Exception:

        return False


# ------------------------------------------------------------

def safe_get_attr(
    attribute: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve an attribute value.
    """

    if not attribute_exists(attribute):

        return default

    try:

        return cmds.getAttr(attribute)

    except Exception:

        return default


# ------------------------------------------------------------

def safe_set_attr(
    attribute: str,
    value: Any,
) -> bool:
    """
    Safely set an attribute value.
    """

    if not attribute_exists(attribute):

        return False

    try:

        cmds.setAttr(
            attribute,
            value,
        )

        return True

    except Exception:

        return False


# ------------------------------------------------------------
# Namespace Utilities
# ------------------------------------------------------------

def namespace(
    node: str,
) -> str:
    """
    Return the namespace of a node.
    """

    if ":" not in node:

        return ""

    return node.rsplit(
        ":",
        1,
    )[0]


# ------------------------------------------------------------

def short_name(
    node: str,
) -> str:
    """
    Return the short node name.
    """

    return node.split("|")[-1]


# ------------------------------------------------------------

def long_name(
    node: str,
) -> str:
    """
    Return the long DAG path if available.
    """

    if not HAS_MAYA:

        return node

    result = cmds.ls(
        node,
        long=True,
    )

    if result:

        return result[0]

    return node


# ------------------------------------------------------------
# Miscellaneous
# ------------------------------------------------------------

def refresh_viewport() -> None:
    """
    Refresh the active Maya viewport.
    """

    if HAS_MAYA:

        cmds.refresh()


# ------------------------------------------------------------

def evaluation_mode() -> Optional[str]:
    """
    Return the current evaluation mode.
    """

    if not HAS_MAYA:
        return None

    try:

        modes = cmds.evaluationManager(
            query=True,
            mode=True,
        )

        return modes[0] if modes else None

    except Exception:

        return None


# ------------------------------------------------------------

def maya_information() -> Dict[str, Any]:
    """
    Return runtime information about Maya.
    """

    return {

        "available":
            HAS_MAYA,

        "version":
            maya_version(),

        "api_version":
            api_version(),

        "evaluation_mode":
            evaluation_mode(),

        "selection_count":
            len(
                current_selection()
            ),

    }


# ------------------------------------------------------------

def safe_execute(
    function: Callable,
    *args,
    **kwargs,
) -> Any:
    """
    Execute a callable safely.

    Returns
    -------
    Any
        Function result, or None if an
        exception occurs.
    """

    try:

        return function(
            *args,
            **kwargs,
        )

    except Exception:

        return None
# ============================================================
# Part 10 - Reports & Diagnostics
# ============================================================

# ------------------------------------------------------------
# Report Builder
# ------------------------------------------------------------

class DiagnosticReport:
    """
    Generic diagnostics report used throughout the
    ARKit mapper subsystem.
    """

    def __init__(
        self,
        title: str = "Diagnostic Report",
    ):

        self.title = title

        self.created = datetime.now()

        self.sections: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self.messages: List[
            Tuple[str, str]
        ] = []

    # -----------------------------------------------------

    def add_section(
        self,
        name: str,
        data: Mapping[str, Any],
    ) -> None:

        self.sections[name] = dict(data)

    # -----------------------------------------------------

    def add_message(
        self,
        level: str,
        message: str,
    ) -> None:

        self.messages.append(

            (
                level.upper(),
                message,
            )

        )

    # -----------------------------------------------------

    def warning(
        self,
        message: str,
    ) -> None:

        self.add_message(
            "WARNING",
            message,
        )

    # -----------------------------------------------------

    def error(
        self,
        message: str,
    ) -> None:

        self.add_message(
            "ERROR",
            message,
        )

    # -----------------------------------------------------

    def info(
        self,
        message: str,
    ) -> None:

        self.add_message(
            "INFO",
            message,
        )

    # -----------------------------------------------------

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "title":
                self.title,

            "created":
                self.created.isoformat(),

            "sections":
                json_safe(
                    self.sections
                ),

            "messages":
                self.messages,

        }

    # -----------------------------------------------------

    def to_json(
        self,
        indent: int = 4,
    ) -> str:

        return json.dumps(

            self.to_dict(),

            indent=indent,

            ensure_ascii=False,

            sort_keys=True,

        )


# ------------------------------------------------------------
# Environment Diagnostics
# ------------------------------------------------------------

def environment_report() -> Dict[str, Any]:
    """
    Collect runtime environment information.
    """

    report = {

        "module":
            MODULE_NAME,

        "version":
            MODULE_VERSION,

        "python_version":
            platform.python_version(),

        "python_implementation":
            platform.python_implementation(),

        "platform":
            platform.platform(),

        "system":
            platform.system(),

        "processor":
            platform.processor(),

        "maya_available":
            HAS_MAYA,

        "numpy_available":
            HAS_NUMPY,

    }

    if HAS_MAYA:

        report.update(

            maya_information()

        )

    return report


# ------------------------------------------------------------
# Runtime Diagnostics
# ------------------------------------------------------------

def runtime_report() -> Dict[str, Any]:
    """
    Return runtime statistics.
    """

    return {

        "performance":
            performance_statistics(),

        "utility_statistics":
            asdict(
                UTILITY_STATISTICS
            ),

        "timestamp":
            datetime.now().isoformat(),

    }


# ------------------------------------------------------------
# Registry Diagnostics
# ------------------------------------------------------------

def registry_report() -> Dict[str, Any]:
    """
    Report the registered utilities.
    """

    return {

        "registered":
            len(
                UTILITY_REGISTRY
            ),

        "utilities":
            UTILITY_REGISTRY.names(),

    }


# ------------------------------------------------------------
# Memory Information
# ------------------------------------------------------------

def memory_report() -> Dict[str, Any]:
    """
    Collect basic memory information.

    Uses psutil if installed.
    """

    report = {

        "psutil":
            False,

    }

    try:

        import psutil

        process = psutil.Process()

        memory = process.memory_info()

        report.update(

            {

                "psutil": True,

                "rss":

                    memory.rss,

                "vms":

                    memory.vms,

                "percent":

                    process.memory_percent(),

            }

        )

    except Exception:

        pass

    return report


# ------------------------------------------------------------
# Blendshape Diagnostics
# ------------------------------------------------------------

def blendshape_report(
    blendshapes: Mapping[str, Number],
) -> Dict[str, Any]:
    """
    Generate diagnostics for a blendshape
    dictionary.
    """

    report = blendshape_statistics(
        blendshapes
    )

    report.update(

        {

            "hash":

                sha256_hash(
                    blendshapes
                ),

            "serialized_size":

                serialization_size(
                    blendshapes
                ),

        }

    )

    return report


# ------------------------------------------------------------
# Mapping Diagnostics
# ------------------------------------------------------------

def mapping_report(
    mapping: MappingDict,
) -> Dict[str, Any]:
    """
    Generate diagnostics for an ARKit mapping.
    """

    total_weights = 0

    driven_channels = set()

    for values in mapping.values():

        total_weights += len(values)

        driven_channels.update(
            values.keys()
        )

    return {

        "arkit_channels":
            len(mapping),

        "driven_channels":
            len(
                driven_channels
            ),

        "weights":
            total_weights,

        "serialized_size":

            serialization_size(
                mapping
            ),

        "hash":

            sha256_hash(
                mapping
            ),

    }


# ------------------------------------------------------------
# Complete Diagnostic Report
# ------------------------------------------------------------

def diagnostics_report() -> DiagnosticReport:
    """
    Build a complete diagnostics report.
    """

    report = DiagnosticReport(
        "ARKit Mapper Diagnostics"
    )

    report.add_section(

        "Environment",

        environment_report(),

    )

    report.add_section(

        "Runtime",

        runtime_report(),

    )

    report.add_section(

        "Registry",

        registry_report(),

    )

    report.add_section(

        "Memory",

        memory_report(),

    )

    report.info(
        "Diagnostics completed successfully."
    )

    return report


# ------------------------------------------------------------
# Health Check
# ------------------------------------------------------------

def health_check() -> Dict[str, Any]:
    """
    Perform a lightweight health check of the
    utility module.
    """

    return {

        "healthy": True,

        "module":

            MODULE_NAME,

        "version":

            MODULE_VERSION,

        "maya":

            HAS_MAYA,

        "numpy":

            HAS_NUMPY,

        "registered_utilities":

            len(
                UTILITY_REGISTRY
            ),

        "timestamp":

            datetime.now().isoformat(),

    }


# ------------------------------------------------------------
# Console Output
# ------------------------------------------------------------

def print_diagnostics() -> None:
    """
    Print a formatted diagnostics report.
    """

    print("=" * 70)
    print("ARKit Mapper Diagnostics")
    print("=" * 70)

    report = diagnostics_report()

    for section, values in report.sections.items():

        print(f"\n[{section}]")

        for key, value in values.items():

            print(f"{key}: {value}")

    if report.messages:

        print("\nMessages")

        print("-" * 70)

        for level, message in report.messages:

            print(f"{level}: {message}")

    print("=" * 70)
# ============================================================
# Part 11 - Public API
# ============================================================
"""
Public API exports for the ARKit Mapper utility module.

This section defines the stable public interface of
blendshapes.arkit_mapper.utils. Internal implementation
details remain private unless explicitly exported here.
"""

# ------------------------------------------------------------
# Module Metadata
# ------------------------------------------------------------

__title__ = "ARKit Mapper Utilities"
__description__ = (
    "Shared utility functions used throughout the "
    "maya_faceit ARKit mapper subsystem."
)

__author__ = "OpenAI"
__license__ = "MIT"

# ------------------------------------------------------------
# Version Information
# ------------------------------------------------------------

try:
    __version__ = MODULE_VERSION
except NameError:
    __version__ = "1.0.0"

# ------------------------------------------------------------
# Public Symbols
# ------------------------------------------------------------

__all__ = [

    # --------------------------------------------------------
    # Foundation
    # --------------------------------------------------------
    "MODULE_NAME",
    "MODULE_VERSION",
    "DEFAULT_PRECISION",
    "DEFAULT_BATCH_SIZE",
    "EPSILON",
    "HAS_MAYA",
    "HAS_NUMPY",

    # --------------------------------------------------------
    # Dictionary Utilities
    # --------------------------------------------------------
    "deep_merge",
    "deep_update",
    "deep_copy",
    "deep_compare",
    "deep_diff",
    "flatten_dictionary",
    "unflatten_dictionary",
    "filter_dictionary",
    "invert_dictionary",
    "dictionary_keys_union",
    "dictionary_keys_intersection",

    # --------------------------------------------------------
    # Numeric Utilities
    # --------------------------------------------------------
    "clamp",
    "saturate",
    "normalize",
    "denormalize",
    "remap",
    "lerp",
    "inverse_lerp",
    "smoothstep",
    "smootherstep",
    "average",
    "weighted_average",
    "moving_average",
    "minimum",
    "maximum",
    "variance",
    "standard_deviation",
    "round_value",
    "almost_equal",
    "snap",

    # --------------------------------------------------------
    # Blendshape Utilities
    # --------------------------------------------------------
    "zero_blendshapes",
    "constant_blendshapes",
    "copy_blendshapes",
    "normalize_blendshapes",
    "normalize_missing_channels",
    "filter_blendshapes",
    "remove_zero_blendshapes",
    "active_blendshapes",
    "scale_blendshapes",
    "offset_blendshapes",
    "mirror_blendshapes",
    "mirrored_channel_name",
    "merge_blendshapes",
    "blendshape_difference",
    "interpolate_blendshapes",
    "blendshape_statistics",
    "validate_blendshapes",

    # --------------------------------------------------------
    # Collection Utilities
    # --------------------------------------------------------
    "chunked",
    "batched",
    "group_by",
    "group_by_attribute",
    "unique",
    "unique_by",
    "flatten",
    "compact",
    "sorted_by",
    "sort_dictionary",
    "count_if",
    "frequencies",
    "partition",
    "pairwise",
    "first",
    "last",
    "take",
    "drop",

    # --------------------------------------------------------
    # String Utilities
    # --------------------------------------------------------
    "safe_identifier",
    "slugify",
    "snake_case",
    "camel_case",
    "pascal_case",
    "title_case",
    "sentence_case",
    "truncate",
    "add_prefix",
    "remove_prefix",
    "add_suffix",
    "remove_suffix",
    "is_valid_identifier",
    "validate_identifier",
    "is_left_name",
    "is_right_name",
    "opposite_side_name",
    "format_float",
    "format_percentage",
    "random_identifier",
    "unique_name",
    "common_prefix",
    "common_suffix",

    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------
    "Stopwatch",
    "Timer",
    "timed",
    "profile",
    "retry",
    "benchmark",
    "measure",
    "fps",
    "milliseconds",
    "seconds",
    "performance_statistics",
    "reset_performance_statistics",

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------
    "json_safe",
    "deep_serialize",
    "dataclass_to_dict",
    "object_to_dict",
    "numpy_to_list",
    "list_to_numpy",
    "serialize_bytes",
    "deserialize_bytes",
    "pretty_json",
    "compact_json",
    "serialization_report",
    "serialization_size",
    "is_json_serializable",
    "content_hash",
    "md5_hash",
    "sha1_hash",
    "sha256_hash",

    # --------------------------------------------------------
    # Maya
    # --------------------------------------------------------
    "maya_available",
    "require_maya",
    "maya_version",
    "api_version",
    "node_exists",
    "ensure_node_exists",
    "node_type",
    "list_nodes",
    "current_selection",
    "select_nodes",
    "PreserveSelection",
    "UndoChunk",
    "attribute_exists",
    "safe_get_attr",
    "safe_set_attr",
    "namespace",
    "short_name",
    "long_name",
    "refresh_viewport",
    "evaluation_mode",
    "maya_information",
    "safe_execute",

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------
    "DiagnosticReport",
    "environment_report",
    "runtime_report",
    "registry_report",
    "memory_report",
    "blendshape_report",
    "mapping_report",
    "diagnostics_report",
    "health_check",
    "print_diagnostics",
]

# ------------------------------------------------------------
# Module Initialization
# ------------------------------------------------------------

_logger = logging.getLogger(__name__)

_logger.debug(
    "%s v%s initialized.",
    MODULE_NAME,
    __version__,
)

# Register initialization in runtime statistics
try:
    UTILITY_STATISTICS.calls += 1
    UTILITY_STATISTICS.last_call = datetime.now()
except Exception:
    pass