"""
diagnostics.py

Diagnostic utilities and helper functions for the ARKit Mapper exception system.
"""

import traceback
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from .base import (
    ARKitMapperError,
    ErrorCategory,
    ErrorSeverity,
    exception_to_dict,
    exception_to_record,
    format_traceback,
)


# ------------------------------------------------------------
# Exception Classification
# ------------------------------------------------------------

def is_mapper_exception(exception: BaseException) -> bool:
    return isinstance(exception, ARKitMapperError)


def exception_category(exception: BaseException) -> str:
    if isinstance(exception, ARKitMapperError):
        return exception.category
    return ErrorCategory.UNKNOWN


def exception_severity(exception: BaseException) -> str:
    if isinstance(exception, ARKitMapperError):
        return exception.severity
    return ErrorSeverity.ERROR


def exception_name(exception: BaseException) -> str:
    return exception.__class__.__name__


# ------------------------------------------------------------
# Formatting
# ------------------------------------------------------------

def format_exception(exception: BaseException) -> str:
    return f"[{exception_category(exception)}] {exception_name(exception)}: {exception}"


def format_exception_verbose(exception: BaseException) -> str:
    lines = [
        f"Type      : {exception_name(exception)}",
        f"Category  : {exception_category(exception)}",
        f"Severity  : {exception_severity(exception)}",
        f"Message   : {exception}",
    ]
    if isinstance(exception, ARKitMapperError):
        lines.extend([
            f"Error ID  : {exception.error_id}",
            f"Timestamp : {exception.timestamp}",
        ])
    return "\n".join(lines)


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

def log_exception(exception: BaseException, logger=None) -> None:
    active_logger = logger
    if active_logger is None:
        import logging
        active_logger = logging.getLogger("ARKitMapper")
    active_logger.error(format_exception_verbose(exception))


def log_exception_with_traceback(exception: BaseException, logger=None) -> None:
    active_logger = logger
    if active_logger is None:
        import logging
        active_logger = logging.getLogger("ARKitMapper")
    active_logger.exception(format_exception_verbose(exception))


# ------------------------------------------------------------
# Serialization
# ------------------------------------------------------------

def serialize_exception(exception: BaseException) -> Dict[str, Any]:
    if isinstance(exception, ARKitMapperError):
        return exception.to_dict()
    return exception_to_dict(exception)


def serialize_exceptions(exceptions: Iterable[BaseException]) -> List[Dict[str, Any]]:
    return [serialize_exception(e) for e in exceptions]


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def summarize_exceptions(exceptions: Iterable[BaseException]) -> Dict[str, Any]:
    exceptions = list(exceptions)
    categories = Counter(exception_category(e) for e in exceptions)
    severities = Counter(exception_severity(e) for e in exceptions)
    types = Counter(exception_name(e) for e in exceptions)
    return {
        "total": len(exceptions),
        "categories": dict(categories),
        "severities": dict(severities),
        "types": dict(types),
    }


# ------------------------------------------------------------
# Reports
# ------------------------------------------------------------

def diagnostics_report(exceptions: Iterable[BaseException]) -> Dict[str, Any]:
    exceptions = list(exceptions)
    return {
        "statistics": summarize_exceptions(exceptions),
        "exceptions": serialize_exceptions(exceptions),
    }


def print_diagnostics(exceptions: Iterable[BaseException]) -> None:
    report = diagnostics_report(exceptions)
    print("========== Exception Diagnostics ==========")
    print(f"Total Exceptions: {report['statistics']['total']}")
    for exc in report["exceptions"]:
        print(f"{exc['exception']} | {exc['message']}")


# ------------------------------------------------------------
# Convenience Helpers
# ------------------------------------------------------------

def raise_if(condition: bool, exception: BaseException) -> None:
    if condition:
        raise exception


def ignore_exception(exception: BaseException) -> None:
    pass


def reraise(exception: BaseException) -> None:
    raise exception


# ------------------------------------------------------------
# Category-specific summaries
# ------------------------------------------------------------

def mapping_exception_summary(exception: BaseException) -> Dict[str, Any]:
    if isinstance(exception, ARKitMapperError):
        return {
            "type": exception.__class__.__name__,
            "message": str(exception),
            "category": exception.category,
            "severity": exception.severity,
            "context": exception.context.to_dict(),
        }
    return exception_to_dict(exception)


preset_exception_summary = mapping_exception_summary
validation_exception_summary = mapping_exception_summary
runtime_exception_summary = mapping_exception_summary
import_export_exception_summary = mapping_exception_summary
maya_exception_summary = mapping_exception_summary