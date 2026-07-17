"""
runtime.py

Runtime exceptions raised while executing the ARKit mapper.
"""

from typing import Any

from .base import ARKitMapperError, ErrorCategory


class RuntimeMapperError(ARKitMapperError):
    def __init__(self, message: str = "Runtime error.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.RUNTIME, **kwargs)


class SessionNotInitializedError(RuntimeMapperError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Runtime session has not been initialized.", **kwargs)


class SessionAlreadyInitializedError(RuntimeMapperError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Runtime session is already initialized.", **kwargs)


class SessionClosedError(RuntimeMapperError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Runtime session has already been closed.", **kwargs)


class InvalidRuntimeStateError(RuntimeMapperError):
    def __init__(self, state: str, **kwargs: Any) -> None:
        self.state = state
        super().__init__(f"Invalid runtime state '{state}'.", **kwargs)


class RuntimeBusyError(RuntimeMapperError):
    def __init__(self, operation: str = "", **kwargs: Any) -> None:
        self.operation = operation
        message = "Runtime is busy." if not operation else f"Runtime is busy executing '{operation}'."
        super().__init__(message, **kwargs)


class PresetActivationError(RuntimeMapperError):
    def __init__(self, preset: str, **kwargs: Any) -> None:
        self.preset = preset
        super().__init__(f"Unable to activate preset '{preset}'.", **kwargs)


class PresetDeactivationError(RuntimeMapperError):
    def __init__(self, preset: str = "", **kwargs: Any) -> None:
        self.preset = preset
        message = "Unable to deactivate preset." if not preset else f"Unable to deactivate preset '{preset}'."
        super().__init__(message, **kwargs)


class EvaluationError(RuntimeMapperError):
    def __init__(self, reason: str = "Evaluation failed.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class EvaluationOverflowError(EvaluationError):
    def __init__(self, value: Any, **kwargs: Any) -> None:
        self.value = value
        super().__init__(f"Evaluation overflow: {value!r}", **kwargs)


class EvaluationCycleError(EvaluationError):
    def __init__(self, node: str, **kwargs: Any) -> None:
        self.node = node
        super().__init__(f"Cyclic dependency detected at '{node}'.", **kwargs)


class CacheError(RuntimeMapperError):
    def __init__(self, message: str = "Cache error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class CacheMissError(CacheError):
    def __init__(self, key: str, **kwargs: Any) -> None:
        self.key = key
        super().__init__(f"Cache miss for '{key}'.", **kwargs)


class CacheCorruptionError(CacheError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Cached runtime data is corrupted.", **kwargs)


class ResourceUnavailableError(RuntimeMapperError):
    def __init__(self, resource: str, **kwargs: Any) -> None:
        self.resource = resource
        super().__init__(f"Required resource '{resource}' is unavailable.", **kwargs)


class RuntimeLockError(RuntimeMapperError):
    def __init__(self, lock_name: str = "", **kwargs: Any) -> None:
        self.lock_name = lock_name
        message = "Failed to acquire runtime lock." if not lock_name else f"Failed to acquire runtime lock '{lock_name}'."
        super().__init__(message, **kwargs)