# ui/widgets/timeline.py

"""
ui/widgets/timeline.py

Timeline widget for animation.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QSlider, QHBoxLayout, QLabel, QPushButton, Signal, Qt, QTimer


class TimelineWidget(QWidget):
    """Timeline control with playhead and transport."""
    frame_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.current_frame_label = QLabel("1")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(1)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(10)
        self.slider.valueChanged.connect(self._on_slider)
        self.total_frames_label = QLabel("100")

        layout.addWidget(QLabel("Frame:"))
        layout.addWidget(self.current_frame_label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.total_frames_label)

        # Transport buttons
        self.play_btn = QPushButton("▶")
        self.play_btn.setCheckable(True)
        self.play_btn.clicked.connect(self._on_play)
        self.stop_btn = QPushButton("■")
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.stop_btn)

        self._playing = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._advance_frame)

    def _on_slider(self, value: int) -> None:
        self.current_frame_label.setText(str(value))
        self.frame_changed.emit(value)

    def _on_play(self) -> None:
        self._playing = self.play_btn.isChecked()
        if self._playing:
            self._timer.start(50)  # 20 fps
        else:
            self._timer.stop()

    def _on_stop(self) -> None:
        self._playing = False
        self.play_btn.setChecked(False)
        self._timer.stop()
        self.set_frame(1)

    def _advance_frame(self) -> None:
        current = self.slider.value() + 1
        if current > self.slider.maximum():
            current = 1
        self.set_frame(current)

    def set_frame(self, frame: int) -> None:
        self.slider.setValue(frame)

    def set_frame_range(self, start: int, end: int) -> None:
        self.slider.setRange(start, end)
        self.total_frames_label.setText(str(end))