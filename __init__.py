# -*- coding: utf-8 -*-
"""
maya_faceit – Professional facial rigging & blendshape pipeline for Maya.

This is the main entry point for the plugin.
"""

import logging
import sys
from pathlib import Path

# Version
from .version import __version__, __author__, __license__, VERSION_STRING

# Application core
from .application import Application, get_application

# Logger
logger = logging.getLogger("maya_faceit")

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def bootstrap() -> bool:
    """Run the bootstrap phase (early initialization)."""
    app = get_application()
    return app.bootstrap()


def startup() -> bool:
    """Start the plugin (load services, UI, etc.)."""
    app = get_application()
    return app.startup()


def shutdown() -> bool:
    """Shut down the plugin cleanly."""
    app = get_application()
    return app.shutdown()


def show() -> None:
    """Show the main UI window."""
    try:
        from .ui import launch_ui
        launch_ui()
    except ImportError as e:
        logger.error("Failed to import UI module: %s", e)
        raise


def get_version() -> str:
    """Return the plugin version string."""
    return VERSION_STRING


# -----------------------------------------------------------------------------
# Package metadata
# -----------------------------------------------------------------------------

__all__ = [
    "Application",
    "get_application",
    "bootstrap",
    "startup",
    "shutdown",
    "show",
    "get_version",
    "__version__",
    "__author__",
    "__license__",
    "VERSION_STRING",
]


# -----------------------------------------------------------------------------
# Auto-initialization (optional)
# -----------------------------------------------------------------------------

# If this module is imported in Maya, we can optionally bootstrap automatically.
# But we leave this to the user or to startup.py to avoid side-effects.
# We'll set a flag to prevent double init.
if not getattr(sys, "_maya_faceit_auto_initialized", False):
    # You can uncomment the following lines to auto-init on import:
    # sys._maya_faceit_auto_initialized = True
    # bootstrap()
    # startup()
    pass