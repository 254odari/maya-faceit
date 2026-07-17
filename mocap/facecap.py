"""
mocap/facecap.py

FaceCap (iPhone) integration.

Processes FaceCap data format and converts to Faceit blendshape format.

FaceCap is an iOS app that captures facial motion using the TrueDepth camera.
It streams data in a format similar to ARKit but with some differences in
naming and structure. This module handles the conversion.

Features:
- Parse FaceCap JSON data
- Convert to ARKit blendshape format
- Apply calibration
- Normalize and clamp values
- Extract head pose data

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Tuple, Union

# Import from other modules
try:
    from ..blendshapes.blendshape_utils import clamp, normalize_weights
    from ..arkit.arkit52 import ARKIT_SET
    HAS_DEPS = True
except ImportError:
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights):
        total = sum(weights.values())
        if total == 0:
            return {k: 0.0 for k in weights}
        return {k: v / total for k, v in weights.items()}
    ARKIT_SET = set()
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class FaceCapError(Exception):
    """Base exception for FaceCap operations."""
    pass


# ---- Data Models ----

@dataclass
class FaceCapSettings:
    """
    Settings for FaceCap processing.
    """
    source_format: str = "arkit"           # 'arkit', 'facecap'
    apply_calibration: bool = True         # Apply calibration profile
    normalize: bool = True                 # Normalize weights
    clamp_values: bool = True              # Clamp to [0, 1]
    calibration_profile: Optional[Dict[str, Dict[str, float]]] = None


@dataclass
class FaceCapData:
    """
    FaceCap frame data.
    """
    timestamp: float
    blendshapes: Dict[str, float]
    head_pose: Optional[Dict[str, float]] = None
    source: str = "FaceCap"
    frame_number: int = 0
    raw_data: Optional[Any] = None


# ---- FaceCap Processor ----

class FaceCapProcessor:
    """
    Process FaceCap data.

    Converts FaceCap format to Faceit's internal format (ARKit blendshapes).
    """

    def __init__(self, settings: Optional[FaceCapSettings] = None):
        """
        Initialize the FaceCap processor.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or FaceCapSettings()
        self._calibration_cache: Dict[str, Dict[str, float]] = {}
        logger.debug("FaceCapProcessor initialized")

    # ---- Processing Methods ----

    def process_json(self, json_data: str) -> FaceCapData:
        """
        Process JSON data from FaceCap.

        Args:
            json_data: JSON string from FaceCap.

        Returns:
            FaceCapData object.

        Raises:
            FaceCapError: If JSON parsing fails.
        """
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise FaceCapError(f"Invalid JSON: {e}")
        return self.process_dict(data)

    def process_dict(self, data: Dict[str, Any]) -> FaceCapData:
        """
        Process a dictionary from FaceCap.

        Args:
            data: Dictionary from FaceCap.

        Returns:
            FaceCapData object.
        """
        # Extract blendshapes
        blendshapes = self._extract_blendshapes(data)

        # Extract head pose
        head_pose = self._extract_head_pose(data)

        # Apply calibration
        if self.settings.apply_calibration:
            blendshapes = self._apply_calibration(blendshapes)

        # Clamp values
        if self.settings.clamp_values:
            blendshapes = {k: clamp(v, 0.0, 1.0) for k, v in blendshapes.items()}

        # Normalize
        if self.settings.normalize:
            blendshapes = normalize_weights(blendshapes)

        # Create result
        return FaceCapData(
            timestamp=data.get("timestamp", time.time()),
            blendshapes=blendshapes,
            head_pose=head_pose,
            frame_number=data.get("frame", 0),
            raw_data=data,
        )

    def _extract_blendshapes(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract blendshape coefficients from FaceCap data.

        FaceCap may use different keys:
        - "blendshapes"
        - "BlendShapes"
        - "blendshapeCoefficients"
        - "coefficients"
        - Or direct mapping (if already ARKit format)

        Returns:
            Dict of blendshape name -> value.
        """
        # Try common keys
        possible_keys = ["blendshapes", "BlendShapes", "blendshapeCoefficients", "coefficients"]

        for key in possible_keys:
            if key in data and isinstance(data[key], dict):
                raw = data[key]
                # Filter to valid values
                return self._filter_blendshapes(raw)

        # If not found, try to find any dict that looks like blendshapes
        for key, value in data.items():
            if isinstance(value, dict) and all(isinstance(v, (int, float)) for v in value.values()):
                # Check if it contains typical ARKit names
                arkit_keys = set(value.keys()) & ARKIT_SET
                if len(arkit_keys) > 0:
                    return self._filter_blendshapes(value)
                # If many values are between 0 and 1, it might be blendshapes
                values = list(value.values())
                if values and all(0.0 <= v <= 1.0 for v in values):
                    return self._filter_blendshapes(value)

        # Fallback: empty dict
        logger.warning("No blendshape data found in FaceCap frame")
        return {}

    def _filter_blendshapes(self, raw: Dict[str, Any]) -> Dict[str, float]:
        """
        Filter raw blendshape data to valid floats.

        Args:
            raw: Raw blendshape dictionary.

        Returns:
            Filtered dictionary.
        """
        result = {}
        for k, v in raw.items():
            try:
                val = float(v)
                # Filter out NaN, inf, and out-of-range (will clamp later)
                result[k] = val
            except (ValueError, TypeError):
                continue
        return result

    def _extract_head_pose(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Extract head pose from FaceCap data.

        Args:
            data: FaceCap data.

        Returns:
            Dict with pitch, yaw, roll, or None.
        """
        # Check for head pose keys
        pose = {}

        # Try "headPose"
        if "headPose" in data and isinstance(data["headPose"], dict):
            hp = data["headPose"]
            pose = {
                "pitch": float(hp.get("pitch", 0.0)),
                "yaw": float(hp.get("yaw", 0.0)),
                "roll": float(hp.get("roll", 0.0)),
            }
            return pose

        # Try "headRotation"
        if "headRotation" in data:
            hr = data["headRotation"]
            if isinstance(hr, list) and len(hr) >= 3:
                pose = {
                    "pitch": float(hr[0]),
                    "yaw": float(hr[1]),
                    "roll": float(hr[2]),
                }
                return pose
            if isinstance(hr, dict):
                pose = {
                    "pitch": float(hr.get("pitch", 0.0)),
                    "yaw": float(hr.get("yaw", 0.0)),
                    "roll": float(hr.get("roll", 0.0)),
                }
                return pose

        # Try "rotation"
        if "rotation" in data:
            rot = data["rotation"]
            if isinstance(rot, list) and len(rot) >= 3:
                pose = {
                    "pitch": float(rot[0]),
                    "yaw": float(rot[1]),
                    "roll": float(rot[2]),
                }
                return pose

        return None

    # ---- Calibration ----

    def _apply_calibration(self, data: Dict[str, float]) -> Dict[str, float]:
        """
        Apply calibration profile to the data.

        Args:
            data: Blendshape data.

        Returns:
            Calibrated data.
        """
        profile = self.settings.calibration_profile
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
                calibrated[channel] = val
            else:
                calibrated[channel] = value

        return calibrated

    def set_calibration_profile(self, profile: Dict[str, Dict[str, float]]) -> None:
        """
        Set the calibration profile.

        Args:
            profile: Dict mapping channel -> {neutral, gain, offset}.
        """
        self.settings.calibration_profile = profile

    def load_calibration_from_file(self, filepath: str) -> None:
        """
        Load calibration profile from a JSON file.

        Args:
            filepath: Path to JSON file.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        self.set_calibration_profile(profile)

    # ---- Batch Processing ----

    def process_batch(self, frames: List[Dict[str, Any]]) -> List[FaceCapData]:
        """
        Process a batch of FaceCap frames.

        Args:
            frames: List of FaceCap dictionaries.

        Returns:
            List of FaceCapData objects.
        """
        results = []
        for frame in frames:
            try:
                result = self.process_dict(frame)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing FaceCap frame: {e}")
        return results

    def process_json_batch(self, json_lines: List[str]) -> List[FaceCapData]:
        """
        Process a batch of JSON lines (one per frame).

        Args:
            json_lines: List of JSON strings.

        Returns:
            List of FaceCapData objects.
        """
        results = []
        for line in json_lines:
            try:
                result = self.process_json(line)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing JSON line: {e}")
        return results

    # ---- Utility ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processor statistics.

        Returns:
            Dict with processing stats.
        """
        return {
            "calibration_enabled": self.settings.apply_calibration,
            "normalize_enabled": self.settings.normalize,
            "clamp_enabled": self.settings.clamp_values,
            "calibration_profile_loaded": self.settings.calibration_profile is not None,
        }


# ---- Convenience Functions ----

def facecap_to_arkit(facecap_data: Dict[str, float]) -> Dict[str, float]:
    """
    Convert FaceCap blendshapes to ARKit format.

    FaceCap uses the same names as ARKit, so this is a direct pass-through.

    Args:
        facecap_data: FaceCap blendshape data.

    Returns:
        ARKit blendshape data.
    """
    return facecap_data.copy()


def facecap_to_faceit(facecap_data: Dict[str, float]) -> Dict[str, float]:
    """
    Convert FaceCap blendshapes to Faceit format.

    Faceit uses the same ARKit names.

    Args:
        facecap_data: FaceCap blendshape data.

    Returns:
        Faceit blendshape data.
    """
    return facecap_data.copy()


# ---- Public API ----

__all__ = [
    "FaceCapProcessor",
    "FaceCapSettings",
    "FaceCapData",
    "FaceCapError",
    "facecap_to_arkit",
    "facecap_to_faceit",
]