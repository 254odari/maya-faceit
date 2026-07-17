# -*- coding: utf-8 -*-
"""
tests/core/test_core.py

Tests for core application and project management.
"""

from maya_faceit.mayafaceit.lib._pytest import pytest
from maya_faceit.core import FaceitApp, FaceitProject, preferences


class TestCoreApp:
    """Test application lifecycle."""

    def test_app_singleton(self):
        app1 = FaceitApp()
        app2 = FaceitApp()
        assert app1 is app2

    def test_app_bootstrap(self, temp_dir):
        app = FaceitApp()
        # TODO: implement bootstrap test
        assert True


class TestCoreProject:
    """Test project management."""

    def test_project_creation(self, temp_dir):
        project = FaceitProject()
        project.create("TestProject", str(temp_dir))
        assert project.get_current() is not None

    def test_project_save_load(self, temp_dir):
        project = FaceitProject()
        project.create("TestProject", str(temp_dir))
        project.save()
        # TODO: load back and verify
        assert True


class TestCorePreferences:
    """Test preferences."""

    def test_preferences_defaults(self):
        prefs = preferences
        assert prefs.get("language") == "en"