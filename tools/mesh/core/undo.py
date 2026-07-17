# -*- coding: utf-8 -*-
"""
tools.mesh.core.undo
~~~~~~~~~~~~~~~~~~~~

Undo chunk context manager.
"""

import maya.cmds as cmds # type: ignore

class UndoChunk:
    """Context manager for Maya undo chunks."""
    def __init__(self, name: str = "Mesh Operation"):
        self.name = name
        self._open = False

    def __enter__(self):
        if not self._open:
            cmds.undoInfo(openChunk=True, chunkName=self.name)
            self._open = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._open:
            cmds.undoInfo(closeChunk=True)
            self._open = False

    def begin(self):
        cmds.undoInfo(openChunk=True, chunkName=self.name)
        self._open = True

    def end(self):
        if self._open:
            cmds.undoInfo(closeChunk=True)
            self._open = False