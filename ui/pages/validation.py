"""
ui/pages/validation.py

Validation reports and diagnostics.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QPushButton, QHBoxLayout
else:
    QWidget = object


class ValidationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Issue", "Severity", "Description"])
        # Add sample items
        for issue, severity in [("Mesh non-manifold", "Error"), ("Missing target", "Warning")]:
            item = QtWidgets.QTreeWidgetItem([issue, severity, "Fix manually"])
            self.tree.addTopLevelItem(item)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        validate_btn = QPushButton("Run Validation")
        validate_btn.clicked.connect(self._validate)
        fix_btn = QPushButton("Auto-Fix")
        fix_btn.clicked.connect(self._fix)
        btn_layout.addWidget(validate_btn)
        btn_layout.addWidget(fix_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _validate(self): pass
    def _fix(self): pass