# -*- coding: utf-8 -*-
"""
tests/conftest.py

Pytest fixtures for Maya FaceIT tests.
"""

import os
import tempfile
import shutil
from pathlib import Path
from maya_faceit.mayafaceit.lib._pytest import pytest


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test output."""
    tmp = tempfile.mkdtemp(prefix="faceit_test_")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def mock_maya():
    """
    Mock Maya environment.
    In real tests, you would use maya.standalone or mock cmds.
    """
    try:
        import maya.standalone
        maya.standalone.initialize()
        yield True
        maya.standalone.uninitialize()
    except ImportError:
        yield False


@pytest.fixture
def sample_mesh_data():
    """Return sample mesh data for testing."""
    return {
        "vertices": [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        "faces": [(0, 1, 2)],
        "name": "test_mesh"
    }


@pytest.fixture
def sample_blendshape_targets():
    """Return sample blendshape target data."""
    return {
        "Smile": {"vertices": [(0.1, 0.1, 0), (0.2, 0, 0), (0, 0.2, 0)]},
        "Frown": {"vertices": [(-0.1, -0.1, 0), (-0.2, 0, 0), (0, -0.2, 0)]}
    }