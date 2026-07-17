# ui/panels/history_panel.py

"""
ui/panels/history_panel.py

History panel – shows undo/redo stack.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QListWidget
else:
    QWidget = object


class HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.history_list = QListWidget()
        self.history_list.addItems([
            "Create Target: Smile",
            "Set Weight: 0.5",
            "Mirror: EyeBlink_L"
        ])
        layout.addWidget(self.history_list)