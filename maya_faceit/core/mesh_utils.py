# mesh_utils.py
# Maya Faceit Plugin - Mesh Utilities
# Converted from Blender to Maya Python 3.11

"""
Mesh utilities for Faceit Maya plugin.
Handles mesh operations, vertex selection, and geometry analysis.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from maya.api.OpenMaya import MVector, MPoint, MFnMesh, MMatrix
import numpy as np
from typing import List, Dict, Optional, Tuple, Set, Union
import math


# ============================================================
# Vertex Group Utilities
# ============================================================

def get_verts_in_vgroup(mesh: str, vertex_group_name: str) -> List[int]:
    """
    Get all vertex indices in a vertex group.
    
    Args:
        mesh: Mesh object name
        vertex_group_name: Name of the vertex group
        
    Returns:
        List of vertex indices
    """
    if not cmds.objExists(mesh):
        return []
    
    # Check if vertex group exists
    if vertex_group_name not in cmds.listAttr(f"{mesh}.vertexGroups"):
        return []
    
    # Get vertices in group
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    result = []
    
    for vtx in vertices:
        # Check if vertex is in group
        if cmds.vertexInGroup(vtx, vertex_group_name):
            # Extract vertex index
            idx = int(vtx.split('[')[1].split(']')[0])
            result.append(idx)
    
    return result


# ============================================================
# Mesh Dimension and Position Utilities
# ============================================================

def get_max_dim_in_direction(
    mesh: str,
    direction: Tuple[float, float, float],
    vertex_group_name: str = None
) -> Tuple[float, float, float]:
    """
    Get the furthest point of the mesh in a specified direction.
    
    Args:
        mesh: Mesh object name
        direction: Direction vector (x, y, z)
        vertex_group_name: Optional vertex group to filter vertices
        
    Returns:
        Furthest point position (x, y, z)
    """
    if not cmds.objExists(mesh):
        return (0.0, 0.0, 0.0)
    
    # Get vertices
    if vertex_group_name:
        vertex_indices = get_verts_in_vgroup(mesh, vertex_group_name)
        vertices = [f"{mesh}.vtx[{i}]" for i in vertex_indices]
    else:
        vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    
    if not vertices:
        return (0.0, 0.0, 0.0)
    
    # Get world matrix
    world_matrix = cmds.xform(mesh, query=True, worldSpace=True, matrix=True)
    
    # Normalize direction
    dir_vec = MVector(direction[0], direction[1], direction[2])
    dir_vec.normalize()
    
    far_distance = -float('inf')
    far_point = MVector(0, 0, 0)
    
    for vtx in vertices:
        pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        if pos:
            point = MVector(pos[0], pos[1], pos[2])
            # Project point onto direction
            temp = point * dir_vec
            if temp > far_distance:
                far_distance = temp
                far_point = point
    
    return (far_point.x, far_point.y, far_point.z)


def get_object_center(mesh: str) -> Tuple[float, float, float]:
    """
    Find the center of a mesh object using the bounding box.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Center position (x, y, z)
    """
    if not cmds.objExists(mesh):
        return (0.0, 0.0, 0.0)
    
    # Get bounding box
    bbox = cmds.xform(mesh, query=True, worldSpace=True, boundingBox=True)
    if not bbox:
        return (0.0, 0.0, 0.0)
    
    # Calculate center
    center = [
        (bbox[0] + bbox[3]) / 2,
        (bbox[1] + bbox[4]) / 2,
        (bbox[2] + bbox[5]) / 2
    ]
    
    return (center[0], center[1], center[2])


def get_mesh_vertices(mesh: str, world_space: bool = True) -> np.ndarray:
    """
    Get all vertex positions of a mesh.
    
    Args:
        mesh: Mesh object name
        world_space: Whether to return world space positions
        
    Returns:
        Numpy array of vertex positions
    """
    if not cmds.objExists(mesh):
        return np.array([])
    
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    positions = []
    
    for vtx in vertices:
        if world_space:
            pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        else:
            pos = cmds.xform(vtx, query=True, objectSpace=True, translation=True)
        
        if pos:
            positions.append(pos)
    
    return np.array(positions)


# ============================================================
# Point-in-Mesh Utilities
# ============================================================

def is_inside_dot(
    target_point: Tuple[float, float, float],
    mesh: str,
    tolerance: float = 0.05
) -> bool:
    """
    Check if a point is inside a mesh using the dot product method.
    
    Args:
        target_point: Point to check (x, y, z)
        mesh: Mesh object name
        tolerance: Inside tolerance threshold
        
    Returns:
        True if point is inside the mesh
    """
    if not cmds.objExists(mesh):
        return False
    
    # Convert point to MPoint
    target_pt = MPoint(target_point[0], target_point[1], target_point[2])
    
    # Get mesh data
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    fn_mesh = MFnMesh(dag_path)
    
    # Find closest point on mesh
    closest_point, face_id = fn_mesh.getClosestPoint(target_pt, om2.MSpace.kWorld)
    
    if closest_point is None:
        return False
    
    # Get face normal
    face_normal = fn_mesh.getFaceNormal(face_id, om2.MSpace.kWorld)
    
    # Calculate vector from closest point to target
    to_target = target_pt - closest_point
    to_target.normalize()
    
    # Calculate dot product
    dot_product = to_target * face_normal
    
    # Convert to angle
    angle = math.acos(max(min(dot_product, 1.0), -1.0)) * 180.0 / math.pi
    
    # Check if inside
    inside = angle < (90.0 - tolerance)
    
    return inside


def closest_point_on_mesh(
    point: Tuple[float, float, float],
    mesh: str
) -> Optional[Tuple[float, float, float]]:
    """
    Find the closest point on a mesh to a given point.
    
    Args:
        point: Point (x, y, z)
        mesh: Mesh object name
        
    Returns:
        Closest point (x, y, z) or None
    """
    if not cmds.objExists(mesh):
        return None
    
    # Convert point to MPoint
    target_pt = MPoint(point[0], point[1], point[2])
    
    # Get mesh data
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    fn_mesh = MFnMesh(dag_path)
    
    # Find closest point
    closest_point, _ = fn_mesh.getClosestPoint(target_pt, om2.MSpace.kWorld)
    
    if closest_point is not None:
        return (closest_point.x, closest_point.y, closest_point.z)
    
    return None


def get_face_normal_at_point(
    point: Tuple[float, float, float],
    mesh: str
) -> Optional[Tuple[float, float, float]]:
    """
    Get the face normal at the closest point on a mesh.
    
    Args:
        point: Point (x, y, z)
        mesh: Mesh object name
        
    Returns:
        Face normal (x, y, z) or None
    """
    if not cmds.objExists(mesh):
        return None
    
    # Convert point to MPoint
    target_pt = MPoint(point[0], point[1], point[2])
    
    # Get mesh data
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    fn_mesh = MFnMesh(dag_path)
    
    # Find closest point
    _, face_id = fn_mesh.getClosestPoint(target_pt, om2.MSpace.kWorld)
    
    if face_id is not None:
        normal = fn_mesh.getFaceNormal(face_id, om2.MSpace.kWorld)
        return (normal.x, normal.y, normal.z)
    
    return None


# ============================================================
# Vertex Selection Utilities
# ============================================================

def select_vertices(
    mesh: str,
    vertex_indices: List[int] = None,
    deselect_others: bool = False
) -> bool:
    """
    Select vertices on a mesh.
    
    Args:
        mesh: Mesh object name
        vertex_indices: List of vertex indices to select (None for all)
        deselect_others: Whether to deselect other vertices
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    # Select the mesh
    cmds.select(mesh)
    
    # Enter vertex mode
    cmds.selectType(vertex=True, object=False)
    
    if vertex_indices is None:
        # Select all vertices
        cmds.select(f"{mesh}.vtx[*]", replace=True)
    else:
        # Select specific vertices
        if deselect_others:
            cmds.select(clear=True)
        
        for idx in vertex_indices:
            cmds.select(f"{mesh}.vtx[{idx}]", add=True)
    
    return True


