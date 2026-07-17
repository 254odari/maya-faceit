"""
ui/controllers/export_controller.py

Controller for export operations.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ExportController:
    """Handles export to various formats."""

    def __init__(self):
        self._export_format = "FBX"
        self._include_weights = True
        self._optimize = True

    def set_format(self, format: str) -> None:
        self._export_format = format

    def set_include_weights(self, include: bool) -> None:
        self._include_weights = include

    def set_optimize(self, optimize: bool) -> None:
        self._optimize = optimize

    def export(self, path: str) -> bool:
        """Export to the specified path."""
        logger.info(f"Exporting to {path} as {self._export_format}")
        # TODO: Call core exporter
        return True

    def get_available_formats(self) -> list:
        return ["FBX", "USD", "Alembic", "JSON", "MetaHuman"]

    def get_export_options(self) -> dict:
        return {
            "format": self._export_format,
            "include_weights": self._include_weights,
            "optimize": self._optimize,
        }