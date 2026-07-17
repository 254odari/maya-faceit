"""
models.py

Data models for the converter.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from ..channels import ARKitChannel
from ..mapping import ARKitMapping, RigTarget


@dataclass(slots=True)
class CompiledMapping:
    """
    Cached mapping for a single ARKit channel.
    """

    channel: ARKitChannel
    mapping: ARKitMapping
    targets: List[RigTarget]


@dataclass(slots=True)
class ConverterStatistics:
    """
    Runtime statistics collected by the converter.
    """

    converted_frames: int = 0
    converted_channels: int = 0
    converted_targets: int = 0
    calibration_calls: int = 0
    merge_operations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    reverse_conversions: int = 0
    validation_runs: int = 0
    errors: int = 0
    warnings: int = 0

    def reset(self) -> None:
        """Reset all counters to zero."""
        self.converted_frames = 0
        self.converted_channels = 0
        self.converted_targets = 0
        self.calibration_calls = 0
        self.merge_operations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.reverse_conversions = 0
        self.validation_runs = 0
        self.errors = 0
        self.warnings = 0

    def serialize(self) -> dict:
        return {
            "converted_frames": self.converted_frames,
            "converted_channels": self.converted_channels,
            "converted_targets": self.converted_targets,
            "calibration_calls": self.calibration_calls,
            "merge_operations": self.merge_operations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "reverse_conversions": self.reverse_conversions,
            "validation_runs": self.validation_runs,
            "errors": self.errors,
            "warnings": self.warnings,
        }