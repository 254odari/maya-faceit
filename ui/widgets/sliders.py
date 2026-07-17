# ui/widgets/sliders.py

"""
ui/widgets/sliders.py

Slider widgets with labels.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QDoubleSpinBox, Signal, Qt


class LabeledSlider(QWidget):
    """Slider with label and value display."""
    value_changed = Signal(float)

    def __init__(self, label: str, min_val: float = 0.0, max_val: float = 1.0,
                 value: float = 0.5, decimals: int = 2, parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._decimals = decimals
        self._scale = 10 ** decimals

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top_layout = QHBoxLayout()
        self.label = QLabel(label)
        self.value_label = QLabel(f"{value:.{decimals}f}")
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        top_layout.addWidget(self.value_label)
        layout.addLayout(top_layout)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100 * self._scale)
        self.slider.setValue(int(value * self._scale))
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider)

    def _on_slider(self, val: int) -> None:
        real_val = val / self._scale
        real_val = max(self._min, min(self._max, real_val))
        self.value_label.setText(f"{real_val:.{self._decimals}f}")
        self.value_changed.emit(real_val)

    def set_value(self, value: float) -> None:
        self.slider.setValue(int(value * self._scale))


class RangeSlider(QWidget):
    """Slider with two handles for range selection."""
    range_changed = Signal(float, float)

    def __init__(self, label: str, min_val: float = 0.0, max_val: float = 1.0,
                 low: float = 0.2, high: float = 0.8, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(label)
        layout.addWidget(self.label)
        self.low_slider = LabeledSlider("Low", min_val, max_val, low)
        self.high_slider = LabeledSlider("High", min_val, max_val, high)
        layout.addWidget(self.low_slider)
        layout.addWidget(self.high_slider)


class WeightSlider(LabeledSlider):
    """Slider specifically for blendshape weights (0-1)."""
    def __init__(self, target_name: str, weight: float = 0.0, parent=None):
        super().__init__(target_name, 0.0, 1.0, weight, 2, parent)
        self.target_name = target_name