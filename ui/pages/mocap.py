"""
ui/pages/mocap.py

Motion capture live drive and recording.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QSlider
else:
    QWidget = object


class MocapPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["None", "LiveLink", "MediaPipe", "FaceCap"])
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)
        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self._record)
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._play)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.play_btn)
        layout.addLayout(btn_layout)

        # Status
        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _connect(self): pass
    def _record(self): pass
    def _play(self): pass