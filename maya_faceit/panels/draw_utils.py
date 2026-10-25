# draw_utils.py
# Maya Faceit Plugin - Draw Utilities
# Converted from Blender to Maya Python 3.11

"""
Drawing utilities for Faceit Maya plugin.
Provides helper functions for UI drawing.
"""

import maya.cmds as cmds
import textwrap
from typing import List, Optional, Any


def draw_web_link(layout: Any, link: str, text_ui: str = '', show_always: bool = False) -> None:
    """
    Draw a web link in the given layout.
    
    Args:
        layout: UI layout
        link: URL link
        text_ui: Optional text to display
        show_always: Whether to always show
    """
    # In Maya, we'd create a clickable label
    layout.text(text_ui or link)


def draw_text_block(
    layout: Any,
    self: Any = None,
    code: str = '',
    text: str = '',
    heading: str = '',
    heading_icon: str = 'ERROR',
    draw_in_op: bool = False,
    chars_per_row: int = 50,
    alert: bool = False
) -> Any:
    """
    Wrap a block of text into multiple lines.
    
    Args:
        layout: UI layout
        self: Operator self reference
        code: Optional code to execute
        text: Text to display
        heading: Optional heading
        heading_icon: Icon for heading
        draw_in_op: Whether drawing in operator
        chars_per_row: Characters per row
        alert: Whether to show as alert
        
    Returns:
        Layout column
    """
    if draw_in_op:
        chars_per_row = 45
    
    # In Maya, we'd create a text layout
    layout.text(heading if heading else text)
    
    for txt_row in textwrap.wrap(text, chars_per_row):
        layout.text(txt_row)
    
    return layout


def draw_anime_style_eyes(layout: Any, scene: Any = None) -> None:
    """
    Draw anime style eyes layout.
    
    Args:
        layout: UI layout
        scene: Scene object
    """
    # In Maya, we'd draw eye settings
    layout.text("Anime Style Eyes")


def draw_head_targets_layout(layout: Any, scene: Any = None, show_head_action: bool = True) -> None:
    """
    Draw head targets layout.
    
    Args:
        layout: UI layout
        scene: Scene object
        show_head_action: Whether to show head action
    """
    # In Maya, we'd draw head target settings
    layout.text("Head Target")