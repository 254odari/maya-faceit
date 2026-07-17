# -*- coding: utf-8 -*-
"""
tools/skin/mirror.py

Skin weight mirroring.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Dict, List
from .types import SkinReport
from .editor import SkinEditor


class SkinMirror:
    """
    Mirror skin weights from one mesh to another.
    """

    def __init__(self, editor: SkinEditor):
        self.editor = editor

    def mirror(self, source: str, target: str,
               mirror_axis: str = "x", **kwargs) -> SkinReport:
        """
        Mirror skin weights from source to target.

        Uses Maya's copySkinWeights with mirroring enabled.
        """
        report = SkinReport(operation="mirror")

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
            # Use copySkinWeights with mirror
            cmds.copySkinWeights(
                sourceSkin=src_skin,
                destinationSkin=tgt_skin,
                noMirror=False,
                mirrorAxis=mirror_axis.upper(),
                surfaceAssociation='closestPoint',
                influenceAssociation='name'
            )
            report.success = True
            report.processed_vertices = cmds.polyEvaluate(target, vertex=True)
        except Exception as e:
            report.errors.append(str(e))
            report.success = False

        return report