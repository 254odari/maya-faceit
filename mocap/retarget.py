"""
mocap/retarget.py

Retarget captured facial motion data to face rigs.

This module handles retargeting of facial motion capture data from various
sources (LiveLink, MediaPipe, FaceCap) to target blendshape rigs.

It supports:
- ARKit blendshape mapping
- MediaPipe blendshape extraction
- FaceCap data processing
- Intensity scaling and normalization
- Calibration application

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Callable

# Import from other modules
try:
    from ..blendshapes.blendshape_utils import clamp, normalize_weights
    from ..expressions.manager import ExpressionManager
    from ..expressions.generator import ExpressionDefinition
    from ..arkit.mapper import ARKitMapper
    from ..arkit.arkit52 import ARKIT_SET
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights): 
        total = sum(weights.values())
        if total == 0:
            return {k: 0.0 for k in weights}
        return {k: v / total for k, v in weights.items()}
    class ExpressionManager: pass
    class ExpressionDefinition: pass
    class ARKitMapper:
        def map(self, data): return data.copy()
    ARKIT_SET = set()
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class RetargetError(Exception):
    """Base exception for retarget operations."""
    pass


# ---- Data Models ----

@dataclass
class RetargetSettings:
    """
    Settings for retargeting operations.
    """
    source: str = "arkit"                  # 'arkit', 'mediapipe', 'facecap'
    target_rig: str = "blendshape"         # Target rig type
    map_file: Optional[str] = None         # Custom mapping file path
    normalize: bool = True                 # Normalize weights to sum to 1
    clamp_values: bool = True              # Clamp values to [0, 1]
    intensity_scale: float = 1.0           # Global intensity multiplier
    use_calibration: bool = True           # Apply calibration profile
    calibration_profile: Optional[str] = None  # Profile name
    apply_smoothing: bool = False          # Apply smoothing during retarget
    smoothing_window: int = 5              # Smoothing window size


@dataclass
class RetargetResult:
    """
    Result of a retarget operation.
    """
    success: bool
    mapped_coefficients: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0
    source_type: str = "unknown"
    target_type: str = "unknown"


# ---- Retarget Engine ----

class RetargetEngine:
    """
    Retarget facial motion data to rig controls.

    Supports various source formats and target rigs with
    configurable mapping and calibration.
    """

    def __init__(self, settings: Optional[RetargetSettings] = None):
        """
        Initialize the retarget engine.

        Args:
            settings: Optional retarget settings.
        """
        self.settings = settings or RetargetSettings()
        self._arkit_mapper = ARKitMapper()
        self._expression_manager = ExpressionManager()
        self._mapping_cache: Dict[str, Dict[str, float]] = {}
        self._calibration_cache: Dict[str, Dict[str, float]] = {}

        logger.debug(f"RetargetEngine initialized with source: {self.settings.source}")

    # ---- Main Retarget Method ----

    def retarget(
        self,
        source_data: Dict[str, float],
        source_type: Optional[str] = None,
        settings: Optional[RetargetSettings] = None,
    ) -> RetargetResult:
        """
        Retarget source data to rig coefficients.

        Args:
            source_data: Raw source coefficients (channel -> value).
            source_type: Type of source data. If None, uses settings.
            settings: Override settings for this operation.

        Returns:
            RetargetResult with mapped coefficients.
        """
        start_time = time.time()

        # Apply settings
        if settings is None:
            settings = self.settings
        else:
            self.settings = settings

        source_type = source_type or settings.source

        result = RetargetResult(
            success=True,
            source_type=source_type,
            target_type=settings.target_rig,
        )

        try:
            # Step 1: Validate input
            if not source_data:
                result.success = False
                result.errors.append("No source data provided.")
                result.elapsed_time = time.time() - start_time
                return result

            # Step 2: Map based on source type
            if source_type == "arkit":
                mapped = self._retarget_arkit(source_data)
            elif source_type == "mediapipe":
                mapped = self._retarget_mediapipe(source_data)
            elif source_type == "facecap":
                mapped = self._retarget_facecap(source_data)
            else:
                result.success = False
                result.errors.append(f"Unsupported source type: {source_type}")
                result.elapsed_time = time.time() - start_time
                return result

            # Step 3: Apply calibration (if enabled)
            if settings.use_calibration:
                mapped = self._apply_calibration(mapped)

            # Step 4: Apply intensity scale
            if settings.intensity_scale != 1.0:
                mapped = {k: v * settings.intensity_scale for k, v in mapped.items()}

            # Step 5: Clamp values
            if settings.clamp_values:
                mapped = {k: clamp(v, 0.0, 1.0) for k, v in mapped.items()}

            # Step 6: Normalize
            if settings.normalize:
                mapped = normalize_weights(mapped)

            # Step 7: Apply smoothing (if enabled)
            if settings.apply_smoothing:
                mapped = self._apply_smoothing(mapped)

            result.mapped_coefficients = mapped

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Retarget failed: {e}")

        result.elapsed_time = time.time() - start_time
        return result

    # ---- Source-Specific Mapping ----

    def _retarget_arkit(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Retarget ARKit data to blendshapes.

        Uses the ARKitMapper to convert ARKit coefficients to
        the target blendshape system.
        """
        # Validate ARKit channels
        for ch in data:
            if ch not in ARKIT_SET:
                logger.warning(f"Unknown ARKit channel: {ch}")

        # Map using ARKit mapper
        return self._arkit_mapper.map(data)

    def _retarget_mediapipe(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Retarget MediaPipe data to blendshapes.

        MediaPipe provides blendshape coefficients in ARKit format.
        We map them directly to the target system.
        """
        # MediaPipe outputs are already in ARKit format
        # Map them using ARKit mapper
        return self._arkit_mapper.map(data)

    def _retarget_facecap(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Retarget FaceCap data to blendshapes.

        FaceCap uses ARKit-like format but may have different naming.
        """
        # Check if data is already in ARKit format
        arkit_keys = [ch for ch in data if ch in ARKIT_SET]
        if len(arkit_keys) == len(data):
            # Already ARKit format
            return self._arkit_mapper.map(data)

        # If not, we need to map FaceCap names to ARKit names
        # For now, we'll assume direct mapping if names match
        return data.copy()

    # ---- Calibration ----

    def _apply_calibration(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Apply calibration profile to the data.
        """
        if not self.settings.calibration_profile:
            return data

        profile = self._get_calibration_profile(self.settings.calibration_profile)
        if not profile:
            return data

        calibrated = {}
        for channel, value in data.items():
            if channel in profile:
                # Apply neutral offset and gain
                neutral = profile[channel].get("neutral", 0.0)
                gain = profile[channel].get("gain", 1.0)
                offset = profile[channel].get("offset", 0.0)
                val = (value - neutral) * gain + offset
                calibrated[channel] = clamp(val, 0.0, 1.0)
            else:
                calibrated[channel] = value

        return calibrated

    def _get_calibration_profile(self, name: str) -> Dict[str, Dict[str, float]]:
        """
        Get a calibration profile by name.
        """
        # Try cache first
        if name in self._calibration_cache:
            return self._calibration_cache[name]

        # Placeholder: would load from file or database
        # For now, return empty (no calibration)
        return {}

    def set_calibration_profile(self, name: str, profile: Dict[str, Dict[str, float]]) -> None:
        """
        Set a calibration profile.
        """
        self._calibration_cache[name] = profile

    # ---- Smoothing ----

    def _apply_smoothing(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Apply smoothing to the data.

        This is a simple version; in production, we'd use a more sophisticated
        smoothing algorithm with history.
        """
        if not hasattr(self, '_smooth_history'):
            self._smooth_history = []

        # Store in history
        self._smooth_history.append(data.copy())
        if len(self._smooth_history) > self.settings.smoothing_window * 2:
            self._smooth_history.pop(0)

        if len(self._smooth_history) < 2:
            return data

        # Simple moving average
        window = min(self.settings.smoothing_window, len(self._smooth_history))
        recent = self._smooth_history[-window:]

        result = {}
        all_channels = set()
        for f in recent:
            all_channels.update(f.keys())

        for ch in all_channels:
            values = [f.get(ch, 0.0) for f in recent]
            result[ch] = sum(values) / len(values)

        return result

    def reset_smoothing(self) -> None:
        """Reset the smoothing history."""
        if hasattr(self, '_smooth_history'):
            self._smooth_history = []

    # ---- Batch Retarget ----

    def batch_retarget(
        self,
        frames: List[Dict[str, float]],
        source_type: Optional[str] = None,
        settings: Optional[RetargetSettings] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> List[RetargetResult]:
        """
        Retarget multiple frames.

        Args:
            frames: List of source data frames.
            source_type: Type of source data.
            settings: Override settings.
            progress_callback: Optional progress callback.

        Returns:
            List of RetargetResult for each frame.
        """
        results = []
        total = len(frames)

        for i, frame in enumerate(frames):
            if progress_callback:
                progress_callback(i / total, f"Retargeting frame {i+1}/{total}")

            result = self.retarget(frame, source_type, settings)
            results.append(result)

        return results

    # ---- Utility Methods ----

    def set_mapping(self, source_channel: str, target_channel: str, multiplier: float = 1.0) -> None:
        """
        Set a custom mapping from source to target.

        Args:
            source_channel: Source channel name.
            target_channel: Target channel name.
            multiplier: Scale factor.
        """
        if source_channel not in self._mapping_cache:
            self._mapping_cache[source_channel] = {}
        self._mapping_cache[source_channel][target_channel] = multiplier

    def clear_mapping(self) -> None:
        """Clear all custom mappings."""
        self._mapping_cache.clear()

    def get_source_channels(self, source_type: str) -> List[str]:
        """
        Get available source channels for a given source type.

        Args:
            source_type: 'arkit', 'mediapipe', 'facecap'.

        Returns:
            List of channel names.
        """
        if source_type == "arkit":
            return list(ARKIT_SET)
        elif source_type == "mediapipe":
            # MediaPipe uses ARKit format
            return list(ARKIT_SET)
        elif source_type == "facecap":
            # FaceCap uses ARKit format plus some extras
            return list(ARKIT_SET) + ["mouthFunnel", "mouthPucker"]  # Placeholder
        else:
            return []

    # ---- Settings ----

    def set_settings(self, settings: RetargetSettings) -> None:
        """Update retarget settings."""
        self.settings = settings

    def get_settings(self) -> RetargetSettings:
        """Get current settings."""
        return self.settings


# ---- Public API ----

__all__ = [
    "RetargetEngine",
    "RetargetSettings",
    "RetargetResult",
    "RetargetError",
]