"""
ui/application/__init__.py

Application-level UI components: main window, workspace, panels, menus, etc.
"""

from .main_window import MainWindow
from .dock_manager import DockManager
from .workspace import Workspace
from .menu_bar import MenuBar
from .tool_bar import ToolBar
from .status_bar import StatusBar
from .command_palette import CommandPalette
from .notifications import NotificationManager
from .shortcuts import ShortcutManager

__all__ = [
    "MainWindow",
    "DockManager",
    "Workspace",
    "MenuBar",
    "ToolBar",
    "StatusBar",
    "CommandPalette",
    "NotificationManager",
    "ShortcutManager",
]