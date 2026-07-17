"""
tools/mesh/utils/smooth.py

Mesh smoothing utilities.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional
from ...smooth import SmoothTools, SmoothSettings, SmoothAlgorithm

def smooth_mesh(mesh: str, iterations: int = 5, strength: float = 0.5,
                preserve_border: bool = True, algorithm: str = "LAPLACIAN") -> int:
    """
    Smooth vertices of a mesh.
    Returns number of vertices processed.
    """
    settings = SmoothSettings(
        iterations=iterations,
        strength=strength,
        preserve_border=preserve_border,
        algorithm=SmoothAlgorithm(algorithm.upper()) if algorithm.upper() in ["LAPLACIAN", "HC", "TAUBIN", "GAUSSIAN", "BILATERAL"] else SmoothAlgorithm.LAPLACIAN
    )
    smooth = SmoothTools(settings)
    report = smooth.mesh(mesh)
    return report.processed_count if report.success else 0