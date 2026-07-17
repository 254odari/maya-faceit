# -*- coding: utf-8 -*-
"""
tests/rig/test_rig.py

Tests for rig building and controllers.
"""

from maya_faceit.mayafaceit.lib._pytest import pytest
from maya_faceit.rig import rig_builder, ControllerBuilder, JointBuilder


class TestRigBuilder:
    """Test rig builder functionality."""

    def test_build_rig(self):
        # TODO: use mock Maya
        result = rig_builder.build_rig("head_geo", template="default")
        assert result.success

    def test_controller_creation(self):
        builder = ControllerBuilder()
        ctrl = builder.create_controller("jaw_ctrl", "circle", radius=2.5)
        assert ctrl.name == "jaw_ctrl"

    def test_joint_creation(self):
        builder = JointBuilder()
        joint = builder.create_joint("jaw_jnt", position=(0, 0, 0))
        assert joint.name == "jaw_jnt"