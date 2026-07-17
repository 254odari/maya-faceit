# -*- coding: utf-8 -*-
"""
export/engines/unity.py

Unity Engine processing.
"""

from ..core.base import BaseEngine
from ..types import ExportResult


class UnityEngine(BaseEngine):
    """Unity Engine processor."""

    def process(self, result: ExportResult) -> ExportResult:
        result.details['unity'] = {
            'processed': True,
            'import_script': self._generate_import_script()
        }
        return result

    def _generate_import_script(self) -> str:
        return f"""
# Unity import script for {self.settings.filepath}
# Use Unity's AssetDatabase
"""