# -*- coding: utf-8 -*-
"""
maya_faceit.exceptions
~~~~~~~~~~~~~~~~~~~~~~

Custom exceptions for Maya FaceIT.
"""


class FaceITError(Exception):
    """Base exception for all Maya FaceIT errors."""
    pass


class InitializationError(FaceITError):
    """Raised when the plugin fails to initialize."""
    pass


class ConfigurationError(FaceITError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(FaceITError):
    """Raised when validation fails."""
    pass


class MeshError(FaceITError):
    """Raised for mesh-related errors."""
    pass


class RigError(FaceITError):
    """Raised for rig-related errors."""
    pass


class AnimationError(FaceITError):
    """Raised for animation-related errors."""
    pass


class BlendshapeError(FaceITError):
    """Raised for blendshape-related errors."""
    pass


class SkinError(FaceITError):
    """Raised for skinning-related errors."""
    pass


class MirrorError(FaceITError):
    """Raised for mirroring-related errors."""
    pass


class SymmetryError(FaceITError):
    """Raised for symmetry-related errors."""
    pass


class TransferError(FaceITError):
    """Raised for transfer-related errors."""
    pass


class ExportError(FaceITError):
    """Raised for export-related errors."""
    pass


class ImportError(FaceITError):
    """Raised for import-related errors."""
    pass


class SerializationError(FaceITError):
    """Raised for serialization/deserialization errors."""
    pass


class PreferencesError(FaceITError):
    """Raised for preferences-related errors."""
    pass


class ProjectError(FaceITError):
    """Raised for project-related errors."""
    pass


class SessionError(FaceITError):
    """Raised for session-related errors."""
    pass


class ComponentError(FaceITError):
    """Raised for component registration/lookup errors."""
    pass


class UIError(FaceITError):
    """Raised for UI-related errors."""
    pass


class PermissionError(FaceITError):
    """Raised when the user lacks necessary permissions."""
    pass


__all__ = [
    "FaceITError",
    "InitializationError",
    "ConfigurationError",
    "ValidationError",
    "MeshError",
    "RigError",
    "AnimationError",
    "BlendshapeError",
    "SkinError",
    "MirrorError",
    "SymmetryError",
    "TransferError",
    "ExportError",
    "ImportError",
    "SerializationError",
    "PreferencesError",
    "ProjectError",
    "SessionError",
    "ComponentError",
    "UIError",
    "PermissionError",
]