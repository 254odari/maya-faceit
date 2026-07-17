"""
cache/cache_statistics.py

Central Analytics and Performance Monitoring System for the Cache Framework.

This module collects, aggregates, analyzes, and reports statistics about cache
performance from all cache modules (MemoryCache, DiskCache, MeshCache, etc.).
It does not store cache data itself; it only tracks metrics.

Responsibilities:
- Record cache operations: hits, misses, reads, writes, updates, deletes, evictions, expirations.
- Track performance metrics: average lookup time, save time, load time, etc.
- Monitor memory usage: RAM usage, peak memory, object count.
- Monitor disk usage: disk usage, compressed size, file count.
- Time serialization, compression, cleanup, and validation.
- Generate aggregated reports per cache and globally.
- Export reports in multiple formats (JSON, CSV, Markdown, HTML).
- Provide benchmarking and diagnostic tools.

Dependencies:
- dataclasses, collections, statistics, time, threading, json, csv, pathlib, typing.
- No Maya or cache-specific imports.
"""

from __future__ import annotations

import csv
import json
import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable, Iterator

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class StatisticType(Enum):
    """Types of statistics counters."""
    HITS = "hits"
    MISSES = "misses"
    READS = "reads"
    WRITES = "writes"
    UPDATES = "updates"
    DELETES = "deletes"
    EVICTIONS = "evictions"
    EXPIRATIONS = "expirations"


class MetricCategory(Enum):
    """Categories for metrics."""
    MEMORY = "memory"
    DISK = "disk"
    SERIALIZATION = "serialization"
    PERFORMANCE = "performance"
    RUNTIME = "runtime"


class ReportFormat(Enum):
    """Export formats for reports."""
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class CacheMetrics:
    """Metrics for a single cache."""
    name: str
    cache_type: str
    hits: int = 0
    misses: int = 0
    reads: int = 0
    writes: int = 0
    updates: int = 0
    deletes: int = 0
    evictions: int = 0
    expirations: int = 0
    object_count: int = 0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    disk_usage_mb: float = 0.0
    peak_disk_mb: float = 0.0
    lookup_times: List[float] = field(default_factory=list)
    save_times: List[float] = field(default_factory=list)
    load_times: List[float] = field(default_factory=list)
    serialization_times: List[float] = field(default_factory=list)
    compression_times: List[float] = field(default_factory=list)
    cleanup_times: List[float] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def average_lookup_time(self) -> float:
        if not self.lookup_times:
            return 0.0
        return statistics.mean(self.lookup_times)

    @property
    def max_lookup_time(self) -> float:
        if not self.lookup_times:
            return 0.0
        return max(self.lookup_times)

    @property
    def average_save_time(self) -> float:
        if not self.save_times:
            return 0.0
        return statistics.mean(self.save_times)

    @property
    def average_load_time(self) -> float:
        if not self.load_times:
            return 0.0
        return statistics.mean(self.load_times)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cache_type": self.cache_type,
            "hits": self.hits,
            "misses": self.misses,
            "reads": self.reads,
            "writes": self.writes,
            "updates": self.updates,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "object_count": self.object_count,
            "memory_usage_mb": self.memory_usage_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "disk_usage_mb": self.disk_usage_mb,
            "peak_disk_mb": self.peak_disk_mb,
            "hit_rate": self.hit_rate,
            "avg_lookup_ms": self.average_lookup_time * 1000,
            "max_lookup_ms": self.max_lookup_time * 1000,
            "avg_save_ms": self.average_save_time * 1000,
            "avg_load_ms": self.average_load_time * 1000,
            "lookup_samples": len(self.lookup_times),
            "save_samples": len(self.save_times),
            "load_samples": len(self.load_times),
        }


@dataclass
class AggregatedStatistics:
    """Aggregated statistics across all caches."""
    total_hits: int = 0
    total_misses: int = 0
    total_reads: int = 0
    total_writes: int = 0
    total_updates: int = 0
    total_deletes: int = 0
    total_evictions: int = 0
    total_expirations: int = 0
    total_objects: int = 0
    total_memory_mb: float = 0.0
    total_disk_mb: float = 0.0
    peak_memory_mb: float = 0.0
    peak_disk_mb: float = 0.0
    global_hit_rate: float = 0.0
    cache_metrics: List[CacheMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "total_reads": self.total_reads,
            "total_writes": self.total_writes,
            "total_updates": self.total_updates,
            "total_deletes": self.total_deletes,
            "total_evictions": self.total_evictions,
            "total_expirations": self.total_expirations,
            "total_objects": self.total_objects,
            "total_memory_mb": self.total_memory_mb,
            "total_disk_mb": self.total_disk_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_disk_mb": self.peak_disk_mb,
            "global_hit_rate": self.global_hit_rate,
            "caches": [c.to_dict() for c in self.cache_metrics],
        }


