"""
preset.py

Exceptions related to preset creation, registration, loading, saving, and runtime management.
"""

from typing import Any

from .base import ARKitMapperError, ErrorCategory


class PresetError(ARKitMapperError):
    def __init__(self, message: str = "Preset error.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.PRESET, **kwargs)


class PresetNotFoundError(PresetError):
    def __init__(self, identifier: str, **kwargs: Any) -> None:
        self.identifier = identifier
        super().__init__(f"Preset '{identifier}' was not found.", **kwargs)


class PresetAlreadyExistsError(PresetError):
    def __init__(self, identifier: str, **kwargs: Any) -> None:
        self.identifier = identifier
        super().__init__(f"Preset '{identifier}' already exists.", **kwargs)


class PresetRegistrationError(PresetError):
    def __init__(self, reason: str = "Failed to register preset.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class PresetUnregistrationError(PresetError):
    def __init__(self, identifier: str, **kwargs: Any) -> None:
        self.identifier = identifier
        super().__init__(f"Unable to unregister preset '{identifier}'.", **kwargs)


class PresetCreationError(PresetError):
    def __init__(self, reason: str = "Preset creation failed.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class PresetCloneError(PresetError):
    def __init__(self, preset_name: str, **kwargs: Any) -> None:
        self.preset_name = preset_name
        super().__init__(f"Failed to clone preset '{preset_name}'.", **kwargs)


class ProtectedPresetError(PresetError):
    def __init__(self, preset_name: str, **kwargs: Any) -> None:
        self.preset_name = preset_name
        super().__init__(f"Preset '{preset_name}' is protected.", **kwargs)


class ActivePresetError(PresetError):
    def __init__(self, message: str = "Invalid active preset operation.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class NoActivePresetError(PresetError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("There is no active preset.", **kwargs)


class PresetLoadError(PresetError):
    def __init__(self, source: str, **kwargs: Any) -> None:
        self.source = source
        super().__init__(f"Failed to load preset from '{source}'.", **kwargs)


class PresetSaveError(PresetError):
    def __init__(self, destination: str, **kwargs: Any) -> None:
        self.destination = destination
        super().__init__(f"Failed to save preset to '{destination}'.", **kwargs)


class PresetImportError(PresetError):
    def __init__(self, source: str, **kwargs: Any) -> None:
        self.source = source
        super().__init__(f"Unable to import preset '{source}'.", **kwargs)


class PresetExportError(PresetError):
    def __init__(self, destination: str, **kwargs: Any) -> None:
        self.destination = destination
        super().__init__(f"Unable to export preset to '{destination}'.", **kwargs)


class PresetSearchError(PresetError):
    def __init__(self, query: str, **kwargs: Any) -> None:
        self.query = query
        super().__init__(f"Preset search failed for '{query}'.", **kwargs)


class PresetCompatibilityError(PresetError):
    def __init__(self, reason: str, **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(f"Preset compatibility error: {reason}", **kwargs)


class PresetVersionError(PresetError):
    def __init__(self, version: str, **kwargs: Any) -> None:
        self.version = version
        super().__init__(f"Unsupported preset version '{version}'.", **kwargs)