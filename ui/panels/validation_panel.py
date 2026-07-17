# ui/panels/validation_panel.py

"""
ui/panels/validation_panel.py

Validation panel – shows validation issues.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout


class ValidationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Issue", "Severity", "Description"])
        layout.addWidget(self.tree)

        # Sample items
        for issue, sev, desc in [
            ("Mesh non-manifold", "Error", "Check geometry"),
            ("Missing target", "Warning", "Add target mesh"),
            ("Weight exceeds 1.0", "Warning", "Normalize weights")
        ]:
            item = QTreeWidgetItem([issue, sev, desc])
            self.tree.addTopLevelItem(item)

        btn_layout = QHBoxLayout()
        validate_btn = QPushButton("Run Validation")
        validate_btn.clicked.connect(self._validate)
        fix_btn = QPushButton("Auto-Fix")
        fix_btn.clicked.connect(self._fix)
        btn_layout.addWidget(validate_btn)
        btn_layout.addWidget(fix_btn)
        layout.addLayout(btn_layout)

    def _validate(self):
        pass

    def _fix(self):
        pass