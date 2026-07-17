"""
ui/application/dock_manager.py

Manages all dockable panels.

The DockManager provides a registry and factory for all dockable panels
in the FaceIT UI. It is accessible from the main window via `dock_manager`.

Public API:
    - add_panel(title, panel_id, dock_area) -> QDockWidget
    - get_panel(panel_id) -> Optional[QDockWidget]
    - get_all_panels() -> Dict[str, QDockWidget]
    - toggle_panel(panel_id)
    - close_panel(panel_id)
    - list_panel_ids() -> List[str]
    - register_custom_panel(panel_id, panel_class)
    - get_panel_widget(panel_id) -> Optional[QWidget]

Usage example:
    # From a controller or script
    main_window = get_main_window()
    dock_mgr = main_window.dock_manager

    # Show a panel
    dock_mgr.toggle_panel("inspector_panel")

    # Get the widget inside a panel
    widget = dock_mgr.get_panel_widget("log_panel")
    if widget:
        widget.append("Hello")
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, List, Type

from ..qt_imports import Qt, QDockWidget, QMainWindow, QWidget

from ..panels import (
    ScenePanel, HierarchyPanel, InspectorPanel, PropertyPanel,
    PreviewPanel, LogPanel, OutputPanel, ProgressPanel,
    StatisticsPanel, ValidationPanel, HistoryPanel, ConsolePanel
)

logger = logging.getLogger(__name__)


class DockManager:
    """
    Registry and manager for all dockable panels in the FaceIT UI.

    This class is responsible for creating, storing, and managing
    all QDockWidget instances. It provides a simple API to add,
    retrieve, toggle, and close panels.
    """

    # Default panel classes (panel_id -> panel class)
    _panel_classes: Dict[str, Type[QWidget]] = {
        "scene_panel": ScenePanel,
        "hierarchy_panel": HierarchyPanel,
        "inspector_panel": InspectorPanel,
        "property_panel": PropertyPanel,
        "preview_panel": PreviewPanel,
        "log_panel": LogPanel,
        "output_panel": OutputPanel,
        "progress_panel": ProgressPanel,
        "statistics_panel": StatisticsPanel,
        "validation_panel": ValidationPanel,
        "history_panel": HistoryPanel,
        "console_panel": ConsolePanel,
    }

    def __init__(self, main_window: QMainWindow) -> None:
        """
        Initialize the DockManager with the parent main window.

        Args:
            main_window: The QMainWindow that will host the dock widgets.
        """
        self.main_window = main_window
        self._docks: Dict[str, QDockWidget] = {}

    # -------------------------------------------------------------------------
    # Panel Addition and Removal
    # -------------------------------------------------------------------------

    def add_panel(
        self,
        title: str,
        panel_id: str,
        dock_area: int = Qt.RightDockWidgetArea
    ) -> QDockWidget:
        """
        Create and add a dockable panel to the main window.

        Args:
            title: The title displayed on the dock widget's title bar.
            panel_id: A unique identifier for the panel (e.g., "inspector_panel").
            dock_area: Qt dock area constant (LeftDockWidgetArea, RightDockWidgetArea,
                       TopDockWidgetArea, BottomDockWidgetArea).

        Returns:
            The newly created QDockWidget instance.

        Raises:
            ValueError: If a panel with the same panel_id already exists.
        """
        if panel_id in self._docks:
            raise ValueError(f"Panel with id '{panel_id}' already exists.")

        panel_cls = self._panel_classes.get(panel_id)
        if panel_cls is None:
            logger.warning(f"Unknown panel id: {panel_id}, using QWidget fallback.")
            panel_cls = QWidget

        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(panel_id)
        widget = panel_cls(dock)
        dock.setWidget(widget)
        self.main_window.addDockWidget(dock_area, dock)
        self._docks[panel_id] = dock
        logger.debug(f"Added panel '{panel_id}' with title '{title}'.")
        return dock

    def register_custom_panel(self, panel_id: str, panel_class: Type[QWidget]) -> None:
        """
        Register a custom panel class that can be instantiated later.

        This allows external modules to add custom panels to the dock manager.

        Args:
            panel_id: The identifier for the panel.
            panel_class: A QWidget subclass to be used as the panel widget.

        Raises:
            ValueError: If the panel_id is already registered.
        """
        if panel_id in self._panel_classes:
            raise ValueError(f"Panel id '{panel_id}' is already registered.")
        self._panel_classes[panel_id] = panel_class
        logger.debug(f"Registered custom panel '{panel_id}' with class {panel_class.__name__}.")

    # -------------------------------------------------------------------------
    # Panel Retrieval
    # -------------------------------------------------------------------------

    def get_panel(self, panel_id: str) -> Optional[QDockWidget]:
        """
        Retrieve a dock widget by its ID.

        Args:
            panel_id: The identifier of the panel.

        Returns:
            The QDockWidget if found, else None.
        """
        return self._docks.get(panel_id)

    def get_panel_widget(self, panel_id: str) -> Optional[QWidget]:
        """
        Retrieve the widget inside a dock panel by its ID.

        Args:
            panel_id: The identifier of the panel.

        Returns:
            The QWidget contained in the dock if found, else None.
        """
        dock = self.get_panel(panel_id)
        if dock:
            return dock.widget()
        return None

    def get_all_panels(self) -> Dict[str, QDockWidget]:
        """
        Return a dictionary of all panels (panel_id -> QDockWidget).

        Returns:
            A copy of the internal panel dictionary.
        """
        return self._docks.copy()

    def list_panel_ids(self) -> List[str]:
        """
        Return a list of all registered panel IDs.

        Returns:
            A list of panel identifiers.
        """
        return list(self._docks.keys())

    # -------------------------------------------------------------------------
    # Panel Visibility Control
    # -------------------------------------------------------------------------

    def toggle_panel(self, panel_id: str) -> None:
        """
        Toggle the visibility of a panel.

        Args:
            panel_id: The identifier of the panel.
        """
        dock = self.get_panel(panel_id)
        if dock:
            dock.setVisible(not dock.isVisible())
        else:
            logger.warning(f"Cannot toggle panel '{panel_id}': not found.")

    def show_panel(self, panel_id: str) -> None:
        """Show a hidden panel."""
        dock = self.get_panel(panel_id)
        if dock:
            dock.setVisible(True)

    def hide_panel(self, panel_id: str) -> None:
        """Hide a visible panel."""
        dock = self.get_panel(panel_id)
        if dock:
            dock.setVisible(False)

    def close_panel(self, panel_id: str) -> None:
        """Close and remove a panel (permanently)."""
        dock = self.get_panel(panel_id)
        if dock:
            dock.close()
            del self._docks[panel_id]
            logger.debug(f"Closed panel '{panel_id}'.")

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def is_panel_visible(self, panel_id: str) -> bool:
        """Check if a panel is currently visible."""
        dock = self.get_panel(panel_id)
        return dock is not None and dock.isVisible()

    def is_panel_registered(self, panel_id: str) -> bool:
        """Check if a panel has been created and registered."""
        return panel_id in self._docks

    def clear(self) -> None:
        """Close and remove all panels."""
        for panel_id in list(self._docks.keys()):
            self.close_panel(panel_id)
        logger.debug("All panels cleared.")