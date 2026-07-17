"""
ui/pages/arkit.py

ARKit 52 blendshape mapping and generation.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, QLabel
else:
    QWidget = object


class ARKitPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Table: ARKit channel | Target | Coverage
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ARKit Channel", "Mapped Target", "Coverage"])
        self.table.setRowCount(10)  # placeholder
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        gen_btn = QPushButton("Generate All")
        gen_btn.clicked.connect(self._generate)
        map_btn = QPushButton("Auto-Map")
        map_btn.clicked.connect(self._map)
        btn_layout.addWidget(gen_btn)
        btn_layout.addWidget(map_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _generate(self): pass
    def _map(self): pass