"""
maya_faceit.rig.deformers

Central deformer management system.

Responsible for creating, managing and rebuilding Maya
deformers used by the facial rig.

Target:
    Maya 2026
    Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class Deformer:

    name: str

    deformer_type: str

    geometry: list[str]

    node: str


# ---------------------------------------------------------
# Manager
# ---------------------------------------------------------

class DeformerManager:

    def __init__(self):

        self.deformers: dict[str, Deformer] = {}

    # --------------------------------------------------

    def _register(
        self,
        name: str,
        deformer_type: str,
        geometry: list[str],
        node: str,
    ) -> Deformer:

        data = Deformer(

            name=name,

            deformer_type=deformer_type,

            geometry=list(geometry),

            node=node,
        )

        self.deformers[name] = data

        return data

    # --------------------------------------------------
    # BlendShape
    # --------------------------------------------------

    def create_blendshape(
        self,
        name: str,
        geometry: list[str],
    ) -> Deformer:

        node = cmds.blendShape(

            geometry,

            name=name,
        )[0]

        return self._register(

            name,

            "blendShape",

            geometry,

            node,
        )

    # --------------------------------------------------
    # Skin Cluster
    # --------------------------------------------------

    def create_skin_cluster(
        self,
        name: str,
        joints: list[str],
        geometry: str,
    ) -> Deformer:

        node = cmds.skinCluster(

            joints,

            geometry,

            tsb=True,

            name=name,
        )[0]

        return self._register(

            name,

            "skinCluster",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Cluster
    # --------------------------------------------------

    def create_cluster(
        self,
        name: str,
        geometry: str,
    ) -> Deformer:

        node = cmds.cluster(

            geometry,

            name=name,
        )[1]

        return self._register(

            name,

            "cluster",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Lattice
    # --------------------------------------------------

    def create_lattice(
        self,
        name: str,
        geometry: str,
    ) -> Deformer:

        lattice = cmds.lattice(

            geometry,

            name=name,
        )

        node = lattice[1]

        return self._register(

            name,

            "lattice",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Wire
    # --------------------------------------------------

    def create_wire(
        self,
        name: str,
        geometry: str,
        curve: str,
    ) -> Deformer:

        node = cmds.wire(

            geometry,

            wire=curve,

            name=name,
        )[0]

        return self._register(

            name,

            "wire",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Wrap
    # --------------------------------------------------

    def create_wrap(
        self,
        name: str,
        source: str,
        target: str,
    ) -> Deformer:

        cmds.select(clear=True)

        cmds.select(source)

        cmds.select(target, add=True)

        node = cmds.deformer(

            type="wrap",

            name=name,
        )[0]

        return self._register(

            name,

            "wrap",

            [target],

            node,
        )

    # --------------------------------------------------
    # Delta Mush
    # --------------------------------------------------

    def create_delta_mush(
        self,
        name: str,
        geometry: str,
    ) -> Deformer:

        node = cmds.deltaMush(

            geometry,

            name=name,
        )[0]

        return self._register(

            name,

            "deltaMush",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Tension
    # --------------------------------------------------

    def create_tension(
        self,
        name: str,
        geometry: str,
    ) -> Deformer:

        node = cmds.deformer(

            geometry,

            type="tension",

            name=name,
        )[0]

        return self._register(

            name,

            "tension",

            [geometry],

            node,
        )

    # --------------------------------------------------
    # Query
    # --------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.deformers

    # --------------------------------------------------

    def get(
        self,
        name: str,
    ) -> Deformer | None:

        return self.deformers.get(name)

    # --------------------------------------------------

    def list(self) -> list[str]:

        return sorted(self.deformers.keys())

    # --------------------------------------------------

    def delete(
        self,
        name: str,
    ):

        deformer = self.deformers.get(name)

        if deformer is None:
            return

        if cmds.objExists(deformer.node):
            cmds.delete(deformer.node)

        del self.deformers[name]

    # --------------------------------------------------

    def clear(self):

        for name in list(self.deformers.keys()):
            self.delete(name)

    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def serialize(self) -> dict:

        data = {}

        for item in self.deformers.values():

            data[item.name] = {

                "type": item.deformer_type,

                "geometry": item.geometry,

                "node": item.node,
            }

        return data


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

deformer_manager = DeformerManager()