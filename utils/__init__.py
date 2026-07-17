# -*- coding: utf-8 -*-
"""
maya_faceit.utils
~~~~~~~~~~~~~~~~~

Shared utilities for the entire Maya FaceIT plugin.
"""

from .api import MayaAPI
from .math import MathUtils
from .matrix import MatrixUtils
from .mesh import MeshUtils
from .curves import CurveUtils
from .transforms import TransformUtils
from .geometry import GeometryUtils
from .serialization import SerializationUtils
from .filesystem import FileSystemUtils
from .decorators import (
    timer,
    timeit,
    debug_log,
    retry,
    deprecated,
    singleton,
)
from .undo import undo_chunk, undoable, begin_undo, end_undo, undo, redo, flush_undo
from .progress import ProgressContext, progress
from .profiler import Profiler, profile
from .threading import ThreadPool, AsyncWorker
from .color import ColorUtils
from .conversion import ConversionUtils

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

__all__ = [
    # api
    "MayaAPI",
    # math
    "MathUtils",
    # matrix
    "MatrixUtils",
    # mesh
    "MeshUtils",
    # curves
    "CurveUtils",
    # transforms
    "TransformUtils",
    # geometry
    "GeometryUtils",
    # serialization
    "SerializationUtils",
    # filesystem
    "FileSystemUtils",
    # decorators
    "timer",
    "timeit",
    "debug_log",
    "retry",
    "deprecated",
    "singleton",
    # undo
    "undo_chunk",
    "undoable",
    "begin_undo",
    "end_undo",
    "undo",
    "redo",
    "flush_undo",
    # progress
    "ProgressContext",
    "progress",
    # profiler
    "Profiler",
    "profile",
    # threading
    "ThreadPool",
    "AsyncWorker",
    # color
    "ColorUtils",
    # conversion
    "ConversionUtils",
]