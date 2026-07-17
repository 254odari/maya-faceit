"""
mapping.py

Exceptions related to ARKit blendshape mappings.
"""

from typing import Any

from .base import ARKitMapperError, ErrorCategory


class MappingError(ARKitMapperError):
    def __init__(self, message: str = "Mapping error.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.MAPPING, **kwargs)


class MappingNotFoundError(MappingError):
    def __init__(self, mapping_name: str, **kwargs: Any) -> None:
        self.mapping_name = mapping_name
        super().__init__(f"Mapping '{mapping_name}' was not found.", **kwargs)


class MappingAlreadyExistsError(MappingError):
    def __init__(self, mapping_name: str, **kwargs: Any) -> None:
        self.mapping_name = mapping_name
        super().__init__(f"Mapping '{mapping_name}' already exists.", **kwargs)


class UnknownARKitChannelError(MappingError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"Unknown ARKit channel '{channel}'.", **kwargs)


class UnknownTargetShapeError(MappingError):
    def __init__(self, shape_name: str, **kwargs: Any) -> None:
        self.shape_name = shape_name
        super().__init__(f"Unknown target blendshape '{shape_name}'.", **kwargs)


class MissingMappingError(MappingError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"No mapping defined for '{channel}'.", **kwargs)


class InvalidWeightError(MappingError):
    def __init__(self, weight: Any, *, minimum: float = 0.0, maximum: float = 1.0, **kwargs: Any) -> None:
        self.weight = weight
        self.minimum = minimum
        self.maximum = maximum
        super().__init__(f"Weight {weight!r} is outside the valid range [{minimum}, {maximum}].", **kwargs)


class WeightNormalizationError(MappingError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"Failed to normalize weights for '{channel}'.", **kwargs)


class InvalidMappingError(MappingError):
    def __init__(self, reason: str = "Invalid mapping.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class EmptyMappingError(MappingError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Mapping contains no entries.", **kwargs)


class DuplicateMappingError(MappingError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"Duplicate mapping for '{channel}'.", **kwargs)


class MappingCompatibilityError(MappingError):
    def __init__(self, reason: str, **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(f"Incompatible mapping: {reason}", **kwargs)


class CharacterMismatchError(MappingError):
    def __init__(self, expected: str, received: str, **kwargs: Any) -> None:
        self.expected = expected
        self.received = received
        super().__init__(f"Expected character '{expected}', received '{received}'.", **kwargs)


class MappingApplicationError(MappingError):
    def __init__(self, channel: str = "", **kwargs: Any) -> None:
        self.channel = channel
        message = "Failed to apply mapping." if not channel else f"Failed to apply mapping for '{channel}'."
        super().__init__(message, **kwargs)


class MappingEvaluationError(MappingError):
    def __init__(self, reason: str = "", **kwargs: Any) -> None:
        self.reason = reason
        message = "Mapping evaluation failed." if not reason else reason
        super().__init__(message, **kwargs)