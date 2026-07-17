"""
tools/mesh/utils/relax.py

Vertex relaxation for meshes (volume-preserving).
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional
from ...relax import RelaxTools, RelaxSettings, RelaxAlgorithm

def relax_mesh(mesh: str, iterations: int = 10, strength: float = 0.5,
               preserve_border: bool = True, algorithm: str = "HC") -> int:
    """
    Relax vertices of a mesh.
    Returns number of vertices processed.
    """
    settings = RelaxSettings(
        iterations=iterations,
        strength=strength,
        preserve_border=preserve_border,
        algorithm=RelaxAlgorithm(algorithm.upper()) if algorithm.upper() in ["LAPLACIAN", "HC", "TAUBIN"] else RelaxAlgorithm.HC
    )
    relax = RelaxTools(settings)
    report = relax.mesh(mesh)
    return report.processed_vertices if report.success else 0