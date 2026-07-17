# -*- coding: utf-8 -*-
"""
tools/analysis/rig.py

Rig analysis (controllers, joints, constraints, skinning).
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Set, List
from .types import RigStats, AnalysisScope, AnalysisLevel


class RigAnalyzer:
    """
    Analyze rig components: controllers, joints, constraints, skinning.
    """

    def __init__(self, settings):
        self.settings = settings

    def analyze(self, scope: AnalysisScope = AnalysisScope.SCENE,
                level: AnalysisLevel = AnalysisLevel.STANDARD) -> RigStats:
        """Analyze rig statistics."""
        stats = RigStats()

        # Joints
        joints = cmds.ls(type='joint', long=True)
        stats.total_joints = len(joints)

        # Controllers (heuristic)
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True) or []
            if shapes and any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                controllers.append(t)
        stats.total_controllers = len(controllers)

        # Constraints
        constraints = cmds.ls(type='constraint', long=True)
        stats.total_constraints = len(constraints)

        # SkinClusters
        skins = cmds.ls(type='skinCluster', long=True)
        stats.total_skin_clusters = len(skins)

        # Blendshapes
        bs_nodes = cmds.ls(type='blendShape', long=True)
        stats.total_blendshape_nodes = len(bs_nodes)

        # Blendshape targets
        target_count = 0
        for bs in bs_nodes:
            targets = cmds.listAttr(bs, m=True, string='weight') or []
            target_count += len(targets)
        stats.total_blendshape_targets = target_count

        # Locked and hidden controllers
        locked = 0
        hidden = 0
        for c in controllers:
            if cmds.lockNode(c, q=True, lock=True)[0]:
                locked += 1
            if not cmds.getAttr(f"{c}.visibility"):
                hidden += 1
        stats.locked_controllers = locked
        stats.hidden_controllers = hidden

        # Controllers with animation
        animated = 0
        for c in controllers:
            attrs = cmds.listAttr(c, keyable=True) or []
            for a in attrs:
                if cmds.keyframe(f"{c}.{a}", q=True, keyframeCount=True):
                    animated += 1
                    break
        stats.controllers_with_animation = animated

        # Joints with animation
        animated_joints = 0
        for j in joints:
            attrs = cmds.listAttr(j, keyable=True) or []
            for a in attrs:
                if cmds.keyframe(f"{j}.{a}", q=True, keyframeCount=True):
                    animated_joints += 1
                    break
        stats.joints_with_animation = animated_joints

        # Orphan joints (no children, no parent)
        orphan_joints = []
        for j in joints:
            children = cmds.listRelatives(j, children=True) or []
            parent = cmds.listRelatives(j, parent=True)
            if not children and not parent:
                orphan_joints.append(j)
        stats.orphan_joints = len(orphan_joints)

        # Orphan controllers
        orphan_controllers = []
        for c in controllers:
            children = cmds.listRelatives(c, children=True) or []
            if not children:
                orphan_controllers.append(c)
        stats.orphan_controllers = len(orphan_controllers)

        # Invalid constraints (broken connections)
        invalid = 0
        for c in constraints:
            targets = cmds.constraint(c, q=True, targetList=True) or []
            if not targets:
                invalid += 1
        stats.invalid_constraints = invalid

        if level == AnalysisLevel.DEEP:
            stats.details['joint_names'] = joints[:10]
            stats.details['controller_names'] = controllers[:10]

        return stats