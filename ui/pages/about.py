"""
ui/pages/about.py

About information.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel
    from PySide2.QtCore import Qt
else:
    QWidget = object


class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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

        copyright = QLabel("© 2026 Maya FaceIT Team")
        copyright.setStyleSheet("color: #666;")
        layout.addWidget(copyright)

        layout.addStretch()