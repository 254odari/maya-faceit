# -*- coding: utf-8 -*-
"""
tools/analysis/performance.py

Performance analysis.
"""

import maya.cmds as cmds # type: ignore
import time
from typing import Optional
from .types import PerformanceStats, AnalysisScope, AnalysisLevel


class PerformanceAnalyzer:
    """
    Analyze scene performance.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> PerformanceStats:
        """Analyze performance statistics."""
        stats = PerformanceStats()

        # Evaluation mode
        try:
            eval_mode = cmds.evaluationManager(q=True, mode=True) or "DG"
            stats.evaluation_mode = eval_mode
        except:
            stats.evaluation_mode = "DG"

        # GPU compatibility (heuristic)
        stats.gpu_compatible = self._check_gpu_compatibility()
        stats.gpu_enabled = stats.gpu_compatible and stats.evaluation_mode == "GPU"

        # Cached playback
        try:
            stats.cached_playback_enabled = cmds.playbackOptions(q=True, useCache=True)
        except:
            stats.cached_playback_enabled = False

        # Parallel evaluation
        stats.parallel_evaluation_enabled = stats.evaluation_mode == "PARALLEL"

        # FPS benchmark
        stats.fps = self._benchmark_fps()

        if level == AnalysisLevel.DEEP:
            # Memory usage (approximate)
            stats.memory_usage_mb = self._get_memory_usage()
            stats.gpu_memory_mb = self._get_gpu_memory()

        return stats

    def _benchmark_fps(self) -> float:
        """Benchmark FPS by evaluating a few frames."""
        try:
            start = time.time()
            frames = self.settings.benchmark_frames
            for _ in range(frames):
                cmds.currentTime(cmds.currentTime(q=True) + 1, update=True)
            elapsed = time.time() - start
            if elapsed > 0:
                return frames / elapsed
        except:
            pass
        return 0.0

    def _check_gpu_compatibility(self) -> bool:
        """Check if GPU evaluation is possible (heuristic)."""
        # Check for nodes that block GPU
        # Simplified: if there are many clusters or complex nodes, may not be compatible
        clusters = cmds.ls(type='cluster')
        if len(clusters) > 10:
            return False
        # Check if GPU override is enabled
        try:
            gpu_override = cmds.getAttr("evaluationManager.gpuOverride")
            return bool(gpu_override)
        except:
            return False

    def _get_memory_usage(self) -> float:
        """Get approximate memory usage."""
        try:
            import maya.mel as mel # type: ignore
            mem = mel.eval('memory -q -size -units MB')
            return float(mem)
        except:
            return 0.0

    def _get_gpu_memory(self) -> float:
        """Get approximate GPU memory usage."""
        # Not directly available in Maya
        return 0.0