def select_vertices_bmesh(
    vertex_indices: List[int],
    mesh: str,
    deselect_others: bool = False
) -> bool:
    """
    Select vertices using bmesh-like API (Maya equivalent).
    
    Args:
        vertex_indices: List of vertex indices
        mesh: Mesh object name
        deselect_others: Whether to deselect other vertices
        
    Returns:
        True if successful
    """
    return select_vertices(mesh, vertex_indices, deselect_others)


def get_selected_vertices(mesh: str) -> List[int]:
    """
    Get selected vertex indices on a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        List of selected vertex indices
    """
    if not cmds.objExists(mesh):
        return []
    
    # Get selected components
    selection = cmds.ls(selection=True, flatten=True)
    vertices = []
    
    for item in selection:
        if f"{mesh}.vtx" in item:
            idx = int(item.split('[')[1].split(']')[0])
            vertices.append(idx)
    
    return vertices


# ============================================================
# Geometry Islands (Connected Components)
# ============================================================

class GeometryIslands:
    """
    Traces the graph of edges and vertices to find connected islands.
    
    Attributes:
        verts: List of vertex indices
        islands: List of connected vertex islands
    """
    
    def __init__(self, mesh: str, vertex_indices: List[int] = None):
        """
        Initialize with mesh and optional vertex subset.
        
        Args:
            mesh: Mesh object name
            vertex_indices: Optional list of vertex indices to analyze
        """
        self.mesh = mesh
        self.verts = vertex_indices or []
        self.islands = []
        
        if self.verts:
            self.islands = self._make_islands()
    
    def _make_vert_paths(self) -> Dict[int, Set[int]]:
        """
        Create vertex paths for connected components.
        
        Returns:
            Dictionary mapping vertex to connected vertices
        """
        paths = {v: set() for v in self.verts}
        
        # Get mesh data
        sel = om2.MSelectionList()
        sel.add(self.mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = MFnMesh(dag_path)
        
        # Get vertex indices
        vert_indices = set(self.verts)
        
        # Get edge connections
        for edge_id in range(fn_mesh.numEdges):
            verts = fn_mesh.getEdgeVertices(edge_id)
            v1, v2 = verts[0], verts[1]
            
            if v1 in vert_indices and v2 in vert_indices:
                paths[v1].add(v2)
                paths[v2].add(v1)
        
        return paths
    
    def _make_island(self, starting_vert: int, paths: Dict[int, Set[int]]) -> List[int]:
        """
        Create a single island from a starting vertex.
        
        Args:
            starting_vert: Starting vertex index
            paths: Vertex path dictionary
            
        Returns:
            List of vertex indices in the island
        """
        island = [starting_vert]
        current = [starting_vert]
        
        # Remove starting vertex from paths
        if starting_vert in paths:
            paths.pop(starting_vert)
        
        while current:
            # Get connected vertices
            eligible = [v for v in current if v in paths]
            if not eligible:
                break
            
            next_verts = []
            for v in eligible:
                connected = paths.get(v, set())
                for conn in connected:
                    if conn not in island and conn in paths:
                        island.append(conn)
                        next_verts.append(conn)
                
                # Remove processed vertex
                if v in paths:
                    paths.pop(v)
            
            current = next_verts
        
        return island
    
    def _make_islands(self) -> List[List[int]]:
        """
        Create all islands.
        
        Returns:
            List of islands (each island is a list of vertex indices)
        """
        if not self.verts:
            return []
        
        paths = self._make_vert_paths()
        result = []
        
        while paths:
            # Get first vertex
            start = next(iter(paths.keys()))
            island = self._make_island(start, paths)
            if island:
                result.append(island)
        
        return result
    
    def get_islands(self) -> List[List[int]]:
        """
        Get all islands.
        
        Returns:
            List of islands
        """
        return self.islands
    
    def get_island_count(self) -> int:
        """
        Get the number of islands.
        
        Returns:
            Number of islands
        """
        return len(self.islands)
    
    def get_island_by_vertex_index(self, vertex_index: int) -> Optional[List[int]]:
        """
        Get the island containing a specific vertex.
        
        Args:
            vertex_index: Vertex index
            
        Returns:
            Island (list of vertex indices) or None
        """
        for island in self.islands:
            if vertex_index in island:
                return island
        return None
    
    def get_selected_islands(self) -> List[List[int]]:
        """
        Get islands that contain selected vertices.
        
        Returns:
            List of selected islands
        """
        selected = get_selected_vertices(self.mesh)
        selected_set = set(selected)
        
        result = []
        for island in self.islands:
            if any(v in selected_set for v in island):
                result.append(island)
        
        return result
    
    def select_linked(self) -> bool:
        """
        Select all linked vertices for surfaces that have a partial selection.
        
        Returns:
            True if successful
        """
        selected_islands = self.get_selected_islands()
        
        if not selected_islands:
            return False
        
        all_vertices = []
        for island in selected_islands:
            all_vertices.extend(island)
        
        return select_vertices(self.mesh, all_vertices, deselect_others=True)


class SelectionIslands(GeometryIslands):
    """
    Traces the graph of edges and vertices to find selected and non-selected islands.
    
    Attributes:
        verts: List of vertex indices
        selection_islands: Islands of adjacent selected vertices
        non_selected_islands: Islands of adjacent non-selected vertices
    """
    
    def __init__(self, mesh: str, selection_state: bool = True):
        """
        Initialize with mesh and selection state.
        
        Args:
            mesh: Mesh object name
            selection_state: True for selected islands, False for non-selected
        """
        self.mesh = mesh
        self.selection_state = selection_state
        
        # Get all vertices
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        all_verts = list(range(vertex_count))
        
        # Filter by selection state
        selected = get_selected_vertices(mesh)
        
        if selection_state:
            self.verts = selected
        else:
            self.verts = [v for v in all_verts if v not in selected]
        
        self.islands = self._make_islands()
    
    def _make_vert_paths(self) -> Dict[int, Set[int]]:
        """
        Create vertex paths for connected components.
        
        Returns:
            Dictionary mapping vertex to connected vertices
        """
        paths = {v: set() for v in self.verts}
        
        # Get mesh data
        sel = om2.MSelectionList()
        sel.add(self.mesh)
        dag_path = sel.getDagPath(0)
        fn_mesh = MFnMesh(dag_path)
        
        # Get vertex indices
        vert_indices = set(self.verts)
        selected = set(get_selected_vertices(self.mesh))
        
        # Get edge connections
        for edge_id in range(fn_mesh.numEdges):
            verts = fn_mesh.getEdgeVertices(edge_id)
            v1, v2 = verts[0], verts[1]
            
            # Check if both vertices match selection state
            v1_selected = v1 in selected
            v2_selected = v2 in selected
            
            if v1_selected == self.selection_state and v2_selected == self.selection_state:
                if v1 in vert_indices and v2 in vert_indices:
                    paths[v1].add(v2)
                    paths[v2].add(v1)
        
        return paths
    
    def get_selected_islands(self) -> List[List[int]]:
        """
        Get islands of selected vertices.
        
        Returns:
            List of selected islands
        """
        if self.selection_state:
            return self.islands
        return []
    
    def get_non_selected_islands(self) -> List[List[int]]:
        """
        Get islands of non-selected vertices.
        
        Returns:
            List of non-selected islands
        """
        if not self.selection_state:
            return self.islands
        return []


# ============================================================
# Mesh Modification Utilities
# ============================================================

def apply_matrix_to_all_mesh_data(
    mesh: str,
    matrix: List[List[float]]
) -> bool:
    """
    Apply a matrix to all mesh data.
    
    Args:
        mesh: Mesh object name
        matrix: 4x4 transformation matrix
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    # Get all vertices
    vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    
    # Create MMatrix
    m_matrix = MMatrix([
        matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3],
        matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3],
        matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3],
        matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3]
    ])
    
    # Apply matrix to each vertex
    for vtx in vertices:
        pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
        if pos:
            mpoint = MPoint(pos[0], pos[1], pos[2])
            transformed = mpoint * m_matrix
            cmds.xform(vtx, worldSpace=True, translation=[transformed.x, transformed.y, transformed.z])
    
    return True


def get_mesh_data(mesh: str, evaluated: bool = True) -> np.ndarray:
    """
    Get mesh vertex data.
    
    Args:
        mesh: Mesh object name
        evaluated: Whether to use evaluated mesh
        
    Returns:
        Numpy array of vertex positions
    """
    if not cmds.objExists(mesh):
        return np.array([])
    
    if evaluated:
        # Get evaluated mesh
        mesh_shape = cmds.listRelatives(mesh, shapes=True)[0] if cmds.listRelatives(mesh, shapes=True) else mesh
        vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
        positions = []
        
        for vtx in vertices:
            pos = cmds.xform(vtx, query=True, worldSpace=True, translation=True)
            if pos:
                positions.append(pos)
        
        return np.array(positions)
    else:
        # Get base mesh data
        return get_mesh_vertices(mesh, world_space=True)


# ============================================================
# Mesh Information Utilities
# ============================================================

def get_vertex_count(mesh: str) -> int:
    """
    Get the number of vertices in a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Number of vertices
    """
    if not cmds.objExists(mesh):
        return 0
    
    return cmds.polyEvaluate(mesh, vertex=True)


def get_edge_count(mesh: str) -> int:
    """
    Get the number of edges in a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Number of edges
    """
    if not cmds.objExists(mesh):
        return 0
    
    return cmds.polyEvaluate(mesh, edge=True)


def get_face_count(mesh: str) -> int:
    """
    Get the number of faces in a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Number of faces
    """
    if not cmds.objExists(mesh):
        return 0
    
    return cmds.polyEvaluate(mesh, face=True)


def get_bounding_box(mesh: str) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Get the bounding box of a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Tuple of (min_point, max_point)
    """
    if not cmds.objExists(mesh):
        return ((0, 0, 0), (0, 0, 0))
    
    bbox = cmds.xform(mesh, query=True, worldSpace=True, boundingBox=True)
    
    if not bbox:
        return ((0, 0, 0), (0, 0, 0))
    
    min_point = (bbox[0], bbox[1], bbox[2])
    max_point = (bbox[3], bbox[4], bbox[5])
    
    return (min_point, max_point)


# ============================================================
# Mesh Creation Utilities
# ============================================================

def create_mesh_from_vertices(vertices: List[Tuple[float, float, float]], name: str = None) -> str:
    """
    Create a mesh from vertex positions.
    
    Args:
        vertices: List of vertex positions
        name: Mesh name (optional)
        
    Returns:
        Created mesh name
    """
    if not vertices:
        return ""
    
    # Create polygon
    mesh_name = cmds.polyCreateFacet(
        point=vertices,
        name=name or "faceit_mesh"
    )[0]
    
    return mesh_name


def duplicate_mesh(mesh: str, name: str = None, construction_history: bool = True) -> Optional[str]:
    """
    Duplicate a mesh.
    
    Args:
        mesh: Mesh object name
        name: New mesh name (optional)
        construction_history: Whether to keep construction history
        
    Returns:
        Duplicated mesh name or None
    """
    if not cmds.objExists(mesh):
        return None
    
    # Duplicate
    new_mesh = cmds.duplicate(mesh, name=name or f"{mesh}_copy")[0]
    
    # Delete construction history if requested
    if not construction_history:
        cmds.delete(new_mesh, constructionHistory=True)
    
    return new_mesh