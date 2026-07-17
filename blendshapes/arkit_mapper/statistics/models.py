"""
maya_faceit/blendshapes/arkit_mapper/statistics/models.py

Dataclasses for the ARKit Mapper statistics system.
"""

import copy
import json
import math
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from .constants import STATISTICS_VERSION, DEFAULT_HISTORY_SIZE, DEFAULT_MOVING_WINDOW
from .enums import StatisticsType, StatisticOperation, StatisticStatus


# ============================================================
# Base Dataclasses
# ============================================================

@dataclass(slots=True)
class StatisticsSnapshot:
    """
    Immutable snapshot of the statistics system.
    """

    timestamp: float = field(default_factory=time.time)
    category: StatisticsType = StatisticsType.RUNTIME
    values: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StatisticsSummary:
    """
    High-level statistics summary.
    """

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    warnings: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    uptime: float = 0.0


@dataclass(slots=True)
class StatisticsConfig:
    """
    Configuration for the statistics manager.
    """

    enabled: bool = True
    history_size: int = DEFAULT_HISTORY_SIZE
    moving_window: int = DEFAULT_MOVING_WINDOW
    collect_runtime: bool = True
    collect_mapping: bool = True
    collect_validation: bool = True
    collect_conversion: bool = True
    auto_trim_history: bool = True
    thread_safe: bool = True


# ============================================================
# Channel Statistics
# ============================================================

@dataclass(slots=True)
class ChannelStatistics:
    """
    Statistics for a single ARKit channel.

    Tracks usage, value distribution,
    activity, and timing information.
    """

    name: str

    samples: int = 0

    minimum: float = math.inf

    maximum: float = -math.inf

    total: float = 0.0

    mean: float = 0.0

    variance: float = 0.0

    std_deviation: float = 0.0

    last_value: float = 0.0

    last_timestamp: float = 0.0

    first_timestamp: float = field(default_factory=time.time)

    active_frames: int = 0

    inactive_frames: int = 0

    updates: int = 0

    values: List[float] = field(default_factory=list)

    @property
    def range(self) -> float:
        if self.samples == 0:
            return 0.0
        return self.maximum - self.minimum

    @property
    def activity_ratio(self) -> float:
        total = self.active_frames + self.inactive_frames
        if total == 0:
            return 0.0
        return self.active_frames / total

    @property
    def average(self) -> float:
        return self.mean


# ============================================================
# Mapping Statistics
# ============================================================

@dataclass(slots=True)
class MappingStatistics:
    """
    Statistics for ARKit → Rig mapping operations.
    """

    mapping_name: str

    total_requests: int = 0

    successful_mappings: int = 0

    failed_mappings: int = 0

    disabled_mappings: int = 0

    unmapped_channels: int = 0

    duplicate_targets: int = 0

    overwritten_values: int = 0

    skipped_channels: int = 0

    total_processing_time: float = 0.0

    minimum_time: float = math.inf

    maximum_time: float = 0.0

    average_time: float = 0.0

    last_processing_time: float = 0.0

    last_timestamp: float = field(default_factory=time.time)

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_mappings / self.total_requests) * 100.0

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.failed_mappings / self.total_requests) * 100.0

    @property
    def throughput(self) -> float:
        if self.average_time <= 0.0:
            return 0.0
        return 1.0 / self.average_time


# ============================================================
# Conversion Statistics
# ============================================================

@dataclass(slots=True)
class ConversionStatistics:
    """
    Statistics for ARKit coefficient conversion.

    Tracks both forward (ARKit → Rig) and reverse
    (Rig → ARKit) conversion performance.
    """

    conversion_name: str

    total_conversions: int = 0

    forward_conversions: int = 0

    reverse_conversions: int = 0

    successful_conversions: int = 0

    failed_conversions: int = 0

    partial_conversions: int = 0

    input_channels: int = 0

    output_channels: int = 0

    unmapped_inputs: int = 0

    disabled_inputs: int = 0

    clipped_outputs: int = 0

    normalized_outputs: int = 0

    total_processing_time: float = 0.0

    minimum_processing_time: float = math.inf

    maximum_processing_time: float = 0.0

    average_processing_time: float = 0.0

    last_processing_time: float = 0.0

    first_conversion: float = field(default_factory=time.time)

    last_conversion: float = 0.0

    processing_history: List[float] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_conversions == 0:
            return 0.0
        return (self.successful_conversions / self.total_conversions) * 100.0

    @property
    def failure_rate(self) -> float:
        if self.total_conversions == 0:
            return 0.0
        return (self.failed_conversions / self.total_conversions) * 100.0

    @property
    def throughput(self) -> float:
        if self.average_processing_time <= 0.0:
            return 0.0
        return 1.0 / self.average_processing_time

    @property
    def uptime(self) -> float:
        return time.time() - self.first_conversion


# ============================================================
# Runtime Statistics
# ============================================================

@dataclass(slots=True)
class RuntimeStatistics:
    """
    Runtime execution statistics.

    Tracks real-time execution performance of the
    ARKit mapper runtime.
    """

    runtime_name: str

    total_frames: int = 0

    processed_frames: int = 0

    dropped_frames: int = 0

    skipped_frames: int = 0

    duplicate_frames: int = 0

    invalid_frames: int = 0

    start_time: float = field(default_factory=time.time)

    stop_time: float = 0.0

    last_frame_time: float = 0.0

    last_update: float = 0.0

    current_fps: float = 0.0

    average_fps: float = 0.0

    minimum_fps: float = math.inf

    maximum_fps: float = 0.0

    fps_history: List[float] = field(default_factory=list)

    total_processing_time: float = 0.0

    average_processing_time: float = 0.0

    minimum_processing_time: float = math.inf

    maximum_processing_time: float = 0.0

    processing_history: List[float] = field(default_factory=list)

    queue_size: int = 0

    maximum_queue_size: int = 0

    average_queue_size: float = 0.0

    queue_history: List[int] = field(default_factory=list)

    current_latency: float = 0.0

    average_latency: float = 0.0

    maximum_latency: float = 0.0

    latency_history: List[float] = field(default_factory=list)

    runtime_errors: int = 0

    runtime_warnings: int = 0

    recoveries: int = 0

    @property
    def uptime(self) -> float:
        if self.stop_time > 0:
            return self.stop_time - self.start_time
        return time.time() - self.start_time

    @property
    def frame_success_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return (self.processed_frames / self.total_frames) * 100.0

    @property
    def drop_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return (self.dropped_frames / self.total_frames) * 100.0


# ============================================================
# Reports
# ============================================================

@dataclass(slots=True)
class StatisticsReport:
    """
    Generated statistics report.
    """

    title: str

    generated_at: float = field(default_factory=time.time)

    version: str = STATISTICS_VERSION

    summary: Dict[str, Any] = field(default_factory=dict)

    sections: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def generated_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.generated_at)