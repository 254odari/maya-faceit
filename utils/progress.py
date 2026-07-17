# -*- coding: utf-8 -*-
"""
maya_faceit.utils.progress
~~~~~~~~~~~~~~~~~~~~~~~~~~

Progress utilities.
"""

import time
from typing import Optional, Callable, Any


class ProgressContext:
    """
    Simple progress context for iterating over items.
    """

    def __init__(self, total: int, description: str = "",
                 callback: Optional[Callable[[int, int, str], None]] = None):
        self.total = total
        self.current = 0
        self.description = description
        self.callback = callback
        self._last_update = 0

    def update(self, step: int = 1, message: str = ""):
        """Update progress by step."""
        self.current += step
        self._report(message)

    def set_progress(self, value: int, message: str = ""):
        """Set progress to a specific value."""
        self.current = min(value, self.total)
        self._report(message)

    def _report(self, message: str):
        """Report progress via callback."""
        if self.callback:
            self.callback(self.current, self.total, message)

    def __enter__(self):
        self._report("Starting...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._report("Complete.")


def progress(total: int, description: str = ""):
    """Create a progress context."""
    return ProgressContext(total, description)