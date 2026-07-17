"""
ui/pages/animation.py

Animation controls and timeline.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
else:
    QWidget = object


class AnimationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Timeline (placeholder)
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(1, 100)
        layout.addWidget(self.timeline_slider)

        # Transport controls
        transport = QHBoxLayout()
        for label in ["⏮", "◀", "▶", "⏭", "⏺"]:
            btn = QPushButton(label)
            btn.clicked.connect(self._transport)
            transport.addWidget(btn)
        layout.addLayout(transport)

        layout.addStretch()

    def _transport(self):
        pass