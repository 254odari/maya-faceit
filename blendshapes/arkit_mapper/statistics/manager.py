"""
maya_faceit/blendshapes/arkit_mapper/statistics/manager.py

Core StatisticsManager class for the ARKit Mapper.

Collects, organizes, and reports all statistics generated
throughout the ARKit Mapper system.
"""

import copy
import json
import math
import statistics
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Deque,
    Dict,
    List,
    Optional,
    Union,
)

from .constants import STATISTICS_VERSION, DEFAULT_HISTORY_SIZE, DEFAULT_MOVING_WINDOW, DEFAULT_PERCENTILE
from .enums import StatisticsType, StatisticOperation, StatisticStatus
from .models import (
    StatisticsSnapshot,
    StatisticsSummary,
    StatisticsConfig,
    ChannelStatistics,
    MappingStatistics,
    ConversionStatistics,
    RuntimeStatistics,
    StatisticsReport,
)


class StatisticsManager:
    """
    Central statistics manager.

    Responsible for collecting, organizing,
    and reporting all statistics generated
    throughout the ARKit Mapper system.
    """

    def __init__(
        self,
        config: Optional[StatisticsConfig] = None,
    ) -> None:

        self.config = config or StatisticsConfig()

        self.summary = StatisticsSummary()

        # Thread safety
        self._lock = threading.RLock()

        # Historical snapshots
        self._history: Deque[StatisticsSnapshot] = deque(
            maxlen=self.config.history_size
        )

        # Category storage
        self._statistics: DefaultDict[StatisticsType, Dict[str, Any]] = defaultdict(dict)

        # Operation counters
        self._operation_counts: DefaultDict[StatisticOperation, int] = defaultdict(int)

        # User-defined counters
        self._counters: DefaultDict[str, int] = defaultdict(int)

        # Numeric measurements
        self._measurements: DefaultDict[str, List[float]] = defaultdict(list)

        # Moving windows
        self._windows: DefaultDict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=self.config.moving_window)
        )

        # Registered callbacks
        self._callbacks: List[Callable[[StatisticsSnapshot], None]] = []

        # Runtime state
        self._status = StatisticStatus.ACTIVE

    # ============================================================
    # Properties
    # ============================================================

    @property
    def status(self) -> StatisticStatus:
        return self._status

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @property
    def history(self) -> List[StatisticsSnapshot]:
        return list(self._history)

    @property
    def categories(self) -> List[StatisticsType]:
        return list(self._statistics.keys())

    @property
    def total_snapshots(self) -> int:
        return len(self._history)

    @property
    def total_measurements(self) -> int:
        return sum(len(values) for values in self._measurements.values())

    @property
    def total_counters(self) -> int:
        return len(self._counters)

    @property
    def uptime(self) -> float:
        return time.time() - self.summary.start_time

    # ============================================================
    # Channel Statistics
    # ============================================================

    def record_channel(
        self,
        channel: str,
        value: float,
        timestamp: Optional[float] = None,
    ) -> None:
        if not self.enabled:
            return
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            stats = self._statistics[StatisticsType.CHANNEL].get(channel)
            if stats is None:
                stats = ChannelStatistics(name=channel)
                self._statistics[StatisticsType.CHANNEL][channel] = stats

            stats.samples += 1
            stats.updates += 1
            stats.last_value = value
            stats.last_timestamp = timestamp
            stats.total += value
            stats.minimum = min(stats.minimum, value)
            stats.maximum = max(stats.maximum, value)
            stats.values.append(value)
            stats.mean = stats.total / stats.samples

            if value > 0.001:
                stats.active_frames += 1
            else:
                stats.inactive_frames += 1

            if stats.samples > 1:
                stats.variance = statistics.pvariance(stats.values)
                stats.std_deviation = math.sqrt(stats.variance)

    def channel_statistics(self, channel: str) -> Optional[ChannelStatistics]:
        return self._statistics[StatisticsType.CHANNEL].get(channel)

    def all_channel_statistics(self) -> Dict[str, ChannelStatistics]:
        return dict(self._statistics[StatisticsType.CHANNEL])

    def channel_exists(self, channel: str) -> bool:
        return channel in self._statistics[StatisticsType.CHANNEL]

    def remove_channel(self, channel: str) -> bool:
        if not self.channel_exists(channel):
            return False
        del self._statistics[StatisticsType.CHANNEL][channel]
        return True

    def clear_channels(self) -> None:
        self._statistics[StatisticsType.CHANNEL].clear()

    def total_channels(self) -> int:
        return len(self._statistics[StatisticsType.CHANNEL])

    def active_channels(self) -> List[str]:
        active = []
        for name, stats in self._statistics[StatisticsType.CHANNEL].items():
            if stats.last_value > 0.001:
                active.append(name)
        return active

    def inactive_channels(self) -> List[str]:
        inactive = []
        for name, stats in self._statistics[StatisticsType.CHANNEL].items():
            if stats.last_value <= 0.001:
                inactive.append(name)
        return inactive

    def most_active_channel(self) -> Optional[ChannelStatistics]:
        channels = self.all_channel_statistics()
        if not channels:
            return None
        return max(channels.values(), key=lambda s: s.active_frames)

    def least_active_channel(self) -> Optional[ChannelStatistics]:
        channels = self.all_channel_statistics()
        if not channels:
            return None
        return min(channels.values(), key=lambda s: s.active_frames)

    def channel_summary(self) -> Dict[str, Any]:
        return {
            "channels": self.total_channels(),
            "active": len(self.active_channels()),
            "inactive": len(self.inactive_channels()),
            "most_active": self.most_active_channel(),
            "least_active": self.least_active_channel(),
            "samples": sum(c.samples for c in self.all_channel_statistics().values()),
        }

    def reset_channel(self, channel: str) -> bool:
        if not self.channel_exists(channel):
            return False
        self._statistics[StatisticsType.CHANNEL][channel] = ChannelStatistics(name=channel)
        return True

    def reset_all_channels(self) -> None:
        names = list(self._statistics[StatisticsType.CHANNEL].keys())
        self.clear_channels()
        for name in names:
            self._statistics[StatisticsType.CHANNEL][name] = ChannelStatistics(name=name)

    # ============================================================
    # Mapping Statistics
    # ============================================================

    def record_mapping(
        self,
        mapping_name: str,
        success: bool,
        processing_time: float,
        *,
        disabled: bool = False,
        unmapped: bool = False,
        duplicate: bool = False,
        overwritten: bool = False,
        skipped: bool = False,
        error: Optional[str] = None,
        warning: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return

        with self._lock:
            stats = self._statistics[StatisticsType.MAPPING].get(mapping_name)
            if stats is None:
                stats = MappingStatistics(mapping_name=mapping_name)
                self._statistics[StatisticsType.MAPPING][mapping_name] = stats

            stats.total_requests += 1
            stats.last_timestamp = time.time()
            stats.last_processing_time = processing_time
            stats.total_processing_time += processing_time
            stats.minimum_time = min(stats.minimum_time, processing_time)
            stats.maximum_time = max(stats.maximum_time, processing_time)
            stats.average_time = stats.total_processing_time / stats.total_requests

            if success:
                stats.successful_mappings += 1
            else:
                stats.failed_mappings += 1

            if disabled:
                stats.disabled_mappings += 1
            if unmapped:
                stats.unmapped_channels += 1
            if duplicate:
                stats.duplicate_targets += 1
            if overwritten:
                stats.overwritten_values += 1
            if skipped:
                stats.skipped_channels += 1
            if error:
                stats.errors.append(error)
            if warning:
                stats.warnings.append(warning)

    def mapping_statistics(self, mapping_name: str) -> Optional[MappingStatistics]:
        return self._statistics[StatisticsType.MAPPING].get(mapping_name)

    def all_mapping_statistics(self) -> Dict[str, MappingStatistics]:
        return dict(self._statistics[StatisticsType.MAPPING])

    def mapping_exists(self, mapping_name: str) -> bool:
        return mapping_name in self._statistics[StatisticsType.MAPPING]

    def remove_mapping(self, mapping_name: str) -> bool:
        if not self.mapping_exists(mapping_name):
            return False
        del self._statistics[StatisticsType.MAPPING][mapping_name]
        return True

    def clear_mappings(self) -> None:
        self._statistics[StatisticsType.MAPPING].clear()

    def total_mappings(self) -> int:
        return len(self._statistics[StatisticsType.MAPPING])

    def successful_mappings(self) -> int:
        return sum(s.successful_mappings for s in self.all_mapping_statistics().values())

    def failed_mappings(self) -> int:
        return sum(s.failed_mappings for s in self.all_mapping_statistics().values())

    def mapping_success_rate(self) -> float:
        total = sum(s.total_requests for s in self.all_mapping_statistics().values())
        if total == 0:
            return 0.0
        return (self.successful_mappings() / total) * 100.0

    def fastest_mapping(self) -> Optional[MappingStatistics]:
        mappings = self.all_mapping_statistics()
        if not mappings:
            return None
        return min(mappings.values(), key=lambda m: m.average_time)

    def slowest_mapping(self) -> Optional[MappingStatistics]:
        mappings = self.all_mapping_statistics()
        if not mappings:
            return None
        return max(mappings.values(), key=lambda m: m.average_time)

    def mapping_summary(self) -> Dict[str, Any]:
        mappings = self.all_mapping_statistics()
        return {
            "mapping_count": len(mappings),
            "total_requests": sum(s.total_requests for s in mappings.values()),
            "successful": self.successful_mappings(),
            "failed": self.failed_mappings(),
            "success_rate": self.mapping_success_rate(),
            "fastest": self.fastest_mapping(),
            "slowest": self.slowest_mapping(),
            "duplicates": sum(s.duplicate_targets for s in mappings.values()),
            "disabled": sum(s.disabled_mappings for s in mappings.values()),
            "unmapped": sum(s.unmapped_channels for s in mappings.values()),
        }

    def reset_mapping(self, mapping_name: str) -> bool:
        if not self.mapping_exists(mapping_name):
            return False
        self._statistics[StatisticsType.MAPPING][mapping_name] = MappingStatistics(mapping_name=mapping_name)
        return True

    def reset_all_mappings(self) -> None:
        names = list(self._statistics[StatisticsType.MAPPING].keys())
        self.clear_mappings()
        for name in names:
            self._statistics[StatisticsType.MAPPING][name] = MappingStatistics(mapping_name=name)

    # ============================================================
    # Conversion Statistics
    # ============================================================

    def record_conversion(
        self,
        conversion_name: str,
        *,
        direction: str = "forward",
        success: bool = True,
        processing_time: float = 0.0,
        input_channels: int = 0,
        output_channels: int = 0,
        unmapped: int = 0,
        disabled: int = 0,
        clipped: int = 0,
        normalized: int = 0,
        partial: bool = False,
        error: Optional[str] = None,
        warning: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return

        with self._lock:
            stats = self._statistics[StatisticsType.CONVERSION].get(conversion_name)
            if stats is None:
                stats = ConversionStatistics(conversion_name=conversion_name)
                self._statistics[StatisticsType.CONVERSION][conversion_name] = stats

            stats.total_conversions += 1
            if direction.lower() == "forward":
                stats.forward_conversions += 1
            else:
                stats.reverse_conversions += 1

            if success:
                stats.successful_conversions += 1
            else:
                stats.failed_conversions += 1

            if partial:
                stats.partial_conversions += 1

            stats.input_channels += input_channels
            stats.output_channels += output_channels
            stats.unmapped_inputs += unmapped
            stats.disabled_inputs += disabled
            stats.clipped_outputs += clipped
            stats.normalized_outputs += normalized

            stats.last_conversion = time.time()
            stats.last_processing_time = processing_time
            stats.total_processing_time += processing_time
            stats.minimum_processing_time = min(stats.minimum_processing_time, processing_time)
            stats.maximum_processing_time = max(stats.maximum_processing_time, processing_time)
            stats.average_processing_time = stats.total_processing_time / stats.total_conversions
            stats.processing_history.append(processing_time)

            if error:
                stats.errors.append(error)
            if warning:
                stats.warnings.append(warning)

    def conversion_statistics(self, conversion_name: str) -> Optional[ConversionStatistics]:
        return self._statistics[StatisticsType.CONVERSION].get(conversion_name)

    def all_conversion_statistics(self) -> Dict[str, ConversionStatistics]:
        return dict(self._statistics[StatisticsType.CONVERSION])

    def conversion_exists(self, conversion_name: str) -> bool:
        return conversion_name in self._statistics[StatisticsType.CONVERSION]

    def total_conversions(self) -> int:
        return sum(s.total_conversions for s in self.all_conversion_statistics().values())

    def successful_conversions(self) -> int:
        return sum(s.successful_conversions for s in self.all_conversion_statistics().values())

    def failed_conversions(self) -> int:
        return sum(s.failed_conversions for s in self.all_conversion_statistics().values())

    def conversion_success_rate(self) -> float:
        total = self.total_conversions()
        if total == 0:
            return 0.0
        return (self.successful_conversions() / total) * 100.0

    def fastest_conversion(self) -> Optional[ConversionStatistics]:
        convs = self.all_conversion_statistics()
        if not convs:
            return None
        return min(convs.values(), key=lambda c: c.average_processing_time)

    def slowest_conversion(self) -> Optional[ConversionStatistics]:
        convs = self.all_conversion_statistics()
        if not convs:
            return None
        return max(convs.values(), key=lambda c: c.average_processing_time)

    def conversion_summary(self) -> Dict[str, Any]:
        convs = self.all_conversion_statistics()
        return {
            "converter_count": len(convs),
            "total_conversions": self.total_conversions(),
            "successful": self.successful_conversions(),
            "failed": self.failed_conversions(),
            "success_rate": self.conversion_success_rate(),
            "forward": sum(c.forward_conversions for c in convs.values()),
            "reverse": sum(c.reverse_conversions for c in convs.values()),
            "partial": sum(c.partial_conversions for c in convs.values()),
            "fastest": self.fastest_conversion(),
            "slowest": self.slowest_conversion(),
            "unmapped_inputs": sum(c.unmapped_inputs for c in convs.values()),
            "disabled_inputs": sum(c.disabled_inputs for c in convs.values()),
            "clipped_outputs": sum(c.clipped_outputs for c in convs.values()),
            "normalized_outputs": sum(c.normalized_outputs for c in convs.values()),
        }

    def reset_conversion(self, conversion_name: str) -> bool:
        if not self.conversion_exists(conversion_name):
            return False
        self._statistics[StatisticsType.CONVERSION][conversion_name] = ConversionStatistics(
            conversion_name=conversion_name
        )
        return True

    def clear_conversions(self) -> None:
        self._statistics[StatisticsType.CONVERSION].clear()

    def reset_all_conversions(self) -> None:
        names = list(self._statistics[StatisticsType.CONVERSION].keys())
        self.clear_conversions()
        for name in names:
            self._statistics[StatisticsType.CONVERSION][name] = ConversionStatistics(conversion_name=name)

    # ============================================================
    # Runtime Statistics
    # ============================================================

    def record_runtime(
        self,
        runtime_name: str,
        *,
        processing_time: float,
        fps: float,
        queue_size: int,
        latency: float,
        processed: bool = True,
        dropped: bool = False,
        skipped: bool = False,
        duplicate: bool = False,
        invalid: bool = False,
    ) -> None:
        if not self.enabled:
            return

        with self._lock:
            stats = self._statistics[StatisticsType.RUNTIME].get(runtime_name)
            if stats is None:
                stats = RuntimeStatistics(runtime_name=runtime_name)
                self._statistics[StatisticsType.RUNTIME][runtime_name] = stats

            stats.total_frames += 1
            if processed:
                stats.processed_frames += 1
            if dropped:
                stats.dropped_frames += 1
            if skipped:
                stats.skipped_frames += 1
            if duplicate:
                stats.duplicate_frames += 1
            if invalid:
                stats.invalid_frames += 1

            now = time.time()
            stats.last_frame_time = now
            stats.last_update = now

            stats.current_fps = fps
            stats.fps_history.append(fps)
            stats.average_fps = statistics.mean(stats.fps_history)
            stats.minimum_fps = min(stats.minimum_fps, fps)
            stats.maximum_fps = max(stats.maximum_fps, fps)

            stats.total_processing_time += processing_time
            stats.processing_history.append(processing_time)
            stats.average_processing_time = stats.total_processing_time / stats.total_frames
            stats.minimum_processing_time = min(stats.minimum_processing_time, processing_time)
            stats.maximum_processing_time = max(stats.maximum_processing_time, processing_time)

            stats.queue_size = queue_size
            stats.queue_history.append(queue_size)
            stats.average_queue_size = statistics.mean(stats.queue_history)
            stats.maximum_queue_size = max(stats.maximum_queue_size, queue_size)

            stats.current_latency = latency
            stats.latency_history.append(latency)
            stats.average_latency = statistics.mean(stats.latency_history)
            stats.maximum_latency = max(stats.maximum_latency, latency)

    def runtime_statistics(self, runtime_name: str) -> Optional[RuntimeStatistics]:
        return self._statistics[StatisticsType.RUNTIME].get(runtime_name)

    def all_runtime_statistics(self) -> Dict[str, RuntimeStatistics]:
        return dict(self._statistics[StatisticsType.RUNTIME])

    def runtime_exists(self, runtime_name: str) -> bool:
        return runtime_name in self._statistics[StatisticsType.RUNTIME]

    def total_runtime_frames(self) -> int:
        return sum(r.total_frames for r in self.all_runtime_statistics().values())

    def processed_runtime_frames(self) -> int:
        return sum(r.processed_frames for r in self.all_runtime_statistics().values())

    def dropped_runtime_frames(self) -> int:
        return sum(r.dropped_frames for r in self.all_runtime_statistics().values())

    def runtime_success_rate(self) -> float:
        total = self.total_runtime_frames()
        if total == 0:
            return 0.0
        return (self.processed_runtime_frames() / total) * 100.0

    def fastest_runtime(self) -> Optional[RuntimeStatistics]:
        runtimes = self.all_runtime_statistics()
        if not runtimes:
            return None
        return min(runtimes.values(), key=lambda r: r.average_processing_time)

    def slowest_runtime(self) -> Optional[RuntimeStatistics]:
        runtimes = self.all_runtime_statistics()
        if not runtimes:
            return None
        return max(runtimes.values(), key=lambda r: r.average_processing_time)

    def runtime_summary(self) -> Dict[str, Any]:
        runtimes = self.all_runtime_statistics()
        return {
            "runtime_count": len(runtimes),
            "frames": self.total_runtime_frames(),
            "processed": self.processed_runtime_frames(),
            "dropped": self.dropped_runtime_frames(),
            "success_rate": self.runtime_success_rate(),
            "fastest": self.fastest_runtime(),
            "slowest": self.slowest_runtime(),
            "average_fps": statistics.mean([r.average_fps for r in runtimes.values()]) if runtimes else 0.0,
            "average_latency": statistics.mean([r.average_latency for r in runtimes.values()]) if runtimes else 0.0,
        }

    def reset_runtime(self, runtime_name: str) -> bool:
        if not self.runtime_exists(runtime_name):
            return False
        self._statistics[StatisticsType.RUNTIME][runtime_name] = RuntimeStatistics(runtime_name=runtime_name)
        return True

    def clear_runtime_statistics(self) -> None:
        self._statistics[StatisticsType.RUNTIME].clear()

    def reset_all_runtimes(self) -> None:
        names = list(self._statistics[StatisticsType.RUNTIME].keys())
        self.clear_runtime_statistics()
        for name in names:
            self._statistics[StatisticsType.RUNTIME][name] = RuntimeStatistics(runtime_name=name)

    # ============================================================
    # Reports
    # ============================================================

    def generate_report(self, title: str = "Statistics Report") -> StatisticsReport:
        report = StatisticsReport(title=title)
        report.summary = {
            "version": STATISTICS_VERSION,
            "status": self.status.value,
            "enabled": self.enabled,
            "uptime": self.uptime,
            "snapshots": self.total_snapshots,
            "measurements": self.total_measurements,
            "counters": self.total_counters,
        }
        report.sections = {
            "channels": self.channel_summary(),
            "mappings": self.mapping_summary(),
            "conversions": self.conversion_summary(),
            "runtime": self.runtime_summary(),
        }
        report.metadata = {
            "history_size": self.config.history_size,
            "moving_window": self.config.moving_window,
            "categories": [c.value for c in self.categories],
        }
        return report

    def report_dict(self) -> Dict[str, Any]:
        report = self.generate_report()
        return {
            "title": report.title,
            "generated_at": report.generated_datetime.isoformat(),
            "version": report.version,
            "summary": report.summary,
            "sections": report.sections,
            "metadata": report.metadata,
        }

    def report_json(self, indent: int = 4) -> str:
        return json.dumps(self.report_dict(), indent=indent, default=str)

    def save_json_report(self, filepath: Union[str, Path], indent: int = 4) -> Path:
        path = Path(filepath)
        path.write_text(self.report_json(indent), encoding="utf-8")
        return path

    def report_markdown(self) -> str:
        report = self.generate_report()
        lines = [
            f"# {report.title}",
            "",
            f"Generated: {report.generated_datetime}",
            "",
            f"Version: {report.version}",
            "",
            "## Summary",
            "",
        ]
        for key, value in report.summary.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        for section, values in report.sections.items():
            lines.append(f"## {section.title()}")
            lines.append("")
            if isinstance(values, dict):
                for k, v in values.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(str(values))
            lines.append("")
        return "\n".join(lines)

    def save_markdown_report(self, filepath: Union[str, Path]) -> Path:
        path = Path(filepath)
        path.write_text(self.report_markdown(), encoding="utf-8")
        return path

    def report_csv(self) -> str:
        rows = ["Section,Metric,Value"]
        report = self.generate_report()
        for section, values in report.sections.items():
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                rows.append(f"{section},{key},{value}")
        return "\n".join(rows)

    def save_csv_report(self, filepath: Union[str, Path]) -> Path:
        path = Path(filepath)
        path.write_text(self.report_csv(), encoding="utf-8")
        return path

    def report_text(self) -> str:
        report = self.generate_report()
        lines = [
            "=" * 70,
            report.title,
            "=" * 70,
            "",
            f"Generated : {report.generated_datetime}",
            f"Version   : {report.version}",
            f"Status    : {self.status.value}",
            "",
        ]
        for section, values in report.sections.items():
            lines.append(section.upper())
            lines.append("-" * 70)
            lines.append("")
            if isinstance(values, dict):
                for key, value in values.items():
                    lines.append(f"{key:<30} {value}")
            else:
                lines.append(str(values))
            lines.append("")
        return "\n".join(lines)

    def save_text_report(self, filepath: Union[str, Path]) -> Path:
        path = Path(filepath)
        path.write_text(self.report_text(), encoding="utf-8")
        return path

    def print_report(self) -> None:
        print(self.report_text())

    def report_summary(self) -> Dict[str, Any]:
        report = self.generate_report()
        return {
            "title": report.title,
            "generated": report.generated_datetime,
            "uptime": self.uptime,
            "status": self.status.value,
            "statistics": len(report.sections),
            "snapshots": self.total_snapshots,
        }

    def export_report(self, filepath: Union[str, Path]) -> Path:
        path = Path(filepath)
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self.save_json_report(path)
        if suffix == ".md":
            return self.save_markdown_report(path)
        if suffix == ".csv":
            return self.save_csv_report(path)
        if suffix == ".txt":
            return self.save_text_report(path)
        raise ValueError(f"Unsupported report format: {suffix}")

    # ============================================================
    # Snapshot Utilities
    # ============================================================

    def create_snapshot(
        self,
        category: StatisticsType,
        description: str = "",
    ) -> StatisticsSnapshot:
        snapshot = StatisticsSnapshot(
            category=category,
            description=description,
            values=copy.deepcopy(self._statistics.get(category, {})),
        )
        self._history.append(snapshot)
        return snapshot

    def latest_snapshot(self) -> Optional[StatisticsSnapshot]:
        if not self._history:
            return None
        return self._history[-1]

    def snapshot(self, index: int) -> Optional[StatisticsSnapshot]:
        if not self._history:
            return None
        if index < 0:
            index = len(self._history) + index
        if index < 0 or index >= len(self._history):
            return None
        return self._history[index]

    def clear_history(self) -> None:
        self._history.clear()

    # ============================================================
    # Merge Utilities
    # ============================================================

    def merge(self, other: "StatisticsManager") -> None:
        if not isinstance(other, StatisticsManager):
            raise TypeError("Expected StatisticsManager.")

        for key, value in other._counters.items():
            self._counters[key] += value

        for key, values in other._measurements.items():
            self._measurements[key].extend(values)

        self._history.extend(copy.deepcopy(other._history))

    def clone(self) -> "StatisticsManager":
        return copy.deepcopy(self)

    # ============================================================
    # Measurement Utilities
    # ============================================================

    def record_measurement(self, name: str, value: float) -> None:
        self._measurements[name].append(value)
        self._windows[name].append(value)

    def measurements(self, name: str) -> List[float]:
        return list(self._measurements.get(name, []))

    def moving_average(self, name: str) -> float:
        values = self._windows.get(name)
        if not values:
            return 0.0
        return statistics.mean(values)

    def minimum(self, name: str) -> float:
        values = self._measurements.get(name)
        if not values:
            return 0.0
        return min(values)

    def maximum(self, name: str) -> float:
        values = self._measurements.get(name)
        if not values:
            return 0.0
        return max(values)

    def average(self, name: str) -> float:
        values = self._measurements.get(name)
        if not values:
            return 0.0
        return statistics.mean(values)

    def percentile(self, name: str, percentile: float = DEFAULT_PERCENTILE) -> float:
        values = sorted(self._measurements.get(name, []))
        if not values:
            return 0.0
        k = (len(values) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return values[int(k)]
        return values[f] * (c - k) + values[c] * (k - f)

    # ============================================================
    # Counter Utilities
    # ============================================================

    def increment(self, counter: str, value: int = 1) -> None:
        self._counters[counter] += value

    def decrement(self, counter: str, value: int = 1) -> None:
        self._counters[counter] -= value

    def counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def reset_counter(self, name: str) -> None:
        self._counters[name] = 0

    # ============================================================
    # Timing Utilities
    # ============================================================

    @contextmanager
    def timer(self, measurement: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.record_measurement(measurement, elapsed)

    def timed(self, measurement: str):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = time.perf_counter() - start
                    self.record_measurement(measurement, elapsed)
            return wrapper
        return decorator

    # ============================================================
    # Benchmark Utilities
    # ============================================================

    def benchmark(
        self,
        func: Callable,
        *args,
        iterations: int = 100,
        **kwargs,
    ) -> Dict[str, float]:
        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            timings.append(time.perf_counter() - start)
        return {
            "iterations": iterations,
            "minimum": min(timings),
            "maximum": max(timings),
            "average": statistics.mean(timings),
            "median": statistics.median(timings),
            "stdev": statistics.stdev(timings) if len(timings) > 1 else 0.0,
        }

    # ============================================================
    # Reset Utilities
    # ============================================================

    def reset(self) -> None:
        self._history.clear()
        self._statistics.clear()
        self._measurements.clear()
        self._windows.clear()
        self._counters.clear()
        self._operation_counts.clear()
        self.summary = StatisticsSummary()
        self._status = StatisticStatus.ACTIVE

    def pause(self) -> None:
        self._status = StatisticStatus.PAUSED

    def resume(self) -> None:
        self._status = StatisticStatus.ACTIVE

    def stop(self) -> None:
        self._status = StatisticStatus.STOPPED
        self.summary.last_update = time.time()

    def __len__(self) -> int:
        return len(self._history)

    def __contains__(self, category: StatisticsType) -> bool:
        return category in self._statistics

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status={self.status.value!r}, "
            f"categories={len(self.categories)}, "
            f"snapshots={len(self._history)}, "
            f"uptime={self.uptime:.2f}s)"
        )