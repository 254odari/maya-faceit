# weight_utils.py
# Maya Faceit Plugin - Weight Utilities
# Converted from Blender to Maya Python 3.11

"""
Weight utilities for Faceit Maya plugin.
Handles weight painting, weight transfer, and weight operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple, Any
import numpy as np


# ============================================================
# Helper Functions
# ============================================================

def get_skin_cluster(mesh: str) -> Optional[str]:
    """
    Get the skin cluster on a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        Skin cluster name or None
    """
    if not cmds.objExists(mesh):
        return None
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    
    for node in history:
        if cmds.nodeType(node) == 'skinCluster':
            return node
    
    return None


def get_skin_influences(skin_cluster: str) -> List[str]:
    """
    Get all influences of a skin cluster.
    
    Args:
        skin_cluster: Skin cluster name
        
    Returns:
        List of influence names
    """
    if not cmds.objExists(skin_cluster):
        return []
    
    return cmds.skinCluster(skin_cluster, query=True, influence=True) or []


def set_skin_weight(
    mesh: str,
    joint: str,
    vertex_index: int,
    weight: float
) -> bool:
    """
    Set skin weight for a vertex.
    
    Args:
        mesh: Mesh object name
        joint: Joint name
        vertex_index: Vertex index
        weight: Weight value
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    if not cmds.objExists(joint):
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        return False
    
    cmds.skinCluster(
        skin_cluster,
        edit=True,
        weight=f"{joint}.vtx[{vertex_index}]",
        value=weight
    )
    
    return True


def normalize_skin_weights(mesh: str, vertices: List[int] = None) -> bool:
    """
    Normalize skin weights for vertices.
    
    Args:
        mesh: Mesh object name
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        return False
    
    influences = get_skin_influences(skin_cluster)
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = list(range(vertex_count))
    
    for vtx in vertices:
        total_weight = 0.0
        weights = {}
        
        for influence in influences:
            weight = cmds.skinCluster(
                skin_cluster,
                query=True,
                weight=f"{influence}.vtx[{vtx}]"
            )
            
            if weight:
                w = weight[0]
                weights[influence] = w
                total_weight += w
        
        if total_weight > 0:
            for influence, w in weights.items():
                normalized = w / total_weight
                cmds.skinCluster(
                    skin_cluster,
                    edit=True,
                    weight=f"{influence}.vtx[{vtx}]",
                    value=normalized
                )
    
    return True


def prune_skin_weights(mesh: str, threshold: float = 0.001) -> bool:
    """
    Prune skin weights below a threshold.
    
    Args:
        mesh: Mesh object name
        threshold: Weight threshold
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        return False
    
    cmds.skinCluster(skin_cluster, edit=True, pruneWeights=threshold)
    return True


# ============================================================
# Weight Painting Utilities
# ============================================================

