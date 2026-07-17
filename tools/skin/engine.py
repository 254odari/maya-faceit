# -*- coding: utf-8 -*-
"""
tools/skin/engine.py

Main facade for skin operations.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Union, Dict, Any, Tuple
from .types import (
    SkinInfo, SkinReport, SkinSettings, WeightStatistics,
    SkinType, NormalizeMode, PruneMode, InfluenceInfo
)
from .settings import DEFAULT_SKIN_SETTINGS
from .editor import SkinEditor
from .weights import WeightTools
from .influences import InfluenceTools
from .mirror import SkinMirror
from .transfer import SkinTransfer
from .validation import SkinValidator


class SkinEngine:
    """
    Main facade for all skin operations.

    Provides unified access to skinCluster management, weight editing,
    influence management, mirroring, transfer, and validation.
    """

    def __init__(self, settings: Optional[SkinSettings] = None):
        self.settings = settings or DEFAULT_SKIN_SETTINGS
        self.editor = SkinEditor(self.settings)
        self.weights = WeightTools(self.editor)
        self.influences = InfluenceTools(self.editor)
        self.mirror = SkinMirror(self.editor)
        self.transfer = SkinTransfer(self.editor)
        self.validator = SkinValidator()

    # =========================================================================
    # SKINCLUSTER MANAGEMENT
    # =========================================================================

    def create(self, mesh: str, influences: List[str],
               max_influences: Optional[int] = None,
               skin_type: Optional[SkinType] = None) -> Optional[str]:
        """
        Create a skinCluster on a mesh.

        Args:
            mesh: Mesh to skin.
            influences: List of influence nodes (joints, controllers).
            max_influences: Maximum influences per vertex.
            skin_type: Type of skinning.

        Returns:
            Name of the created skinCluster, or None on failure.
        """
        return self.editor.create_skin(mesh, influences, max_influences, skin_type)

    def remove(self, skin: str) -> bool:
        """Remove a skinCluster."""
        return self.editor.remove_skin(skin)

    def get_skin(self, mesh: str) -> Optional[str]:
        """Get the skinCluster on a mesh."""
        return self.editor.get_skin_cluster(mesh)

    def get_info(self, skin: str) -> Optional[SkinInfo]:
        """Get detailed information about a skinCluster."""
        return self.editor.get_skin_info(skin)

    def list_skins(self) -> List[str]:
        """List all skinClusters in the scene."""
        return self.editor.list_skins()

    # =========================================================================
    # WEIGHT OPERATIONS
    # =========================================================================

    def get_weights(self, skin: str, vertex: Optional[int] = None) -> Union[List[float], Dict[int, List[float]]]:
        """Get weights for all vertices or a specific vertex."""
        return self.weights.get_weights(skin, vertex)

    def set_weights(self, skin: str, vertex: int, weights: List[float]) -> bool:
        """Set weights for a specific vertex."""
        return self.weights.set_weights(skin, vertex, weights)

    def normalize(self, skin: str, mode: Optional[NormalizeMode] = None) -> bool:
        """Normalize skin weights."""
        return self.weights.normalize(skin, mode or self.settings.normalize_mode)

    def smooth(self, skin: str, iterations: int = 5, strength: float = 0.5) -> bool:
        """Smooth skin weights."""
        return self.weights.smooth(skin, iterations, strength)

    def clamp(self, skin: str, min_val: float = 0.0, max_val: float = 1.0) -> bool:
        """Clamp skin weights."""
        return self.weights.clamp(skin, min_val, max_val)

    def prune(self, skin: str, threshold: Optional[float] = None,
              keep: Optional[int] = None) -> int:
        """Prune small weights and limit influences."""
        return self.weights.prune(skin, threshold or self.settings.prune_threshold, keep)

    def statistics(self, skin: str, vertex: Optional[int] = None) -> Union[WeightStatistics, List[WeightStatistics]]:
        """Get weight statistics."""
        return self.weights.statistics(skin, vertex)

    # =========================================================================
    # INFLUENCE OPERATIONS
    # =========================================================================

    def add_influence(self, skin: str, influence: str) -> bool:
        """Add an influence to a skinCluster."""
        return self.influences.add_influence(skin, influence)

    def remove_influence(self, skin: str, influence: str) -> bool:
        """Remove an influence from a skinCluster."""
        return self.influences.remove_influence(skin, influence)

    def reorder_influences(self, skin: str, order: List[str]) -> bool:
        """Reorder influences."""
        return self.influences.reorder_influences(skin, order)

    def get_influences(self, skin: str) -> List[InfluenceInfo]:
        """Get all influences with their info."""
        return self.influences.get_influences(skin)

    # =========================================================================
    # MIRRORING
    # =========================================================================

    def mirror_weights(self, source: str, target: str,
                       mirror_axis: str = "x", **kwargs) -> SkinReport:
        """Mirror skin weights from source to target."""
        return self.mirror.mirror(source, target, mirror_axis, **kwargs)

    # =========================================================================
    # TRANSFER
    # =========================================================================

    def transfer_weights(self, source: str, target: str,
                         method: Optional[str] = None) -> SkinReport:
        """Transfer skin weights from source to target."""
        return self.transfer.transfer(source, target, method or self.settings.transfer_method)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(self, skin: str) -> SkinReport:
        """Validate a skinCluster."""
        return self.validator.validate(skin)

    # =========================================================================
    # UTILITY
    # =========================================================================

    def set_settings(self, settings: SkinSettings) -> None:
        """Update settings."""
        self.settings = settings
        self.editor.settings = settings

    def get_settings(self) -> SkinSettings:
        """Get current settings."""
        return self.settings


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

skin = SkinEngine()

__all__ = ["SkinEngine", "skin"]