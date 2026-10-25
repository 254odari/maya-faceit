# __init__.py
# Maya Faceit Plugin - Panels Module
# Version: 1.0.0

__version__ = "1.0.0"

print("Faceit Panels module loading...")

# ============================================================
# Imports
# ============================================================

try:
    from .ui_main import (
        FaceitMainWindow,
        show_faceit_window,
        close_faceit_window,
        is_faceit_window_open,
    )
    _UI_AVAILABLE = True
    print("  UI main loaded")
except ImportError as e:
    print(f"  Warning: UI main not available: {e}")
    _UI_AVAILABLE = False

try:
    from .ui_tabs import (
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
    _TABS_AVAILABLE = True
    print("  UI tabs loaded")
except ImportError as e:
    print(f"  Warning: UI tabs not available: {e}")
    _TABS_AVAILABLE = False

# ============================================================
# Registration Functions
# ============================================================

def register_panels():
    """Register Faceit panels."""
    import maya.cmds as cmds
    if cmds.about(batch=True):
        return False
    if _UI_AVAILABLE and not is_faceit_window_open():
        show_faceit_window()
        return True
    return False

def unregister_panels():
    """Unregister Faceit panels."""
    if _UI_AVAILABLE:
        close_faceit_window()
    return True

def initialize_module():
    """Initialize the panels module."""
    print(f"Panels Module v{__version__} initializing...")
    register_panels()
    return True

def uninitialize_module():
    """Uninitialize the panels module."""
    print(f"Panels Module v{__version__} uninitializing...")
    unregister_panels()
    return True

# ============================================================
# Exports
# ============================================================

__all__ = [
    '__version__',
    'FaceitMainWindow',
    'show_faceit_window',
    'close_faceit_window',
    'is_faceit_window_open',
    'SetupTab',
    'RiggingTab',
    'ExpressionsTab',
    'ShapesTab',
    'ControlRigTab',
    'MocapTab',
    'BakeTab',
    'RetargetTab',
    'UtilsTab',
    'register_panels',
    'unregister_panels',
    'initialize_module',
    'uninitialize_module',
]

print("Faceit Panels module loaded successfully")