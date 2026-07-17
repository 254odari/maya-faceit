"""
manager.py

ARKitCalibration manager – profiles, activation, frame calibration.
"""

from typing import Dict, List, Optional

from .enums import CalibrationCurve
from .models import ChannelCalibration, CalibrationProfile
from ..channels import ARKitChannel


class ARKitCalibration:
    """
    Manages calibration profiles for ARKit coefficient conversion.

    Usage:
        cal = ARKitCalibration()
        cal.profile("MyProfile").calibration(ARKitChannel.JAW_OPEN).multiplier = 1.2
        calibrated = cal.calibrate_frame(raw_coefficients)
    """

    def __init__(self):
        self._profiles: Dict[str, CalibrationProfile] = {}
        self._active = "Default"
        self.create_profile("Default")

    # --------------------------------------------------------
    # Profile Management
    # --------------------------------------------------------

    def create_profile(self, name: str) -> CalibrationProfile:
        """Create a new empty profile."""
        if name in self._profiles:
            raise KeyError(f"Profile '{name}' already exists.")
        profile = CalibrationProfile(name=name)
        self._profiles[name] = profile
        return profile

    def delete_profile(self, name: str) -> None:
        """Delete a profile (cannot delete the active one)."""
        if name == self._active:
            raise ValueError("Cannot delete the active profile.")
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' not found.")
        del self._profiles[name]

    def get_profile(self, name: Optional[str] = None) -> CalibrationProfile:
        """Get a profile by name, or the active profile if name is None."""
        if name is None:
            name = self._active
        if name not in self._profiles:
            raise KeyError(f"Profile '{name}' not found.")
        return self._profiles[name]

    def set_active(self, name: str) -> None:
        """Set the active profile."""
        if name not in self._profiles:
            raise KeyError(f"Unknown profile: {name}")
        self._active = name

    @property
    def active_profile(self) -> str:
        return self._active

    @property
    def profiles(self) -> List[str]:
        return list(self._profiles.keys())

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    def evaluate(self, channel: ARKitChannel, value: float) -> float:
        """Apply the active profile's calibration to a single channel."""
        return self.get_profile().evaluate(channel, value)

    def calibrate_frame(
        self,
        coefficients: Dict[ARKitChannel, float],
    ) -> Dict[ARKitChannel, float]:
        """
        Apply the active calibration profile to an entire frame of coefficients.

        Args:
            coefficients: Raw ARKit coefficients (channel -> value).

        Returns:
            Calibrated coefficients.
        """
        profile = self.get_profile()
        output = {}
        for channel, value in coefficients.items():
            output[channel] = profile.evaluate(channel, value)
        return output

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------

    def serialize(self) -> dict:
        return {
            "active": self._active,
            "profiles": {
                name: profile.serialize()
                for name, profile in self._profiles.items()
            },
        }

    def deserialize(self, data: dict) -> None:
        """Load calibration profiles from serialized data."""
        self._profiles.clear()
        for name, prof_data in data.get("profiles", {}).items():
            profile = CalibrationProfile(name=name)
            for ch_str, cal_data in prof_data.get("channels", {}).items():
                try:
                    channel = ARKitChannel(ch_str)
                except ValueError:
                    continue
                cal = ChannelCalibration(
                    multiplier=cal_data.get("multiplier", 1.0),
                    offset=cal_data.get("offset", 0.0),
                    minimum=cal_data.get("minimum", 0.0),
                    maximum=cal_data.get("maximum", 1.0),
                    enabled=cal_data.get("enabled", True),
                    curve=CalibrationCurve(cal_data.get("curve", "linear")),
                )
                profile.channels[channel] = cal
            profile.metadata = prof_data.get("metadata", {})
            self._profiles[name] = profile
        self._active = data.get("active", "Default")
        if self._active not in self._profiles and self._profiles:
            self._active = next(iter(self._profiles.keys()))
        elif not self._profiles:
            self.create_profile("Default")


# ============================================================
# Singleton
# ============================================================

arkit_calibration = ARKitCalibration()