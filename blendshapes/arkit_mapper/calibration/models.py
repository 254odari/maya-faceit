"""
models.py

Data models for calibration.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from .enums import CalibrationCurve
from ..channels import ARKitChannel


@dataclass(slots=True)
class ChannelCalibration:
    """
    Calibration settings for a single ARKit channel.
    """

    multiplier: float = 1.0
    offset: float = 0.0
    minimum: float = 0.0
    maximum: float = 1.0
    enabled: bool = True
    curve: CalibrationCurve = CalibrationCurve.LINEAR

    def evaluate(self, value: float) -> float:
        """
        Apply calibration to a raw coefficient value.

        Args:
            value: Raw coefficient (0-1).

        Returns:
            Calibrated value.
        """
        if not self.enabled:
            return value

        value *= self.multiplier
        value += self.offset
        value = self._apply_curve(value)
        value = max(self.minimum, min(self.maximum, value))

        return value

    def _apply_curve(self, value: float) -> float:
        """
        Apply the selected easing curve.
        Assumes value is already clamped to [0, 1].
        """
        value = max(0.0, min(1.0, value))

        if self.curve == CalibrationCurve.LINEAR:
            return value

        if self.curve == CalibrationCurve.EASE_IN:
            return value * value

        if self.curve == CalibrationCurve.EASE_OUT:
            return value * (2.0 - value)

        if self.curve == CalibrationCurve.EASE_IN_OUT:
            if value < 0.5:
                return 2 * value * value
            return -1 + (4 - 2 * value) * value

        return value

    def serialize(self) -> dict:
        return {
            "multiplier": self.multiplier,
            "offset": self.offset,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "enabled": self.enabled,
            "curve": self.curve.value,
        }


@dataclass(slots=True)
class CalibrationProfile:
    """
    Named collection of channel calibrations.
    """

    name: str
    channels: Dict[ARKitChannel, ChannelCalibration] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def calibration(self, channel: ARKitChannel) -> ChannelCalibration:
        """Get or create a calibration for a channel."""
        if channel not in self.channels:
            self.channels[channel] = ChannelCalibration()
        return self.channels[channel]

    def evaluate(self, channel: ARKitChannel, value: float) -> float:
        """Evaluate calibration for a single channel."""
        return self.calibration(channel).evaluate(value)

    def serialize(self) -> dict:
        return {
            "name": self.name,
            "channels": {
                channel.value: cal.serialize()
                for channel, cal in self.channels.items()
            },
            "metadata": self.metadata,
        }