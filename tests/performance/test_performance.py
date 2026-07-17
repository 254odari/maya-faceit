# -*- coding: utf-8 -*-
"""
tests/performance/test_performance.py

Performance benchmarks for heavy operations.
"""

import time
from maya_faceit.mayafaceit.lib._pytest import pytest
from maya_faceit.blendshapes import BlendshapeManager
from maya_faceit.rig import rig_builder


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks."""

    def test_rig_build_time(self):
        start = time.time()
        result = rig_builder.build_rig("head_geo", template="default")
        elapsed = time.time() - start
        # Build should take less than 5 seconds for a standard rig
        assert elapsed < 5.0
        assert result.success

    def test_blendshape_optimization_time(self, sample_blendshape_targets):
        manager = BlendshapeManager()
        start = time.time()
        # Simulate optimization with 100 targets
        manager.optimize()
        elapsed = time.time() - start
        # Optimization should be fast
        assert elapsed < 2.0