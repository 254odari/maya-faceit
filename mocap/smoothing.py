"""
mocap/smoothing.py

Smoothing filters for tracking data.

Applies various smoothing algorithms to reduce jitter in facial tracking data.
Supports moving average, exponential, and Gaussian smoothing with configurable
parameters.

Features:
- Moving average smoothing
- Exponential smoothing (weighted)
- Gaussian smoothing (weighted average)
- History-based smoothing with configurable window size
- Per-channel smoothing with separate parameters
- Real-time and batch processing

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class SmoothingError(Exception):
    """Base exception for smoothing operations."""
    pass


# ---- Data Models ----

@dataclass
class SmoothingSettings:
    """
    Settings for smoothing.
    """
    window_size: int = 5                   # Number of frames for smoothing window
    method: str = "moving_average"         # 'moving_average', 'exponential', 'gaussian'
    alpha: float = 0.3                     # For exponential smoothing (0-1)
    sigma: float = 1.0                     # For Gaussian smoothing (standard deviation)
    min_samples: int = 2                   # Minimum samples before applying smoothing
    per_channel_alpha: Optional[Dict[str, float]] = None  # Per-channel alpha values


# ---- Smoothing Filter ----

class SmoothingFilter:
    """
    Apply smoothing to facial tracking data.

    Supports moving average, exponential, and Gaussian smoothing.

    Usage:
        filter = SmoothingFilter()
        filter.set_settings(SmoothingSettings(window_size=10, method='exponential', alpha=0.2))
        smoothed = filter.smooth(raw_frame)
    """

    def __init__(self, settings: Optional[SmoothingSettings] = None):
        """
        Initialize the smoothing filter.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or SmoothingSettings()
        self._history: List[Dict[str, float]] = []
        self._exponential_state: Dict[str, float] = {}  # Last smoothed value per channel
        logger.debug(f"SmoothingFilter initialized with method: {self.settings.method}")

    # ---- Core Smoothing ----

    def smooth(self, frame: Dict[str, float]) -> Dict[str, float]:
        """
        Smooth a single frame.

        Args:
            frame: Raw coefficients.

        Returns:
            Smoothed coefficients.
        """
        if not frame:
            return {}

        # Add to history
        self._history.append(frame.copy())
        if len(self._history) > self.settings.window_size * 3:
            self._history.pop(0)

        # Check if we have enough samples
        if len(self._history) < self.settings.min_samples:
            return frame.copy()

        method = self.settings.method
        if method == "moving_average":
            return self._moving_average()
        elif method == "exponential":
            return self._exponential_smoothing()
        elif method == "gaussian":
            return self._gaussian_smooth()
        else:
            logger.warning(f"Unknown smoothing method: {method}, using moving average")
            return self._moving_average()

    def smooth_batch(self, frames: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Smooth a batch of frames.

        Args:
            frames: List of raw frames.

        Returns:
            List of smoothed frames.
        """
        results = []
        for frame in frames:
            # Reset history for batch processing (optional)
            # We'll process sequentially to maintain continuity
            result = self.smooth(frame)
            results.append(result)
        return results

    # ---- Smoothing Methods ----

    def _moving_average(self) -> Dict[str, float]:
        """Apply moving average smoothing."""
        window = min(self.settings.window_size, len(self._history))
        recent = self._history[-window:]

        result = {}
        all_channels = set()
        for f in recent:
            all_channels.update(f.keys())

        for ch in all_channels:
            values = [f.get(ch, 0.0) for f in recent]
            result[ch] = sum(values) / len(values)

        return result

    def _exponential_smoothing(self) -> Dict[str, float]:
        """Apply exponential smoothing."""
        if len(self._history) < 2:
            return self._history[-1].copy() if self._history else {}

        alpha = self.settings.alpha
        prev = self._history[-2]
        curr = self._history[-1]

        result = {}
        all_channels = set(prev.keys()) | set(curr.keys())

        for ch in all_channels:
            # Check per-channel alpha
            alpha_ch = self.settings.per_channel_alpha.get(ch, alpha) if self.settings.per_channel_alpha else alpha

            prev_val = prev.get(ch, 0.0)
            curr_val = curr.get(ch, 0.0)

            # Exponential smoothing: new = alpha * current + (1 - alpha) * previous
            if ch in self._exponential_state:
                smoothed = alpha_ch * curr_val + (1 - alpha_ch) * self._exponential_state[ch]
            else:
                # No previous state, use current value
                smoothed = curr_val

            result[ch] = smoothed
            self._exponential_state[ch] = smoothed

        return result

    def _gaussian_smooth(self) -> Dict[str, float]:
        """Apply Gaussian smoothing (weighted average)."""
        window = min(self.settings.window_size, len(self._history))
        recent = self._history[-window:]

        if len(recent) < 2:
            return recent[-1].copy() if recent else {}

        # Compute Gaussian weights
        sigma = self.settings.sigma
        weights = []
        center = (window - 1) / 2.0
        for i in range(window):
            x = i - center
            w = math.exp(-(x * x) / (2 * sigma * sigma))
            weights.append(w)
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        result = {}
        all_channels = set()
        for f in recent:
            all_channels.update(f.keys())

        for ch in all_channels:
            values = [f.get(ch, 0.0) for f in recent]
            result[ch] = sum(v * w for v, w in zip(values, weights))

        return result

    # ---- History Management ----

    def reset(self) -> None:
        """Reset the filter history and state."""
        self._history = []
        self._exponential_state = {}
        logger.debug("Smoothing filter reset")

    def get_history(self) -> List[Dict[str, float]]:
        """Get the current history."""
        return self._history.copy()

    def set_history(self, history: List[Dict[str, float]]) -> None:
        """Set the history (for batch processing)."""
        self._history = history.copy()

    def get_state(self) -> Dict[str, float]:
        """Get the exponential smoothing state."""
        return self._exponential_state.copy()

    def set_state(self, state: Dict[str, float]) -> None:
        """Set the exponential smoothing state."""
        self._exponential_state = state.copy()

    # ---- Settings ----

    def set_settings(self, settings: SmoothingSettings) -> None:
        """Update smoothing settings."""
        self.settings = settings
        # Reset exponential state if method changes? We'll keep it.
        logger.debug(f"Smoothing settings updated: method={settings.method}, window={settings.window_size}")

    def set_per_channel_alpha(self, alphas: Dict[str, float]) -> None:
        """Set per-channel alpha values for exponential smoothing."""
        self.settings.per_channel_alpha = alphas

    # ---- Statistics ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get filter statistics.

        Returns:
            Dict with history size, settings, etc.
        """
        return {
            "history_size": len(self._history),
            "window_size": self.settings.window_size,
            "method": self.settings.method,
            "alpha": self.settings.alpha,
            "sigma": self.settings.sigma,
            "min_samples": self.settings.min_samples,
        }


# ---- Convenience Functions ----

def create_moving_average_filter(window_size: int = 5) -> SmoothingFilter:
    """Create a moving average smoothing filter."""
    settings = SmoothingSettings(method="moving_average", window_size=window_size)
    return SmoothingFilter(settings)


def create_exponential_filter(alpha: float = 0.3, window_size: int = 10) -> SmoothingFilter:
    """Create an exponential smoothing filter."""
    settings = SmoothingSettings(method="exponential", alpha=alpha, window_size=window_size)
    return SmoothingFilter(settings)


def create_gaussian_filter(sigma: float = 1.0, window_size: int = 7) -> SmoothingFilter:
    """Create a Gaussian smoothing filter."""
    settings = SmoothingSettings(method="gaussian", sigma=sigma, window_size=window_size)
    return SmoothingFilter(settings)


# ---- Public API ----

__all__ = [
    "SmoothingFilter",
    "SmoothingSettings",
    "SmoothingError",
    "create_moving_average_filter",
    "create_exponential_filter",
    "create_gaussian_filter",
]