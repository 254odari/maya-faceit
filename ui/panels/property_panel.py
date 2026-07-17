# ui/panels/property_panel.py

"""
ui/panels/property_panel.py

Property panel – detailed attributes of selected item.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton


class PropertyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.setRowCount(3)
        self.table.setItem(0, 0, QTableWidgetItem("Translate X"))
        self.table.setItem(0, 1, QTableWidgetItem("0.0"))
        self.table.setItem(1, 0, QTableWidgetItem("Rotate Y"))
        self.table.setItem(1, 1, QTableWidgetItem("45.0"))
        self.table.setItem(2, 0, QTableWidgetItem("Scale Z"))
        self.table.setItem(2, 1, QTableWidgetItem("1.0"))
        layout.addWidget(self.table)

        btn = QPushButton("Apply Changes")
        btn.clicked.connect(self._apply)
        layout.addWidget(btn)

    def _apply(self):
        pass