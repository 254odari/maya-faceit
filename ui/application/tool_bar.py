"""
ui/application/tool_bar.py

Main toolbar with common actions.
"""

from __future__ import annotations

import logging

from ..qt_imports import QToolBar, QAction, Signal

logger = logging.getLogger(__name__)


class ToolBar(QToolBar):
    """
    Application toolbar with common actions (New, Open, Save, Undo, Redo,
    Build Rig, Create Blendshape, Generate ARKit, Mirror, Validate, Export).

    Signals:
        status_message(str): Emitted to show a message in the status bar.
    """

    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Main Toolbar", parent)
        self.setObjectName("main_toolbar")

        # Actions
        self._add_action("New", "New Project", self._on_new)
        self._add_action("Open", "Open Project", self._on_open)
        self._add_action("Save", "Save", self._on_save)
        self.addSeparator()
        self._add_action("Undo", "Undo", self._on_undo)
        self._add_action("Redo", "Redo", self._on_redo)
        self.addSeparator()
        self._add_action("Rig", "Build Rig", self._on_build_rig)
        self._add_action("Blendshape", "Create Blendshape", self._on_blendshape)
        self._add_action("ARKit", "Generate ARKit", self._on_arkit)
        self.addSeparator()
        self._add_action("Mirror", "Mirror", self._on_mirror)
        self._add_action("Validate", "Validate", self._on_validate)
        self._add_action("Export", "Export", self._on_export)

    def _add_action(self, name: str, tooltip: str, slot) -> QAction:
        """Helper to create and add an action."""
        action = QAction(name, self)
        action.setToolTip(tooltip)
        action.triggered.connect(slot)
        self.addAction(action)
        return action

    # ---------- Slots ----------
    def _on_new(self) -> None:
        self.status_message.emit("New")

    def _on_open(self) -> None:
        self.status_message.emit("Open")

    def _on_save(self) -> None:
        self.status_message.emit("Save")

    def _on_undo(self) -> None:
        self.status_message.emit("Undo")

    def _on_redo(self) -> None:
        self.status_message.emit("Redo")

    def _on_build_rig(self) -> None:
        self.status_message.emit("Build Rig")

    def _on_blendshape(self) -> None:
        self.status_message.emit("Create Blendshape")

    def _on_arkit(self) -> None:
        self.status_message.emit("Generate ARKit")

    def _on_mirror(self) -> None:
        self.status_message.emit("Mirror")

    def _on_validate(self) -> None:
        self.status_message.emit("Validate")

    def _on_export(self) -> None:
        self.status_message.emit("Export")