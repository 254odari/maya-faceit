"""
ui/application/menu_bar.py

Application menu bar.
"""

from __future__ import annotations

import logging

from ..qt_imports import QMenuBar, QAction, Signal, QtWidgets

logger = logging.getLogger(__name__)


class MenuBar(QMenuBar):
    """
    Main menu bar with File, Edit, Create, Tools, Window, and Help menus.

    Signals:
        status_message(str): Emitted to show a message in the status bar.
    """
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # File menu
        file_menu = self.addMenu("&File")
        file_menu.addAction("New Project", self._on_new)
        file_menu.addAction("Open Project...", self._on_open)
        file_menu.addSeparator()
        file_menu.addAction("Save", self._on_save)
        file_menu.addAction("Save As...", self._on_save_as)
        file_menu.addSeparator()
        file_menu.addAction("Import", self._on_import)
        file_menu.addAction("Export", self._on_export)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self._on_exit)

        # Edit menu
        edit_menu = self.addMenu("&Edit")
        edit_menu.addAction("Undo", self._on_undo)
        edit_menu.addAction("Redo", self._on_redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Preferences", self._on_preferences)

        # Create menu
        create_menu = self.addMenu("&Create")
        create_menu.addAction("Rig", self._on_create_rig)
        create_menu.addAction("Blendshape", self._on_create_blendshape)
        create_menu.addAction("ARKit Library", self._on_create_arkit)

        # Tools menu
        tools_menu = self.addMenu("&Tools")
        tools_menu.addAction("Mirror", self._on_mirror)
        tools_menu.addAction("Normalize", self._on_normalize)
        tools_menu.addAction("Optimize", self._on_optimize)

        # Window menu
        window_menu = self.addMenu("&Window")
        window_menu.addAction("Command Palette", self._on_command_palette)

        # Help menu
        help_menu = self.addMenu("&Help")
        help_menu.addAction("Documentation", self._on_docs)
        help_menu.addAction("About", self._on_about)

    # ---------- Slots ----------
    def _on_new(self) -> None:
        self.status_message.emit("New project")

    def _on_open(self) -> None:
        self.status_message.emit("Open project")

    def _on_save(self) -> None:
        self.status_message.emit("Save project")

    def _on_save_as(self) -> None:
        self.status_message.emit("Save As")

    def _on_import(self) -> None:
        self.status_message.emit("Import")

    def _on_export(self) -> None:
        self.status_message.emit("Export")

    def _on_exit(self) -> None:
        QtWidgets.qApp.quit()

    def _on_undo(self) -> None:
        self.status_message.emit("Undo")

    def _on_redo(self) -> None:
        self.status_message.emit("Redo")

    def _on_preferences(self) -> None:
        from ..dialogs import PreferencesDialog
        dlg = PreferencesDialog(self.parent())
        dlg.exec_()

    def _on_create_rig(self) -> None:
        self.status_message.emit("Create Rig")

    def _on_create_blendshape(self) -> None:
        self.status_message.emit("Create Blendshape")

    def _on_create_arkit(self) -> None:
        self.status_message.emit("Create ARKit Library")

    def _on_mirror(self) -> None:
        self.status_message.emit("Mirror")

    def _on_normalize(self) -> None:
        self.status_message.emit("Normalize")

    def _on_optimize(self) -> None:
        self.status_message.emit("Optimize")

    def _on_command_palette(self) -> None:
        self.status_message.emit("Command Palette")

    def _on_docs(self) -> None:
        self.status_message.emit("Documentation")

    def _on_about(self) -> None:
        from ..dialogs import AboutDialog
        dlg = AboutDialog(self.parent())
        dlg.exec_()