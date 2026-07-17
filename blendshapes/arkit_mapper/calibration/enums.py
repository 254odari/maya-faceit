"""
enums.py

Enumerations for calibration.
"""

from enum import Enum


class CalibrationCurve(Enum):
    """Easing curves for calibration values."""

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"