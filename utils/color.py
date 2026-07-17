# -*- coding: utf-8 -*-
"""
maya_faceit.utils.color
~~~~~~~~~~~~~~~~~~~~~~~

Color utilities.
"""

import maya.cmds as cmds # type: ignore
from typing import Tuple, List, Optional, Union


class ColorUtils:
    """Utilities for color operations."""

    # RGB → Index → Maya color index mapping (common colors)
    COLOR_MAP = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
        "pink": (255, 192, 203),
        "teal": (0, 128, 128),
    }

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB tuple to hex string."""
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def rgb_to_maya(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB (0-255) to Maya color (0-1)."""
        return (r/255.0, g/255.0, b/255.0)

    @staticmethod
    def maya_to_rgb(r: float, g: float, b: float) -> Tuple[int, int, int]:
        """Convert Maya color (0-1) to RGB (0-255)."""
        return (int(r*255), int(g*255), int(b*255))

    @staticmethod
    def set_override_color(node: str, color: Tuple[float, float, float]) -> bool:
        """Set the override color of a node."""
        if not cmds.objExists(node):
            return False
        cmds.setAttr(f"{node}.overrideEnabled", 1)
        cmds.setAttr(f"{node}.overrideRGBColors", 1)
        cmds.setAttr(f"{node}.overrideColorR", color[0])
        cmds.setAttr(f"{node}.overrideColorG", color[1])
        cmds.setAttr(f"{node}.overrideColorB", color[2])
        return True

    @staticmethod
    def set_override_color_index(node: str, color_index: int) -> bool:
        """Set the override color by Maya color index (1-31)."""
        if not cmds.objExists(node):
            return False
        cmds.setAttr(f"{node}.overrideEnabled", 1)
        cmds.setAttr(f"{node}.overrideColor", color_index)
        return True

    @staticmethod
    def get_override_color(node: str) -> Optional[Tuple[float, float, float]]:
        """Get the override color of a node."""
        if not cmds.objExists(node):
            return None
        if cmds.getAttr(f"{node}.overrideEnabled"):
            if cmds.getAttr(f"{node}.overrideRGBColors"):
                r = cmds.getAttr(f"{node}.overrideColorR")
                g = cmds.getAttr(f"{node}.overrideColorG")
                b = cmds.getAttr(f"{node}.overrideColorB")
                return (r, g, b)
            else:
                idx = cmds.getAttr(f"{node}.overrideColor")
                return ColorUtils.maya_color_index_to_rgb(idx)
        return None

    @staticmethod
    def maya_color_index_to_rgb(index: int) -> Tuple[float, float, float]:
        """Convert Maya color index (1-31) to RGB (0-1)."""
        # This is simplified; Maya has specific color indices.
        # For production, we'd need a full mapping.
        return (0.5, 0.5, 0.5)

    @staticmethod
    def lerp_color(c1: Tuple[float, float, float],
                   c2: Tuple[float, float, float],
                   t: float) -> Tuple[float, float, float]:
        """Linear interpolate between two colors."""
        return (
            c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t
        )