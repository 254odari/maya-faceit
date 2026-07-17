# ui/panels/statistics_panel.py

"""
ui/panels/statistics_panel.py

Statistics panel – shows metrics.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QFormLayout, QLabel, QPushButton


class StatisticsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.total_targets = QLabel("0")
        self.active_weights = QLabel("0")
        self.vertices = QLabel("0")
        self.fps = QLabel("0")

        form.addRow("Total Targets:", self.total_targets)
        form.addRow("Active Weights:", self.active_weights)
        form.addRow("Vertices:", self.vertices)
        form.addRow("FPS:", self.fps)

        layout.addLayout(form)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        layout.addWidget(refresh_btn)
        layout.addStretch()

    def _refresh(self):
        # Placeholder
        self.total_targets.setText("12")
        self.active_weights.setText("5")
        self.vertices.setText("2450")
        self.fps.setText("60")