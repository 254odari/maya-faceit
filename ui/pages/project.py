"""
ui/pages/project.py

Project settings and configuration.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton
else:
    QWidget = object


class ProjectPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.path_edit = QLineEdit()
        self.template_combo = QComboBox()
        self.template_combo.addItems(["Default", "Cartoon", "Realistic"])

        form.addRow("Project Name:", self.name_edit)
        form.addRow("Project Path:", self.path_edit)
        form.addRow("Rig Template:", self.template_combo)

        layout.addLayout(form)

        btn = QPushButton("Save Project")
        btn.clicked.connect(self._save)
        layout.addWidget(btn)
        layout.addStretch()

    def _save(self):
        pass