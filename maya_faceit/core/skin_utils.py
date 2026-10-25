# skin_utils.py
# Maya Faceit Plugin - Skin Utilities
# Converted from Blender to Maya Python 3.11

"""
Skin utilities for Faceit Maya plugin.
Handles skin cluster creation, weight management, and binding operations.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple, Any
import numpy as np


# ============================================================
# Skin Cluster Detection
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


# ============================================================
# Skin Cluster Creation
# ============================================================

def create_skin_cluster(
    mesh: str,
    joints: List[str],
    name: str = None,
    max_influences: int = 5,
    skin_method: int = 0,
    normalize_weights: int = 1
) -> Optional[str]:
    """
    Create a skin cluster on a mesh.
    
    Args:
        mesh: Mesh object name
        joints: List of joint names
        name: Skin cluster name (optional)
        max_influences: Maximum number of influences per vertex
        skin_method: Skin method (0=classic linear, 1=dual quaternion)
        normalize_weights: Whether to normalize weights
        
    Returns:
        Skin cluster name or None
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return None
    
    if not joints:
        cmds.warning("No joints provided for skin cluster")
        return None
    
    # Filter joints that exist
    valid_joints = [j for j in joints if cmds.objExists(j)]
    
    if not valid_joints:
        cmds.warning("No valid joints found for skin cluster")
        return None
    
    # Create skin cluster
    try:
        skin_cluster = cmds.skinCluster(
            valid_joints,
            mesh,
            name=name or f"{mesh}_skinCluster",
            maximumInfluences=max_influences,
            skinMethod=skin_method,
            normalizeWeights=normalize_weights
        )[0]
        
        return skin_cluster
    except Exception as e:
        cmds.warning(f"Error creating skin cluster: {str(e)}")
        return None


def add_joints_to_skin_cluster(
    skin_cluster: str,
    joints: List[str]
) -> bool:
    """
    Add joints to a skin cluster.
    
    Args:
        skin_cluster: Skin cluster name
        joints: List of joint names to add
        
    Returns:
        True if successful
    """
    if not cmds.objExists(skin_cluster):
        cmds.warning(f"Skin cluster '{skin_cluster}' does not exist")
        return False
    
    valid_joints = [j for j in joints if cmds.objExists(j)]
    
    if not valid_joints:
        cmds.warning("No valid joints to add")
        return False
    
    for joint in valid_joints:
        cmds.skinCluster(skin_cluster, edit=True, addInfluence=joint)
    
    return True


def remove_joints_from_skin_cluster(
    skin_cluster: str,
    joints: List[str]
) -> bool:
    """
    Remove joints from a skin cluster.
    
    Args:
        skin_cluster: Skin cluster name
        joints: List of joint names to remove
        
    Returns:
        True if successful
    """
    if not cmds.objExists(skin_cluster):
        cmds.warning(f"Skin cluster '{skin_cluster}' does not exist")
        return False
    
    valid_joints = [j for j in joints if cmds.objExists(j)]
    
    if not valid_joints:
        cmds.warning("No valid joints to remove")
        return False
    
    for joint in valid_joints:
        cmds.skinCluster(skin_cluster, edit=True, removeInfluence=joint)
    
    return True


# ============================================================
# Skin Binding Operations
# ============================================================