# ---- Part 4: Statistics Manager ---------------------------------------

class CacheStatisticsManager:
    """
    Central manager for collecting and reporting cache statistics.

    This is a singleton that all cache modules should use to record events.
    """

    _instance: Optional[CacheStatisticsManager] = None

    def __new__(cls) -> CacheStatisticsManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # Per-cache metrics: cache_name -> CacheMetrics
        self._cache_metrics: Dict[str, CacheMetrics] = {}
        self._lock = threading.RLock()

        # Global aggregated statistics (computed on demand)
        self._global_stats: Optional[AggregatedStatistics] = None
        self._dirty = False

        # Timing for overall session
        self._session_start = time.time()
        self._session_ops = 0

        # Benchmark results
        self._benchmarks: Dict[str, Dict[str, float]] = {}

        logger.debug("CacheStatisticsManager initialized")

    # ---- Record Methods ----

    def record_hit(self, cache_name: str) -> None:
        """Record a cache hit."""
        with self._lock:
            self._get_metrics(cache_name).hits += 1
            self._dirty = True

    def record_miss(self, cache_name: str) -> None:
        """Record a cache miss."""
        with self._lock:
            self._get_metrics(cache_name).misses += 1
            self._dirty = True

    def record_read(self, cache_name: str) -> None:
        """Record a cache read operation."""
        with self._lock:
            self._get_metrics(cache_name).reads += 1
            self._dirty = True

    def record_write(self, cache_name: str) -> None:
        """Record a cache write operation."""
        with self._lock:
            self._get_metrics(cache_name).writes += 1
            self._dirty = True

    def record_update(self, cache_name: str) -> None:
        """Record a cache update operation."""
        with self._lock:
            self._get_metrics(cache_name).updates += 1
            self._dirty = True

    def record_delete(self, cache_name: str) -> None:
        """Record a cache delete operation."""
        with self._lock:
            self._get_metrics(cache_name).deletes += 1
            self._dirty = True

    def record_eviction(self, cache_name: str) -> None:
        """Record a cache eviction."""
        with self._lock:
            self._get_metrics(cache_name).evictions += 1
            self._dirty = True

    def record_expiration(self, cache_name: str) -> None:
        """Record a cache expiration."""
        with self._lock:
            self._get_metrics(cache_name).expirations += 1
            self._dirty = True

    def record_object_count(self, cache_name: str, count: int) -> None:
        """Record the current number of objects in a cache."""
        with self._lock:
            self._get_metrics(cache_name).object_count = count
            self._dirty = True

    def record_memory_usage(self, cache_name: str, usage_mb: float) -> None:
        """Record memory usage for a cache."""
        with self._lock:
            metrics = self._get_metrics(cache_name)
            metrics.memory_usage_mb = usage_mb
            if usage_mb > metrics.peak_memory_mb:
                metrics.peak_memory_mb = usage_mb
            self._dirty = True

    def record_disk_usage(self, cache_name: str, usage_mb: float) -> None:
        """Record disk usage for a cache."""
        with self._lock:
            metrics = self._get_metrics(cache_name)
            metrics.disk_usage_mb = usage_mb
            if usage_mb > metrics.peak_disk_mb:
                metrics.peak_disk_mb = usage_mb
            self._dirty = True

    def record_lookup_time(self, cache_name: str, seconds: float) -> None:
        """Record the time taken for a cache lookup."""
        with self._lock:
            self._get_metrics(cache_name).lookup_times.append(seconds)
            self._dirty = True

    def record_save_time(self, cache_name: str, seconds: float) -> None:
        """Record the time taken to save to cache."""
        with self._lock:
            self._get_metrics(cache_name).save_times.append(seconds)
            self._dirty = True

    def record_load_time(self, cache_name: str, seconds: float) -> None:
        """Record the time taken to load from cache."""
        with self._lock:
            self._get_metrics(cache_name).load_times.append(seconds)
            self._dirty = True

    def record_serialization_time(self, cache_name: str, seconds: float) -> None:
        """Record serialization time."""
        with self._lock:
            self._get_metrics(cache_name).serialization_times.append(seconds)
            self._dirty = True

    def record_compression_time(self, cache_name: str, seconds: float) -> None:
        """Record compression time."""
        with self._lock:
            self._get_metrics(cache_name).compression_times.append(seconds)
            self._dirty = True

    def record_cleanup_time(self, cache_name: str, seconds: float) -> None:
        """Record cleanup time."""
        with self._lock:
            self._get_metrics(cache_name).cleanup_times.append(seconds)
            self._dirty = True

    # ---- Internal Helper ----

    def _get_metrics(self, cache_name: str) -> CacheMetrics:
        """Get or create metrics for a cache."""
        if cache_name not in self._cache_metrics:
            # Default type is inferred from name (could be improved)
            cache_type = "unknown"
            if "mesh" in cache_name.lower():
                cache_type = "mesh"
            elif "blendshape" in cache_name.lower():
                cache_type = "blendshape"
            elif "landmark" in cache_name.lower():
                cache_type = "landmark"
            elif "project" in cache_name.lower():
                cache_type = "project"
            elif "memory" in cache_name.lower():
                cache_type = "memory"
            elif "disk" in cache_name.lower():
                cache_type = "disk"
            self._cache_metrics[cache_name] = CacheMetrics(
                name=cache_name,
                cache_type=cache_type,
            )
        return self._cache_metrics[cache_name]

    # ---- Aggregation ----

    def get_metrics(self, cache_name: str) -> Optional[CacheMetrics]:
        """Return metrics for a specific cache."""
        with self._lock:
            return self._cache_metrics.get(cache_name)

    def get_all_metrics(self) -> List[CacheMetrics]:
        """Return metrics for all caches."""
        with self._lock:
            return list(self._cache_metrics.values())

    def get_aggregated(self) -> AggregatedStatistics:
        """Compute aggregated statistics across all caches."""
        with self._lock:
            if not self._dirty and self._global_stats is not None:
                return self._global_stats

            metrics_list = list(self._cache_metrics.values())
            agg = AggregatedStatistics(
                cache_metrics=metrics_list.copy(),
            )

            for m in metrics_list:
                agg.total_hits += m.hits
                agg.total_misses += m.misses
                agg.total_reads += m.reads
                agg.total_writes += m.writes
                agg.total_updates += m.updates
                agg.total_deletes += m.deletes
                agg.total_evictions += m.evictions
                agg.total_expirations += m.expirations
                agg.total_objects += m.object_count
                agg.total_memory_mb += m.memory_usage_mb
                agg.total_disk_mb += m.disk_usage_mb
                if m.peak_memory_mb > agg.peak_memory_mb:
                    agg.peak_memory_mb = m.peak_memory_mb
                if m.peak_disk_mb > agg.peak_disk_mb:
                    agg.peak_disk_mb = m.peak_disk_mb

            total_requests = agg.total_hits + agg.total_misses
            if total_requests > 0:
                agg.global_hit_rate = agg.total_hits / total_requests
            else:
                agg.global_hit_rate = 0.0

            self._global_stats = agg
            self._dirty = False
            return agg

    # ---- Reporting ----

    def generate_report(
        self,
        format: ReportFormat = ReportFormat.TEXT,
        include_timings: bool = True,
        include_memory: bool = True,
        include_disk: bool = True,
    ) -> str:
        """
        Generate a formatted report of cache statistics.

        Args:
            format: Output format (text, json, csv, html, markdown).
            include_timings: Include timing metrics.
            include_memory: Include memory metrics.
            include_disk: Include disk metrics.

        Returns:
            Formatted report string.
        """
        agg = self.get_aggregated()
        if format == ReportFormat.JSON:
            return self._format_json(agg, include_timings, include_memory, include_disk)
        elif format == ReportFormat.CSV:
            return self._format_csv(agg, include_timings, include_memory, include_disk)
        elif format == ReportFormat.MARKDOWN:
            return self._format_markdown(agg, include_timings, include_memory, include_disk)
        elif format == ReportFormat.HTML:
            return self._format_html(agg, include_timings, include_memory, include_disk)
        else:  # TEXT
            return self._format_text(agg, include_timings, include_memory, include_disk)

    def _format_text(self, agg: AggregatedStatistics, include_timings: bool, include_memory: bool, include_disk: bool) -> str:
        lines = []
        lines.append("Cache Statistics Report")
        lines.append("=" * 40)
        lines.append(f"Session Duration: {time.time() - self._session_start:.2f}s")
        lines.append("")

        # Global summary
        lines.append("Global Summary")
        lines.append("-" * 20)
        lines.append(f"Total Hits:        {agg.total_hits}")
        lines.append(f"Total Misses:      {agg.total_misses}")
        lines.append(f"Global Hit Rate:   {agg.global_hit_rate*100:.2f}%")
        lines.append(f"Total Reads:       {agg.total_reads}")
        lines.append(f"Total Writes:      {agg.total_writes}")
        lines.append(f"Total Updates:     {agg.total_updates}")
        lines.append(f"Total Deletes:     {agg.total_deletes}")
        lines.append(f"Total Evictions:   {agg.total_evictions}")
        lines.append(f"Total Expirations: {agg.total_expirations}")
        lines.append("")

        if include_memory:
            lines.append("Memory Usage")
            lines.append("-" * 20)
            lines.append(f"Total Memory:      {agg.total_memory_mb:.2f} MB")
            lines.append(f"Peak Memory:       {agg.peak_memory_mb:.2f} MB")
            lines.append(f"Total Objects:     {agg.total_objects}")
            lines.append("")

        if include_disk:
            lines.append("Disk Usage")
            lines.append("-" * 20)
            lines.append(f"Total Disk:        {agg.total_disk_mb:.2f} MB")
            lines.append(f"Peak Disk:         {agg.peak_disk_mb:.2f} MB")
            lines.append("")

        # Per-cache details
        lines.append("Per-Cache Details")
        lines.append("-" * 20)
        for m in agg.cache_metrics:
            lines.append(f"\nCache: {m.name} ({m.cache_type})")
            lines.append(f"  Hits: {m.hits}, Misses: {m.misses}, Hit Rate: {m.hit_rate*100:.2f}%")
            lines.append(f"  Reads: {m.reads}, Writes: {m.writes}, Updates: {m.updates}")
            lines.append(f"  Deletes: {m.deletes}, Evictions: {m.evictions}, Expirations: {m.expirations}")
            if include_memory:
                lines.append(f"  Memory: {m.memory_usage_mb:.2f} MB (Peak: {m.peak_memory_mb:.2f} MB), Objects: {m.object_count}")
            if include_disk:
                lines.append(f"  Disk: {m.disk_usage_mb:.2f} MB (Peak: {m.peak_disk_mb:.2f} MB)")
            if include_timings:
                lines.append(f"  Avg Lookup: {m.average_lookup_time*1000:.3f} ms, Max: {m.max_lookup_time*1000:.3f} ms")
                lines.append(f"  Avg Save: {m.average_save_time*1000:.3f} ms, Avg Load: {m.average_load_time*1000:.3f} ms")
                if m.serialization_times:
                    avg_ser = statistics.mean(m.serialization_times) if m.serialization_times else 0
                    lines.append(f"  Avg Serialization: {avg_ser*1000:.3f} ms")
                if m.compression_times:
                    avg_comp = statistics.mean(m.compression_times) if m.compression_times else 0
                    lines.append(f"  Avg Compression: {avg_comp*1000:.3f} ms")

        return "\n".join(lines)

    def _format_json(self, agg: AggregatedStatistics, include_timings: bool, include_memory: bool, include_disk: bool) -> str:
        data = agg.to_dict()
        # Filter fields based on flags
        if not include_timings:
            for c in data["caches"]:
                c.pop("avg_lookup_ms", None)
                c.pop("max_lookup_ms", None)
                c.pop("avg_save_ms", None)
                c.pop("avg_load_ms", None)
                c.pop("lookup_samples", None)
                c.pop("save_samples", None)
                c.pop("load_samples", None)
        if not include_memory:
            for c in data["caches"]:
                c.pop("memory_usage_mb", None)
                c.pop("peak_memory_mb", None)
                c.pop("object_count", None)
            data.pop("total_memory_mb", None)
            data.pop("peak_memory_mb", None)
            data.pop("total_objects", None)
        if not include_disk:
            for c in data["caches"]:
                c.pop("disk_usage_mb", None)
                c.pop("peak_disk_mb", None)
            data.pop("total_disk_mb", None)
            data.pop("peak_disk_mb", None)
        return json.dumps(data, indent=2)

    def _format_csv(self, agg: AggregatedStatistics, include_timings: bool, include_memory: bool, include_disk: bool) -> str:
        import io
        output = io.StringIO()
        fieldnames = ["name", "type", "hits", "misses", "hit_rate", "reads", "writes",
                     "updates", "deletes", "evictions", "expirations"]
        if include_memory:
            fieldnames.extend(["memory_mb", "peak_memory_mb", "objects"])
        if include_disk:
            fieldnames.extend(["disk_mb", "peak_disk_mb"])
        if include_timings:
            fieldnames.extend(["avg_lookup_ms", "max_lookup_ms", "avg_save_ms", "avg_load_ms"])
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for m in agg.cache_metrics:
            row = {
                "name": m.name,
                "type": m.cache_type,
                "hits": m.hits,
                "misses": m.misses,
                "hit_rate": f"{m.hit_rate*100:.2f}%",
                "reads": m.reads,
                "writes": m.writes,
                "updates": m.updates,
                "deletes": m.deletes,
                "evictions": m.evictions,
                "expirations": m.expirations,
            }
            if include_memory:
                row["memory_mb"] = f"{m.memory_usage_mb:.2f}"
                row["peak_memory_mb"] = f"{m.peak_memory_mb:.2f}"
                row["objects"] = m.object_count
            if include_disk:
                row["disk_mb"] = f"{m.disk_usage_mb:.2f}"
                row["peak_disk_mb"] = f"{m.peak_disk_mb:.2f}"
            if include_timings:
                row["avg_lookup_ms"] = f"{m.average_lookup_time*1000:.3f}"
                row["max_lookup_ms"] = f"{m.max_lookup_time*1000:.3f}"
                row["avg_save_ms"] = f"{m.average_save_time*1000:.3f}"
                row["avg_load_ms"] = f"{m.average_load_time*1000:.3f}"
            writer.writerow(row)
        return output.getvalue()

    def _format_markdown(self, agg: AggregatedStatistics, include_timings: bool, include_memory: bool, include_disk: bool) -> str:
        lines = ["# Cache Statistics Report", ""]
        lines.append(f"**Session Duration:** {time.time() - self._session_start:.2f}s")
        lines.append("")

        lines.append("## Global Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Hits | {agg.total_hits} |")
        lines.append(f"| Total Misses | {agg.total_misses} |")
        lines.append(f"| Global Hit Rate | {agg.global_hit_rate*100:.2f}% |")
        lines.append(f"| Total Reads | {agg.total_reads} |")
        lines.append(f"| Total Writes | {agg.total_writes} |")
        if include_memory:
            lines.append(f"| Total Memory | {agg.total_memory_mb:.2f} MB |")
            lines.append(f"| Peak Memory | {agg.peak_memory_mb:.2f} MB |")
            lines.append(f"| Total Objects | {agg.total_objects} |")
        if include_disk:
            lines.append(f"| Total Disk | {agg.total_disk_mb:.2f} MB |")
            lines.append(f"| Peak Disk | {agg.peak_disk_mb:.2f} MB |")
        lines.append("")

        lines.append("## Per-Cache Details")
        lines.append("")
        # Build a table
        headers = ["Cache", "Type", "Hits", "Misses", "Hit Rate", "Reads", "Writes"]
        if include_memory:
            headers.extend(["Memory (MB)", "Peak (MB)", "Objects"])
        if include_disk:
            headers.extend(["Disk (MB)", "Peak (MB)"])
        if include_timings:
            headers.extend(["Avg Lookup (ms)", "Max Lookup (ms)", "Avg Save (ms)", "Avg Load (ms)"])
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
        for m in agg.cache_metrics:
            row = [
                m.name,
                m.cache_type,
                str(m.hits),
                str(m.misses),
                f"{m.hit_rate*100:.2f}%",
                str(m.reads),
                str(m.writes),
            ]
            if include_memory:
                row.extend([f"{m.memory_usage_mb:.2f}", f"{m.peak_memory_mb:.2f}", str(m.object_count)])
            if include_disk:
                row.extend([f"{m.disk_usage_mb:.2f}", f"{m.peak_disk_mb:.2f}"])
            if include_timings:
                row.extend([
                    f"{m.average_lookup_time*1000:.3f}",
                    f"{m.max_lookup_time*1000:.3f}",
                    f"{m.average_save_time*1000:.3f}",
                    f"{m.average_load_time*1000:.3f}",
                ])
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def _format_html(self, agg: AggregatedStatistics, include_timings: bool, include_memory: bool, include_disk: bool) -> str:
        lines = []
        lines.append("<!DOCTYPE html><html><head><title>Cache Statistics</title>")
        lines.append("<style>table { border-collapse: collapse; width: 100%; }")
        lines.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        lines.append("th { background-color: #4CAF50; color: white; }")
        lines.append("tr:nth-child(even) { background-color: #f2f2f2; }")
        lines.append("</style></head><body>")
        lines.append(f"<h1>Cache Statistics Report</h1>")
        lines.append(f"<p><strong>Session Duration:</strong> {time.time() - self._session_start:.2f}s</p>")

        lines.append("<h2>Global Summary</h2><ul>")
        lines.append(f"<li>Total Hits: {agg.total_hits}</li>")
        lines.append(f"<li>Total Misses: {agg.total_misses}</li>")
        lines.append(f"<li>Global Hit Rate: {agg.global_hit_rate*100:.2f}%</li>")
        if include_memory:
            lines.append(f"<li>Total Memory: {agg.total_memory_mb:.2f} MB</li>")
            lines.append(f"<li>Peak Memory: {agg.peak_memory_mb:.2f} MB</li>")
            lines.append(f"<li>Total Objects: {agg.total_objects}</li>")
        if include_disk:
            lines.append(f"<li>Total Disk: {agg.total_disk_mb:.2f} MB</li>")
            lines.append(f"<li>Peak Disk: {agg.peak_disk_mb:.2f} MB</li>")
        lines.append("</ul>")

        lines.append("<h2>Per-Cache Details</h2>")
        headers = ["Cache", "Type", "Hits", "Misses", "Hit Rate", "Reads", "Writes"]
        if include_memory:
            headers.extend(["Memory (MB)", "Peak (MB)", "Objects"])
        if include_disk:
            headers.extend(["Disk (MB)", "Peak (MB)"])
        if include_timings:
            headers.extend(["Avg Lookup (ms)", "Max Lookup (ms)", "Avg Save (ms)", "Avg Load (ms)"])
        lines.append("<table><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
        for m in agg.cache_metrics:
            row = [m.name, m.cache_type, str(m.hits), str(m.misses), f"{m.hit_rate*100:.2f}%",
                   str(m.reads), str(m.writes)]
            if include_memory:
                row.extend([f"{m.memory_usage_mb:.2f}", f"{m.peak_memory_mb:.2f}", str(m.object_count)])
            if include_disk:
                row.extend([f"{m.disk_usage_mb:.2f}", f"{m.peak_disk_mb:.2f}"])
            if include_timings:
                row.extend([
                    f"{m.average_lookup_time*1000:.3f}",
                    f"{m.max_lookup_time*1000:.3f}",
                    f"{m.average_save_time*1000:.3f}",
                    f"{m.average_load_time*1000:.3f}",
                ])
            lines.append("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>")
        lines.append("</table></body></html>")
        return "\n".join(lines)

    # ---- Export ----

    def export(self, filepath: Union[str, Path], format: ReportFormat = ReportFormat.JSON) -> None:
        """
        Export the current statistics report to a file.

        Args:
            filepath: Path to output file.
            format: Output format.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_report(format)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Exported cache statistics to {path}")

    # ---- Reset ----

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._cache_metrics.clear()
            self._global_stats = None
            self._dirty = False
            self._session_start = time.time()
            self._benchmarks.clear()
            logger.debug("Cache statistics reset")

    # ---- Benchmarking ----

    def record_benchmark(self, name: str, value: float, unit: str = "s") -> None:
        """Record a benchmark result."""
        if name not in self._benchmarks:
            self._benchmarks[name] = {}
        self._benchmarks[name]["value"] = value
        self._benchmarks[name]["unit"] = unit
        self._benchmarks[name]["timestamp"] = time.time()

    def get_benchmark(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a benchmark result."""
        return self._benchmarks.get(name)

    def get_benchmarks(self) -> Dict[str, Dict[str, Any]]:
        """Get all benchmark results."""
        return dict(self._benchmarks)


# ---- Part 14: Utilities ----------------------------------------------

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a value as a percentage string."""
    return f"{value*100:.{decimals}f}%"


def format_size_mb(value: float) -> str:
    """Format a size in MB with appropriate units."""
    if value < 1:
        return f"{value*1024:.2f} KB"
    elif value < 1024:
        return f"{value:.2f} MB"
    else:
        return f"{value/1024:.2f} GB"


def format_time_ms(value: float) -> str:
    """Format time in milliseconds."""
    return f"{value*1000:.3f} ms"


# ---- Part 15: Public API -----------------------------------------------

__all__ = [
    "CacheStatisticsManager",
    "CacheMetrics",
    "AggregatedStatistics",
    "StatisticType",
    "MetricCategory",
    "ReportFormat",
    "format_percentage",
    "format_size_mb",
    "format_time_ms",
]