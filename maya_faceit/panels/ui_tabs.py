# __init__.py
# Maya Faceit Plugin - Panels Module
# Version: 1.0.0

"""
Faceit Panels Module for Maya
=============================

This module provides UI panels for the Faceit plugin using PySide2/PySide6.

Main Components:
    - Main UI window with tabbed interface
    - Setup, Rigging, Expressions, Shapes, Control Rig, Mocap, Bake, Retarget, Utils tabs
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

# Import UI components
from .ui_main import (
    FaceitMainWindow,
    show_faceit_window,
    close_faceit_window,
    is_faceit_window_open,
)

# Import tab components
from .ui_main import (
    SetupTab,
    RiggingTab,
    ExpressionsTab,
    ShapesTab,
    ControlRigTab,
    MocapTab,
    BakeTab,
    RetargetTab,
    UtilsTab,
)

# Import panel classes (for compatibility with Blender-style UI)
from .ui import (
    FACEIT_PT_Base,
    FACEIT_PT_BaseSub,
    FACEIT_PT_MainPanel,
)

from .draw_utils import (
    draw_web_link,
    draw_text_block,
    draw_anime_style_eyes,
    draw_head_targets_layout,
)

# ============================================================
# Module Registration
# ============================================================

def register_panels():
    """Register Faceit panels with Maya."""
    print("Faceit panels registered")


def unregister_panels():
    """Unregister Faceit panels from Maya."""
    close_faceit_window()
    print("Faceit panels unregistered")


def initialize_module():
    """Initialize the panels module."""
    print(f"Panels Module v{__version__} initialized")
    if not is_faceit_window_open():
        show_faceit_window()


def uninitialize_module():
    """Uninitialize the panels module."""
    unregister_panels()
    print(f"Panels Module v{__version__} uninitialized")


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # UI Base
    'FACEIT_PT_Base',
    'FACEIT_PT_BaseSub',
    'FACEIT_PT_MainPanel',
    
    # Main Window
    'FaceitMainWindow',
    'show_faceit_window',
    'close_faceit_window',
    'is_faceit_window_open',
    
    # Tabs
    'SetupTab',
    'RiggingTab',
    'ExpressionsTab',
    'ShapesTab',
    'ControlRigTab',
    'MocapTab',
    'BakeTab',
    'RetargetTab',
    'UtilsTab',
    
    # Draw utilities
    'draw_web_link',
    'draw_text_block',
    'draw_anime_style_eyes',
    'draw_head_targets_layout',
    
    # Module functions
    'register_panels',
    'unregister_panels',
    'initialize_module',
    'uninitialize_module',
]