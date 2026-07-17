"""
arkit/calibration.py

ARKit Calibration Engine

This module provides personalization and normalization of ARKit facial
coefficients. It adapts generic ARKit values to the unique characteristics
of a specific performer, character, or facial rig.

Without calibration, two users performing the same expression may produce
very different ARKit values. Calibration makes those expressions consistent,
improving the quality of downstream mapping and animation.

The calibration pipeline:
    Live ARKit Frame
            │
            ▼
    Subtract Neutral
            │
            ▼
    Apply Gain / Scale
            │
            ▼
    Apply Offset
            │
            ▼
    Clamp to [0,1]
            │
            ▼
    Dead Zone Filter
            │
            ▼
    Normalized Coefficients
            │
            ▼
    mapper.py → Rig Controls

Responsibilities
----------------
• Capture neutral face (baseline)
• Capture maximum range for each channel (optional)
• Store per-channel calibration parameters (neutral, gain, offset, clamp, dead zone)
• Apply symmetry correction (separate gains for left/right)
• Support non-linear gain curves (linear, exponential, logarithmic, custom)
• Apply dead zones to eliminate micro-movements
• Maintain multiple calibration profiles (per actor, per character, per rig)
• Import/export profiles (JSON, binary)
• Live recalibration of individual channels
• Automatic calibration from a short recording (neutral + max expressions)
• Diagnostics and statistics

Dependencies
------------
• arkit52.py - canonical ARKit channel list, left/right pairs
• validator.py - validate calibration profiles and runtime frames
• (optional) pose_generator.py - for generating expression poses for calibration
"""

from __future__ import annotations

import copy
import json
import math
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any, Tuple, Callable, Union
from enum import Enum

try:
    from .arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}

try:
    from .validator import ARKitValidator, ValidationLevel
