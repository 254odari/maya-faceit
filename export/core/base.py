# -*- coding: utf-8 -*-
"""
export/core/base.py

Base classes for exporters and engines.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..types import ExportSettings, ExportResult


class BaseExporter(ABC):
    """Base class for all format exporters."""

    def __init__(self, settings: ExportSettings):
        self.settings = settings

    @abstractmethod
    def export(self) -> ExportResult:
        """Perform the export operation."""
        pass

    def validate(self) -> bool:
        """Validate settings before export."""
        return True


class BaseEngine(ABC):
    """Base class for game engine processors."""

    def __init__(self, settings: ExportSettings):
        self.settings = settings

    @abstractmethod
    def process(self, result: ExportResult) -> ExportResult:
        """Process the exported result for the engine."""
        pass