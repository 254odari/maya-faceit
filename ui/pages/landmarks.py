"""
ui/pages/landmarks.py

Facial landmarks management.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
else:
    QWidget = object


class LandmarksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.addItems(["Left Eye", "Right Eye", "Nose", "Mouth", "Eyebrow L", "Eyebrow R"])
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        detect_btn = QPushButton("Detect Landmarks")
        detect_btn.clicked.connect(self._detect)
        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self._edit)
        btn_layout.addWidget(detect_btn)
        btn_layout.addWidget(edit_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _detect(self): pass
    def _edit(self): pass