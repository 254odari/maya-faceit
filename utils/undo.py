# -*- coding: utf-8 -*-
"""
maya_faceit.utils.undo
~~~~~~~~~~~~~~~~~~~~~~

Undo utilities.
"""

import maya.cmds as cmds # type: ignore
from contextlib import contextmanager
from typing import Optional, Callable, Any


@contextmanager
def undo_chunk(name: str = "Operation", close_on_exit: bool = True):
    """Context manager for Maya undo chunks."""
    try:
        cmds.undoInfo(openChunk=True, chunkName=name)
        yield
    finally:
        if close_on_exit:
            cmds.undoInfo(closeChunk=True)


def undoable(func: Callable) -> Callable:
    """Decorator to wrap a function in an undo chunk."""
    def wrapper(*args, **kwargs):
        with undo_chunk(func.__name__):
            return func(*args, **kwargs)
    return wrapper


def begin_undo(name: str = "Operation"):
    """Begin an undo chunk."""
    cmds.undoInfo(openChunk=True, chunkName=name)


def end_undo():
    """End an undo chunk."""
    cmds.undoInfo(closeChunk=True)


def undo():
    """Perform undo."""
    cmds.undo()


def redo():
    """Perform redo."""
    cmds.redo()


def flush_undo():
    """Flush undo history."""
    cmds.flushUndo()