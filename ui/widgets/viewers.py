# ui/widgets/viewers.py

"""
ui/widgets/viewers.py

3D and graph viewers.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QWidget, QVBoxLayout, QLabel, QPixmap, Qt


class MeshViewer(QWidget):
    """Placeholder for a 3D mesh viewer (could embed Maya viewport)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #444;")
        label = QLabel("3D Preview")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888;")
        layout = QVBoxLayout(self)
        layout.addWidget(label)


class GraphViewer(QWidget):
    """Placeholder for a graph/curve viewer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #444;")
        label = QLabel("Graph View")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888;")
        layout = QVBoxLayout(self)
        layout.addWidget(label)


class ImageViewer(QWidget):
    """Placeholder for image display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #444;")
        self.label = QLabel("No Image")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #888;")
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def set_image(self, pixmap: Optional[QPixmap]) -> None:
        """Set image to display."""
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled)
            self.label.setText("")
        else:
            self.label.setText("No Image")
            self.label.setPixmap(QPixmap())