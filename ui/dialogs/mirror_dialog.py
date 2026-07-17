# ui/dialogs/mirror_dialog.py

"""
ui/dialogs/mirror_dialog.py

Mirror options dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QPushButton, QHBoxLayout
)


class MirrorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mirror Options")
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Left → Right", "Right → Left"])
        self.mirror_weights = QCheckBox("Mirror Weights")
        self.mirror_weights.setChecked(True)
        self.mirror_correctives = QCheckBox("Mirror Correctives")
        self.mirror_correctives.setChecked(True)

        form.addRow("Direction:", self.direction_combo)
        form.addRow("", self.mirror_weights)
        form.addRow("", self.mirror_correctives)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Mirror")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)