def bind_skin_to_rig(
    mesh: str,
    rig: str,
    max_influences: int = 5,
    skin_method: int = 0
) -> Optional[str]:
    """
    Bind a mesh to a rig.
    
    Args:
        mesh: Mesh object name
        rig: Rig object name
        max_influences: Maximum influences per vertex
        skin_method: Skin method
        
    Returns:
        Skin cluster name or None
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return None
    
    if not cmds.objExists(rig):
        cmds.warning(f"Rig '{rig}' does not exist")
        return None
    
    # Get all joints in the rig
    joints = cmds.ls(f"{rig}.bones", type='joint') or []
    
    if not joints:
        cmds.warning(f"No joints found in rig '{rig}'")
        return None
    
    return create_skin_cluster(mesh, joints, max_influences=max_influences, skin_method=skin_method)


# ============================================================
# Skin Weight Operations
# ============================================================

def get_skin_weights(
    skin_cluster: str,
    vertex_index: int
) -> Dict[str, float]:
    """
    Get skin weights for a vertex.
    
    Args:
        skin_cluster: Skin cluster name
        vertex_index: Vertex index
        
    Returns:
        Dictionary mapping joint names to weights
    """
    if not cmds.objExists(skin_cluster):
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


def set_skin_weight(
    skin_cluster: str,
    joint: str,
    vertex_index: int,
    weight: float
) -> bool:
    """
    Set skin weight for a vertex.
    
    Args:
        skin_cluster: Skin cluster name
        joint: Joint name
        vertex_index: Vertex index
        weight: Weight value
        
    Returns:
        True if successful
    """
    if not cmds.objExists(skin_cluster):
        cmds.warning(f"Skin cluster '{skin_cluster}' does not exist")
        return False
    
    if not cmds.objExists(joint):
        cmds.warning(f"Joint '{joint}' does not exist")
        return False
    
    cmds.skinCluster(
        skin_cluster,
        edit=True,
        weight=f"{joint}.vtx[{vertex_index}]",
        value=weight
    )
    
    return True


def normalize_skin_weights(
    skin_cluster: str,
    vertices: List[int] = None
) -> bool:
    """
    Normalize skin weights for vertices.
    
    Args:
        skin_cluster: Skin cluster name
        vertices: List of vertex indices (None for all)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(skin_cluster):
        cmds.warning(f"Skin cluster '{skin_cluster}' does not exist")
        return False
    
    influences = get_skin_influences(skin_cluster)
    
    # Get the mesh from the skin cluster
    mesh = cmds.skinCluster(skin_cluster, query=True, geometry=True)[0]
    
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


def prune_skin_weights(
    skin_cluster: str,
    threshold: float = 0.001
) -> bool:
    """
    Prune skin weights below a threshold.
    
    Args:
        skin_cluster: Skin cluster name
        threshold: Weight threshold
        
    Returns:
        True if successful
    """
    if not cmds.objExists(skin_cluster):
        cmds.warning(f"Skin cluster '{skin_cluster}' does not exist")
        return False
    
    cmds.skinCluster(skin_cluster, edit=True, pruneWeights=threshold)
    return True


# ============================================================
# Skin Weight Copy/Transfer
# ============================================================

def copy_skin_weights(
    source_mesh: str,
    target_mesh: str,
    source_skin: str = None,
    target_skin: str = None
) -> bool:
    """
    Copy skin weights from source to target mesh.
    
    Args:
        source_mesh: Source mesh name
        target_mesh: Target mesh name
        source_skin: Source skin cluster (auto-detected if None)
        target_skin: Target skin cluster (auto-detected if None)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(source_mesh):
        cmds.warning(f"Source mesh '{source_mesh}' does not exist")
        return False
    
    if not cmds.objExists(target_mesh):
        cmds.warning(f"Target mesh '{target_mesh}' does not exist")
        return False
    
    # Get skin clusters
    if source_skin is None:
        source_skin = get_skin_cluster(source_mesh)
    
    if target_skin is None:
        target_skin = get_skin_cluster(target_mesh)
    
    if not source_skin:
        cmds.warning(f"No skin cluster found on source mesh '{source_mesh}'")
        return False
    
    if not target_skin:
        cmds.warning(f"No skin cluster found on target mesh '{target_mesh}'")
        return False
    
    # Copy weights
    try:
        cmds.copySkinWeights(
            sourceSkin=source_skin,
            destinationSkin=target_skin,
            sourceMesh=source_mesh,
            destinationMesh=target_mesh,
            noNormals=True,
            surfaceAssociation='closestPoint'
        )
        return True
    except Exception as e:
        cmds.warning(f"Error copying skin weights: {str(e)}")
        return False


def transfer_skin_weights(
    source_mesh: str,
    target_mesh: str,
    joints: List[str] = None
) -> bool:
    """
    Transfer skin weights from source to target mesh.
    
    Args:
        source_mesh: Source mesh name
        target_mesh: Target mesh name
        joints: List of joints (uses source skin influences if None)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(source_mesh):
        cmds.warning(f"Source mesh '{source_mesh}' does not exist")
        return False
    
    if not cmds.objExists(target_mesh):
        cmds.warning(f"Target mesh '{target_mesh}' does not exist")
        return False
    
    # Get source skin
    source_skin = get_skin_cluster(source_mesh)
    
    if not source_skin:
        cmds.warning(f"No skin cluster found on source mesh '{source_mesh}'")
        return False
    
    # Get joints
    if joints is None:
        joints = get_skin_influences(source_skin)
    
    if not joints:
        cmds.warning("No joints found for transfer")
        return False
    
    # Create target skin
    target_skin = create_skin_cluster(target_mesh, joints)
    
    if not target_skin:
        cmds.warning(f"Failed to create skin cluster on target mesh '{target_mesh}'")
        return False
    
    # Copy weights
    return copy_skin_weights(source_mesh, target_mesh, source_skin, target_skin)