def paint_weight(
    mesh: str,
    joint: str,
    vertices: List[int],
    value: float
) -> bool:
    """
    Paint weight on vertices.
    
    Args:
        mesh: Mesh object name
        joint: Joint name
        vertices: List of vertex indices
        value: Weight value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    if not cmds.objExists(joint):
        cmds.warning(f"Joint '{joint}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    for vtx in vertices:
        cmds.skinCluster(
            skin_cluster,
            edit=True,
            weight=f"{joint}.vtx[{vtx}]",
            value=value
        )
    
    return True


def get_weight_at_vertex(
    mesh: str,
    joint: str,
    vertex_index: int
) -> float:
    """
    Get weight at a vertex.
    
    Args:
        mesh: Mesh object name
        joint: Joint name
        vertex_index: Vertex index
        
    Returns:
        Weight value
    """
    if not cmds.objExists(mesh):
        return 0.0
    
    if not cmds.objExists(joint):
        return 0.0
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        return 0.0
    
    weight = cmds.skinCluster(
        skin_cluster,
        query=True,
        weight=f"{joint}.vtx[{vertex_index}]"
    )
    
    return weight[0] if weight else 0.0


def get_all_weights_at_vertex(
    mesh: str,
    vertex_index: int
) -> Dict[str, float]:
    """
    Get all weights at a vertex.
    
    Args:
        mesh: Mesh object name
        vertex_index: Vertex index
        
    Returns:
        Dictionary mapping joint names to weights
    """
    if not cmds.objExists(mesh):
        return {}
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        return {}
    
    influences = get_skin_influences(skin_cluster)
    weights = {}
    
    for influence in influences:
        weight = cmds.skinCluster(
            skin_cluster,
            query=True,
            weight=f"{influence}.vtx[{vertex_index}]"
        )
        
        if weight:
            weights[influence] = weight[0]
    
    return weights


# ============================================================
# Weight Transfer Utilities
# ============================================================

def transfer_weights_between_joints(
    mesh: str,
    source_joint: str,
    target_joint: str,
    vertices: List[int] = None
) -> bool:
    """
    Transfer weights from one joint to another.
    
    Args:
        mesh: Mesh object name
        source_joint: Source joint name
        target_joint: Target joint name
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    if not cmds.objExists(source_joint):
        cmds.warning(f"Source joint '{source_joint}' does not exist")
        return False
    
    if not cmds.objExists(target_joint):
        cmds.warning(f"Target joint '{target_joint}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = list(range(vertex_count))
    
    # Get current weight on source joint
    for vtx in vertices:
        weight = get_weight_at_vertex(mesh, source_joint, vtx)
        
        if weight > 0:
            # Set weight on target joint
            set_skin_weight(mesh, target_joint, vtx, weight)
            # Remove weight from source joint
            set_skin_weight(mesh, source_joint, vtx, 0)
    
    # Normalize weights
    normalize_skin_weights(mesh)
    
    return True


def mirror_weights(
    mesh: str,
    axis: str = 'X',
    tolerance: float = 0.001
) -> bool:
    """
    Mirror weights across an axis.
    
    Args:
        mesh: Mesh object name
        axis: Mirror axis ('X', 'Y', or 'Z')
        tolerance: Weight tolerance
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    cmds.skinCluster(skin_cluster, edit=True, mirror=True, axis=axis)
    prune_skin_weights(mesh, tolerance)
    
    return True


# ============================================================
# Weight Smoothing Utilities
# ============================================================

def get_vertex_neighbors(mesh: str, vertex_index: int) -> List[int]:
    """
    Get neighboring vertices of a vertex.
    
    Args:
        mesh: Mesh object name
        vertex_index: Vertex index
        
    Returns:
        List of neighboring vertex indices
    """
    if not cmds.objExists(mesh):
        return []
    
    # Get connected vertices
    connected = cmds.polyListComponentConversion(
        f"{mesh}.vtx[{vertex_index}]",
        toVertex=True,
        internal=True
    )
    
    if connected:
        indices = []
        for item in connected:
            idx = int(item.split('[')[1].split(']')[0])
            if idx != vertex_index:
                indices.append(idx)
        return indices
    
    return []


def smooth_weights(
    mesh: str,
    iterations: int = 1,
    vertices: List[int] = None
) -> bool:
    """
    Smooth weights on vertices.
    
    Args:
        mesh: Mesh object name
        iterations: Number of smoothing iterations
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = list(range(vertex_count))
    
    # Get all influences
    influences = get_skin_influences(skin_cluster)
    
    for vtx in vertices:
        # Get current weights
        weights = get_all_weights_at_vertex(mesh, vtx)
        
        if not weights:
            continue
        
        # Get neighboring vertices
        neighbors = get_vertex_neighbors(mesh, vtx)
        
        if not neighbors:
            continue
        
        # Smooth weights
        for _ in range(iterations):
            smoothed = {}
            
            for influence, weight in weights.items():
                neighbor_weights = []
                
                for neighbor in neighbors:
                    n_weight = get_weight_at_vertex(mesh, influence, neighbor)
                    neighbor_weights.append(n_weight)
                
                if neighbor_weights:
                    avg_weight = sum(neighbor_weights) / len(neighbor_weights)
                    smoothed[influence] = (weight + avg_weight) / 2
                else:
                    smoothed[influence] = weight
            
            # Apply smoothed weights
            for influence, weight in smoothed.items():
                set_skin_weight(mesh, influence, vtx, weight)
    
    # Normalize weights
    normalize_skin_weights(mesh)
    
    return True


# ============================================================
# Weight Lock Utilities
# ============================================================

def lock_weights(
    mesh: str,
    vertices: List[int],
    joint: str = None
) -> bool:
    """
    Lock weights on vertices.
    
    Args:
        mesh: Mesh object name
        vertices: List of vertex indices
        joint: Joint name (None for all joints)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if joint:
        if not cmds.objExists(joint):
            cmds.warning(f"Joint '{joint}' does not exist")
            return False
        
        for vtx in vertices:
            cmds.skinCluster(
                skin_cluster,
                edit=True,
                lock=f"{joint}.vtx[{vtx}]",
                lockValue=True
            )
    else:
        influences = get_skin_influences(skin_cluster)
        
        for influence in influences:
            for vtx in vertices:
                cmds.skinCluster(
                    skin_cluster,
                    edit=True,
                    lock=f"{influence}.vtx[{vtx}]",
                    lockValue=True
                )
    
    return True


def unlock_weights(
    mesh: str,
    vertices: List[int],
    joint: str = None
) -> bool:
    """
    Unlock weights on vertices.
    
    Args:
        mesh: Mesh object name
        vertices: List of vertex indices
        joint: Joint name (None for all joints)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if joint:
        if not cmds.objExists(joint):
            cmds.warning(f"Joint '{joint}' does not exist")
            return False
        
        for vtx in vertices:
            cmds.skinCluster(
                skin_cluster,
                edit=True,
                lock=f"{joint}.vtx[{vtx}]",
                lockValue=False
            )
    else:
        influences = get_skin_influences(skin_cluster)
        
        for influence in influences:
            for vtx in vertices:
                cmds.skinCluster(
                    skin_cluster,
                    edit=True,
                    lock=f"{influence}.vtx[{vtx}]",
                    lockValue=False
                )
    
    return True


# ============================================================
# Weight Normalization Utilities
# ============================================================

def normalize_weights(
    mesh: str,
    vertices: List[int] = None
) -> bool:
    """
    Normalize weights on vertices.
    
    Args:
        mesh: Mesh object name
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = list(range(vertex_count))
    
    influences = get_skin_influences(skin_cluster)
    
    for vtx in vertices:
        total_weight = 0.0
        weights = {}
        
        for influence in influences:
            weight = get_weight_at_vertex(mesh, influence, vtx)
            weights[influence] = weight
            total_weight += weight
        
        if total_weight > 0:
            for influence, weight in weights.items():
                normalized = weight / total_weight
                set_skin_weight(mesh, influence, vtx, normalized)
    
    return True


def clamp_weights(
    mesh: str,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    vertices: List[int] = None
) -> bool:
    """
    Clamp weights to a range.
    
    Args:
        mesh: Mesh object name
        min_weight: Minimum weight
        max_weight: Maximum weight
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    if vertices is None:
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        vertices = list(range(vertex_count))
    
    influences = get_skin_influences(skin_cluster)
    
    for vtx in vertices:
        for influence in influences:
            weight = get_weight_at_vertex(mesh, influence, vtx)
            clamped = max(min_weight, min(max_weight, weight))
            
            if clamped != weight:
                set_skin_weight(mesh, influence, vtx, clamped)
    
    return True


# ============================================================
# Weight Export/Import Utilities
# ============================================================

def export_weights(
    mesh: str,
    filepath: str
) -> bool:
    """
    Export skin weights to a file.
    
    Args:
        mesh: Mesh object name
        filepath: File path
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    try:
        # Correct syntax for exporting weights
        cmds.deformerWeights(
            export=True,
            path=filepath,
            deformer=skin_cluster
        )
        cmds.confirmDialog(
            title="Export Weights",
            message=f"Weights exported successfully to:\n{filepath}",
            button=["OK"]
        )
        return True
    except Exception as e:
        cmds.warning(f"Error exporting weights: {str(e)}")
        cmds.confirmDialog(
            title="Export Weights Error",
            message=f"Failed to export weights:\n{str(e)}",
            button=["OK"]
        )
        return False


def import_weights(
    mesh: str,
    filepath: str
) -> bool:
    """
    Import skin weights from a file.
    
    Args:
        mesh: Mesh object name
        filepath: File path
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    # Check if file exists
    import os
    if not os.path.exists(filepath):
        cmds.warning(f"Weight file '{filepath}' does not exist")
        return False
    
    skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    try:
        # Correct syntax for importing weights
        cmds.deformerWeights(
            **{'import': True},
            path=filepath,
            deformer=skin_cluster
        )
        cmds.confirmDialog(
            title="Import Weights",
            message=f"Weights imported successfully from:\n{filepath}",
            button=["OK"]
        )
        return True
    except Exception as e:
        cmds.warning(f"Error importing weights: {str(e)}")
        cmds.confirmDialog(
            title="Import Weights Error",
            message=f"Failed to import weights:\n{str(e)}",
            button=["OK"]
        )
        return False