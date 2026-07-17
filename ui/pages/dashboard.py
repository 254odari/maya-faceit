"""
ui/pages/dashboard.py

Dashboard – home page with quick actions and recent projects.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QListWidget, QFrame
    from PySide2.QtCore import Qt
else:
    QWidget = object


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Header
        header = QLabel("FaceIT Pro")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(header)

        # Quick action buttons
        grid = QGridLayout()
        actions = [
            ("📁 New Project", self._new_project),
            ("📂 Open Project", self._open_project),
            ("🦴 Build Rig", self._build_rig),
            ("🎭 Generate ARKit", self._gen_arkit),
            ("📹 Mocap", self._mocap),
            ("📦 Export", self._export),
        ]
        for i, (label, callback) in enumerate(actions):
            btn = QPushButton(label)
            btn.setMinimumHeight(48)
            btn.clicked.connect(callback)
            grid.addWidget(btn, i // 3, i % 3)
        main_layout.addLayout(grid)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Recent projects
        recent_label = QLabel("Recent Projects")
        recent_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(recent_label)
        self.recent_list = QListWidget()
        self.recent_list.addItems(["Project_A", "Project_B", "Project_C"])
        main_layout.addWidget(self.recent_list)

        # Status / activity (placeholder)
        status_label = QLabel("System ready")
        status_label.setStyleSheet("color: #888;")
        main_layout.addWidget(status_label)

        main_layout.addStretch()

    # ---------- Slots (to be connected to controllers) ----------
    def _new_project(self): pass
    def _open_project(self): pass
    def _build_rig(self): pass
    def _gen_arkit(self): pass
    def _mocap(self): pass
    def _export(self): pass