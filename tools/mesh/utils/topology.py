"""
tools/mesh/utils/topology.py

Topology fingerprinting, hashing, and comparison.
"""

import hashlib
import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import Dict, List, Tuple

class TopologyUtils:
    """Topology fingerprint utilities."""

    @staticmethod
    def get_fingerprint(mesh: str) -> str:
        """Compute a topology fingerprint (hash of vertex and face data)."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        vtx_count = fn_mesh.numVertices()
        face_count = fn_mesh.numPolygons()
        # Get face vertex counts
        face_vert_counts = []
        for i in range(face_count):
            face_vert_counts.append(len(fn_mesh.getPolygonVertices(i)))
        # Create a string: vertex_count|face_count|face_vert_counts
        data = f"{vtx_count}|{face_count}|" + "|".join(str(x) for x in face_vert_counts)
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def compare_topology(mesh1: str, mesh2: str) -> bool:
        """Compare topology of two meshes."""
        return TopologyUtils.get_fingerprint(mesh1) == TopologyUtils.get_fingerprint(mesh2)

    @staticmethod
    def get_face_vertex_counts(mesh: str) -> List[int]:
        """Get list of vertex counts per face."""
        sel = om2.MSelectionList()
        sel.add(mesh)
        dag = sel.getDagPath(0)
        fn_mesh = om2.MFnMesh(dag)
        return [len(fn_mesh.getPolygonVertices(i)) for i in range(fn_mesh.numPolygons())]