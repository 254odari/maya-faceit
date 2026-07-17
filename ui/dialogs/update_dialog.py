# ui/dialogs/update_dialog.py

"""
ui/dialogs/update_dialog.py

Software update notification dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar
)


class UpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.resize(450, 200)

        layout = QVBoxLayout(self)

        title = QLabel("New Update Available!")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel("Version 2.1.0 is now available. You are running 2.0.0.")
        info.setWordWrap(True)
        layout.addWidget(info)

        changelog = QLabel("What's new:\n• Improved ARKit mapping\n• Bug fixes\n• Performance improvements")
        changelog.setStyleSheet("background-color: #3a3a3a; padding: 8px; border-radius: 4px;")
        changelog.setWordWrap(True)
        layout.addWidget(changelog)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        download_btn = QPushButton("Download & Install")
        download_btn.clicked.connect(self._download)
        later_btn = QPushButton("Later")
        later_btn.clicked.connect(self.reject)
        skip_btn = QPushButton("Skip This Version")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(download_btn)
        btn_layout.addWidget(later_btn)
        btn_layout.addWidget(skip_btn)
        layout.addLayout(btn_layout)

    def _download(self):
        # Simulate download
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indeterminate
        self.reject()