"""
maya_faceit.rig.tongue_solver

High-level tongue rig solver.

Coordinates FK, IK, stretch, volume, and blend
systems into a unified animation rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import maya.cmds as cmds


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class TongueSolverState:

    master_control: Optional[str] = None

    enabled: bool = True

    built: bool = False


# ------------------------------------------------------------
# Solver
# ------------------------------------------------------------

class TongueSolver:

    """
    High-level coordinator.

    Does not build joints or controls.

    It connects all tongue modules together.
    """

    def __init__(self):

        self.state = TongueSolverState()

    # -----------------------------------------------------

    def build(

        self,

        master_control: str,

        fk_system,

        ik_system,

        stretch_system,

        volume_system,

        blend_system,

    ):

        self.state.master_control = master_control

        self._connect_fk(

            master_control,

            fk_system,

        )

        self._connect_ik(

            master_control,

            ik_system,

        )

        self._connect_stretch(

            master_control,

            stretch_system,

        )

        self._connect_volume(

            master_control,

            volume_system,

        )

        self._connect_blend(

            master_control,

            blend_system,

        )

        self.state.built = True

    # -----------------------------------------------------

    def enable(self):

        self.state.enabled = True

    # -----------------------------------------------------

    def disable(self):

        self.state.enabled = False

    # -----------------------------------------------------

    def rebuild(self):

        if not self.state.master_control:

            return

        print("Tongue solver rebuild requested.")

    # -----------------------------------------------------
    # FK
    # -----------------------------------------------------

    def _connect_fk(

        self,

        ctrl,

        fk,

    ):

        if fk is None:

            return

        attrs = (

            "curlRoot",

            "curlTip",

            "roll",

            "twist",

            "side",

        )

        for attr in attrs:

            if hasattr(fk, "connect"):

                fk.connect(ctrl, attr)

    # -----------------------------------------------------
    # IK
    # -----------------------------------------------------

    def _connect_ik(

        self,

        ctrl,

        ik,

    ):

        if ik is None:

            return

        attrs = (

            "ikTwist",

            "ikRoll",

            "ikFollow",

        )

        for attr in attrs:

            if hasattr(ik, "connect"):

                ik.connect(ctrl, attr)

    # -----------------------------------------------------
    # Stretch
    # -----------------------------------------------------

    def _connect_stretch(

        self,

        ctrl,

        stretch,

    ):

        if stretch is None:

            return

        attrs = (

            "stretch",

            "squash",

            "autoStretch",

            "autoSquash",

        )

        for attr in attrs:

            if hasattr(stretch, "connect"):

                stretch.connect(ctrl, attr)

    # -----------------------------------------------------
    # Volume
    # -----------------------------------------------------

    def _connect_volume(

        self,

        ctrl,

        volume,

    ):

        if volume is None:

            return

        attrs = (

            "volume",

            "thickness",

            "taper",

        )

        for attr in attrs:

            if hasattr(volume, "connect"):

                volume.connect(ctrl, attr)

    # -----------------------------------------------------
    # Blend
    # -----------------------------------------------------

    def _connect_blend(

        self,

        ctrl,

        blend,

    ):

        if blend is None:

            return

        if hasattr(blend, "connect"):

            blend.connect(

                ctrl,

                "fkIkBlend",

            )


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

tongue_solver = TongueSolver()