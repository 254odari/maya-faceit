# -*- coding: utf-8 -*-
"""
maya_faceit.startup

Startup script for Maya FaceIT.

This module is typically called from userSetup.py to load the plugin on Maya startup.
It ensures the plugin is bootstrapped and started, and provides a `show()` function
to launch the UI.

Usage in userSetup.py:
    import maya_faceit.startup
    maya_faceit.startup.auto_start()
"""

import logging
import sys
from pathlib import Path

# Add the package to sys.path if needed (though usually it's already there)
package_dir = Path(__file__).parent
if str(package_dir) not in sys.path:
    sys.path.insert(0, str(package_dir))

logger = logging.getLogger("maya_faceit")


def auto_start() -> bool:
    """
    Automatically bootstrap and start the plugin.
    This is the main entry point for userSetup.py.
    """
    try:
        from . import bootstrap, startup
        if not bootstrap():
            logger.error("Maya FaceIT bootstrap failed.")
            return False
        if not startup():
            logger.error("Maya FaceIT startup failed.")
            return False
        logger.info("Maya FaceIT auto-started successfully.")
        return True
    except Exception as e:
        logger.exception("Auto-start error: %s", e)
        return False


def show() -> None:
    """Show the main UI window."""
    try:
        from . import show as show_ui
        show_ui()
    except Exception as e:
        logger.exception("Failed to show UI: %s", e)


# -----------------------------------------------------------------------------
# Auto-run when imported? (We'll leave it to the user to call auto_start)
# -----------------------------------------------------------------------------

# If you want to automatically start when this module is imported, uncomment:
# if not getattr(sys, "_maya_faceit_startup_ran", False):
#     sys._maya_faceit_startup_ran = True
#     auto_start()

__all__ = ["auto_start", "show"]