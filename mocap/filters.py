"""
mocap/filters.py

Various filters for mocap data.

Provides a collection of filters for cleaning and processing facial tracking data:
- Noise reduction (threshold-based)
- Jitter removal (outlier detection and smoothing)
- Median filter (outlier removal)
- Low-pass filter (smoothing)
- Filter chain for composing multiple filters

All filters operate on coefficient dictionaries and can be chained together.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class FilterError(Exception):
    """Base exception for filter operations."""
    pass


# ---- Data Models ----

@dataclass
class FilterSettings:
    """
    Settings for filters.
    """
    noise_threshold: float = 0.01          # Threshold for noise reduction
    jitter_window: int = 3                 # Window size for jitter detection
    low_pass_cutoff: float = 0.5           # Cutoff frequency for low-pass filter (0-1)
    median_window: int = 3                 # Window size for median filter
    outlier_std_threshold: float = 2.0     # Standard deviation threshold for outlier detection


# ---- Filter Base ----

class FilterBase:
    """
    Base class for all filters.

    All filters should inherit from this and implement the apply() method.
    """

    def __init__(self, settings: Optional[FilterSettings] = None):
        """
        Initialize the filter.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or FilterSettings()
        self._name = self.__class__.__name__

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        """
        Apply the filter to a frame.

        Args:
            frame: Coefficients to filter.

        Returns:
            Filtered coefficients.
        """
        raise NotImplementedError(f"{self._name}.apply() must be implemented")

    def apply_batch(self, frames: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Apply the filter to a batch of frames.

        Args:
            frames: List of frames.

        Returns:
            List of filtered frames.
        """
        return [self.apply(f) for f in frames]

    def get_name(self) -> str:
        """Get the filter name."""
        return self._name

    def get_settings(self) -> FilterSettings:
        """Get current settings."""
        return self.settings

    def set_settings(self, settings: FilterSettings) -> None:
        """Update settings."""
        self.settings = settings


# ---- Specific Filters ----

class NoiseReductionFilter(FilterBase):
    """
    Reduce noise by zeroing out small values.

    Any value below the noise threshold is set to 0.
    """

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        threshold = self.settings.noise_threshold
        result = {}
        for ch, val in frame.items():
            if abs(val) < threshold:
                result[ch] = 0.0
            else:
                result[ch] = val
        return result


class JitterFilter(FilterBase):
    """
    Remove jitter by detecting outliers and smoothing them.

    Uses a moving window to detect values that deviate significantly
    from the local average and smooths them.
    """

    def __init__(self, settings: Optional[FilterSettings] = None):
        super().__init__(settings)
        self._history: List[Dict[str, float]] = []

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        self._history.append(frame.copy())
        if len(self._history) > self.settings.jitter_window * 2:
            self._history.pop(0)

        if len(self._history) < 2:
            return frame.copy()

        window = min(self.settings.jitter_window, len(self._history))
        recent = self._history[-window:]

        result = {}
        all_channels = set()
        for f in recent:
            all_channels.update(f.keys())

        for ch in all_channels:
            values = [f.get(ch, 0.0) for f in recent]
            mean = sum(values) / len(values)
            std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)) if len(values) > 1 else 0.0

            # Current value
            current = frame.get(ch, 0.0)

            if std > 0.001:
                # Check if current value is an outlier
                if abs(current - mean) > self.settings.outlier_std_threshold * std:
                    # Replace with mean (or smoothed value)
                    result[ch] = mean
                else:
                    result[ch] = current
            else:
                result[ch] = current

        return result

    def reset(self) -> None:
        """Reset the filter history."""
        self._history = []


class MedianFilter(FilterBase):
    """
    Apply median filter to remove outliers.

    Uses a sliding window and takes the median value for each channel.
    """

    def __init__(self, settings: Optional[FilterSettings] = None):
        super().__init__(settings)
        self._history: List[Dict[str, float]] = []

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        self._history.append(frame.copy())
        if len(self._history) > self.settings.median_window * 2:
            self._history.pop(0)

        if len(self._history) < 2:
            return frame.copy()

        window = min(self.settings.median_window, len(self._history))
        recent = self._history[-window:]

        result = {}
        all_channels = set()
        for f in recent:
            all_channels.update(f.keys())

        for ch in all_channels:
            values = sorted([f.get(ch, 0.0) for f in recent])
            mid = len(values) // 2
            if len(values) % 2 == 0:
                result[ch] = (values[mid - 1] + values[mid]) / 2
            else:
                result[ch] = values[mid]

        return result

    def reset(self) -> None:
        """Reset the filter history."""
        self._history = []


class LowPassFilter(FilterBase):
    """
    Apply low-pass filter to smooth data.

    Uses exponential smoothing with a cutoff frequency parameter.
    Higher cutoff = more responsive, lower cutoff = smoother.
    """

    def __init__(self, settings: Optional[FilterSettings] = None):
        super().__init__(settings)
        self._prev: Dict[str, float] = {}

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        cutoff = self.settings.low_pass_cutoff
        # Clamp cutoff to [0, 1]
        cutoff = max(0.0, min(1.0, cutoff))

        result = {}
        for ch, val in frame.items():
            prev_val = self._prev.get(ch, val)
            # Low-pass: new = cutoff * current + (1 - cutoff) * previous
            result[ch] = cutoff * val + (1 - cutoff) * prev_val

        self._prev = result.copy()
        return result

    def reset(self) -> None:
        """Reset the filter state."""
        self._prev = {}


class ClampFilter(FilterBase):
    """
    Clamp values to a specified range.

    Default range is [0, 1].
    """

    def __init__(self, settings: Optional[FilterSettings] = None, min_val: float = 0.0, max_val: float = 1.0):
        super().__init__(settings)
        self.min_val = min_val
        self.max_val = max_val

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        result = {}
        for ch, val in frame.items():
            if val < self.min_val:
                result[ch] = self.min_val
            elif val > self.max_val:
                result[ch] = self.max_val
            else:
                result[ch] = val
        return result


class NormalizeFilter(FilterBase):
    """
    Normalize weights to sum to 1.0.

    This ensures that all coefficients sum to approximately 1.0,
    which is useful for blendshape systems.
    """

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        total = sum(frame.values())
        if total == 0:
            return frame.copy()
        return {ch: val / total for ch, val in frame.items()}


class ScaleFilter(FilterBase):
    """
    Scale all values by a factor.

    Useful for adjusting overall intensity.
    """

    def __init__(self, settings: Optional[FilterSettings] = None, scale: float = 1.0):
        super().__init__(settings)
        self._scale = scale

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        if self._scale == 1.0:
            return frame.copy()
        return {ch: val * self._scale for ch, val in frame.items()}

    def set_scale(self, scale: float) -> None:
        """Update the scale factor."""
        self._scale = scale


class BiasFilter(FilterBase):
    """
    Add a bias to all values.

    Useful for adjusting neutral pose.
    """

    def __init__(self, settings: Optional[FilterSettings] = None, bias: float = 0.0):
        super().__init__(settings)
        self._bias = bias

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        if self._bias == 0.0:
            return frame.copy()
        return {ch: val + self._bias for ch, val in frame.items()}

    def set_bias(self, bias: float) -> None:
        """Update the bias."""
        self._bias = bias


# ---- Filter Chain ----

class FilterChain(FilterBase):
    """
    Chain multiple filters together.

    Filters are applied in the order they are added.

    Usage:
        chain = FilterChain()
        chain.add(NoiseReductionFilter())
        chain.add(MedianFilter())
        chain.add(LowPassFilter())
        result = chain.apply(frame)
    """

    def __init__(self, filters: Optional[List[FilterBase]] = None, settings: Optional[FilterSettings] = None):
        super().__init__(settings)
        self._filters = filters or []

    def add(self, filter_obj: FilterBase) -> None:
        """Add a filter to the chain."""
        self._filters.append(filter_obj)
        logger.debug(f"Added filter '{filter_obj.get_name()}' to chain")

    def remove(self, filter_name: str) -> bool:
        """Remove a filter by name."""
        for i, f in enumerate(self._filters):
            if f.get_name() == filter_name:
                del self._filters[i]
                return True
        return False

    def clear(self) -> None:
        """Remove all filters from the chain."""
        self._filters = []

    def apply(self, frame: Dict[str, float]) -> Dict[str, float]:
        result = frame.copy()
        for filter_obj in self._filters:
            result = filter_obj.apply(result)
        return result

    def get_filters(self) -> List[FilterBase]:
        """Get the list of filters in the chain."""
        return self._filters.copy()

    def get_filter_names(self) -> List[str]:
        """Get the names of filters in the chain."""
        return [f.get_name() for f in self._filters]


# ---- Convenience Functions ----

def create_noise_reduction_filter(threshold: float = 0.01) -> NoiseReductionFilter:
    """Create a noise reduction filter."""
    settings = FilterSettings(noise_threshold=threshold)
    return NoiseReductionFilter(settings)


def create_jitter_filter(window: int = 3, std_threshold: float = 2.0) -> JitterFilter:
    """Create a jitter filter."""
    settings = FilterSettings(jitter_window=window, outlier_std_threshold=std_threshold)
    return JitterFilter(settings)


def create_median_filter(window: int = 3) -> MedianFilter:
    """Create a median filter."""
    settings = FilterSettings(median_window=window)
    return MedianFilter(settings)


def create_low_pass_filter(cutoff: float = 0.5) -> LowPassFilter:
    """Create a low-pass filter."""
    settings = FilterSettings(low_pass_cutoff=cutoff)
    return LowPassFilter(settings)


def create_standard_chain() -> FilterChain:
    """
    Create a standard filter chain for mocap data.

    Returns:
        FilterChain with noise reduction, median filter, and low-pass filter.
    """
    chain = FilterChain()
    chain.add(NoiseReductionFilter(FilterSettings(noise_threshold=0.005)))
    chain.add(MedianFilter(FilterSettings(median_window=3)))
    chain.add(LowPassFilter(FilterSettings(low_pass_cutoff=0.4)))
    return chain


# ---- Public API ----

__all__ = [
    "FilterBase",
    "FilterSettings",
    "FilterError",
    "NoiseReductionFilter",
    "JitterFilter",
    "MedianFilter",
    "LowPassFilter",
    "ClampFilter",
    "NormalizeFilter",
    "ScaleFilter",
    "BiasFilter",
    "FilterChain",
    "create_noise_reduction_filter",
    "create_jitter_filter",
    "create_median_filter",
    "create_low_pass_filter",
    "create_standard_chain",
]