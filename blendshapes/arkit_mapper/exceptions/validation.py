"""
validation.py

Exceptions raised during validation of ARKit mappings, presets, blendshapes, runtime data, and configuration.
"""

from typing import Any, Iterable

from .base import ARKitMapperError, ErrorCategory


class ValidationError(ARKitMapperError):
    def __init__(self, message: str = "Validation failed.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)


PresetValidationError = ValidationError


class MissingFieldError(ValidationError):
    def __init__(self, field_name: str, **kwargs: Any) -> None:
        self.field_name = field_name
        super().__init__(f"Required field '{field_name}' is missing.", **kwargs)


class InvalidFieldError(ValidationError):
    def __init__(self, field_name: str, value: Any, **kwargs: Any) -> None:
        self.field_name = field_name
        self.value = value
        super().__init__(f"Invalid value for field '{field_name}': {value!r}", **kwargs)


class InvalidTypeError(ValidationError):
    def __init__(self, expected: Any, received: Any, **kwargs: Any) -> None:
        self.expected = expected
        self.received = received
        super().__init__(f"Expected {expected!r}, received {received!r}.", **kwargs)


class InvalidChannelError(ValidationError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"Invalid ARKit channel '{channel}'.", **kwargs)


class MissingChannelError(ValidationError):
    def __init__(self, channel: str, **kwargs: Any) -> None:
        self.channel = channel
        super().__init__(f"Missing required ARKit channel '{channel}'.", **kwargs)


class InvalidBlendshapeError(ValidationError):
    def __init__(self, blendshape: str, **kwargs: Any) -> None:
        self.blendshape = blendshape
        super().__init__(f"Invalid blendshape '{blendshape}'.", **kwargs)


class DuplicateBlendshapeError(ValidationError):
    def __init__(self, blendshape: str, **kwargs: Any) -> None:
        self.blendshape = blendshape
        super().__init__(f"Duplicate blendshape '{blendshape}'.", **kwargs)


class InvalidWeightRangeError(ValidationError):
    def __init__(self, value: float, minimum: float, maximum: float, **kwargs: Any) -> None:
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        super().__init__(f"Weight {value} is outside [{minimum}, {maximum}].", **kwargs)


class WeightSumError(ValidationError):
    def __init__(self, total: float, expected: float = 1.0, **kwargs: Any) -> None:
        self.total = total
        self.expected = expected
        super().__init__(f"Weight total {total:.6f} does not equal {expected:.6f}.", **kwargs)


class InvalidPresetStructureError(ValidationError):
    def __init__(self, reason: str, **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class DuplicatePresetNameError(ValidationError):
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        super().__init__(f"Duplicate preset name '{name}'.", **kwargs)


class DuplicatePresetUUIDError(ValidationError):
    def __init__(self, uuid: str, **kwargs: Any) -> None:
        self.uuid = uuid
        super().__init__(f"Duplicate preset UUID '{uuid}'.", **kwargs)


class VersionMismatchError(ValidationError):
    def __init__(self, message: str = "Version mismatch.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class CompatibilityValidationError(ValidationError):
    def __init__(self, reason: str, **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class MultipleValidationError(ValidationError):
    def __init__(self, errors: Iterable[str], **kwargs: Any) -> None:
        self.errors = list(errors)
        super().__init__(f"{len(self.errors)} validation error(s) occurred.", **kwargs)

    def __iter__(self):
        return iter(self.errors)