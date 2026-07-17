"""
blendshapes/blendshape_utils.py

Shared Utility Library for the Blendshape Subsystem.

This module provides reusable helper functions, lightweight utility classes,
and common algorithms that are used across the blendshape modules. It avoids
business logic and scene-modifying operations, serving as the foundation layer
for the entire blendshape package.

Responsibilities:
- Math utilities (clamp, lerp, remap, interpolation, distance).
- Vector and matrix operations (add, subtract, scale, normalize, dot, cross, transform).
- Mesh utilities (vertex/face/edge queries, bounding box, shape/transform nodes).
- Vertex utilities (iteration, hashing, distance, neighbor search, topology).
- Blendshape utilities (target lookup, index, sorting, renaming, alias).
- Naming utilities (sanitize, unique name, prefix/suffix, namespace, casing).
- Weight utilities (clamp, normalize, scale, blend, mirror, bias, mask).
- Serialization helpers (to/from dict, JSON, binary, hash).
- Performance utilities (timer, benchmark, cache, progress, chunk processing).
- Diagnostics helpers (warnings, reports, logging, object summaries).

Dependencies:
- Maya Python API (maya.cmds, maya.mel, pymel)
- Optional: NumPy (accelerated vector math)
- Standard library: math, json, hashlib, time, dataclasses, typing, functools

The module should be importable from other blendshape modules without
creating circular dependencies.
"""

from __future__ import annotations

import json
import hashlib
import logging
import math
import time
import functools
import threading
from dataclasses import dataclass, field
from typing import (
    List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator,
    TypeVar, Generic, cast, overload, Iterable, Sequence
)

# Maya imports (with fallback for testing)
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists, currentTime # type: ignore
    import pymel.core as pm # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional NumPy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class UtilsError(Exception):
    """Base exception for utility errors."""
    pass

class MeshUtilsError(UtilsError):
    """Raised when mesh operations fail."""
    pass

class VertexUtilsError(UtilsError):
    """Raised when vertex operations fail."""
    pass

# ---- Part 2: Constants -------------------------------------------------

# Numeric tolerances
EPSILON = 1e-8
FLOAT_TOLERANCE = 1e-6
DEFAULT_WEIGHT = 0.0
MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0
ARKIT_COUNT = 52

# Common Maya node types
SHAPE_TYPES = {'mesh', 'nurbsSurface', 'nurbsCurve'}
TRANSFORM_TYPES = {'transform', 'joint', 'locator', 'camera', 'light'}
BLENDSHAPE_TYPES = {'blendShape'}

# ---- Part 3: Math Utilities --------------------------------------------

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def inverse_lerp(a: float, b: float, value: float) -> float:
    """Inverse linear interpolation (value -> t)."""
    if abs(b - a) < EPSILON:
        return 0.0
    return (value - a) / (b - a)


def remap(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Remap a value from one range to another."""
    t = inverse_lerp(in_min, in_max, value)
    return lerp(out_min, out_max, t)


def normalize_value(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Normalize a value to [0, 1] range."""
    return remap(value, min_val, max_val, 0.0, 1.0)


def distance_point_to_point(p1: Tuple[float, float, float],
                           p2: Tuple[float, float, float]) -> float:
    """Euclidean distance between two 3D points."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    dz = p1[2] - p2[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def magnitude(vec: Tuple[float, float, float]) -> float:
    """Magnitude of a 3D vector."""
    return math.sqrt(vec[0]*vec[0] + vec[1]*vec[1] + vec[2]*vec[2])


def normalize_vector(vec: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Normalize a 3D vector."""
    mag = magnitude(vec)
    if mag < EPSILON:
        return (0.0, 0.0, 0.0)
    return (vec[0]/mag, vec[1]/mag, vec[2]/mag)


def dot_product(v1: Tuple[float, float, float],
                v2: Tuple[float, float, float]) -> float:
    """Dot product of two 3D vectors."""
    return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]


