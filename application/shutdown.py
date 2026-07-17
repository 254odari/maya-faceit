# -*- coding: utf-8 -*-
"""
maya_faceit.application.shutdown

Cleanup phase: save preferences, session, and close resources.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import Application

logger = logging.getLogger(__name__)


class Shutdown:
    """Shutdown phase handler."""

    def __init__(self) -> None:
        self._initialized = False

    def run(self, app: 'Application') -> bool:
        """Execute shutdown."""
        if self._initialized:
            return True

        try:
            # 1. Save session
            app.session.save()

            # 2. Save preferences
            app.preferences.save()

            # 3. Close any open resources
            # (e.g., disconnect mocap, stop threads)

            # 4. Unregister services (optional)
            # app.registry.clear()

            self._initialized = True
            logger.info("Shutdown completed.")
            return True

        except Exception as e:
            logger.exception("Shutdown error: %s", e)
            return False