# -*- coding: utf-8 -*-
"""
maya_faceit.plugin

Maya plugin entry point.

This module is loaded by Maya when the plugin is enabled.
It handles the plugin lifecycle: initialization and uninitialization.
"""

import logging
import sys

# Import the public API from the root package
from maya_faceit import bootstrap, startup, shutdown, show, get_application

logger = logging.getLogger(__name__)


def initializePlugin(plugin_name: str) -> None:
    """
    Maya calls this when the plugin is loaded.

    Args:
        plugin_name: The name of the plugin (as registered in Maya).
    """
    logger.info("Initializing Maya FaceIT plugin: %s", plugin_name)

    try:
        # Run bootstrap and startup
        if not bootstrap():
            logger.error("Bootstrap failed.")
            return

        if not startup():
            logger.error("Startup failed.")
            return

        logger.info("Maya FaceIT plugin initialized successfully.")

        # Show the main UI window
        show()

    except Exception as e:
        logger.exception("Error during plugin initialization: %s", e)
        # Re-raise to let Maya know something went wrong
        raise


def uninitializePlugin(plugin_name: str) -> None:
    """
    Maya calls this when the plugin is unloaded.

    Args:
        plugin_name: The name of the plugin (as registered in Maya).
    """
    logger.info("Uninitializing Maya FaceIT plugin: %s", plugin_name)

    try:
        if not shutdown():
            logger.error("Shutdown failed.")
            return

        logger.info("Maya FaceIT plugin uninitialized successfully.")

    except Exception as e:
        logger.exception("Error during plugin uninitialization: %s", e)
        raise


# -----------------------------------------------------------------------------
# Optional: Register the plugin with Maya's plugin manager (if loaded directly)
# -----------------------------------------------------------------------------

def maya_useNewAPI() -> None:
    """
    This function is recognized by Maya to indicate that the plugin
    uses the new API (which we do by using Python).
    """
    pass


# -----------------------------------------------------------------------------
# For debugging: if this script is run directly (not through Maya), we can
# simulate the plugin lifecycle.
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Simple test: just run bootstrap/startup/shutdown in a non-Maya context
    logging.basicConfig(level=logging.INFO)
    print("Testing plugin lifecycle...")
    try:
        bootstrap()
        startup()
        print("Plugin started.")
        shutdown()
        print("Plugin shut down.")
    except Exception as e:
        print(f"Error: {e}")