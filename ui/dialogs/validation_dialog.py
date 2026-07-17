# ui/dialogs/validation_dialog.py

"""
ui/dialogs/validation_dialog.py

Validation results and fix options.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout
)


class ValidationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Validation Results")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Issue", "Severity", "Description"])
        # Sample entries
        items = [
            ("Mesh non-manifold", "Error", "Check geometry"),
            ("Missing target", "Warning", "Add target mesh"),
            ("Weight exceeds 1.0", "Warning", "Normalize weights"),
        ]
        for issue, sev, desc in items:
            item = QTreeWidgetItem([issue, sev, desc])
            self.tree.addTopLevelItem(item)
        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        fix_btn = QPushButton("Auto-Fix Selected")
        fix_btn.clicked.connect(self._fix)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(fix_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _fix(self):
        pass