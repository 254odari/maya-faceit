"""
ui/pages/cache.py

Cache management page.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QGroupBox, QFormLayout
    from PySide2.QtCore import Qt
else:
    QWidget = object


class CachePage(QWidget):
    """Page for managing caches (meshes, deltas, generated data)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Info group
        info_group = QGroupBox("Cache Information")
        info_layout = QFormLayout(info_group)
        self.total_size_label = QLabel("0 MB")
        self.item_count_label = QLabel("0")
        self.last_clean_label = QLabel("Never")
        info_layout.addRow("Total Cache Size:", self.total_size_label)
        info_layout.addRow("Cached Items:", self.item_count_label)
        info_layout.addRow("Last Cleaned:", self.last_clean_label)
        layout.addWidget(info_group)

        # Actions
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)

        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear All Cache")
        clear_btn.clicked.connect(self._clear_all)
        clear_btn.setStyleSheet("background-color: #8b3a3a;")
        btn_layout.addWidget(clear_btn)

        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self._refresh_stats)
        btn_layout.addWidget(refresh_btn)
        action_layout.addLayout(btn_layout)

        # Optional: clear specific types
        type_layout = QHBoxLayout()
        self.clear_meshes = QPushButton("Clear Meshes")
        self.clear_meshes.clicked.connect(lambda: self._clear_type("meshes"))
        self.clear_deltas = QPushButton("Clear Deltas")
        self.clear_deltas.clicked.connect(lambda: self._clear_type("deltas"))
        self.clear_poses = QPushButton("Clear Poses")
        self.clear_poses.clicked.connect(lambda: self._clear_type("poses"))
        type_layout.addWidget(self.clear_meshes)
        type_layout.addWidget(self.clear_deltas)
        type_layout.addWidget(self.clear_poses)
        action_layout.addLayout(type_layout)

        layout.addWidget(action_group)

        # Progress bar for long operations
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Initial refresh
        self._refresh_stats()

    def _refresh_stats(self):
        """Update cache statistics (placeholder)."""
        # In a real implementation, query the cache manager.
        self.total_size_label.setText("42.5 MB")
        self.item_count_label.setText("127")
        self.last_clean_label.setText("Today, 10:30 AM")
        self.status_label.setText("Statistics updated")

    def _clear_all(self):
        """Clear all caches."""
        self.status_label.setText("Clearing all caches...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indeterminate
        # Simulate operation
        QtCore.QTimer.singleShot(1500, self._on_clear_done)

    def _on_clear_done(self):
        self.progress.setVisible(False)
        self.status_label.setText("All caches cleared.")
        self._refresh_stats()

    def _clear_type(self, cache_type: str):
        """Clear a specific cache type."""
        self.status_label.setText(f"Clearing {cache_type}...")
        # Simulate
        QtCore.QTimer.singleShot(800, lambda: self.status_label.setText(f"{cache_type} cleared."))