except ImportError:
    class ARKitValidator:
        def validate_coefficients(self, coeffs, *args, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class DummyReport:
                is_valid = True
                errors = []
                warnings = []
            return DummyReport()
    ValidationLevel = None

# ---- Part 1: Foundation --------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class ARKitCalibrationError(Exception):
    """Base exception for calibration errors."""
    pass

class CalibrationProfileError(ARKitCalibrationError):
    """Raised when a calibration profile is invalid or missing."""
    pass

class CalibrationDataError(ARKitCalibrationError):
    """Raised when calibration data (neutral, ranges) is invalid."""
    pass

class CalibrationStateError(ARKitCalibrationError):
    """Raised when calibration state is inconsistent."""
    pass

# ---- Part 2: Data Models ------------------------------------------------

class GainCurve(Enum):
    """Supported gain curve types."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    CUSTOM = "custom"


@dataclass
class ChannelCalibration:
    """
    Calibration parameters for a single ARKit channel.
    """
    enabled: bool = True
    neutral: float = 0.0          # baseline value in neutral pose
    maximum: float = 1.0          # maximum expected raw value (for range normalization)
    gain: float = 1.0             # multiplier (after subtract neutral)
    offset: float = 0.0           # additive offset
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    dead_zone: float = 0.0        # values below this absolute threshold become 0
    curve: str = "linear"         # 'linear', 'exponential', 'logarithmic', 'custom'
    curve_params: Dict[str, float] = field(default_factory=dict)  # e.g., {'exponent': 2.0}
    # For custom curve, a callable can be set at runtime (not serialized)

    def apply(self, raw_value: float) -> float:
        """
        Apply calibration to a raw ARKit value.
        Steps:
            1. Subtract neutral.
            2. Scale by gain.
            3. Apply offset.
            4. Clamp to [clamp_min, clamp_max].
            5. Apply dead zone (if |value| < dead_zone, set to 0).
            6. Apply gain curve.
        """
        if not self.enabled:
            return raw_value

        # Step 1: subtract neutral
        value = raw_value - self.neutral

        # Step 2: gain
        value *= self.gain

        # Step 3: offset
        value += self.offset

        # Step 4: clamp
        if value < self.clamp_min:
            value = self.clamp_min
        elif value > self.clamp_max:
            value = self.clamp_max

        # Step 5: dead zone
        if abs(value) < self.dead_zone:
            value = 0.0

        # Step 6: gain curve (applied after dead zone, but before final clamp?)
        # Usually after scaling, we apply a curve to shape the response.
        # We'll apply it after dead zone.
        if self.curve == "exponential":
            exponent = self.curve_params.get("exponent", 2.0)
            if value >= 0.0:
                value = math.pow(value, exponent)
            else:
                # For negative values, mirror
                value = -math.pow(abs(value), exponent)
        elif self.curve == "logarithmic":
            # Map to [0,1] log scale: y = log(1 + x * (exp(1)-1)) / log(exp(1))
            # Simplified: just apply log transform
            if value > 0.0:
                value = math.log1p(value * (math.e - 1)) / math.log(math.e)
            # else leave as 0
        # 'custom' requires a callable set separately; not serialized

        # Final clamp to 0-1 (should already be clamped)
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0

        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "neutral": self.neutral,
            "maximum": self.maximum,
            "gain": self.gain,
            "offset": self.offset,
            "clamp_min": self.clamp_min,
            "clamp_max": self.clamp_max,
            "dead_zone": self.dead_zone,
            "curve": self.curve,
            "curve_params": self.curve_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChannelCalibration:
        return cls(
            enabled=data.get("enabled", True),
            neutral=data.get("neutral", 0.0),
            maximum=data.get("maximum", 1.0),
            gain=data.get("gain", 1.0),
            offset=data.get("offset", 0.0),
            clamp_min=data.get("clamp_min", 0.0),
            clamp_max=data.get("clamp_max", 1.0),
            dead_zone=data.get("dead_zone", 0.0),
            curve=data.get("curve", "linear"),
            curve_params=data.get("curve_params", {}),
        )


@dataclass
class CalibrationProfile:
    """
    A complete calibration profile for a performer or character.
    Contains per-channel calibration data and global settings.
    """
    name: str
    description: str = ""
    author: str = "unknown"
    version: str = "1.0"
    created: str = ""  # ISO timestamp
    modified: str = ""  # ISO timestamp
    channels: Dict[str, ChannelCalibration] = field(default_factory=dict)
    # Global settings
    use_symmetry_correction: bool = False
    symmetry_gain_left: float = 1.0  # overall gain multiplier for left channels
    symmetry_gain_right: float = 1.0  # overall gain multiplier for right channels
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_channel(self, channel_name: str) -> ChannelCalibration:
        """Get calibration for a channel, or create default if missing."""
        if channel_name not in self.channels:
            self.channels[channel_name] = ChannelCalibration()
        return self.channels[channel_name]

    def apply_symmetry(self, channel_name: str, raw_value: float) -> float:
        """
        Apply symmetry gain correction for left/right channels.
        """
        if not self.use_symmetry_correction:
            return raw_value
        # Detect if it's a left or right channel
        if channel_name.endswith("Left") and "Right" in channel_name:
            # Left channel
            gain = self.symmetry_gain_left
        elif channel_name.endswith("Right"):
            gain = self.symmetry_gain_right
        else:
            gain = 1.0
        return raw_value * gain

    def normalize(self, raw_frame: Dict[str, float]) -> Dict[str, float]:
        """
        Apply the full calibration pipeline to a raw ARKit frame.
        """
        normalized = {}
        for channel, raw_value in raw_frame.items():
            # Skip if not a number
            if not isinstance(raw_value, (int, float)):
                continue
            # Get calibration for this channel, or default
            cal = self.get_channel(channel)
            # Apply symmetry correction (if any)
            corrected_value = self.apply_symmetry(channel, raw_value)
            # Apply channel calibration
            normalized[channel] = cal.apply(corrected_value)
        return normalized

    def capture_neutral(self, frame: Dict[str, float]) -> None:
        """
        Capture neutral values from a frame (average of multiple frames ideally).
        For each channel, set neutral to the frame's value.
        """
        for channel, value in frame.items():
            if not isinstance(value, (int, float)):
                continue
            cal = self.get_channel(channel)
            cal.neutral = value

    def capture_maximum(self, frame: Dict[str, float]) -> None:
        """
        Capture maximum values from a frame (e.g., from a maximum expression).
        Updates the 'maximum' field of each channel.
        """
        for channel, value in frame.items():
            if not isinstance(value, (int, float)):
                continue
            cal = self.get_channel(channel)
            # Only update if value > current maximum
            if value > cal.maximum:
                cal.maximum = value

    def compute_gain_from_ranges(self) -> None:
        """
        Automatically compute gain for each channel based on neutral and maximum.
        Gain = 1.0 / (maximum - neutral) if maximum > neutral, else 1.0.
        This normalizes the range to [0,1].
        """
        for cal in self.channels.values():
            range_val = cal.maximum - cal.neutral
            if range_val > 0.001:
                cal.gain = 1.0 / range_val
            else:
                cal.gain = 1.0

    def enable_all(self, enabled: bool = True) -> None:
        """Enable or disable all channels."""
        for cal in self.channels.values():
            cal.enabled = enabled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "created": self.created,
            "modified": self.modified,
            "channels": {k: v.to_dict() for k, v in self.channels.items()},
            "use_symmetry_correction": self.use_symmetry_correction,
            "symmetry_gain_left": self.symmetry_gain_left,
            "symmetry_gain_right": self.symmetry_gain_right,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CalibrationProfile:
        channels = {}
        for ch_name, ch_data in data.get("channels", {}).items():
            channels[ch_name] = ChannelCalibration.from_dict(ch_data)
        return cls(
            name=data.get("name", "Unnamed"),
            description=data.get("description", ""),
            author=data.get("author", "unknown"),
            version=data.get("version", "1.0"),
            created=data.get("created", ""),
            modified=data.get("modified", ""),
            channels=channels,
            use_symmetry_correction=data.get("use_symmetry_correction", False),
            symmetry_gain_left=data.get("symmetry_gain_left", 1.0),
            symmetry_gain_right=data.get("symmetry_gain_right", 1.0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def clone(self) -> CalibrationProfile:
        return CalibrationProfile.from_dict(self.to_dict())


# ---- Part 3: Neutral Calibration ----------------------------------------

class NeutralCapture:
    """
    Helper for capturing neutral calibration from multiple frames.
    """
    def __init__(self):
        self._accumulator: Dict[str, float] = {}
        self._count: Dict[str, int] = {}

    def add_frame(self, frame: Dict[str, float]) -> None:
        """Add a frame to the neutral capture."""
        for ch, val in frame.items():
            if not isinstance(val, (int, float)):
                continue
            if ch not in self._accumulator:
                self._accumulator[ch] = 0.0
                self._count[ch] = 0
            self._accumulator[ch] += val
            self._count[ch] += 1

    def get_neutral(self) -> Dict[str, float]:
        """Return the average neutral values."""
        neutral = {}
        for ch in self._accumulator:
            if self._count[ch] > 0:
                neutral[ch] = self._accumulator[ch] / self._count[ch]
            else:
                neutral[ch] = 0.0
        return neutral

    def reset(self) -> None:
        self._accumulator.clear()
        self._count.clear()


# ---- Part 4: Range Calibration -----------------------------------------

class RangeCapture:
    """
    Helper for capturing maximum range from multiple frames.
    """
    def __init__(self):
        self._max_values: Dict[str, float] = {}

    def add_frame(self, frame: Dict[str, float]) -> None:
        """Update maximum values from a frame."""
        for ch, val in frame.items():
            if not isinstance(val, (int, float)):
                continue
            if ch not in self._max_values or val > self._max_values[ch]:
                self._max_values[ch] = val

    def get_maxima(self) -> Dict[str, float]:
        return self._max_values.copy()

    def reset(self) -> None:
        self._max_values.clear()


# ---- Part 5: Channel Calibration (implemented in ChannelCalibration) ----

# ---- Part 6: Symmetry Calibration --------------------------------------

class SymmetryCalibrator:
    """
    Helper to compute symmetry correction factors from paired channels.
    """
    @staticmethod
    def compute_symmetry_gains(
        frame: Dict[str, float],
        pair_map: Dict[str, str] = LEFT_RIGHT_PAIRS,
    ) -> Tuple[float, float]:
        """
        Compute left and right symmetry gains from a single frame.
        Returns (gain_left, gain_right) such that left * gain_left ≈ right * gain_right.
        """
        # Collect left and right values for paired channels
        left_vals = []
        right_vals = []
        for left, right in pair_map.items():
            if left in frame and right in frame:
                left_vals.append(frame[left])
                right_vals.append(frame[right])
        if not left_vals:
            return 1.0, 1.0  # no pairs

        # Compute average ratio
        ratios = []
        for l, r in zip(left_vals, right_vals):
            if l > 0.001 and r > 0.001:
                ratios.append(l / r)
        if not ratios:
            return 1.0, 1.0
        avg_ratio = sum(ratios) / len(ratios)
        # We want left * gain_left = right * gain_right = normalized value
        # Choose gain_left = 1.0, gain_right = avg_ratio (if left is reference)
        # Or we can make them such that gain_left * gain_right = 1
        # For simplicity, set gain_left = 1.0, gain_right = avg_ratio
        return 1.0, avg_ratio


# ---- Part 7: Runtime Normalization (implemented in CalibrationProfile.normalize) ----

# ---- Part 8: Calibration Profiles --------------------------------------

class CalibrationProfileManager:
    """
    Manages multiple calibration profiles.
    """
    def __init__(self):
        self._profiles: Dict[str, CalibrationProfile] = {}
        self._active_profile_name: Optional[str] = None

    def add_profile(self, profile: CalibrationProfile) -> None:
        self._profiles[profile.name] = profile

    def remove_profile(self, name: str) -> None:
        if name in self._profiles:
            del self._profiles[name]
            if self._active_profile_name == name:
                self._active_profile_name = None

    def get_profile(self, name: str) -> Optional[CalibrationProfile]:
        return self._profiles.get(name)

    def active_profile(self) -> Optional[CalibrationProfile]:
        if self._active_profile_name:
            return self._profiles.get(self._active_profile_name)
        return None

    def set_active(self, name: str) -> None:
        if name not in self._profiles:
            raise CalibrationProfileError(f"Profile '{name}' not found")
        self._active_profile_name = name

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def clear(self) -> None:
        self._profiles.clear()
        self._active_profile_name = None


# ---- Part 9: Import / Export -------------------------------------------

class CalibrationSerializer:
    """
    Serialize and deserialize calibration profiles to/from JSON and binary.
    """
    @staticmethod
    def to_json(profile: CalibrationProfile) -> str:
        return json.dumps(profile.to_dict(), indent=2)

    @staticmethod
    def from_json(data: str) -> CalibrationProfile:
        try:
            obj = json.loads(data)
            return CalibrationProfile.from_dict(obj)
        except json.JSONDecodeError as e:
            raise CalibrationDataError(f"Invalid JSON: {e}")

    @staticmethod
    def save_to_file(profile: CalibrationProfile, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, indent=2)

    @staticmethod
    def load_from_file(filepath: str) -> CalibrationProfile:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return CalibrationProfile.from_dict(data)

    # Optional binary serialization (could use pickle or custom)
    @staticmethod
    def to_binary(profile: CalibrationProfile) -> bytes:
        import pickle
        return pickle.dumps(profile.to_dict())

    @staticmethod
    def from_binary(data: bytes) -> CalibrationProfile:
        import pickle
        obj = pickle.loads(data)
        return CalibrationProfile.from_dict(obj)


# ---- Part 10: Diagnostics & Statistics ---------------------------------

class CalibrationDiagnostics:
    """
    Generates diagnostic reports for calibration profiles.
    """
    @staticmethod
    def diagnose_profile(profile: CalibrationProfile) -> Dict[str, Any]:
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "channel_count": len(profile.channels),
            "enabled_count": sum(1 for c in profile.channels.values() if c.enabled),
            "dead_zone_count": sum(1 for c in profile.channels.values() if c.dead_zone > 0.0),
            "neutral_range": {},
            "gain_range": {},
        }
        # Check each channel
        for ch_name, cal in profile.channels.items():
            # Check neutral vs maximum
            if cal.maximum <= cal.neutral:
                report["warnings"].append(f"Channel '{ch_name}': maximum <= neutral")
            # Check gain
            if cal.gain < 0.0 or cal.gain > 10.0:
                report["warnings"].append(f"Channel '{ch_name}': gain {cal.gain} is extreme")
            # Check dead zone
            if cal.dead_zone > 0.5:
                report["warnings"].append(f"Channel '{ch_name}': dead zone {cal.dead_zone} is large")
            # Check clamp
            if cal.clamp_min >= cal.clamp_max:
                report["errors"].append(f"Channel '{ch_name}': clamp_min >= clamp_max")
                report["is_valid"] = False

        # Check symmetry gains
        if profile.use_symmetry_correction:
            if profile.symmetry_gain_left <= 0.0 or profile.symmetry_gain_right <= 0.0:
                report["errors"].append("Symmetry gains must be positive")
                report["is_valid"] = False

        return report

    @staticmethod
    def statistics(profile: CalibrationProfile) -> Dict[str, Any]:
        stats = {
            "channel_count": len(profile.channels),
            "enabled_count": 0,
            "average_neutral": 0.0,
            "average_gain": 0.0,
            "average_dead_zone": 0.0,
            "total_dead_zones": 0,
        }
        if not profile.channels:
            return stats
        total_neutral = 0.0
        total_gain = 0.0
        total_dead = 0.0
        enabled = 0
        dead_count = 0
        for cal in profile.channels.values():
            if cal.enabled:
                enabled += 1
            total_neutral += cal.neutral
            total_gain += cal.gain
            total_dead += cal.dead_zone
            if cal.dead_zone > 0.0:
                dead_count += 1
        n = len(profile.channels)
        stats["enabled_count"] = enabled
        stats["average_neutral"] = total_neutral / n
        stats["average_gain"] = total_gain / n
        stats["average_dead_zone"] = total_dead / n
        stats["total_dead_zones"] = dead_count
        stats["use_symmetry"] = profile.use_symmetry_correction
        if profile.use_symmetry_correction:
            stats["symmetry_gain_left"] = profile.symmetry_gain_left
            stats["symmetry_gain_right"] = profile.symmetry_gain_right
        return stats


# ---- Part 11: Public API ------------------------------------------------

class CalibrationManager:
    """
    Main public API for calibration system.

    Provides:
        - Creating and editing calibration profiles
        - Capturing neutral and range from frames
        - Applying calibration to frames
        - Switching between profiles
        - Import/Export of profiles
        - Diagnostics and statistics
    """
    def __init__(self):
        self._profile_manager = CalibrationProfileManager()
        self._neutral_capturer = NeutralCapture()
        self._range_capturer = RangeCapture()
        self._validator = ARKitValidator() if 'ARKitValidator' in globals() else None
        self._current_calibration_target: Optional[str] = None  # name of profile being edited

    # --- Profile Management ---

    def create_profile(self, name: str, **kwargs) -> CalibrationProfile:
        """Create a new empty calibration profile."""
        profile = CalibrationProfile(name=name, **kwargs)
        self._profile_manager.add_profile(profile)
        return profile

    def get_profile(self, name: str) -> Optional[CalibrationProfile]:
        return self._profile_manager.get_profile(name)

    def remove_profile(self, name: str) -> None:
        self._profile_manager.remove_profile(name)

    def list_profiles(self) -> List[str]:
        return self._profile_manager.list_profiles()

    def set_active_profile(self, name: str) -> None:
        self._profile_manager.set_active(name)

    def active_profile(self) -> Optional[CalibrationProfile]:
        return self._profile_manager.active_profile()

    def clone_profile(self, source_name: str, new_name: str) -> CalibrationProfile:
        """Clone an existing profile."""
        source = self.get_profile(source_name)
        if not source:
            raise CalibrationProfileError(f"Profile '{source_name}' not found")
        clone = source.clone()
        clone.name = new_name
        self._profile_manager.add_profile(clone)
        return clone

    # --- Editing Profile (Calibration) ---

    def start_editing(self, profile_name: str) -> None:
        """Set the profile to be edited by subsequent capture calls."""
        if profile_name not in self._profile_manager._profiles:
            raise CalibrationProfileError(f"Profile '{profile_name}' not found")
        self._current_calibration_target = profile_name

    def stop_editing(self) -> None:
        self._current_calibration_target = None
        self._neutral_capturer.reset()
        self._range_capturer.reset()

    def add_neutral_frame(self, frame: Dict[str, float]) -> None:
        """Add a frame to the neutral capture accumulator."""
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing. Call start_editing() first.")
        self._neutral_capturer.add_frame(frame)

    def add_range_frame(self, frame: Dict[str, float]) -> None:
        """Add a frame to the range capture accumulator."""
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing. Call start_editing() first.")
        self._range_capturer.add_frame(frame)

    def capture_neutral(self, clear_accumulator: bool = True) -> Dict[str, float]:
        """
        Capture the current neutral accumulator into the active profile.
        Returns the neutral values captured.
        """
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing.")
        profile = self.get_profile(self._current_calibration_target)
        if profile is None:
            raise CalibrationProfileError("Profile not found")

        neutral = self._neutral_capturer.get_neutral()
        profile.capture_neutral(neutral)
        if clear_accumulator:
            self._neutral_capturer.reset()
        return neutral

    def capture_range(self, clear_accumulator: bool = True) -> Dict[str, float]:
        """
        Capture the current range (maximum) accumulator into the active profile.
        Returns the maximum values.
        """
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing.")
        profile = self.get_profile(self._current_calibration_target)
        if profile is None:
            raise CalibrationProfileError("Profile not found")

        maxima = self._range_capturer.get_maxima()
        profile.capture_maximum(maxima)
        if clear_accumulator:
            self._range_capturer.reset()
        return maxima

    def compute_gains_from_ranges(self) -> None:
        """Compute gains for the active profile based on neutral and maximum ranges."""
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing.")
        profile = self.get_profile(self._current_calibration_target)
        if profile is None:
            raise CalibrationProfileError("Profile not found")
        profile.compute_gain_from_ranges()

    def set_symmetry_correction(self, enabled: bool, left_gain: float = 1.0, right_gain: float = 1.0) -> None:
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing.")
        profile = self.get_profile(self._current_calibration_target)
        if profile is None:
            raise CalibrationProfileError("Profile not found")
        profile.use_symmetry_correction = enabled
        profile.symmetry_gain_left = left_gain
        profile.symmetry_gain_right = right_gain

    def calibrate_channel(self, channel: str, **kwargs) -> None:
        """Update calibration parameters for a specific channel in the active profile."""
        if self._current_calibration_target is None:
            raise CalibrationStateError("No profile set for editing.")
        profile = self.get_profile(self._current_calibration_target)
        if profile is None:
            raise CalibrationProfileError("Profile not found")
        cal = profile.get_channel(channel)
        for key, value in kwargs.items():
            if hasattr(cal, key):
                setattr(cal, key, value)

    # --- Runtime Normalization ---

    def normalize(self, frame: Dict[str, float], profile_name: Optional[str] = None) -> Dict[str, float]:
        """
        Apply calibration to a raw ARKit frame using a specific profile or the active one.
        """
        if profile_name is None:
            profile = self.active_profile()
        else:
            profile = self.get_profile(profile_name)
        if profile is None:
            raise CalibrationProfileError("No active profile or specified profile not found")
        return profile.normalize(frame)

    # --- Automatic Calibration from Recording ---

    def auto_calibrate_from_recordings(
        self,
        neutral_frames: List[Dict[str, float]],
        smile_frames: List[Dict[str, float]],
        blink_frames: List[Dict[str, float]],
        jawopen_frames: List[Dict[str, float]],
        profile_name: str = "AutoCalibrated",
    ) -> CalibrationProfile:
        """
        Automatic calibration from captured recordings.
        This is a simplified version; a full implementation would detect
        neutral, smile, blink, jaw open from a longer recording.
        """
        # Capture neutral
        for f in neutral_frames:
            self.add_neutral_frame(f)
        neutral = self.capture_neutral()

        # Capture maxima
        for frames in [smile_frames, blink_frames, jawopen_frames]:
            for f in frames:
                self.add_range_frame(f)
        maxima = self.capture_range()

        # Create profile
        profile = self.create_profile(profile_name)
        # Update neutral and maxima
        profile.capture_neutral(neutral)
        profile.capture_maximum(maxima)
        profile.compute_gain_from_ranges()

        return profile

    # --- Import/Export ---

    def save_profile(self, name: str, filepath: str) -> None:
        profile = self.get_profile(name)
        if not profile:
            raise CalibrationProfileError(f"Profile '{name}' not found")
        CalibrationSerializer.save_to_file(profile, filepath)

    def load_profile(self, filepath: str) -> CalibrationProfile:
        profile = CalibrationSerializer.load_from_file(filepath)
        self._profile_manager.add_profile(profile)
        return profile

    def export_active(self, filepath: str) -> None:
        profile = self.active_profile()
        if not profile:
            raise CalibrationProfileError("No active profile")
        CalibrationSerializer.save_to_file(profile, filepath)

    def import_profile(self, filepath: str) -> CalibrationProfile:
        return self.load_profile(filepath)

    # --- Diagnostics & Statistics ---

    def diagnose(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        profile = self.get_profile(profile_name) if profile_name else self.active_profile()
        if not profile:
            return {"is_valid": False, "errors": ["No profile selected"]}
        return CalibrationDiagnostics.diagnose_profile(profile)

    def statistics(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        profile = self.get_profile(profile_name) if profile_name else self.active_profile()
        if not profile:
            return {}
        return CalibrationDiagnostics.statistics(profile)

    # --- Reset ---

    def reset_profile(self, profile_name: Optional[str] = None) -> None:
        """Reset a profile to default (all channels reset)."""
        profile = self.get_profile(profile_name) if profile_name else self.active_profile()
        if not profile:
            return
        for channel in profile.channels.keys():
            profile.channels[channel] = ChannelCalibration()


# ---- Public API --------------------------------------------------------

__all__ = [
    "CalibrationManager",
    "CalibrationProfile",
    "ChannelCalibration",
    "CalibrationProfileManager",
    "CalibrationSerializer",
    "NeutralCapture",
    "RangeCapture",
    "SymmetryCalibrator",
    "GainCurve",
    "ARKitCalibrationError",
    "CalibrationProfileError",
    "CalibrationDataError",
    "CalibrationStateError",
]