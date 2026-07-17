"""
maya.py

Exceptions related to Autodesk Maya integration.
"""

from typing import Any, Optional

from .base import ARKitMapperError, ErrorCategory


class MayaIntegrationError(ARKitMapperError):
    def __init__(self, message: str = "Maya integration error.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.MAYA, **kwargs)


class MayaUnavailableError(MayaIntegrationError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Autodesk Maya is not available.", **kwargs)


class MayaVersionError(MayaIntegrationError):
    def __init__(self, version: str, *, minimum: Optional[str] = None, maximum: Optional[str] = None, **kwargs: Any) -> None:
        self.version = version
        self.minimum = minimum
        self.maximum = maximum
        if minimum and maximum:
            message = f"Maya {version} is unsupported. Supported versions: {minimum} - {maximum}."
        elif minimum:
            message = f"Maya {version} is unsupported. Minimum supported version is {minimum}."
        else:
            message = f"Unsupported Maya version {version}."
        super().__init__(message, **kwargs)


class MayaPluginError(MayaIntegrationError):
    def __init__(self, message: str = "Plugin error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class PluginNotLoadedError(MayaPluginError):
    def __init__(self, plugin: str, **kwargs: Any) -> None:
        self.plugin = plugin
        super().__init__(f"Plugin '{plugin}' is not loaded.", **kwargs)


class PluginLoadError(MayaPluginError):
    def __init__(self, plugin: str, **kwargs: Any) -> None:
        self.plugin = plugin
        super().__init__(f"Failed to load plugin '{plugin}'.", **kwargs)


class SceneError(MayaIntegrationError):
    def __init__(self, message: str = "Scene error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class SceneNotOpenError(SceneError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("No Maya scene is currently open.", **kwargs)


class SceneSaveError(SceneError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Unable to save the current scene.", **kwargs)


class NodeError(MayaIntegrationError):
    def __init__(self, message: str = "Node error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class NodeNotFoundError(NodeError):
    def __init__(self, node: str, **kwargs: Any) -> None:
        self.node = node
        super().__init__(f"Node '{node}' was not found.", **kwargs)


class DuplicateNodeError(NodeError):
    def __init__(self, node: str, **kwargs: Any) -> None:
        self.node = node
        super().__init__(f"Multiple nodes named '{node}' were found.", **kwargs)


class BlendShapeNodeError(NodeError):
    def __init__(self, message: str = "BlendShape node error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class BlendShapeNodeNotFoundError(BlendShapeNodeError):
    def __init__(self, node: str, **kwargs: Any) -> None:
        self.node = node
        super().__init__(f"BlendShape node '{node}' was not found.", **kwargs)


class BlendShapeTargetError(BlendShapeNodeError):
    def __init__(self, target: str, **kwargs: Any) -> None:
        self.target = target
        super().__init__(f"Blendshape target '{target}' is invalid.", **kwargs)


class MayaCommandError(MayaIntegrationError):
    def __init__(self, command: str, **kwargs: Any) -> None:
        self.command = command
        super().__init__(f"Maya command '{command}' failed.", **kwargs)


class UndoChunkError(MayaIntegrationError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Undo chunk operation failed.", **kwargs)


class SelectionError(MayaIntegrationError):
    def __init__(self, message: str = "Invalid selection.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ObjectLockedError(MayaIntegrationError):
    def __init__(self, node: str, **kwargs: Any) -> None:
        self.node = node
        super().__init__(f"Object '{node}' is locked.", **kwargs)