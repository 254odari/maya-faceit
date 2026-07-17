"""
maya_faceit.rig.tongue_ik

Spline IK tongue builder.

Creates a spline IK rig suitable for
animation, FK/IK blending and procedural
deformation.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds # type: ignore

from .tongue_chain import TongueChain
from .tongue_controls import (
    tongue_controls,
    ControlData,
)


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class TongueIKRig:

    handle: str | None = None

    effector: str | None = None

    curve: str | None = None

    group: str | None = None

    controls: list[ControlData] | None = None

    clusters: list[str] | None = None


# ---------------------------------------------------------
# Builder
# ---------------------------------------------------------

class TongueIKBuilder:

    def __init__(self):

        self.rig = TongueIKRig()

    # -----------------------------------------------------

    def build(
        self,
        chain: TongueChain,
    ) -> TongueIKRig:

        self.delete()

        group = cmds.group(
            empty=True,
            name="Tongue_IK_GRP",
        )

        handle, effector, curve = cmds.ikHandle(

            solver="ikSplineSolver",

            startJoint=chain.root,

            endEffector=chain.tip,

            parentCurve=False,

            createCurve=True,

            simplifyCurve=False,

            name="Tongue_IK_Handle",

        )

        controls = tongue_controls.create_spline()

        clusters = self._create_clusters(curve)

        self._attach_clusters(
            controls,
            clusters,
        )

        cmds.parent(
            handle,
            group,
        )

        cmds.parent(
            curve,
            group,
        )

        for cluster in clusters:

            cmds.parent(
                cluster,
                group,
            )

        if controls:

            cmds.parent(
                controls[0].zero,
                group,
            )

        self.rig = TongueIKRig(

            handle=handle,

            effector=effector,

            curve=curve,

            group=group,

            controls=controls,

            clusters=clusters,

        )

        return self.rig

    # -----------------------------------------------------

    def delete(self):

        if (
            self.rig.group
            and cmds.objExists(self.rig.group)
        ):

            cmds.delete(self.rig.group)

        self.rig = TongueIKRig()

    # -----------------------------------------------------

    def set_visibility(
        self,
        visible: bool,
    ):

        tongue_controls.set_spline_visibility(
            visible,
        )

    # -----------------------------------------------------

    def curve(self):

        return self.rig.curve

    # -----------------------------------------------------

    def handle(self):

        return self.rig.handle

    # -----------------------------------------------------

    def controls(self):

        return self.rig.controls

    # -----------------------------------------------------
    # Internal
    # -----------------------------------------------------

    def _create_clusters(
        self,
        curve: str,
    ) -> list[str]:

        cvs = cmds.ls(
            curve + ".cv[*]",
            flatten=True,
        )

        clusters = []

        for index, cv in enumerate(cvs):

            cluster, handle = cmds.cluster(

                cv,

                name=f"Tongue_Cluster_{index+1:02d}",

            )

            clusters.append(handle)

        return clusters

    # -----------------------------------------------------

    def _attach_clusters(

        self,

        controls: list[ControlData],

        clusters: list[str],

    ):

        if len(controls) < 3:

            return

        count = len(clusters)

        for index, cluster in enumerate(clusters):

            t = index / max(count - 1, 1)

            if t <= 0.33:

                ctrl = controls[0]

            elif t <= 0.66:

                ctrl = controls[1]

            else:

                ctrl = controls[2]

            cmds.parent(

                cluster,

                ctrl.control,

            )


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue_ik = TongueIKBuilder()