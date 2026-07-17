"""
maya_faceit/blendshapes/arkit_mapper/calibration/__init__.py

Calibration system for ARKit coefficients.

Provides:
    • Channel-level calibration (multiplier, offset, min/max, curves)
    • Calibration profiles (named collections of channel calibrations)
    • Profile management (create, switch, serialize)

Target
------
Maya 2026
Python 3.11
"""

from .enums import CalibrationCurve
from .models import ChannelCalibration, CalibrationProfile
from .manager import ARKitCalibration, arkit_calibration

__all__ = [
    "CalibrationCurve",
    "ChannelCalibration",
    "CalibrationProfile",
    "ARKitCalibration",
    "arkit_calibration",
]