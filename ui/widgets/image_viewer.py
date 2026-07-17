# ui/widgets/image_viewer.py

"""
ui/widgets/image_viewer.py

Widget for displaying and zooming images.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QPixmap, Qt
)


class ImageViewerWidget(QWidget):
    """Image viewer with zoom and pan support."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Scroll area for image
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: #1a1a1a; border: 1px solid #444;")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

        # Controls
        controls = QHBoxLayout()
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.clicked.connect(self.fit_to_view)
        controls.addWidget(self.zoom_in_btn)
        controls.addWidget(self.zoom_out_btn)
        controls.addWidget(self.fit_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self._pixmap: Optional[QPixmap] = None
        self._zoom_factor = 1.0

    def set_image(self, pixmap: QPixmap) -> None:
        """Set the image to display."""
        self._pixmap = pixmap
        self._zoom_factor = 1.0
        self._update_display()

    def _update_display(self) -> None:
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self._pixmap.size() * self._zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            self.image_label.setFixedSize(scaled.size())
        else:
            self.image_label.setText("No Image")
            self.image_label.setPixmap(QPixmap())

    def zoom_in(self) -> None:
        self._zoom_factor *= 1.2
        self._update_display()

    def zoom_out(self) -> None:
        self._zoom_factor /= 1.2
        if self._zoom_factor < 0.1:
            self._zoom_factor = 0.1
        self._update_display()

    def fit_to_view(self) -> None:
        if self._pixmap and not self._pixmap.isNull():
            view_size = self.scroll.viewport().size()
            img_size = self._pixmap.size()
            h_ratio = view_size.width() / img_size.width()
            v_ratio = view_size.height() / img_size.height()
            self._zoom_factor = min(h_ratio, v_ratio)
            self._update_display()