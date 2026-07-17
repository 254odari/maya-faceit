# -*- coding: utf-8 -*-
"""
tools/relax/reporter.py

Report formatting and saving.
"""

import json
from typing import Dict, Any
from .types import RelaxReport


class RelaxReporter:
    """Format and save relaxation reports."""

    def save_report(self, report: RelaxReport, filepath: str, format: str = "json") -> bool:
        """Save a report to a file."""
        try:
            if format == "json":
                data = self._report_to_dict(report)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
            elif format == "txt":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self._report_to_text(report))
            else:
                return False
            return True
        except Exception as e:
            print(f"Error saving report: {e}")
            return False

    def _report_to_dict(self, report: RelaxReport) -> Dict[str, Any]:
        return {
            'success': report.success,
            'mode': report.mode.value,
            'processed_vertices': report.processed_vertices,
            'iterations': report.iterations,
            'average_displacement': report.average_displacement,
            'max_displacement': report.max_displacement,
            'time_ms': report.time_ms,
            'warnings': report.warnings,
            'errors': report.errors,
            'details': report.details,
        }

    def _report_to_text(self, report: RelaxReport) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"Relaxation Report - {report.mode.value}")
        lines.append("=" * 60)
        lines.append(f"  Success: {report.success}")
        lines.append(f"  Processed: {report.processed_vertices} vertices")
        lines.append(f"  Iterations: {report.iterations}")
        lines.append(f"  Avg Displacement: {report.average_displacement:.6f}")
        lines.append(f"  Max Displacement: {report.max_displacement:.6f}")
        lines.append(f"  Time: {report.time_ms:.2f}ms")
        if report.warnings:
            lines.append("  Warnings:")
            for w in report.warnings:
                lines.append(f"    - {w}")
        if report.errors:
            lines.append("  Errors:")
            for e in report.errors:
                lines.append(f"    - {e}")
        lines.append("=" * 60)
        return "\n".join(lines)