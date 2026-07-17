"""
ui/application/shortcuts.py

Global shortcut manager for registering key combinations to actions.
"""

from __future__ import annotations

import logging
from typing import Dict, Callable

from ..qt_imports import QShortcut, QKeySequence, QtGui

logger = logging.getLogger(__name__)


class ShortcutManager:
    """
    Register and manage global keyboard shortcuts.

    Usage:
        mgr = ShortcutManager(main_window)
        mgr.register("Ctrl+Shift+X", lambda: print("Pressed"))
        mgr.unregister("Ctrl+Shift+X")
    """

    def __init__(self, parent) -> None:
        self.parent = parent
        self._shortcuts: Dict[str, QShortcut] = {}

        # Register default shortcuts
        self.register("Ctrl+N", self._on_new)
        self.register("Ctrl+O", self._on_open)
        self.register("Ctrl+S", self._on_save)
        self.register("Ctrl+Z", self._on_undo)
        self.register("Ctrl+Y", self._on_redo)
        self.register("Ctrl+Shift+P", self._on_command_palette)

    def register(self, key_seq: str, callback: Callable) -> QShortcut:
        """
        Register a global shortcut.

        Args:
            key_seq: String representation of the key sequence (e.g., "Ctrl+Shift+P").
            callback: Function to call when the shortcut is activated.

        Returns:
            The QShortcut object.
        """
        if key_seq in self._shortcuts:
            self.unregister(key_seq)
        shortcut = QShortcut(QKeySequence(key_seq), self.parent)
        shortcut.activated.connect(callback)
        self._shortcuts[key_seq] = shortcut
        logger.debug(f"Registered shortcut: {key_seq}")
        return shortcut

    def unregister(self, key_seq: str) -> None:
        """Remove a shortcut."""
        if key_seq in self._shortcuts:
            self._shortcuts[key_seq].deleteLater()
            del self._shortcuts[key_seq]
            logger.debug(f"Unregistered shortcut: {key_seq}")

    def clear(self) -> None:
        """Remove all shortcuts."""
        for key_seq in list(self._shortcuts.keys()):
            self.unregister(key_seq)

    # ---------- Default Callbacks ----------
    def _on_new(self) -> None:
        self.parent.status_message.emit("New (shortcut)")

    def _on_open(self) -> None:
        self.parent.status_message.emit("Open (shortcut)")

    def _on_save(self) -> None:
        self.parent.status_message.emit("Save (shortcut)")

    def _on_undo(self) -> None:
        self.parent.status_message.emit("Undo (shortcut)")

    def _on_redo(self) -> None:
        self.parent.status_message.emit("Redo (shortcut)")

    def _on_command_palette(self) -> None:
        if hasattr(self.parent, "command_palette"):
            self.parent.command_palette.show()