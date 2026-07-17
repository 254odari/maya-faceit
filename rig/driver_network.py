"""
maya_faceit.rig.driver_network

Node-based driver network builder for Maya Faceit.

This module creates and manages Maya Dependency Graph (DG)
networks that drive controllers, joints, blendshapes,
correctives and animation.

Target:
    Maya 2026
    Python 3.11

Author: Your Name
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ----------------------------------------------------------
# Data Classes
# ----------------------------------------------------------

@dataclass(slots=True)
class DriverNetwork:
    """Represents a driver network."""

    name: str
    driver: str
    output: str
    nodes: list[str] = field(default_factory=list)


# ----------------------------------------------------------
# Driver Network Builder
# ----------------------------------------------------------

class DriverNetworkBuilder:
    """Creates reusable Maya node networks."""

    def __init__(self):

        self.networks: dict[str, DriverNetwork] = {}

    # ======================================================
    # Internal
    # ======================================================

    def _register(
        self,
        name: str,
        driver: str,
        output: str,
        nodes: list[str],
    ) -> DriverNetwork:

        network = DriverNetwork(
            name=name,
            driver=driver,
            output=output,
            nodes=nodes,
        )

        self.networks[name] = network

        return network

    # ------------------------------------------------------

    def _connect_output(
        self,
        source: str,
        destination: str,
    ):

        if not cmds.isConnected(source, destination):
            cmds.connectAttr(
                source,
                destination,
                force=True,
            )

    # ======================================================
    # Basic Connections
    # ======================================================

    def connect(
        self,
        source: str,
        destination: str,
    ):

        self._connect_output(
            source,
            destination,
        )

    # ------------------------------------------------------

    def disconnect(
        self,
        source: str,
        destination: str,
    ):

        if cmds.isConnected(source, destination):

            cmds.disconnectAttr(
                source,
                destination,
            )

    # ======================================================
    # Multiply
    # ======================================================

    def multiply(
        self,
        name: str,
        input1: str,
        input2: float,
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "multiplyDivide",
            name=f"{name}_MD",
        )

        cmds.connectAttr(
            input1,
            node + ".input1X",
            force=True,
        )

        cmds.setAttr(
            node + ".input2X",
            input2,
        )

        self._connect_output(
            node + ".outputX",
            output,
        )

        return self._register(
            name,
            input1,
            output,
            [node],
        )

    # ======================================================
    # Divide
    # ======================================================

    def divide(
        self,
        name: str,
        input1: str,
        divisor: float,
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "multiplyDivide",
            name=f"{name}_DIV",
        )

        cmds.setAttr(
            node + ".operation",
            2,
        )

        cmds.connectAttr(
            input1,
            node + ".input1X",
            force=True,
        )

        cmds.setAttr(
            node + ".input2X",
            divisor,
        )

        self._connect_output(
            node + ".outputX",
            output,
        )

        return self._register(
            name,
            input1,
            output,
            [node],
        )

    # ======================================================
    # Add
    # ======================================================

    def add(
        self,
        name: str,
        inputs: list[str],
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "plusMinusAverage",
            name=f"{name}_ADD",
        )

        cmds.setAttr(
            node + ".operation",
            1,
        )

        for i, attr in enumerate(inputs):

            cmds.connectAttr(
                attr,
                f"{node}.input1D[{i}]",
                force=True,
            )

        self._connect_output(
            node + ".output1D",
            output,
        )

        return self._register(
            name,
            ",".join(inputs),
            output,
            [node],
        )

    # ======================================================
    # Subtract
    # ======================================================

    def subtract(
        self,
        name: str,
        inputs: list[str],
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "plusMinusAverage",
            name=f"{name}_SUB",
        )

        cmds.setAttr(
            node + ".operation",
            2,
        )

        for i, attr in enumerate(inputs):

            cmds.connectAttr(
                attr,
                f"{node}.input1D[{i}]",
                force=True,
            )

        self._connect_output(
            node + ".output1D",
            output,
        )

        return self._register(
            name,
            ",".join(inputs),
            output,
            [node],
        )

    # ======================================================
    # Clamp
    # ======================================================

    def clamp(
        self,
        name: str,
        input_attr: str,
        minimum: float,
        maximum: float,
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "clamp",
            name=f"{name}_CLAMP",
        )

        cmds.connectAttr(
            input_attr,
            node + ".inputR",
            force=True,
        )

        cmds.setAttr(
            node + ".minR",
            minimum,
        )

        cmds.setAttr(
            node + ".maxR",
            maximum,
        )

        self._connect_output(
            node + ".outputR",
            output,
        )

        return self._register(
            name,
            input_attr,
            output,
            [node],
        )

    # ======================================================
    # Reverse
    # ======================================================

    def reverse(
        self,
        name: str,
        input_attr: str,
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "reverse",
            name=f"{name}_REV",
        )

        cmds.connectAttr(
            input_attr,
            node + ".inputX",
            force=True,
        )

        self._connect_output(
            node + ".outputX",
            output,
        )

        return self._register(
            name,
            input_attr,
            output,
            [node],
        )

    # ======================================================
    # Remap Value
    # ======================================================

    def remap(
        self,
        name: str,
        input_attr: str,
        input_min: float,
        input_max: float,
        output_min: float,
        output_max: float,
        output: str,
    ) -> DriverNetwork:

        node = cmds.createNode(
            "remapValue",
            name=f"{name}_REMAP",
        )

        cmds.connectAttr(
            input_attr,
            node + ".inputValue",
            force=True,
        )

        cmds.setAttr(node + ".inputMin", input_min)
        cmds.setAttr(node + ".inputMax", input_max)
        cmds.setAttr(node + ".outputMin", output_min)
        cmds.setAttr(node + ".outputMax", output_max)

        self._connect_output(
            node + ".outValue",
            output,
        )

        return self._register(
            name,
            input_attr,
            output,
            [node],
        )

    # ======================================================
    # Blendshape Driver
    # ======================================================

    def create_blendshape_driver(
        self,
        controller_attribute: str,
        blendshape_attribute: str,
    ):

        self.connect(
            controller_attribute,
            blendshape_attribute,
        )

    # ======================================================
    # Joint Driver
    # ======================================================

    def create_joint_driver(
        self,
        controller_attribute: str,
        joint_attribute: str,
    ):

        self.connect(
            controller_attribute,
            joint_attribute,
        )

    # ======================================================
    # Delete
    # ======================================================

    def delete_network(
        self,
        name: str,
    ):

        network = self.networks.get(name)

        if not network:
            return

        for node in network.nodes:

            if cmds.objExists(node):
                cmds.delete(node)

        del self.networks[name]

    # ======================================================
    # Registry
    # ======================================================

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.networks

    # ------------------------------------------------------

    def get(
        self,
        name: str,
    ) -> DriverNetwork | None:

        return self.networks.get(name)

    # ------------------------------------------------------

    def list_networks(self) -> list[str]:

        return sorted(self.networks.keys())

    # ------------------------------------------------------

    def clear(self):

        for name in list(self.networks.keys()):
            self.delete_network(name)


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

driver_network = DriverNetworkBuilder()