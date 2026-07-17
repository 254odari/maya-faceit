# ui/widgets/progress.py

"""
ui/widgets/progress.py

Progress indicators.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QPushButton, Qt


class ProgressWidget(QWidget):
    """Widget with label and progress bar."""
    def __init__(self, label_text: str = "Progress:", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel(label_text)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

    def set_value(self, value: int) -> None:
        self.progress.setValue(value)

    def set_label(self, text: str) -> None:
        self.label.setText(text)

    def set_range(self, minimum: int, maximum: int) -> None:
        self.progress.setRange(minimum, maximum)

    def reset(self) -> None:
        self.progress.reset()
        self.label.setText("Ready")


class SpinnerWidget(QWidget):
    """Indeterminate spinner animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.label = QLabel("Loading...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setVisible(False)

    def show_spinner(self, text: str = "Loading...") -> None:
        self.label.setText(text)
        self.setVisible(True)

    def hide_spinner(self) -> None:
        self.setVisible(False)