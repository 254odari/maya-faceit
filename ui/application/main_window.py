"""
ui/application/main_window.py

Main application window with dockable workspace.

This is the primary UI container for FaceIT. It manages the workspace,
dockable panels, menus, toolbars, status bar, command palette, and shortcuts.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..qt_imports import Qt, QMainWindow, QWidget, Signal

from .dock_manager import DockManager
from .workspace import Workspace
from .menu_bar import MenuBar
from .tool_bar import ToolBar
from .status_bar import StatusBar
from .command_palette import CommandPalette
from .notifications import NotificationManager
from .shortcuts import ShortcutManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.

    This window provides the workspace (central area with pages),
    dockable panels, menu bar, tool bar, status bar, command palette,
    notification manager, and shortcut manager.

    Signals:
        status_message(str): Emitted to update the status bar message.
    """
    status_message = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("FaceIT Pro")
        self.setMinimumSize(1280, 800)

        # Central widget is a workspace container
        self.workspace = Workspace(self)
        self.setCentralWidget(self.workspace)

        # Create UI components
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.tool_bar = ToolBar(self)
        self.addToolBar(self.tool_bar)

        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_message.connect(self.status_bar.show_message)

        # Dock manager
        self.dock_manager = DockManager(self)

        # Command palette (global shortcut)
        self.command_palette = CommandPalette(self)

        # Notification manager
        self.notification_manager = NotificationManager(self)

        # Shortcut manager
        self.shortcut_manager = ShortcutManager(self)

        # Setup default workspace layout
        self._setup_default_workspace()

        # Connect signals
        self._connect_signals()

    def _setup_default_workspace(self) -> None:
        """Create initial panels and pages."""
        # Add dockable panels
        self.dock_manager.add_panel("Scene", "scene_panel", dock_area=Qt.LeftDockWidgetArea)
        self.dock_manager.add_panel("Hierarchy", "hierarchy_panel", dock_area=Qt.LeftDockWidgetArea)
        self.dock_manager.add_panel("Inspector", "inspector_panel", dock_area=Qt.RightDockWidgetArea)
        self.dock_manager.add_panel("Properties", "property_panel", dock_area=Qt.RightDockWidgetArea)
        self.dock_manager.add_panel("Preview", "preview_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Log", "log_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Output", "output_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Progress", "progress_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Statistics", "statistics_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Validation", "validation_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("History", "history_panel", dock_area=Qt.BottomDockWidgetArea)
        self.dock_manager.add_panel("Console", "console_panel", dock_area=Qt.BottomDockWidgetArea)

        # Set initial page (Dashboard)
        self.workspace.set_page("dashboard")

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.menu_bar.status_message.connect(self.status_message.emit)
        self.tool_bar.status_message.connect(self.status_message.emit)

    def closeEvent(self, event) -> None:
        """Handle close event."""
        self.workspace.save_layout()
        super().closeEvent(event)