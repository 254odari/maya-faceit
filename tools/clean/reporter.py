# -*- coding: utf-8 -*-
"""
tools/clean/reporter.py

Report formatting and saving.
"""

import json
from typing import Dict, Any
from .types import CleanupReport


class CleanupReporter:
    """
    Format and save cleanup reports.
    """

    def save_report(self, report: CleanupReport, filepath: str, format: str = "json") -> bool:
        """
        Save a report to a file.

        Args:
            report: CleanupReport to save.
            filepath: Path to save.
            format: "json" or "txt".

        Returns:
            True if successful.
        """
        try:
            if format == "json":
                data = self._report_to_dict(report)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
            elif format == "txt":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report.summary())
            else:
                return False
            return True
        except Exception as e:
            print(f"Error saving report: {e}")
            return False

    def _report_to_dict(self, report: CleanupReport) -> Dict[str, Any]:
        """Convert report to dict for JSON serialization."""
        return {
            'type': report.type.value,
            'mode': report.mode.value,
            'success': report.success,
            'elapsed_time_ms': report.elapsed_time_ms,
            'scene': report.scene.__dict__,
            'mesh': report.mesh.__dict__,
            'material': report.material.__dict__,
            'animation': report.animation.__dict__,
            'rig': report.rig.__dict__,
            'blendshape': report.blendshape.__dict__,
            'namespace': report.namespace.__dict__,
            'warnings': report.warnings,
            'errors': report.errors,
            'details': report.details,
        }