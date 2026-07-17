"""
ui/pages/export.py

Export settings and execution.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QCheckBox, QPushButton
else:
    QWidget = object


class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.format_combo = QComboBox()
        self.format_combo.addItems(["FBX", "USD", "Alembic", "JSON", "MetaHuman"])
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Export path...")
        self.include_weights = QCheckBox("Include Weights")
        self.include_weights.setChecked(True)
        self.optimize_mesh = QCheckBox("Optimize Mesh")
        self.optimize_mesh.setChecked(True)

        form.addRow("Format:", self.format_combo)
        form.addRow("Output Path:", self.path_edit)
        form.addRow("", self.include_weights)
        form.addRow("", self.optimize_mesh)

        layout.addLayout(form)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)
        layout.addWidget(export_btn)

        layout.addStretch()

    def _export(self): pass