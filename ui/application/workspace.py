"""
ui/application/workspace.py

Manages the central workspace and page switching.

The workspace is a QStackedWidget that holds all page widgets.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List

from ..qt_imports import QStackedWidget, QWidget, QtWidgets, QtCore

from ..pages import (
    DashboardPage, ProjectPage, RigPage, LandmarksPage,
    BlendshapesPage, ARKitPage, MocapPage, AnimationPage,
    ExpressionsPage, PickerPage, ToolsPage, ExportPage,
    ValidationPage, SettingsPage, AboutPage
)

logger = logging.getLogger(__name__)


class Workspace(QStackedWidget):
    """
    Central workspace that switches between pages.

    Pages are created lazily and can be accessed by their ID.
    The current page can be set using `set_page(page_id)`.
    """

    _page_classes = {
        "dashboard": DashboardPage,
        "project": ProjectPage,
        "rig": RigPage,
        "landmarks": LandmarksPage,
        "blendshapes": BlendshapesPage,
        "arkit": ARKitPage,
        "mocap": MocapPage,
        "animation": AnimationPage,
        "expressions": ExpressionsPage,
        "picker": PickerPage,
        "tools": ToolsPage,
        "export": ExportPage,
        "validation": ValidationPage,
        "settings": SettingsPage,
        "about": AboutPage,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pages: Dict[str, QWidget] = {}
        self._current_page_id: Optional[str] = None

        # Create all pages lazily
        for page_id, cls in self._page_classes.items():
            try:
                page = cls(self)
                self.addWidget(page)
                self._pages[page_id] = page
            except Exception as e:
                logger.error(f"Failed to create page '{page_id}': {e}")
                # Add placeholder
                placeholder = QtWidgets.QLabel(f"Page '{page_id}' failed to load")
                placeholder.setAlignment(QtCore.Qt.AlignCenter)
                self.addWidget(placeholder)
                self._pages[page_id] = placeholder

        # Set default page
        self.set_page("dashboard")

    def set_page(self, page_id: str) -> None:
        """
        Switch to a specific page.

        Args:
            page_id: The identifier of the page (e.g., "rig", "blendshapes").

        Raises:
            KeyError: If the page_id is unknown.
        """
        if page_id not in self._pages:
            raise KeyError(f"Unknown page: {page_id}")
        widget = self._pages[page_id]
        self.setCurrentWidget(widget)
        self._current_page_id = page_id
        logger.debug(f"Switched to page: {page_id}")

    def get_page(self, page_id: str) -> Optional[QWidget]:
        """
        Retrieve a page widget by its ID.

        Args:
            page_id: The page identifier.

        Returns:
            The QWidget for that page, or None if not found.
        """
        return self._pages.get(page_id)

    def current_page_id(self) -> Optional[str]:
        """Return the ID of the currently visible page."""
        return self._current_page_id

    def list_pages(self) -> List[str]:
        """Return a list of all available page IDs."""
        return list(self._pages.keys())

    def save_layout(self) -> None:
        """Save workspace layout (stub for future implementation)."""
        pass