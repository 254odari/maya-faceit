"""
ui/application/command_palette.py

Global command palette (Ctrl+Shift+P).

Provides a searchable list of commands, similar to VS Code's Command Palette.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional, Callable

from ..qt_imports import Qt, QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, Signal

logger = logging.getLogger(__name__)


class CommandPalette(QDialog):
    """
    Floating command palette for executing actions via keyboard.

    Opens with a search box that filters commands as you type.
    Press Enter to execute the selected command.

    Usage:
        palette = CommandPalette(parent)
        palette.show()

    Signals:
        command_executed(str): Emitted when a command is executed (command name).
    """
    command_executed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.Popup)
        self.setWindowTitle("Command Palette")
        self.resize(500, 300)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type a command...")
        self.search_edit.textChanged.connect(self._filter_commands)
        self.search_edit.setStyleSheet("padding: 6px; border: none;")
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._execute_command)
        self.list_widget.setStyleSheet("border: none;")
        layout.addWidget(self.list_widget)

        # Build command registry
        self._commands: List[Tuple[str, Callable]] = [
            ("New Project", self._cmd_new),
            ("Open Project", self._cmd_open),
            ("Save", self._cmd_save),
            ("Build Rig", self._cmd_build_rig),
            ("Generate ARKit", self._cmd_arkit),
            ("Mirror", self._cmd_mirror),
            ("Validate", self._cmd_validate),
            ("Export", self._cmd_export),
            ("Preferences", self._cmd_preferences),
        ]
        self._populate_commands()

    def _populate_commands(self) -> None:
        """Populate the list with all commands."""
        self.list_widget.clear()
        for name, _ in self._commands:
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

    def _filter_commands(self, text: str) -> None:
        """Filter commands based on search text."""
        text = text.lower()
        self.list_widget.clear()
        for name, _ in self._commands:
            if text in name.lower():
                item = QListWidgetItem(name)
                self.list_widget.addItem(item)

    def _execute_command(self, item: QListWidgetItem) -> None:
        """Execute the selected command."""
        command_name = item.text()
        for name, callback in self._commands:
            if name == command_name:
                callback()
                self.command_executed.emit(command_name)
                self.close()
                break

    def showEvent(self, event) -> None:
        """Focus the search box when shown."""
        super().showEvent(event)
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def keyPressEvent(self, event) -> None:
        """Handle Escape key to close."""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    # ---------- Command Callbacks ----------
    def _cmd_new(self) -> None:
        main = self.parent()
        if hasattr(main, "status_message"):
            main.status_message.emit("New Project via command")

    def _cmd_open(self) -> None:
        self._cmd_new()

    def _cmd_save(self) -> None:
        self._cmd_new()

    def _cmd_build_rig(self) -> None:
        self._cmd_new()

    def _cmd_arkit(self) -> None:
        self._cmd_new()

    def _cmd_mirror(self) -> None:
        self._cmd_new()

    def _cmd_validate(self) -> None:
        self._cmd_new()

    def _cmd_export(self) -> None:
        self._cmd_new()

    def _cmd_preferences(self) -> None:
        from ..dialogs import PreferencesDialog
        dlg = PreferencesDialog(self.parent())
        dlg.exec_()