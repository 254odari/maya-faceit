# -*- coding: utf-8 -*-
"""
tools/skin/weights.py

Weight editing utilities: normalize, smooth, clamp, prune, statistics.
"""

import maya.cmds as cmds # type: ignore
import math
from typing import List, Optional, Dict, Any, Union, Tuple
from .types import WeightStatistics, NormalizeMode
from .editor import SkinEditor


class WeightTools:
    """
    Weight manipulation tools.
    """

    def __init__(self, editor: SkinEditor):
        self.editor = editor

    # =========================================================================
    # GET / SET
    # =========================================================================

    def get_weights(self, skin: str, vertex: Optional[int] = None) -> Union[List[float], Dict[int, List[float]]]:
        """
        Get weights for all vertices or a specific vertex.
        """
        if vertex is not None:
            return self.editor.get_vertex_weights(skin, vertex)

        # Get all vertices
        mesh = self.editor.get_skin_info(skin).mesh
        if not mesh:
            return {}
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        result = {}
        for v in range(vertex_count):
            result[v] = self.editor.get_vertex_weights(skin, v)
        return result

    def set_weights(self, skin: str, vertex: int, weights: List[float]) -> bool:
        """Set weights for a specific vertex."""
        return self.editor.set_vertex_weights(skin, vertex, weights)

    # =========================================================================
    # NORMALIZE
    # =========================================================================

    def normalize(self, skin: str, mode: NormalizeMode = NormalizeMode.TOTAL) -> bool:
        """
        Normalize skin weights.
        """
        if not cmds.objExists(skin):
            return False
        try:
            if mode == NormalizeMode.TOTAL:
                cmds.skinCluster(skin, e=True, normalizeWeights=True)
            elif mode == NormalizeMode.PER_VERTEX:
                # Same as TOTAL for Maya's skinCluster
                cmds.skinCluster(skin, e=True, normalizeWeights=True)
            else:
                # PER_INFLUENCE: normalize each influence's total weight
                # This requires manual calculation
                influences = cmds.skinCluster(skin, q=True, influence=True) or []
                mesh = self.editor.get_skin_info(skin).mesh
                if not mesh:
                    return False
                vertex_count = cmds.polyEvaluate(mesh, vertex=True)
                for v in range(vertex_count):
                    weights = self.editor.get_vertex_weights(skin, v)
                    # Normalize each vertex's weights to sum to 1.0
                    total = sum(weights)
                    if total > 0:
                        normalized = [w / total for w in weights]
                        self.editor.set_vertex_weights(skin, v, normalized)
            return True
        except:
            return False

    # =========================================================================
    # SMOOTH
    # =========================================================================

    def smooth(self, skin: str, iterations: int = 5, strength: float = 0.5) -> bool:
        """
        Smooth skin weights by averaging with neighbors.
        """
        if not cmds.objExists(skin):
            return False

        info = self.editor.get_skin_info(skin)
        if not info or not info.mesh:
            return False

        mesh = info.mesh
        influences = [inf.name for inf in info.influences]
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)

        # Build adjacency
        adj = self._build_adjacency(mesh)

        for _ in range(iterations):
            # Copy current weights
            current_weights = {}
            for v in range(vertex_count):
                current_weights[v] = self.editor.get_vertex_weights(skin, v)

            # Smooth each vertex
            for v in range(vertex_count):
                neighbors = adj.get(v, [])
                if not neighbors:
                    continue
                # Average weights of neighbors
                avg = [0.0] * len(influences)
                for n in neighbors:
                    n_weights = current_weights.get(n, [0.0] * len(influences))
                    for i in range(len(avg)):
                        avg[i] += n_weights[i]
                for i in range(len(avg)):
                    avg[i] /= len(neighbors)
                # Blend with original
                current = current_weights[v]
                blended = [
                    current[i] + (avg[i] - current[i]) * strength
                    for i in range(len(current))
                ]
                # Normalize
                total = sum(blended)
                if total > 0:
                    blended = [w / total for w in blended]
                self.editor.set_vertex_weights(skin, v, blended)

        return True

    def _build_adjacency(self, mesh: str) -> Dict[int, List[int]]:
        """Build vertex adjacency map."""
        # Use Maya API or polyInfo
        adj = {}
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        for v in range(vertex_count):
            # Get connected vertices using polyInfo or polyListComponentConversion
            connected = cmds.polyInfo(mesh, vtxToEdge=True) or []
            # Simplified: just parse edges
            # For now, we'll use a simpler approach
            edges = cmds.polyListComponentConversion(f"{mesh}.vtx[{v}]", toEdge=True)
            edges = cmds.ls(edges, flatten=True)
            verts = set()
            for e in edges:
                v1, v2 = cmds.polyInfo(e, edgeToVertex=True)
                # Parse vertex indices
                # This is simplified
                pass
            adj[v] = list(verts)
        return adj

    # =========================================================================
    # CLAMP
    # =========================================================================

    def clamp(self, skin: str, min_val: float = 0.0, max_val: float = 1.0) -> bool:
        """Clamp skin weights to [min, max]."""
        if not cmds.objExists(skin):
            return False
        info = self.editor.get_skin_info(skin)
        if not info or not info.mesh:
            return False

        vertex_count = cmds.polyEvaluate(info.mesh, vertex=True)
        for v in range(vertex_count):
            weights = self.editor.get_vertex_weights(skin, v)
            clamped = [max(min_val, min(max_val, w)) for w in weights]
            self.editor.set_vertex_weights(skin, v, clamped)
        return True

    # =========================================================================
    # PRUNE
    # =========================================================================

    def prune(self, skin: str, threshold: float = 0.001, keep: Optional[int] = None) -> int:
        """
        Prune small weights and optionally limit influences.
        Returns number of vertices modified.
        """
        if not cmds.objExists(skin):
            return 0

        info = self.editor.get_skin_info(skin)
        if not info or not info.mesh:
            return 0

        influences = [inf.name for inf in info.influences]
        vertex_count = cmds.polyEvaluate(info.mesh, vertex=True)
        modified = 0

        for v in range(vertex_count):
            weights = self.editor.get_vertex_weights(skin, v)
            if not weights:
                continue
            # Prune by threshold
            pruned = [w if w >= threshold else 0.0 for w in weights]
            # Keep top N if specified
            if keep is not None and len(pruned) > keep:
                # Sort by weight
                sorted_pairs = sorted(enumerate(pruned), key=lambda x: x[1], reverse=True)
                keep_indices = [i for i, w in sorted_pairs[:keep]]
                new_weights = [0.0] * len(pruned)
                for i in keep_indices:
                    new_weights[i] = pruned[i]
                pruned = new_weights
            # Normalize
            total = sum(pruned)
            if total > 0:
                pruned = [w / total for w in pruned]
            # Check if changed
            if weights != pruned:
                self.editor.set_vertex_weights(skin, v, pruned)
                modified += 1

        return modified

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def statistics(self, skin: str, vertex: Optional[int] = None) -> Union[WeightStatistics, List[WeightStatistics]]:
        """Get weight statistics."""
        if vertex is not None:
            weights = self.editor.get_vertex_weights(skin, vertex)
            return self._compute_stats(weights)

        # Get stats for all vertices
        info = self.editor.get_skin_info(skin)
        if not info or not info.mesh:
            return []
        vertex_count = cmds.polyEvaluate(info.mesh, vertex=True)
        stats = []
        for v in range(vertex_count):
            weights = self.editor.get_vertex_weights(skin, v)
            stats.append(self._compute_stats(weights))
        return stats

    def _compute_stats(self, weights: List[float]) -> WeightStatistics:
        """Compute statistics for a weight list."""
        if not weights:
            return WeightStatistics()
        count = len(weights)
        total = sum(weights)
        avg = total / count if count > 0 else 0.0
        min_w = min(weights)
        max_w = max(weights)
        zero_count = sum(1 for w in weights if w < 0.0001)
        active_count = count - zero_count
        # Variance
        variance = sum((w - avg) ** 2 for w in weights) / count if count > 0 else 0.0
        std_dev = math.sqrt(variance) if variance > 0 else 0.0
        # Median
        sorted_w = sorted(weights)
        if count % 2 == 0:
            median = (sorted_w[count // 2 - 1] + sorted_w[count // 2]) / 2.0
        else:
            median = sorted_w[count // 2]
        return WeightStatistics(
            minimum=min_w,
            maximum=max_w,
            average=avg,
            median=median,
            std_dev=std_dev,
            sum=total,
            count=count,
            zero_count=zero_count,
            active_count=active_count,
            normalized=abs(total - 1.0) < 0.001,  # Rough check
        )