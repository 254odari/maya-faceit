# ui/dialogs/about_dialog.py

"""
ui/dialogs/about_dialog.py

About dialog.
"""

from __future__ import annotations

from ..qt_imports import Qt, QDialog, QVBoxLayout, QLabel, QPushButton


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About FaceIT")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("FaceIT Pro")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        version = QLabel("Version 2.0.0")
        version.setStyleSheet("font-size: 16px; color: #888;")
        layout.addWidget(version)

        desc = QLabel("Advanced facial rigging and blendshape tool for Maya.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        copyright_label = QLabel("© 2026 Maya FaceIT Team")
        copyright_label.setStyleSheet("color: #666;")
        layout.addWidget(copyright_label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)