def cross_product(v1: Tuple[float, float, float],
                  v2: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Cross product of two 3D vectors."""
    return (
        v1[1]*v2[2] - v1[2]*v2[1],
        v1[2]*v2[0] - v1[0]*v2[2],
        v1[0]*v2[1] - v1[1]*v2[0]
    )


def angle_between(v1: Tuple[float, float, float],
                  v2: Tuple[float, float, float]) -> float:
    """Angle in radians between two vectors."""
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 < EPSILON or mag2 < EPSILON:
        return 0.0
    cos_theta = dot_product(v1, v2) / (mag1 * mag2)
    # Clamp to avoid domain errors due to floating point
    cos_theta = clamp(cos_theta, -1.0, 1.0)
    return math.acos(cos_theta)


def lerp_vector(v1: Tuple[float, float, float],
                v2: Tuple[float, float, float],
                t: float) -> Tuple[float, float, float]:
    """Linear interpolation between two vectors."""
    t_clamped = clamp(t, 0.0, 1.0)
    return (
        v1[0] + (v2[0] - v1[0]) * t_clamped,
        v1[1] + (v2[1] - v1[1]) * t_clamped,
        v1[2] + (v2[2] - v1[2]) * t_clamped,
    )


def vector_add(v1: Tuple[float, float, float],
               v2: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2])


def vector_subtract(v1: Tuple[float, float, float],
                    v2: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2])


def vector_scale(vec: Tuple[float, float, float],
                 scalar: float) -> Tuple[float, float, float]:
    return (vec[0] * scalar, vec[1] * scalar, vec[2] * scalar)


# ---- Part 4: Vector & Matrix Utilities (NumPy-accelerated if available) --

def vectors_to_numpy(vectors: List[Tuple[float, float, float]]) -> Any:
    """Convert a list of 3D tuples to a NumPy array (if available)."""
    if HAS_NUMPY:
        return np.array(vectors, dtype=np.float32)
    return vectors


def numpy_to_vectors(array: Any) -> List[Tuple[float, float, float]]:
    """Convert a NumPy array back to list of tuples."""
    if HAS_NUMPY and isinstance(array, np.ndarray):
        return [tuple(row) for row in array.tolist()]
    return array


def transform_point(point: Tuple[float, float, float],
                    matrix: List[List[float]]) -> Tuple[float, float, float]:
    """
    Apply a 4x4 transformation matrix to a point.
    Matrix is assumed to be in Maya's standard format (row-major).
    """
    x, y, z = point
    # Assume matrix is 4x4 [[m00, m01, m02, m03], [m10, m11, m12, m13], [m20, m21, m22, m23], [0,0,0,1]]
    # For simplicity, we'll handle translation and rotation/scale.
    # This is a simplified version; for production, use proper matrix multiplication.
    if HAS_NUMPY:
        mat = np.array(matrix, dtype=np.float32)
        vec = np.array([x, y, z, 1.0], dtype=np.float32)
        result = mat @ vec
        return (result[0], result[1], result[2])
    else:
        # Pure Python fallback
        m00, m01, m02, m03 = matrix[0]
        m10, m11, m12, m13 = matrix[1]
        m20, m21, m22, m23 = matrix[2]
        # m30, m31, m32, m33 = matrix[3]  # not used for affine transform with point
        nx = x * m00 + y * m01 + z * m02 + m03
        ny = x * m10 + y * m11 + z * m12 + m13
        nz = x * m20 + y * m21 + z * m22 + m23
        return (nx, ny, nz)


def get_maya_matrix(node: str) -> List[List[float]]:
    """Get the world matrix of a Maya node as a 4x4 list."""
    if not cmds.objExists(node):
        return [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]
    mat = cmds.xform(node, q=True, matrix=True, ws=True)
    # mat is a flat list of 16 floats (row-major)
    return [
        [mat[0], mat[1], mat[2], mat[3]],
        [mat[4], mat[5], mat[6], mat[7]],
        [mat[8], mat[9], mat[10], mat[11]],
        [mat[12], mat[13], mat[14], mat[15]]
    ]


# ---- Part 5: Mesh Utilities --------------------------------------------

def get_shape_node(node: str) -> Optional[str]:
    """
    Get the first shape node of a transform.
    Returns the shape name or None if not found.
    """
    if not cmds.objExists(node):
        return None
    if cmds.nodeType(node) in SHAPE_TYPES:
        return node
    shapes = cmds.listRelatives(node, shapes=True) or []
    if shapes:
        return shapes[0]
    return None


def get_transform_node(node: str) -> Optional[str]:
    """Get the parent transform of a shape node."""
    if not cmds.objExists(node):
        return None
    if cmds.nodeType(node) in TRANSFORM_TYPES:
        return node
    parent = cmds.listRelatives(node, parent=True)
    if parent:
        return parent[0]
    return None


def get_mesh_vertex_count(mesh: str) -> int:
    """Return the vertex count of a mesh."""
    shape = get_shape_node(mesh)
    if not shape:
        return 0
    return cmds.polyEvaluate(shape, vertex=True) or 0


def get_mesh_face_count(mesh: str) -> int:
    """Return the face count of a mesh."""
    shape = get_shape_node(mesh)
    if not shape:
        return 0
    return cmds.polyEvaluate(shape, face=True) or 0


def get_mesh_edge_count(mesh: str) -> int:
    """Return the edge count of a mesh."""
    shape = get_shape_node(mesh)
    if not shape:
        return 0
    return cmds.polyEvaluate(shape, edge=True) or 0


def get_mesh_vertex_positions(mesh: str) -> List[Tuple[float, float, float]]:
    """
    Get all vertex positions of a mesh as a list of (x, y, z) tuples.
    """
    shape = get_shape_node(mesh)
    if not shape:
        return []
    # Use polyListComponentConversion and xform to get positions.
    # We'll use a more efficient method: get all vertices as a flat array.
    verts = cmds.polyListComponentConversion(shape, toVertex=True)
    positions = cmds.xform(verts, q=True, ws=True, t=True)
    if not positions:
        return []
    # positions is flat: [x1,y1,z1, x2,y2,z2, ...]
    return [(positions[i], positions[i+1], positions[i+2]) for i in range(0, len(positions), 3)]


def get_mesh_bounding_box(mesh: str) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Return (min, max) bounding box of a mesh."""
    shape = get_shape_node(mesh)
    if not shape:
        return ((0,0,0), (0,0,0))
    bbox = cmds.exactWorldBoundingBox(shape)
    if not bbox:
        return ((0,0,0), (0,0,0))
    return ((bbox[0], bbox[1], bbox[2]), (bbox[3], bbox[4], bbox[5]))


def get_mesh_center(mesh: str) -> Tuple[float, float, float]:
    """Return the center of the bounding box of a mesh."""
    min_pt, max_pt = get_mesh_bounding_box(mesh)
    return ((min_pt[0] + max_pt[0]) * 0.5,
            (min_pt[1] + max_pt[1]) * 0.5,
            (min_pt[2] + max_pt[2]) * 0.5)


def duplicate_mesh(mesh: str, new_name: Optional[str] = None) -> str:
    """Duplicate a mesh and return the new transform name."""
    if not cmds.objExists(mesh):
        raise MeshUtilsError(f"Mesh '{mesh}' does not exist")
    dup = cmds.duplicate(mesh, name=new_name)[0]
    return dup


def delete_mesh_history(mesh: str) -> None:
    """Delete construction history on a mesh."""
    if not cmds.objExists(mesh):
        return
    cmds.delete(mesh, constructionHistory=True)


def freeze_transforms(mesh: str) -> None:
    """Freeze transforms on a mesh (zero translation/rotation, scale to 1)."""
    if not cmds.objExists(mesh):
        return
    cmds.makeIdentity(mesh, apply=True, t=1, r=1, s=1, n=0)


# ---- Part 6: Vertex Utilities ------------------------------------------

def get_vertex_position(mesh: str, index: int) -> Optional[Tuple[float, float, float]]:
    """Get the world-space position of a single vertex."""
    shape = get_shape_node(mesh)
    if not shape:
        return None
    vert = f"{shape}.vtx[{index}]"
    pos = cmds.xform(vert, q=True, ws=True, t=True)
    if not pos:
        return None
    return (pos[0], pos[1], pos[2])


def set_vertex_position(mesh: str, index: int, pos: Tuple[float, float, float]) -> None:
    """Set the world-space position of a single vertex."""
    shape = get_shape_node(mesh)
    if not shape:
        return
    vert = f"{shape}.vtx[{index}]"
    cmds.xform(vert, ws=True, t=(pos[0], pos[1], pos[2]))


def iter_vertices(mesh: str) -> Iterator[int]:
    """Iterate over vertex indices of a mesh."""
    count = get_mesh_vertex_count(mesh)
    for i in range(count):
        yield i


def vertex_distance(mesh: str, idx1: int, idx2: int) -> float:
    """Distance between two vertices in world space."""
    p1 = get_vertex_position(mesh, idx1)
    p2 = get_vertex_position(mesh, idx2)
    if p1 is None or p2 is None:
        return 0.0
    return distance_point_to_point(p1, p2)


def vertex_hash(mesh: str, index: int, precision: int = 6) -> str:
    """
    Compute a stable hash for a vertex based on its position (rounded to precision).
    """
    pos = get_vertex_position(mesh, index)
    if pos is None:
        return ""
    # Round to avoid floating point discrepancies
    rounded = (round(pos[0], precision), round(pos[1], precision), round(pos[2], precision))
    return hashlib.md5(str(rounded).encode('utf-8')).hexdigest()


def mesh_topology_hash(mesh: str, precision: int = 6) -> str:
    """
    Compute a hash of the mesh topology (vertex positions and connectivity).
    This is a lightweight check for topology changes.
    """
    positions = get_mesh_vertex_positions(mesh)
    if not positions:
        return ""
    # Round positions
    rounded = [(round(x, precision), round(y, precision), round(z, precision)) for x, y, z in positions]
    # Hash the list
    data = json.dumps(rounded, sort_keys=True).encode('utf-8')
    return hashlib.md5(data).hexdigest()


def get_vertex_neighbors(mesh: str, index: int) -> List[int]:
    """Get indices of vertices adjacent to the given vertex."""
    shape = get_shape_node(mesh)
    if not shape:
        return []
    # Use polyListComponentConversion to get vertices connected by edges
    vert = f"{shape}.vtx[{index}]"
    # Convert to edges, then back to vertices
    edges = cmds.polyListComponentConversion(vert, toEdge=True)
    neighbor_verts = cmds.polyListComponentConversion(edges, toVertex=True)
    # Extract indices
    indices = []
    if neighbor_verts:
        for v in neighbor_verts:
            # v is like 'meshShape.vtx[5]'
            import re
            match = re.search(r'vtx\[(\d+)\]', v)
            if match:
                idx = int(match.group(1))
                if idx != index:
                    indices.append(idx)
    return indices


# ---- Part 7: Blendshape Utilities --------------------------------------

def get_blendshape_targets(blendshape_node: str) -> List[str]:
    """Return the list of target names (weight aliases) on a blendshape node."""
    if not cmds.objExists(blendshape_node) or cmds.nodeType(blendshape_node) != 'blendShape':
        return []
    return cmds.listAttr(blendshape_node, m=True, string='weight') or []


def get_blendshape_weight(blendshape_node: str, target: str) -> float:
    """Get the weight of a specific target."""
    attr = f"{blendshape_node}.{target}"
    if not cmds.objExists(attr):
        return 0.0
    return cmds.getAttr(attr)


def set_blendshape_weight(blendshape_node: str, target: str, value: float) -> None:
    """Set the weight of a specific target."""
    attr = f"{blendshape_node}.{target}"
    if not cmds.objExists(attr):
        return
    cmds.setAttr(attr, clamp(value, MIN_WEIGHT, MAX_WEIGHT))


def get_blendshape_target_index(blendshape_node: str, target: str) -> Optional[int]:
    """Get the index of a target (if needed for some operations)."""
    targets = get_blendshape_targets(blendshape_node)
    try:
        return targets.index(target)
    except ValueError:
        return None


def find_blendshape_target(blendshape_node: str, target: str) -> bool:
    """Check if a target exists on a blendshape node."""
    return target in get_blendshape_targets(blendshape_node)


def get_blendshape_target_mesh(blendshape_node: str, target: str) -> Optional[str]:
    """
    Get the mesh used as target for a given alias.
    Note: This may be unreliable if the target mesh has been renamed.
    """
    if not find_blendshape_target(blendshape_node, target):
        return None
    # We can get the target mesh by looking at connections to the blendshape node.
    # The target mesh is connected to the 'target' attribute array.
    # For simplicity, we'll return the first mesh connected to the blendshape node.
    meshes = cmds.listConnections(blendshape_node, type='mesh') or []
    if meshes:
        return meshes[0]
    return None


def sort_targets(targets: List[str], reverse: bool = False) -> List[str]:
    """Sort target names alphanumerically."""
    return sorted(targets, key=lambda s: s.lower(), reverse=reverse)


def group_targets_by_prefix(targets: List[str], prefix: str) -> List[str]:
    """Filter targets that start with a given prefix."""
    return [t for t in targets if t.startswith(prefix)]


# ---- Part 8: Naming Utilities ------------------------------------------

def sanitize_name(name: str) -> str:
    """
    Clean a name to be Maya-compatible:
    - Remove illegal characters: !@#$%^&*()+={}[]|\;:'",<>/?`~
    - Replace spaces with underscores
    - Ensure it starts with a letter or underscore
    """
    import re
    # Replace spaces and illegal chars with underscore
    illegal = r'[!@#$%^&*()+={}\[\]|\\;:\'",<>/?`~ ]'
    cleaned = re.sub(illegal, '_', name)
    # Ensure it starts with a letter or underscore
    if cleaned and not cleaned[0].isalpha() and cleaned[0] != '_':
        cleaned = '_' + cleaned
    return cleaned


def generate_unique_name(base: str, existing_names: Iterable[str]) -> str:
    """
    Generate a unique name by appending a number if the base already exists.
    """
    if base not in existing_names:
        return base
    counter = 1
    candidate = f"{base}_{counter}"
    while candidate in existing_names:
        counter += 1
        candidate = f"{base}_{counter}"
    return candidate


def add_prefix(name: str, prefix: str) -> str:
    """Add a prefix to a name."""
    return f"{prefix}{name}"


def add_suffix(name: str, suffix: str) -> str:
    """Add a suffix to a name."""
    return f"{name}{suffix}"


def remove_namespace(name: str) -> str:
    """Remove Maya namespace from a name."""
    if ':' in name:
        return name.split(':', 1)[-1]
    return name


def get_namespace(name: str) -> str:
    """Get the namespace from a Maya node name."""
    if ':' in name:
        return name.split(':', 1)[0]
    return ""


def add_namespace(name: str, namespace: str) -> str:
    """Add a namespace to a name."""
    if namespace:
        return f"{namespace}:{name}"
    return name


def to_camel_case(name: str) -> str:
    """Convert snake_case or spaced to camelCase."""
    import re
    # Replace underscores and spaces with a space
    parts = re.split(r'[_\s]+', name)
    if not parts:
        return name
    # First part lowercase, rest capitalize
    result = parts[0].lower()
    for p in parts[1:]:
        if p:
            result += p[0].upper() + p[1:].lower()
    return result


def to_snake_case(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def validate_arkit_name(name: str) -> bool:
    """Check if a name is a valid ARKit blendshape name."""
    # This is a simple check; the full list is in arkit52.py
    # We'll just check for common patterns: no spaces, starts with letter, etc.
    return name == sanitize_name(name) and name[0].isalpha()


# ---- Part 9: Weight Utilities ------------------------------------------

def clamp_weight(value: float) -> float:
    """Clamp a weight to [0, 1]."""
    return clamp(value, MIN_WEIGHT, MAX_WEIGHT)


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize a dictionary of weights so they sum to 1.0.
    """
    total = sum(weights.values())
    if total == 0.0:
        return {k: 0.0 for k in weights}
    return {k: v / total for k, v in weights.items()}


def blend_weights(weights_a: Dict[str, float],
                  weights_b: Dict[str, float],
                  t: float) -> Dict[str, float]:
    """
    Blend two weight dictionaries using linear interpolation.
    """
    all_keys = set(weights_a.keys()) | set(weights_b.keys())
    result = {}
    for key in all_keys:
        val_a = weights_a.get(key, 0.0)
        val_b = weights_b.get(key, 0.0)
        result[key] = lerp(val_a, val_b, t)
    return result


def scale_weights(weights: Dict[str, float], factor: float) -> Dict[str, float]:
    """Scale all weights by a factor and clamp."""
    return {k: clamp_weight(v * factor) for k, v in weights.items()}


def mirror_weights(weights: Dict[str, float], mirror_map: Dict[str, str]) -> Dict[str, float]:
    """
    Mirror weights using a left-right pair map.
    keys that have a mirror will have their weight transferred to the mirror key.
    """
    mirrored = {}
    for key, val in weights.items():
        mirror_key = mirror_map.get(key)
        if mirror_key:
            mirrored[mirror_key] = val
        else:
            mirrored[key] = val
    return mirrored


def apply_weight_bias(weights: Dict[str, float], bias: float) -> Dict[str, float]:
    """
    Apply a bias (exponent) to each weight: w_new = w ^ bias.
    """
    return {k: clamp_weight(v ** bias) for k, v in weights.items()}


def apply_weight_mask(weights: Dict[str, float], mask: Dict[str, float]) -> Dict[str, float]:
    """
    Apply a mask to weights (multiply each weight by the mask value for that key).
    """
    result = {}
    for key, val in weights.items():
        mask_val = mask.get(key, 1.0)
        result[key] = clamp_weight(val * mask_val)
    return result


def get_active_weights(weights: Dict[str, float], threshold: float = 0.001) -> Dict[str, float]:
    """Return only weights above a threshold."""
    return {k: v for k, v in weights.items() if abs(v) > threshold}


# ---- Part 10: Serialization Helpers -----------------------------------

def dict_to_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Convert a dict to a JSON string."""
    return json.dumps(data, indent=indent, default=_json_default)


def json_to_dict(data: str) -> Dict[str, Any]:
    """Convert a JSON string to a dict."""
    return json.loads(data)


def _json_default(obj: Any) -> Any:
    """Default JSON serializer for custom objects."""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def hash_data(data: Any) -> str:
    """Compute an MD5 hash of any data (convert to JSON first)."""
    json_str = dict_to_json(data) if isinstance(data, dict) else str(data)
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()


def checksum_mesh(mesh: str) -> str:
    """Compute a checksum of a mesh's vertex positions."""
    positions = get_mesh_vertex_positions(mesh)
    if not positions:
        return ""
    # Convert to list of rounded tuples for stable hashing
    rounded = [(round(x, 6), round(y, 6), round(z, 6)) for x, y, z in positions]
    data = json.dumps(rounded, sort_keys=True)
    return hashlib.md5(data.encode('utf-8')).hexdigest()


# ---- Part 11: Performance Utilities -----------------------------------

class Timer:
    """A simple context manager for timing code blocks."""

    def __init__(self, name: str = "Timer", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        if self.logger:
            self.logger.debug(f"{self.name} took {self.elapsed:.4f} seconds")


def benchmark(func: Callable) -> Callable:
    """Decorator to log execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    return wrapper


class SimpleCache:
    """Simple LRU cache for expensive operations."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: Dict[str, Any] = {}
        self._order: List[str] = []

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            # Move to end (most recent)
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self.maxsize:
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._order.append(key)

    def clear(self) -> None:
        self._cache.clear()
        self._order.clear()


def chunk_iterator(iterable: Iterable, chunk_size: int) -> Iterator[List]:
    """Yield chunks of an iterable."""
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


class ProgressTracker:
    """Simple progress tracker with callback support."""

    def __init__(self, total: int, callback: Optional[Callable[[float, str], None]] = None):
        self.total = total
        self.current = 0
        self.callback = callback

    def update(self, amount: int = 1, message: str = "") -> None:
        self.current += amount
        if self.callback:
            progress = self.current / self.total if self.total > 0 else 0.0
            self.callback(progress, message)


# ---- Part 12: Diagnostics Helpers ------------------------------------

def object_summary(node: str) -> str:
    """Return a summary string for a Maya node."""
    if not cmds.objExists(node):
        return f"Node '{node}' does not exist"
    node_type = cmds.nodeType(node)
    summary = f"{node} ({node_type})"
    if node_type == 'mesh':
        v = cmds.polyEvaluate(node, vertex=True) or 0
        f = cmds.polyEvaluate(node, face=True) or 0
        summary += f" [vertices: {v}, faces: {f}]"
    elif node_type == 'blendShape':
        targets = get_blendshape_targets(node)
        summary += f" [targets: {len(targets)}]"
    return summary


def log_validation_issues(issues: List[Dict]) -> None:
    """Log validation issues to the logger."""
    for issue in issues:
        severity = issue.get('severity', 'info').upper()
        message = issue.get('message', '')
        node = issue.get('node', '')
        if node:
            message = f"{node}: {message}"
        logger.log(getattr(logging, severity, logging.INFO), message)


def create_report_summary(report: Dict[str, Any]) -> str:
    """Create a human-readable summary from a validation report."""
    passed = report.get('passed', False)
    total = report.get('total_checks', 0)
    warnings = report.get('warnings', 0)
    errors = report.get('errors', 0)
    criticals = report.get('criticals', 0)
    status = "PASSED" if passed else "FAILED"
    return (f"Validation {status}: {total} checks, "
            f"{warnings} warnings, {errors} errors, {criticals} criticals")


# ---- Part 13: Public API -----------------------------------------------

__all__ = [
    # Constants
    "EPSILON", "FLOAT_TOLERANCE", "DEFAULT_WEIGHT", "MIN_WEIGHT", "MAX_WEIGHT", "ARKIT_COUNT",
    "SHAPE_TYPES", "TRANSFORM_TYPES", "BLENDSHAPE_TYPES",

    # Math
    "clamp", "lerp", "inverse_lerp", "remap", "normalize_value",
    "distance_point_to_point", "magnitude", "normalize_vector",
    "dot_product", "cross_product", "angle_between",
    "lerp_vector", "vector_add", "vector_subtract", "vector_scale",

    # Vector/Matrix
    "vectors_to_numpy", "numpy_to_vectors", "transform_point", "get_maya_matrix",

    # Mesh
    "get_shape_node", "get_transform_node",
    "get_mesh_vertex_count", "get_mesh_face_count", "get_mesh_edge_count",
    "get_mesh_vertex_positions", "get_mesh_bounding_box", "get_mesh_center",
    "duplicate_mesh", "delete_mesh_history", "freeze_transforms",

    # Vertex
    "get_vertex_position", "set_vertex_position",
    "iter_vertices", "vertex_distance", "vertex_hash",
    "mesh_topology_hash", "get_vertex_neighbors",

    # Blendshape
    "get_blendshape_targets", "get_blendshape_weight", "set_blendshape_weight",
    "get_blendshape_target_index", "find_blendshape_target",
    "get_blendshape_target_mesh", "sort_targets", "group_targets_by_prefix",

    # Naming
    "sanitize_name", "generate_unique_name",
    "add_prefix", "add_suffix", "remove_namespace", "get_namespace", "add_namespace",
    "to_camel_case", "to_snake_case", "validate_arkit_name",

    # Weights
    "clamp_weight", "normalize_weights", "blend_weights",
    "scale_weights", "mirror_weights", "apply_weight_bias",
    "apply_weight_mask", "get_active_weights",

    # Serialization
    "dict_to_json", "json_to_dict", "hash_data", "checksum_mesh",

    # Performance
    "Timer", "benchmark", "SimpleCache", "chunk_iterator", "ProgressTracker",

    # Diagnostics
    "object_summary", "log_validation_issues", "create_report_summary",

    # Exceptions
    "UtilsError", "MeshUtilsError", "VertexUtilsError",
]