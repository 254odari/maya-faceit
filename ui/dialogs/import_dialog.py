# ui/dialogs/import_dialog.py

"""
ui/dialogs/import_dialog.py

Import configuration dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QFileDialog, QCheckBox
)


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import")
        self.resize(500, 200)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select file...")
        self.path_btn = QPushButton("Browse...")
        self.path_btn.clicked.connect(self._browse)
        self.path_layout = QHBoxLayout()
        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.path_btn)

        self.merge_check = QCheckBox("Merge with current project")
        self.merge_check.setChecked(False)

        form.addRow("File:", self.path_layout)
        form.addRow("", self.merge_check)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Import")
        if path:
            self.path_edit.setText(path)