# -*- coding: utf-8 -*-
"""
export/engines/metahuman.py

MetaHuman Engine processing.
"""

from ..core.base import BaseEngine
from ..types import ExportResult


class MetaHumanEngine(BaseEngine):
    """MetaHuman Engine processor."""

    def process(self, result: ExportResult) -> ExportResult:
        result.details['metahuman'] = {
            'processed': True,
            'export_script': self._generate_export_script()
        }
        return result

    def _generate_export_script(self) -> str:
        return f"""
# MetaHuman export script for {self.settings.filepath}
# Use MetaHuman SDK
"""