# ============================================================
# Skin Weight Mirror
# ============================================================

def mirror_skin_weights(
    mesh: str,
    skin_cluster: str = None,
    axis: str = 'X'
) -> bool:
    """
    Mirror skin weights across an axis.
    
    Args:
        mesh: Mesh object name
        skin_cluster: Skin cluster name (auto-detected if None)
        axis: Mirror axis ('X', 'Y', or 'Z')
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    if skin_cluster is None:
        skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    # Mirror weights
    try:
        cmds.skinCluster(skin_cluster, edit=True, mirror=True, axis=axis)
        return True
    except Exception as e:
        cmds.warning(f"Error mirroring skin weights: {str(e)}")
        return False


def smooth_skin_weights(
    mesh: str,
    skin_cluster: str = None,
    iterations: int = 1
) -> bool:
    """
    Smooth skin weights.
    
    Args:
        mesh: Mesh object name
        skin_cluster: Skin cluster name (auto-detected if None)
        iterations: Number of smoothing iterations
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    if skin_cluster is None:
        skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    try:
        cmds.skinCluster(skin_cluster, edit=True, smoothWeights=iterations)
        return True
    except Exception as e:
        cmds.warning(f"Error smoothing skin weights: {str(e)}")
        return False


# ============================================================
# Skin Weight Export/Import
# ============================================================

def export_skin_weights(
    mesh: str,
    filepath: str,
    skin_cluster: str = None
) -> bool:
    """
    Export skin weights to a file.
    
    Args:
        mesh: Mesh object name
        filepath: File path
        skin_cluster: Skin cluster name (auto-detected if None)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    if skin_cluster is None:
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
            title="Export Skin Weights",
            message=f"Skin weights exported successfully to:\n{filepath}",
            button=["OK"]
        )
        return True
    except Exception as e:
        cmds.warning(f"Error exporting skin weights: {str(e)}")
        cmds.confirmDialog(
            title="Export Skin Weights Error",
            message=f"Failed to export skin weights:\n{str(e)}",
            button=["OK"]
        )
        return False


def import_skin_weights(
    mesh: str,
    filepath: str,
    skin_cluster: str = None
) -> bool:
    """
    Import skin weights from a file.
    
    Args:
        mesh: Mesh object name
        filepath: File path
        skin_cluster: Skin cluster name (auto-detected if None)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        cmds.warning(f"Mesh '{mesh}' does not exist")
        return False
    
    # Check if file exists
    import os
    if not os.path.exists(filepath):
        cmds.warning(f"Skin weight file '{filepath}' does not exist")
        return False
    
    if skin_cluster is None:
        skin_cluster = get_skin_cluster(mesh)
    
    if not skin_cluster:
        cmds.warning(f"No skin cluster found on '{mesh}'")
        return False
    
    try:
        # Correct syntax for importing weights
        cmds.deformerWeights(
            **{"import": True},
            path=filepath,
            deformer=skin_cluster
        )
        cmds.confirmDialog(
            title="Import Skin Weights",
            message=f"Skin weights imported successfully from:\n{filepath}",
            button=["OK"]
        )
        return True
    except Exception as e:
        cmds.warning(f"Error importing skin weights: {str(e)}")
        cmds.confirmDialog(
            title="Import Skin Weights Error",
            message=f"Failed to import skin weights:\n{str(e)}",
            button=["OK"]
        )
        return False