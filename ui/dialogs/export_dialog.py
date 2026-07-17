# ui/dialogs/export_dialog.py

"""
ui/dialogs/export_dialog.py

Export configuration dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QCheckBox, QPushButton, QHBoxLayout, QFileDialog
)


class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.resize(500, 350)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["FBX", "USD", "Alembic", "JSON", "MetaHuman"])
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select output path...")
        self.path_btn = QPushButton("Browse...")
        self.path_btn.clicked.connect(self._browse)
        self.path_layout = QHBoxLayout()
        self.path_layout.addWidget(self.path_edit)
        self.path_layout.addWidget(self.path_btn)

        self.include_weights = QCheckBox("Include Weights")
        self.include_weights.setChecked(True)
        self.optimize_mesh = QCheckBox("Optimize Mesh")
        self.optimize_mesh.setChecked(True)
        self.export_arkit = QCheckBox("Export ARKit Mapping")
        self.export_arkit.setChecked(True)

        form.addRow("Format:", self.format_combo)
        form.addRow("Output Path:", self.path_layout)
        form.addRow("", self.include_weights)
        form.addRow("", self.optimize_mesh)
        form.addRow("", self.export_arkit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select Export Path", filter="All Files (*.*)")
        if path:
            self.path_edit.setText(path)