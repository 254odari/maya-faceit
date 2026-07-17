# -*- coding: utf-8 -*-
"""
tools/analysis/reporter.py

Report generation and formatting.
"""

import json
from typing import Dict, Any
from .types import AnalysisReport


class AnalysisReporter:
    """
    Format and save analysis reports.
    """

    def save_report(self, report: AnalysisReport, filepath: str, format: str = "json") -> bool:
        """
        Save a report to a file.

        Args:
            report: AnalysisReport to save.
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

    def _report_to_dict(self, report: AnalysisReport) -> Dict[str, Any]:
        """Convert report to dict for JSON serialization."""
        return {
            'scope': report.scope.value,
            'level': report.level.value,
            'timestamp': report.timestamp,
            'duration_ms': report.duration_ms,
            'scene': {
                'total_nodes': report.scene.total_nodes,
                'total_meshes': report.scene.total_meshes,
                'total_joints': report.scene.total_joints,
                'total_controllers': report.scene.total_controllers,
                'total_constraints': report.scene.total_constraints,
                'total_references': report.scene.total_references,
                'unknown_nodes': report.scene.unknown_nodes,
                'empty_groups': report.scene.empty_groups,
            },
            'mesh': {
                'total_vertices': report.mesh.total_vertices,
                'total_faces': report.mesh.total_faces,
                'total_ngons': report.mesh.total_ngons,
                'non_manifold_edges': report.mesh.non_manifold_edges,
                'open_borders': report.mesh.open_borders,
            },
            'rig': {
                'total_controllers': report.rig.total_controllers,
                'total_joints': report.rig.total_joints,
                'total_blendshape_targets': report.rig.total_blendshape_targets,
                'orphan_joints': report.rig.orphan_joints,
                'orphan_controllers': report.rig.orphan_controllers,
            },
            'animation': {
                'total_animated_objects': report.animation.total_animated_objects,
                'total_keyframes': report.animation.total_keyframes,
                'time_range_start': report.animation.time_range_start,
                'time_range_end': report.animation.time_range_end,
            },
            'performance': {
                'fps': report.performance.fps,
                'evaluation_mode': report.performance.evaluation_mode,
                'gpu_compatible': report.performance.gpu_compatible,
                'cached_playback_enabled': report.performance.cached_playback_enabled,
            },
            'warnings': report.warnings,
            'errors': report.errors,
        }