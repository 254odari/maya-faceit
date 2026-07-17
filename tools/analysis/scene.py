# -*- coding: utf-8 -*-
"""
tools/analysis/scene.py

Scene-level analysis.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional
from .types import SceneStats, AnalysisScope, AnalysisLevel


class SceneAnalyzer:
    """
    Analyze overall scene statistics.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> SceneStats:
        """Analyze scene statistics."""
        stats = SceneStats()

        if scope == AnalysisScope.SCENE:
            # All nodes
            all_nodes = cmds.ls(long=True)
            stats.total_nodes = len(all_nodes)

            # Transforms
            transforms = cmds.ls(type='transform', long=True)
            stats.total_transforms = len(transforms)

            # Meshes
            meshes = cmds.ls(type='mesh', long=True)
            # Count unique transform parents
            mesh_set = set()
            for m in meshes:
                parents = cmds.listRelatives(m, parent=True, fullPath=True)
                if parents:
                    mesh_set.add(parents[0])
            stats.total_meshes = len(mesh_set)

            # Joints
            stats.total_joints = len(cmds.ls(type='joint', long=True))

            # Controllers (heuristic)
            controllers = []
            for t in transforms:
                shapes = cmds.listRelatives(t, shapes=True) or []
                if shapes and any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                    controllers.append(t)
            stats.total_controllers = len(controllers)

            # Constraints
            stats.total_constraints = len(cmds.ls(type='constraint', long=True))

            # SkinClusters
            stats.total_skin_clusters = len(cmds.ls(type='skinCluster', long=True))

            # Blendshapes
            stats.total_blendshapes = len(cmds.ls(type='blendShape', long=True))

            # References
            stats.total_references = len(cmds.ls(type='reference', long=True))

            # Namespaces
            namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
            stats.total_namespaces = len([ns for ns in namespaces if ns not in [':', 'UI', 'shared']])

            # Display layers
            stats.total_display_layers = len(cmds.ls(type='displayLayer', long=True))

            # Render layers
            stats.total_render_layers = len(cmds.ls(type='renderLayer', long=True))

            # Unknown nodes
            stats.unknown_nodes = len(cmds.ls(type='unknown', long=True))

            # Empty groups
            groups = cmds.ls(type='group', long=True)
            stats.empty_groups = len([g for g in groups if not cmds.listRelatives(g, children=True)])

            if level == AnalysisLevel.DEEP:
                # More detailed analysis
                stats.details['transforms_with_children'] = len([t for t in transforms if cmds.listRelatives(t, children=True)])
                stats.details['transforms_without_children'] = len([t for t in transforms if not cmds.listRelatives(t, children=True)])

        return stats