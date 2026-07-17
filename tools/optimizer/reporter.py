# -*- coding: utf-8 -*-
"""
tools/optimizer/reporter.py

Report formatting and saving.
"""

import json
from typing import Dict, Any
from .types import OptimizationReport


class OptimizationReporter:
    """
    Format and save optimization reports.
    """

    def save_report(self, report: OptimizationReport, filepath: str, format: str = "json") -> bool:
        """
        Save a report to a file.

        Args:
            report: OptimizationReport to save.
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

    def _report_to_dict(self, report: OptimizationReport) -> Dict[str, Any]:
        """Convert report to dict for JSON serialization."""
        return {
            'type': report.type.value,
            'level': report.level.value,
            'success': report.success,
            'fps_before': report.fps_before,
            'fps_after': report.fps_after,
            'memory_saved_mb': report.memory_saved_mb,
            'elapsed_time_ms': report.elapsed_time_ms,
            'scene': report.scene.__dict__,
            'mesh': report.mesh.__dict__,
            'rig': report.rig.__dict__,
            'blendshape': report.blendshape.__dict__,
            'skin': report.skin.__dict__,
            'deformer': report.deformer.__dict__,
            'animation': report.animation.__dict__,
            'evaluation': report.evaluation.__dict__,
            'warnings': report.warnings,
            'errors': report.errors,
            'details': report.details,
        }