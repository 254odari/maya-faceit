# -*- coding: utf-8 -*-
"""
tools/skin/editor.py

Low-level skinCluster operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Any, Tuple, Union
from .types import SkinInfo, InfluenceInfo, SkinType, SkinState
from .settings import SkinSettings


class SkinEditor:
    """
    Low-level Maya skinCluster operations.
    """

    def __init__(self, settings: SkinSettings):
        self.settings = settings
        self._cache: Dict[str, SkinInfo] = {}

    # =========================================================================
    # SKINCLUSTER CREATION / REMOVAL
    # =========================================================================

    def create_skin(self, mesh: str, influences: List[str],
                    max_influences: Optional[int] = None,
                    skin_type: Optional[SkinType] = None) -> Optional[str]:
        """
        Create a skinCluster on a mesh.
        """
        if not cmds.objExists(mesh):
            return None
        if not influences:
            return None

        max_inf = max_influences or self.settings.max_influences
        skin_type_str = skin_type or self.settings.skin_type
        skin_type_str = skin_type_str.value if hasattr(skin_type_str, 'value') else str(skin_type_str)

        try:
            # Create the skinCluster
            result = cmds.skinCluster(
                influences,
                mesh,
                toSelectedBones=True,
                maximumInfluences=max_inf,
                skinMethod=skin_type_str,
                name=f"{mesh}_skinCluster"
            )
            if result:
                skin_node = result[0]
                # Auto-normalize if enabled
                if self.settings.auto_normalize:
                    cmds.skinCluster(skin_node, e=True, normalizeWeights=True)
                return skin_node
        except Exception as e:
            print(f"Failed to create skinCluster: {e}")
        return None

    def remove_skin(self, skin: str) -> bool:
        """Remove a skinCluster."""
        if not cmds.objExists(skin):
            return False
        try:
            cmds.delete(skin)
            return True
        except:
            return False

    # =========================================================================
    # QUERY
    # =========================================================================

    def get_skin_cluster(self, mesh: str) -> Optional[str]:
        """Get the skinCluster on a mesh."""
        if not cmds.objExists(mesh):
            return None
        connections = cmds.listConnections(mesh, type='skinCluster') or []
        return connections[0] if connections else None

    def list_skins(self) -> List[str]:
        """List all skinClusters in the scene."""
        return cmds.ls(type='skinCluster', long=True)

    def get_skin_info(self, skin: str) -> Optional[SkinInfo]:
        """Get detailed information about a skinCluster."""
        if not cmds.objExists(skin):
            return None

        # Cache check
        if skin in self._cache:
            return self._cache[skin]

        # Get influences
        influences = cmds.skinCluster(skin, q=True, influence=True) or []
        influences_info = []
        for inf in influences:
            inf_info = InfluenceInfo(
                name=inf,
                index=influences.index(inf),
            )
            influences_info.append(inf_info)

        # Get bound mesh
        geom = cmds.skinCluster(skin, q=True, geometry=True)
        mesh = geom[0] if geom else ""

        # Get max influences
        max_inf = cmds.getAttr(f"{skin}.maximumInfluences") or 5

        # Get skin method
        method = cmds.getAttr(f"{skin}.skinMethod") or 0
        skin_type_map = {0: SkinType.STANDARD, 1: SkinType.DUAL_QUATERNION}
        skin_type = skin_type_map.get(method, SkinType.STANDARD)

        # Vertex count
        vertex_count = cmds.polyEvaluate(mesh, vertex=True) if mesh else 0

        info = SkinInfo(
            name=skin,
            mesh=mesh,
            influences=influences_info,
            vertex_count=vertex_count,
            max_influences=max_inf,
            skin_type=skin_type,
            normalized=True,  # Assume normalized
            state=SkinState.NORMAL,
        )

        # Cache it
        self._cache[skin] = info
        return info

    def get_vertex_weights(self, skin: str, vertex: int) -> List[float]:
        """Get weights for a specific vertex."""
        if not cmds.objExists(skin):
            return []
        try:
            return cmds.skinPercent(skin, f"{skin}.vtx[{vertex}]", q=True, value=True) or []
        except:
            return []

    def set_vertex_weights(self, skin: str, vertex: int, weights: List[float]) -> bool:
        """Set weights for a specific vertex."""
        if not cmds.objExists(skin):
            return False
        influences = cmds.skinCluster(skin, q=True, influence=True) or []
        if len(weights) != len(influences):
            return False
        try:
            for inf, w in zip(influences, weights):
                cmds.skinPercent(skin, f"{skin}.vtx[{vertex}]", transformValue=[(inf, w)])
            return True
        except:
            return False