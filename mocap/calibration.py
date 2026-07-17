"""
mocap/calibration.py

Calibrate facial capture data.

Captures neutral, range, and symmetry calibration for mocap data.
This is essential for adapting generic facial capture to specific performers,
ensuring consistent and natural results across different subjects.

Features:
- Neutral pose capture (average of multiple frames)
- Range calibration (min/max values per channel)
- Gain and offset computation
- Symmetry correction for left/right balance
- Calibration profile management (save/load)
- Apply calibration to arbitrary frames
- Per-channel calibration with fallback defaults

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union

# Import from other modules
try:
    from ..blendshapes.blendshape_utils import clamp, normalize_weights
    from ..arkit.arkit52 import LEFT_RIGHT_PAIRS, ARKIT_SET
    HAS_DEPS = True
except ImportError:
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights):
        total = sum(weights.values())
        if total == 0:
            return {k: 0.0 for k in weights}
        return {k: v / total for k, v in weights.items()}
    LEFT_RIGHT_PAIRS = {
        "eyeBlinkLeft": "eyeBlinkRight",
        "mouthSmileLeft": "mouthSmileRight",
        "browDownLeft": "browDownRight",
        "browOuterUpLeft": "browOuterUpRight",
        "cheekSquintLeft": "cheekSquintRight",
        "eyeSquintLeft": "eyeSquintRight",
        "eyeWideLeft": "eyeWideRight",
        "mouthDimpleLeft": "mouthDimpleRight",
        "mouthFrownLeft": "mouthFrownRight",
        "mouthPressLeft": "mouthPressRight",
        "mouthStretchLeft": "mouthStretchRight",
        "mouthUpperUpLeft": "mouthUpperUpRight",
        "mouthLowerDownLeft": "mouthLowerDownRight",
        "noseSneerLeft": "noseSneerRight",
    }
    ARKIT_SET = set()
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class CalibrationError(Exception):
    """Base exception for calibration operations."""
    pass


# ---- Data Models ----

@dataclass
class CalibrationProfile:
    """
    Calibration profile for a performer or character.

    Stores per-channel calibration parameters:
    - neutral: neutral pose value (baseline)
    - min: minimum observed value
    - max: maximum observed value
    - gain: scaling factor = 1.0 / (max - min)
    - offset: offset to normalize to [0,1]
    """
    name: str
    neutral: Dict[str, float] = field(default_factory=dict)
    min_values: Dict[str, float] = field(default_factory=dict)
    max_values: Dict[str, float] = field(default_factory=dict)
    gains: Dict[str, float] = field(default_factory=dict)
    offsets: Dict[str, float] = field(default_factory=dict)
    symmetry_gain_left: float = 1.0
    symmetry_gain_right: float = 1.0
    use_symmetry_correction: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "neutral": self.neutral,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "gains": self.gains,
            "offsets": self.offsets,
            "symmetry_gain_left": self.symmetry_gain_left,
            "symmetry_gain_right": self.symmetry_gain_right,
            "use_symmetry_correction": self.use_symmetry_correction,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationProfile':
        return cls(
            name=data.get("name", "Default"),
            neutral=data.get("neutral", {}),
            min_values=data.get("min_values", {}),
            max_values=data.get("max_values", {}),
            gains=data.get("gains", {}),
            offsets=data.get("offsets", {}),
            symmetry_gain_left=data.get("symmetry_gain_left", 1.0),
            symmetry_gain_right=data.get("symmetry_gain_right", 1.0),
            use_symmetry_correction=data.get("use_symmetry_correction", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CalibrationResult:
    """
    Result of a calibration operation.
    """
    success: bool
    profile: Optional[CalibrationProfile] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    frame_count: int = 0


# ---- Mocap Calibration ----

class MocapCalibration:
    """
    Calibrate facial capture data.

    Captures neutral, range, and symmetry calibration.

    Usage:
        calibrator = MocapCalibration()
        # Capture neutral frames
        calibrator.capture_neutral(frame1)
        calibrator.capture_neutral(frame2)
        # Capture max frames
        calibrator.capture_max(max_frame1)
        calibrator.capture_max(max_frame2)
        # Compute profile
        profile = calibrator.compute_profile("MyPerformer")
        # Apply calibration
        calibrated = calibrator.apply_calibration(raw_frame, profile)
        # Save profile
        calibrator.save_profile(profile, "my_profile.json")
    """

    def __init__(self):
        """
        Initialize the calibration.
        """
        self._neutral_frames: List[Dict[str, float]] = []
        self._max_frames: List[Dict[str, float]] = []
        self._min_frames: List[Dict[str, float]] = []

        # Track all channels seen
        self._all_channels: set = set()

        logger.debug("MocapCalibration initialized")

    # ---- Capture Methods ----

    def capture_neutral(self, frame: Dict[str, float]) -> None:
        """
        Capture a neutral frame (relaxed face).

        Args:
            frame: Blendshape coefficients for neutral pose.
        """
        self._neutral_frames.append(frame.copy())
        self._all_channels.update(frame.keys())
        logger.debug(f"Neutral frame captured ({len(self._neutral_frames)} total)")

    def capture_max(self, frame: Dict[str, float]) -> None:
        """
        Capture a maximum expression frame.

        Args:
            frame: Blendshape coefficients for maximum expression.
        """
        self._max_frames.append(frame.copy())
        self._all_channels.update(frame.keys())
        logger.debug(f"Max frame captured ({len(self._max_frames)} total)")

    def capture_min(self, frame: Dict[str, float]) -> None:
        """
        Capture a minimum expression frame.

        Args:
            frame: Blendshape coefficients for minimum expression.
        """
        self._min_frames.append(frame.copy())
        self._all_channels.update(frame.keys())
        logger.debug(f"Min frame captured ({len(self._min_frames)} total)")

    def capture_from_sequence(
        self,
        frames: List[Dict[str, float]],
        neutral_range: Tuple[float, float] = (0.1, 0.3),
        max_range: Tuple[float, float] = (0.7, 0.9),
        min_range: Tuple[float, float] = (0.0, 0.1),
    ) -> None:
        """
        Automatically capture neutral, max, and min from a sequence.

        Args:
            frames: List of frames.
            neutral_range: Value range for neutral detection (0-1).
            max_range: Value range for max detection (0-1).
            min_range: Value range for min detection (0-1).
        """
        if not frames:
            return

        # For each channel, find neutral, max, min frames
        channel_values = {}
        for frame in frames:
            for ch, val in frame.items():
                if ch not in channel_values:
                    channel_values[ch] = []
                channel_values[ch].append(val)

        # Find neutral frames (values in neutral range)
        neutral_frames = []
        for frame in frames:
            is_neutral = True
            for ch, val in frame.items():
                if ch in channel_values:
                    # Check if value is in neutral range
                    if not (neutral_range[0] <= val <= neutral_range[1]):
                        # For ARKit channels, neutral is typically near 0
                        if val > neutral_range[1] * 1.5:
                            is_neutral = False
                            break
            if is_neutral:
                neutral_frames.append(frame)

        # Find max frames
        max_frames = []
        for frame in frames:
            is_max = False
            for ch, val in frame.items():
                if val > max_range[0]:
                    is_max = True
                    break
            if is_max:
                max_frames.append(frame)

        # Find min frames
        min_frames = []
        for frame in frames:
            is_min = False
            for ch, val in frame.items():
                if val < min_range[1]:
                    is_min = True
                    break
            if is_min:
                min_frames.append(frame)

        # Add captured frames
        for f in neutral_frames:
            self.capture_neutral(f)
        for f in max_frames:
            self.capture_max(f)
        for f in min_frames:
            self.capture_min(f)

        logger.info(f"Auto-captured: {len(neutral_frames)} neutral, {len(max_frames)} max, {len(min_frames)} min frames")

    # ---- Profile Computation ----

    def compute_profile(self, name: str = "Default") -> CalibrationProfile:
        """
        Compute calibration profile from captured frames.

        Args:
            name: Profile name.

        Returns:
            CalibrationProfile object.
        """
        # Compute neutral average
        neutral = {}
        if self._neutral_frames:
            all_channels = set()
            for f in self._neutral_frames:
                all_channels.update(f.keys())
            for ch in all_channels:
                values = [f.get(ch, 0.0) for f in self._neutral_frames]
                neutral[ch] = sum(values) / len(values)
        else:
            # No neutral frames, use zeros
            neutral = {ch: 0.0 for ch in self._all_channels}

        # Compute max values
        max_vals = {}
        if self._max_frames:
            all_channels = set()
            for f in self._max_frames:
                all_channels.update(f.keys())
            for ch in all_channels:
                values = [f.get(ch, 0.0) for f in self._max_frames]
                max_vals[ch] = max(values) if values else 1.0
        else:
            max_vals = {ch: 1.0 for ch in self._all_channels}

        # Compute min values
        min_vals = {}
        if self._min_frames:
            all_channels = set()
            for f in self._min_frames:
                all_channels.update(f.keys())
            for ch in all_channels:
                values = [f.get(ch, 0.0) for f in self._min_frames]
                min_vals[ch] = min(values) if values else 0.0
        else:
            min_vals = {ch: 0.0 for ch in self._all_channels}

        # Compute gains and offsets
        gains = {}
        offsets = {}
        all_channels = set(neutral.keys()) | set(max_vals.keys()) | set(min_vals.keys())

        for ch in all_channels:
            max_v = max_vals.get(ch, 1.0)
            min_v = min_vals.get(ch, 0.0)
            range_v = max_v - min_v

            if range_v > 0.001:
                gains[ch] = 1.0 / range_v
            else:
                # Range too small, use default gain
                gains[ch] = 1.0

            # Offset: -min * gain
            offsets[ch] = -min_v * gains[ch]

        # Compute symmetry gains
        symmetry_left, symmetry_right = self._compute_symmetry_gains(neutral)

        # Create profile
        profile = CalibrationProfile(
            name=name,
            neutral=neutral,
            min_values=min_vals,
            max_values=max_vals,
            gains=gains,
            offsets=offsets,
            symmetry_gain_left=symmetry_left,
            symmetry_gain_right=symmetry_right,
            metadata={
                "created": time.ctime(),
                "neutral_frames": len(self._neutral_frames),
                "max_frames": len(self._max_frames),
                "min_frames": len(self._min_frames),
                "channels": list(all_channels),
            },
        )

        logger.info(f"Calibration profile '{name}' computed with {len(all_channels)} channels")
        return profile

    def _compute_symmetry_gains(self, neutral: Dict[str, float]) -> Tuple[float, float]:
        """
        Compute symmetry gains for left/right balance.

        Args:
            neutral: Neutral values.

        Returns:
            (left_gain, right_gain)
        """
        left_vals = []
        right_vals = []

        for left, right in LEFT_RIGHT_PAIRS.items():
            if left in neutral and right in neutral:
                left_vals.append(neutral[left])
                right_vals.append(neutral[right])

        if not left_vals:
            return 1.0, 1.0

        # Compute average left and right values
        avg_left = sum(left_vals) / len(left_vals)
        avg_right = sum(right_vals) / len(right_vals)

        if avg_left == 0 and avg_right == 0:
            return 1.0, 1.0

        if avg_left > 0 and avg_right > 0:
            # Adjust gains to balance
            total = avg_left + avg_right
            if total > 0:
                return total / (2 * avg_left), total / (2 * avg_right)

        return 1.0, 1.0

    # ---- Apply Calibration ----

    def apply_calibration(
        self,
        frame: Dict[str, float],
        profile: CalibrationProfile,
        clamp_output: bool = True,
    ) -> Dict[str, float]:
        """
        Apply calibration to a frame.

        Args:
            frame: Raw blendshape coefficients.
            profile: CalibrationProfile to apply.
            clamp_output: If True, clamp values to [0, 1].

        Returns:
            Calibrated coefficients.
        """
        calibrated = {}
        all_channels = set(frame.keys()) | set(profile.neutral.keys())

        for channel in all_channels:
            value = frame.get(channel, 0.0)

            # Subtract neutral
            neutral = profile.neutral.get(channel, 0.0)
            val = value - neutral

            # Apply gain
            gain = profile.gains.get(channel, 1.0)
            val *= gain

            # Apply offset
            offset = profile.offsets.get(channel, 0.0)
            val += offset

            # Apply symmetry correction
            if profile.use_symmetry_correction:
                if channel.endswith("Left") and channel in LEFT_RIGHT_PAIRS:
                    val *= profile.symmetry_gain_left
                elif channel.endswith("Right") and channel in LEFT_RIGHT_PAIRS:
                    val *= profile.symmetry_gain_right

            # Clamp
            if clamp_output:
                val = clamp(val, 0.0, 1.0)

            calibrated[channel] = val

        return calibrated

    def apply_calibration_batch(
        self,
        frames: List[Dict[str, float]],
        profile: CalibrationProfile,
        clamp_output: bool = True,
    ) -> List[Dict[str, float]]:
        """
        Apply calibration to a batch of frames.

        Args:
            frames: List of raw frames.
            profile: CalibrationProfile to apply.
            clamp_output: If True, clamp values to [0, 1].

        Returns:
            List of calibrated frames.
        """
        return [self.apply_calibration(f, profile, clamp_output) for f in frames]

    # ---- Profile Management ----

    def save_profile(self, profile: CalibrationProfile, filepath: str) -> None:
        """
        Save a calibration profile to a JSON file.

        Args:
            profile: CalibrationProfile to save.
            filepath: Output file path.
        """
        data = profile.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Calibration profile saved to {filepath}")

    def load_profile(self, filepath: str) -> CalibrationProfile:
        """
        Load a calibration profile from a JSON file.

        Args:
            filepath: Input file path.

        Returns:
            CalibrationProfile object.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        profile = CalibrationProfile.from_dict(data)
        logger.info(f"Calibration profile loaded from {filepath}")
        return profile

    # ---- Reset ----

    def reset(self) -> None:
        """Reset all captured frames."""
        self._neutral_frames = []
        self._max_frames = []
        self._min_frames = []
        self._all_channels = set()
        logger.debug("Calibration reset")

    # ---- Statistics ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get calibration statistics.

        Returns:
            Dict with capture stats.
        """
        return {
            "neutral_frames": len(self._neutral_frames),
            "max_frames": len(self._max_frames),
            "min_frames": len(self._min_frames),
            "total_channels": len(self._all_channels),
        }


# ---- Convenience Functions ----

def create_calibration_profile(
    name: str,
    neutral: Dict[str, float],
    max_values: Dict[str, float],
    min_values: Optional[Dict[str, float]] = None,
) -> CalibrationProfile:
    """
    Create a calibration profile from data.

    Args:
        name: Profile name.
        neutral: Neutral values.
        max_values: Maximum values.
        min_values: Minimum values (default: zeros).

    Returns:
        CalibrationProfile.
    """
    if min_values is None:
        min_values = {ch: 0.0 for ch in neutral.keys()}

    # Compute gains and offsets
    gains = {}
    offsets = {}
    all_channels = set(neutral.keys()) | set(max_values.keys()) | set(min_values.keys())

    for ch in all_channels:
        max_v = max_values.get(ch, 1.0)
        min_v = min_values.get(ch, 0.0)
        range_v = max_v - min_v
        if range_v > 0.001:
            gains[ch] = 1.0 / range_v
            offsets[ch] = -min_v * gains[ch]
        else:
            gains[ch] = 1.0
            offsets[ch] = 0.0

    return CalibrationProfile(
        name=name,
        neutral=neutral,
        min_values=min_values,
        max_values=max_values,
        gains=gains,
        offsets=offsets,
    )


# ---- Public API ----

__all__ = [
    "MocapCalibration",
    "CalibrationProfile",
    "CalibrationResult",
    "CalibrationError",
    "create_calibration_profile",
]