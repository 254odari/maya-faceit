"""
base.py

Base exception hierarchy for the ARKit Mapper.

All exceptions raised by the ARKit mapper derive from ARKitMapperError.
"""

from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

# ------------------------------------------------------------
# Module Information
# ------------------------------------------------------------

MODULE_NAME = "blendshapes.arkit_mapper.exceptions.base"
MODULE_VERSION = "1.0.0"

# ------------------------------------------------------------
# Error Severity
# ------------------------------------------------------------

class ErrorSeverity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ------------------------------------------------------------
# Error Categories
# ------------------------------------------------------------

class ErrorCategory:
    GENERAL = "general"
    MAPPING = "mapping"
    PRESET = "preset"
    VALIDATION = "validation"
    RUNTIME = "runtime"
    IMPORT_EXPORT = "import_export"
    VERSIONING = "versioning"
    MIGRATION = "migration"
    MAYA = "maya"
    IO = "io"
    UNKNOWN = "unknown"


# ------------------------------------------------------------
# Error Context
# ------------------------------------------------------------

@dataclass(slots=True)
class ErrorContext:
    operation: str = ""
    component: str = ""
    object_name: str = ""
    file_path: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "component": self.component,
            "object_name": self.object_name,
            "file_path": self.file_path,
            "extra": dict(self.extra),
        }


# ------------------------------------------------------------
# Error Record
# ------------------------------------------------------------

@dataclass(slots=True)
class ErrorRecord:
    id: str
    timestamp: str
    exception: str
    message: str
    severity: str
    category: str
    context: Dict[str, Any]
    traceback: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "exception": self.exception,
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
            "context": dict(self.context),
            "traceback": self.traceback,
        }


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def generate_error_id() -> str:
    return uuid.uuid4().hex


def current_timestamp() -> str:
    return datetime.utcnow().isoformat()


def format_traceback() -> str:
    return traceback.format_exc()


def build_error_record(
    exception: Exception,
    *,
    severity: str = ErrorSeverity.ERROR,
    category: str = ErrorCategory.GENERAL,
    context: Optional[Mapping[str, Any]] = None,
) -> ErrorRecord:
    return ErrorRecord(
        id=generate_error_id(),
        timestamp=current_timestamp(),
        exception=type(exception).__name__,
        message=str(exception),
        severity=severity,
        category=category,
        context=dict(context or {}),
        traceback=format_traceback(),
    )


# ------------------------------------------------------------
# Base Exception
# ------------------------------------------------------------

class ARKitMapperError(Exception):
    """Root exception for the ARKit Mapper subsystem."""

    def __init__(
        self,
        message: str = "An unknown ARKit mapper error occurred.",
        *,
        severity: str = ErrorSeverity.ERROR,
        category: str = ErrorCategory.GENERAL,
        context: Optional[ErrorContext] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext()
        self.cause = cause
        self.error_id = generate_error_id()
        self.timestamp = current_timestamp()

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"

    def to_record(self) -> ErrorRecord:
        return ErrorRecord(
            id=self.error_id,
            timestamp=self.timestamp,
            exception=self.__class__.__name__,
            message=self.message,
            severity=self.severity,
            category=self.category,
            context=self.context.to_dict(),
            traceback=format_traceback(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.to_record().to_dict()


# ------------------------------------------------------------
# General Exceptions
# ------------------------------------------------------------

class ConfigurationError(ARKitMapperError):
    def __init__(self, message: str = "Invalid configuration.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.GENERAL, **kwargs)


class InitializationError(ARKitMapperError):
    def __init__(self, message: str = "Initialization failed.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.GENERAL, **kwargs)


class UnsupportedFeatureError(ARKitMapperError):
    def __init__(self, feature: str, **kwargs: Any) -> None:
        self.feature = feature
        super().__init__(f"Unsupported feature: {feature}", category=ErrorCategory.GENERAL, **kwargs)


class NotImplementedMapperError(ARKitMapperError):
    def __init__(self, feature: str = "", **kwargs: Any) -> None:
        message = "Feature has not been implemented." if not feature else f"Feature '{feature}' has not been implemented."
        self.feature = feature
        super().__init__(message, category=ErrorCategory.GENERAL, **kwargs)


class InternalMapperError(ARKitMapperError):
    def __init__(self, message: str = "Internal ARKit mapper error.", **kwargs: Any) -> None:
        super().__init__(message, severity=ErrorSeverity.CRITICAL, category=ErrorCategory.GENERAL, **kwargs)


class CancelledOperationError(ARKitMapperError):
    def __init__(self, message: str = "Operation cancelled.", **kwargs: Any) -> None:
        super().__init__(message, severity=ErrorSeverity.INFO, category=ErrorCategory.GENERAL, **kwargs)


class TimeoutError(ARKitMapperError):
    def __init__(self, timeout: Optional[float] = None, **kwargs: Any) -> None:
        if timeout is None:
            message = "Operation timed out."
        else:
            message = f"Operation timed out after {timeout:.2f} seconds."
        self.timeout = timeout
        super().__init__(message, category=ErrorCategory.GENERAL, **kwargs)


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def exception_to_record(exception: BaseException) -> ErrorRecord:
    if isinstance(exception, ARKitMapperError):
        return exception.to_record()
    return build_error_record(exception)


def exception_to_dict(exception: BaseException) -> Dict[str, Any]:
    return exception_to_record(exception).to_dict()