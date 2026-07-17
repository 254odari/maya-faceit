"""
enums.py

Enumerations for the converter.
"""

from enum import Enum


class MergeMode(str, Enum):
    """
    Determines how multiple ARKit channels contribute
    to the same rig target.
    """

    MAX = "max"
    ADD = "add"
    AVERAGE = "average"
    OVERRIDE = "override"