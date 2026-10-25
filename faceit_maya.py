# -*- coding: utf-8 -*-
"""Maya plugin entry point for FaceIT for Maya."""

import os
import sys

PLUGIN_NAME = "faceit_maya"
__version__ = "1.0.0"


def _plugin_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        import maya.cmds as cmds
        path = cmds.pluginInfo(PLUGIN_NAME, query=True, path=True)
        return os.path.dirname(os.path.abspath(path))


def _ensure_path():
    directory = _plugin_dir()
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return directory


def initializePlugin(plugin):
    _ensure_path()
    import maya_faceit
    maya_faceit.initializePlugin(plugin)


def uninitializePlugin(plugin):
    import maya_faceit
    maya_faceit.uninitializePlugin(plugin)
