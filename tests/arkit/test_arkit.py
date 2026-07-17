# -*- coding: utf-8 -*-
"""
tests/arkit/test_arkit.py

Tests for ARKit mapping and generation.
"""

import pytest
from maya_faceit.blendshapes.arkit import (
    ARKitMapper,
    ARKitValidator,
    ARKit_BLENDSHAPES,
)


class TestARKitMapper:
    """Test ARKit mapping engine."""

    def test_mapper_creation(self):
        mapper = ARKitMapper()
        assert mapper is not None

    def test_map_channel(self):
        mapper = ARKitMapper()
        mapper.map_channel("EyeBlink_L", "blink_L")
        mapping = mapper.get_mapping()
        assert mapping["EyeBlink_L"] == "blink_L"

    def test_evaluation(self):
        mapper = ARKitMapper()
        result = mapper.evaluate({"EyeBlink_L": 0.5})
        assert result is not None


class TestARKitValidator:
    """Test ARKit validation."""

    def test_validate_coefficients(self):
        validator = ARKitValidator()
        report = validator.validate_coefficients({"EyeBlink_L": 1.5})
        assert not report.success