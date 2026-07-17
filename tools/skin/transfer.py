# -*- coding: utf-8 -*-
"""
tools/skin/transfer.py

Skin weight transfer between meshes.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Dict, List
from .types import SkinReport
from .editor import SkinEditor


class SkinTransfer:
    """
    Transfer skin weights from one mesh to another.
    """

    def __init__(self, editor: SkinEditor):
        self.editor = editor

    def transfer(self, source: str, target: str,
                 method: str = "closest_point") -> SkinReport:
        """
        Transfer skin weights from source to target.

        Methods:
            - closest_point: Uses Maya's copySkinWeights with closestPoint.
            - barycentric: Uses barycentric interpolation (requires matching topology).
        """
        report = SkinReport(operation="transfer")

        if not cmds.objExists(source) or not cmds.objExists(target):
            report.errors.append("Source or target mesh does not exist.")
            report.success = False
            return report

        # Get skinClusters
        src_skin = self.editor.get_skin_cluster(source)
        tgt_skin = self.editor.get_skin_cluster(target)

        if not src_skin:
            report.errors.append("Source mesh has no skinCluster.")
            report.success = False
            return report

        # If target has no skinCluster, create one with same influences
        if not tgt_skin:
            influences = cmds.skinCluster(src_skin, q=True, influence=True) or []
            if influences:
                tgt_skin = cmds.skinCluster(influences, target, toSelectedBones=True)[0]

        if not tgt_skin:
            report.errors.append("Target could not be skinned.")
            report.success = False
            return report

        try:
            # Use copySkinWeights
            surface_assoc = 'closestPoint' if method == 'closest_point' else 'topology'
            cmds.copySkinWeights(
                sourceSkin=src_skin,
                destinationSkin=tgt_skin,
                noMirror=True,
                surfaceAssociation=surface_assoc,
                influenceAssociation='name'
            )
            report.success = True
            report.processed_vertices = cmds.polyEvaluate(target, vertex=True)
        except Exception as e:
            report.errors.append(str(e))
            report.success = False

        return report