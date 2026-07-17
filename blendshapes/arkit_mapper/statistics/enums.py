"""
maya_faceit/blendshapes/arkit_mapper/statistics/enums.py

Enumerations for the ARKit Mapper statistics system.
"""

from enum import Enum


class StatisticsType(Enum):
    """Categories of statistics."""

    CHANNEL = "channel"
    MAPPING = "mapping"
    CONVERSION = "conversion"
    VALIDATION = "validation"
    RUNTIME = "runtime"
    PERFORMANCE = "performance"
    PROFILING = "profiling"
    BENCHMARK = "benchmark"


class StatisticOperation(Enum):
    """Recorded operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESET = "reset"
    IMPORT = "import"
    EXPORT = "export"
    CONVERT = "convert"
    VALIDATE = "validate"
    MAP = "map"


class StatisticStatus(Enum):
    """Statistics status."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    RESET = "reset"