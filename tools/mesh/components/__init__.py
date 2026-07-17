"""
tools/mesh/components/__init__.py

Component-level tools package.
Provides Vertex, Edge, Face, and Selection utilities.
"""

from __future__ import annotations

# Import main classes
from .vertices import VertexTools
from .edges import EdgeTools
from .faces import FaceTools
from .selection import MeshSelectionTools

# Package-level convenience functions and re-exports

__all__ = [
    "VertexTools",
    "EdgeTools",
    "FaceTools",
    "MeshSelectionTools",
    
    # Convenience aliases
    "vertex",
    "edge",
    "face",
    "selection",
]


# Lazy initialization helper for easy access from MeshEngine
class ComponentTools:
    """
    Convenience container for all component tools.
    Instantiated by MeshEngine.
    """
    
    def __init__(self, editor):
        self.vertices = VertexTools(editor)
        self.edges = EdgeTools(editor)
        self.faces = FaceTools(editor)
        self.selection = MeshSelectionTools(editor)


# Global instances (for direct import if needed)
# These will be properly initialized through MeshEngine in normal usage

__version__ = "1.0.0"


# Optional: Quick access shortcuts (used internally)
def _initialize_components(editor):
    """Called by MeshEngine to set up component tools."""
    global vertex, edge, face, selection
    
    vertex = VertexTools(editor)
    edge = EdgeTools(editor)
    face = FaceTools(editor)
    selection = MeshSelectionTools(editor)


# These will be populated when MeshEngine initializes
vertex: VertexTools = None  # type: ignore
edge: EdgeTools = None      # type: ignore
face: FaceTools = None      # type: ignore
selection: MeshSelectionTools = None  # type: ignore