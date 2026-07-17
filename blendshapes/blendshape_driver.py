"""
blendshapes/blendshape_driver.py

Blendshape Driver System for Maya.

This module connects blendshapes to animation controls, joints, custom attributes,
expressions, constraints, SDKs (Set Driven Keys), matrices, ARKit coefficients,
Live Link streams, and procedural systems. It controls how blendshapes are driven
during animation and real-time performance.

Responsibilities:
- Connect controller attributes to blendshape weights.
- Drive blendshapes via joint rotations/translations.
- Create Set Driven Key (SDK) relationships.
- Use matrix nodes for advanced transform-based driving.
- Build expression and utility-node driver networks.
- Connect ARKit 52-shape coefficients to blendshapes.
- Support live data streams (Live Link, Faceware, etc.).
- Evaluate the entire driver network efficiently.
- Provide diagnostics, statistics, and validation.

Dependencies:
- blendshape_weights.py: Apply weights.
- blendshape_validator.py: Validate drivers.
- blendshape_utils.py: Shared utilities.
- blendshape_pose.py: Pose-space drivers.
- animation/: Keyframes, constraints, baking, layers.
- rig/: Controller and joint definitions.
- blendshapes/arkit/: ARKit mapping and calibration.

The module is Maya-independent in interface but uses Maya commands internally.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable

# Maya imports (with fallback for testing)
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists, currentTime # type: ignore
    import pymel.core as pm # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Import blendshape exceptions (centralized)
try:
    from .blendshape_exceptions import (
        BlendshapeError,
        BlendshapeCreationError,
        BlendshapeNodeError,
        TargetNotFoundError,
        MeshNotFoundError,
        InvalidWeightError,
        TransferError,
        ValidationError,
    )
except ImportError:
    # Fallback exceptions if not available
    class BlendshapeError(Exception): pass
    class BlendshapeCreationError(BlendshapeError): pass
    class BlendshapeNodeError(BlendshapeError): pass
    class TargetNotFoundError(BlendshapeError): pass
    class MeshNotFoundError(BlendshapeError): pass
    class InvalidWeightError(BlendshapeError): pass
    class TransferError(BlendshapeError): pass
    class ValidationError(BlendshapeError): pass

# Local imports (with fallbacks)
try:
    from .blendshape_utils import (
        get_shape_node, get_mesh_vertex_count, get_mesh_vertex_positions,
        get_blendshape_targets, get_blendshape_weight, set_blendshape_weight,
        clamp, lerp, sanitize_name, generate_unique_name,
        remove_namespace, add_namespace, Timer, ProgressTracker,
        dict_to_json, json_to_dict, hash_data, checksum_mesh
    )
except ImportError:
    # Minimal fallback
    def get_shape_node(x): return x
    def get_mesh_vertex_count(x): return 0
    def get_mesh_vertex_positions(x): return []
    def get_blendshape_targets(n): return []
    def get_blendshape_weight(n,t): return 0.0
    def set_blendshape_weight(n,t,v): pass
    def clamp(a,b,c): return max(b, min(a, c))
    def lerp(a,b,t): return a + (b-a)*t
    def sanitize_name(n): return n
    def generate_unique_name(n, existing): return n
    def remove_namespace(n): return n
    def add_namespace(n, ns): return n
    class Timer: pass
    class ProgressTracker: pass
    def dict_to_json(d, indent=2): return "{}"
    def json_to_dict(s): return {}
    def hash_data(d): return ""
    def checksum_mesh(m): return ""

try:
    from .blendshape_weights import WeightManager
except ImportError:
    WeightManager = None

try:
    from .blendshape_validator import BlendshapeValidator, ValidationLevel
except ImportError:
    BlendshapeValidator = None
    ValidationLevel = None

try:
    from .blendshape_pose import PoseManager
except ImportError:
    PoseManager = None

try:
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
except ImportError:
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)


# ---- Part 2: Constants & Enumerations --------------------------------

class DriverType(Enum):
    """Types of driver sources."""
    ATTRIBUTE = "attribute"          # Custom attribute on a control
    CONTROLLER = "controller"        # Transform attribute of a controller
    JOINT = "joint"                  # Joint rotation/translation
    SDK = "sdk"                      # Set Driven Key relationship
    EXPRESSION = "expression"        # Maya expression node
    NODE = "node"                    # Any Maya node (utility node)
    MATRIX = "matrix"                # Matrix-based driving
    ARKIT = "arkit"                  # ARKit coefficient
    LIVELINK = "livelink"            # Live Link stream (Faceware, etc.)
    PYTHON = "python"                # Python callback
    CUSTOM = "custom"                # Custom driver


class EvaluationMode(Enum):
    """How the driver network is evaluated."""
    DIRECT = "direct"               # Directly set attribute
    DG = "dg"                       # Through Maya's dependency graph
    PARALLEL = "parallel"           # Parallel evaluation (Maya 2016+)
    GPU = "gpu"                     # GPU evaluation (experimental)
    MANUAL = "manual"               # Manual evaluation (via script)


class DriverSpace(Enum):
    """Space in which the driver operates."""
    LOCAL = "local"
    WORLD = "world"
    OBJECT = "object"
    CUSTOM = "custom"


class BlendMode(Enum):
    """Blending mode for multiple drivers affecting the same target."""
    OVERRIDE = "override"           # Last driver wins
    ADDITIVE = "additive"           # Sum of all drivers
    MULTIPLY = "multiply"           # Product of all drivers
    MAX = "max"                     # Maximum value
    MIN = "min"                     # Minimum value
    AVERAGE = "average"             # Weighted average


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class DriverDefinition:
    """
    Definition of a single driver connection.
    """
    name: str
    source: str                # Maya attribute path (e.g., 'ctrl.tx')
    destination: str           # Blendshape target name (or full attr path)
    driver_type: DriverType = DriverType.CONTROLLER
    multiplier: float = 1.0
    offset: float = 0.0
    clamp_min: Optional[float] = None
    clamp_max: Optional[float] = None
    remap_input_min: Optional[float] = None
    remap_input_max: Optional[float] = None
    remap_output_min: Optional[float] = None
    remap_output_max: Optional[float] = None
    blend_mode: BlendMode = BlendMode.ADDITIVE
    space: DriverSpace = DriverSpace.WORLD
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, value: float) -> float:
        """Apply multiplier, offset, clamp, and remap to an input value."""
        # Apply offset and multiplier
        result = value * self.multiplier + self.offset
        # Apply remap if defined
        if self.remap_input_min is not None and self.remap_input_max is not None:
            if self.remap_input_max != self.remap_input_min:
                t = (result - self.remap_input_min) / (self.remap_input_max - self.remap_input_min)
                t = clamp(t, 0.0, 1.0)
                if self.remap_output_min is not None and self.remap_output_max is not None:
                    result = lerp(self.remap_output_min, self.remap_output_max, t)
        # Clamp
        if self.clamp_min is not None:
            result = max(result, self.clamp_min)
        if self.clamp_max is not None:
            result = min(result, self.clamp_max)
        return result


@dataclass
class DriverConnection:
    """
    A connection between one driver and one destination with evaluation logic.
    """
    driver_def: DriverDefinition
    source_node: str
    source_attr: str
    dest_node: str
    dest_attr: str
    weight_manager: Optional[WeightManager] = None


@dataclass
class DriverNetwork:
    """
    A network of driver connections.
    """
    name: str
    connections: List[DriverConnection] = field(default_factory=list)
    evaluation_mode: EvaluationMode = EvaluationMode.DG
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriverStatistics:
    """Statistics for driver system."""
    total_drivers: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    active_drivers: int = 0
    disabled_drivers: int = 0
    blendshape_targets_affected: int = 0


@dataclass
class DriverReport:
    """Diagnostic report for driver network."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    network_count: int = 0
    driver_count: int = 0
    evaluation_time_ms: float = 0.0


# ---- Part 4: Driver Manager --------------------------------------------

class BlendshapeDriver:
    """
    Main controller for driving blendshapes from various sources.
    """
    def __init__(self):
        self._weight_manager = WeightManager() if WeightManager else None
        self._validator = BlendshapeValidator() if BlendshapeValidator else None
        self._pose_manager = PoseManager() if PoseManager else None
        self._networks: Dict[str, DriverNetwork] = {}
        self._driver_defs: Dict[str, DriverDefinition] = {}
        self._last_report: Optional[DriverReport] = None
        self._last_stats: Optional[DriverStatistics] = None

    # ---- Main Management ----

    def create_network(self, name: str) -> DriverNetwork:
        """Create a new driver network."""
        if name in self._networks:
            raise BlendshapeError(f"Driver network '{name}' already exists")
        network = DriverNetwork(name=name)
        self._networks[name] = network
        return network

    def remove_network(self, name: str) -> None:
        """Remove a driver network."""
        if name not in self._networks:
            raise BlendshapeError(f"Driver network '{name}' not found")
        del self._networks[name]

    def add_connection(self, network_name: str, connection: DriverConnection) -> None:
        """Add a connection to a network."""
        if network_name not in self._networks:
            raise BlendshapeError(f"Network '{network_name}' not found")
        self._networks[network_name].connections.append(connection)

    def remove_connection(self, network_name: str, index: int) -> None:
        """Remove a connection by index."""
        if network_name not in self._networks:
            raise BlendshapeError(f"Network '{network_name}' not found")
        if index < 0 or index >= len(self._networks[network_name].connections):
            raise BlendshapeError(f"Connection index {index} out of range")
        del self._networks[network_name].connections[index]

    def get_network(self, name: str) -> Optional[DriverNetwork]:
        return self._networks.get(name)

    def list_networks(self) -> List[str]:
        return list(self._networks.keys())

    # ---- Driver Creation Methods ----

    def connect_controller(
        self,
        target_blendshape: str,
        controller_attr: str,
        multiplier: float = 1.0,
        offset: float = 0.0,
        clamp_min: Optional[float] = None,
        clamp_max: Optional[float] = None,
        remap_input: Optional[Tuple[float, float]] = None,
        remap_output: Optional[Tuple[float, float]] = None,
        network_name: str = "Default",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Connect a controller attribute (transform or custom attr) to a blendshape target.

        Args:
            target_blendshape: Name of the blendshape target (or full attr path).
            controller_attr: Maya attribute path (e.g., 'CTRL_head.tx').
            multiplier: Scale factor.
            offset: Additive offset.
            clamp_min/max: Clamp the final value.
            remap_input/remap_output: Optional remapping ranges.
            network_name: Network to add this driver to.
            blend_mode: How this driver blends with others.

        Returns:
            DriverDefinition created.
        """
        if not cmds.objExists(controller_attr):
            raise MeshNotFoundError(f"Controller attribute '{controller_attr}' not found")

        # Determine destination attribute
        dest_attr = self._resolve_blendshape_target(target_blendshape)

        # Create driver definition
        name = sanitize_name(f"{controller_attr}_to_{target_blendshape}")
        defn = DriverDefinition(
            name=name,
            source=controller_attr,
            destination=dest_attr,
            driver_type=DriverType.CONTROLLER,
            multiplier=multiplier,
            offset=offset,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
            remap_input_min=remap_input[0] if remap_input else None,
            remap_input_max=remap_input[1] if remap_input else None,
            remap_output_min=remap_output[0] if remap_output else None,
            remap_output_max=remap_output[1] if remap_output else None,
            blend_mode=blend_mode,
        )
        self._driver_defs[name] = defn

        # Build connection
        src_node, src_attr = self._split_attr(controller_attr)
        dest_node, dest_attr = self._split_attr(dest_attr)
        conn = DriverConnection(
            driver_def=defn,
            source_node=src_node,
            source_attr=src_attr,
            dest_node=dest_node,
            dest_attr=dest_attr,
            weight_manager=self._weight_manager,
        )

        # Add to network
        if network_name not in self._networks:
            self.create_network(network_name)
        self.add_connection(network_name, conn)

        logger.debug(f"Connected controller {controller_attr} -> {target_blendshape}")
        return defn

    def connect_joint(
        self,
        target_blendshape: str,
        joint_name: str,
        attribute: str = 'rx',  # 'tx', 'ty', 'tz', 'rx', 'ry', 'rz'
        multiplier: float = 1.0,
        offset: float = 0.0,
        clamp_min: Optional[float] = None,
        clamp_max: Optional[float] = None,
        space: DriverSpace = DriverSpace.LOCAL,
        network_name: str = "Default",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Drive a blendshape from a joint's transform attribute.
        """
        if not cmds.objExists(joint_name):
            raise MeshNotFoundError(f"Joint '{joint_name}' not found")
        if cmds.nodeType(joint_name) != 'joint':
            raise BlendshapeError(f"'{joint_name}' is not a joint")
        full_attr = f"{joint_name}.{attribute}"
        if not cmds.objExists(full_attr):
            raise BlendshapeError(f"Attribute '{full_attr}' not found on joint '{joint_name}'")

        return self.connect_controller(
            target_blendshape,
            full_attr,
            multiplier=multiplier,
            offset=offset,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
            network_name=network_name,
            blend_mode=blend_mode,
        )

    def create_sdk(
        self,
        target_blendshape: str,
        driver_attr: str,
        driven_attr: str,
        driver_values: List[float],
        driven_values: List[float],
        interpolation: str = "linear",
        network_name: str = "Default",
    ) -> DriverDefinition:
        """
        Create a Set Driven Key (SDK) relationship between a driver attribute
        and a driven blendshape weight.

        Args:
            target_blendshape: The blendshape target name.
            driver_attr: The driver attribute (e.g., 'CTRL_smile.tx').
            driven_attr: The driven attribute (e.g., 'blendShapeNode.mouthSmileLeft').
            driver_values: List of driver values (keys).
            driven_values: List of driven values (weights at each key).
            interpolation: Interpolation type ('linear', 'spline', 'clamped').
            network_name: Network to add this to.

        Returns:
            DriverDefinition describing the connection.
        """
        # Ensure driver and driven attributes exist
        if not cmds.objExists(driver_attr):
            raise MeshNotFoundError(f"Driver attribute '{driver_attr}' not found")
        if not cmds.objExists(driven_attr):
            # Try to resolve blendshape target
            driven_attr = self._resolve_blendshape_target(target_blendshape)
            if not cmds.objExists(driven_attr):
                raise TargetNotFoundError(f"Driven attribute '{driven_attr}' not found")

        # Create the SDK using Maya's setDrivenKeyframe
        # First, set the driver attribute to each value and set driven key
        for dv, sv in zip(driver_values, driven_values):
            cmds.setAttr(driver_attr, dv)
            cmds.setDrivenKeyframe(driven_attr, currentDriver=driver_attr, value=sv)

        # Create driver definition
        name = sanitize_name(f"SDK_{driver_attr}_to_{target_blendshape}")
        defn = DriverDefinition(
            name=name,
            source=driver_attr,
            destination=driven_attr,
            driver_type=DriverType.SDK,
            multiplier=1.0,
            offset=0.0,
            metadata={"driver_values": driver_values, "driven_values": driven_values, "interpolation": interpolation},
        )
        self._driver_defs[name] = defn

        # Build connection
        src_node, src_attr = self._split_attr(driver_attr)
        dest_node, dest_attr = self._split_attr(driven_attr)
        conn = DriverConnection(
            driver_def=defn,
            source_node=src_node,
            source_attr=src_attr,
            dest_node=dest_node,
            dest_attr=dest_attr,
            weight_manager=self._weight_manager,
        )

        # Add to network
        if network_name not in self._networks:
            self.create_network(network_name)
        self.add_connection(network_name, conn)

        logger.debug(f"Created SDK: {driver_attr} -> {target_blendshape}")
        return defn

    def connect_arkit(
        self,
        arkit_channel: str,
        blendshape_target: str,
        multiplier: float = 1.0,
        offset: float = 0.0,
        calibration_profile: Optional[str] = None,
        network_name: str = "ARKit",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Connect an ARKit coefficient to a blendshape target.
        This is a convenience wrapper; it can also handle calibration.

        Args:
            arkit_channel: Name of ARKit channel (e.g., 'jawOpen').
            blendshape_target: Blendshape target to drive.
            multiplier: Scale factor.
            offset: Offset.
            calibration_profile: Optional calibration profile name.
            network_name: Network to add to.
            blend_mode: Blend mode.

        Returns:
            DriverDefinition.
        """
        # Ensure ARKit channel exists (by checking against known set)
        if arkit_channel not in ARKIT_SET:
            logger.warning(f"ARKit channel '{arkit_channel}' not in standard ARKit list; continuing anyway")

        # In a real implementation, we would have a source node for ARKit data.
        # For now, we'll use a placeholder: assume there is an ARKit root node
        # with attributes for each channel. We'll create a dummy attribute if needed.
        # In a production system, this could be a custom node or live link input.
        arkit_node = "ARKitInput"  # This would be created by the live link module
        if not cmds.objExists(arkit_node):
            # Create a dummy node for demonstration
            cmds.createNode('transform', name=arkit_node)
            # Add attributes for each ARKit channel
            for ch in ARKIT_BLENDSHAPES:
                if not cmds.objExists(f"{arkit_node}.{ch}"):
                    cmds.addAttr(arkit_node, longName=ch, attributeType='float', min=0, max=1, defaultValue=0)

        driver_attr = f"{arkit_node}.{arkit_channel}"
        dest_attr = self._resolve_blendshape_target(blendshape_target)

        return self.connect_controller(
            blendshape_target,
            driver_attr,
            multiplier=multiplier,
            offset=offset,
            network_name=network_name,
            blend_mode=blend_mode,
        )

    def connect_live(
        self,
        blendshape_target: str,
        stream_name: str,
        channel: str,
        multiplier: float = 1.0,
        offset: float = 0.0,
        network_name: str = "Live",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Connect a live data stream channel to a blendshape target.

        Args:
            blendshape_target: Target blendshape.
            stream_name: Name of the live stream (e.g., 'LiveLink', 'Faceware').
            channel: Channel name within the stream.
            multiplier, offset: Scaling/offset.
            network_name: Network to add to.
            blend_mode: Blend mode.

        Returns:
            DriverDefinition.
        """
        # In production, this would interface with the live stream system.
        # We'll create a placeholder node for the stream.
        stream_node = f"LiveStream_{stream_name}"
        if not cmds.objExists(stream_node):
            cmds.createNode('transform', name=stream_node)
            # Add channel attribute
            if not cmds.objExists(f"{stream_node}.{channel}"):
                cmds.addAttr(stream_node, longName=channel, attributeType='float', min=0, max=1, defaultValue=0)

        driver_attr = f"{stream_node}.{channel}"
        dest_attr = self._resolve_blendshape_target(blendshape_target)

        return self.connect_controller(
            blendshape_target,
            driver_attr,
            multiplier=multiplier,
            offset=offset,
            network_name=network_name,
            blend_mode=blend_mode,
        )

    def connect_matrix(
        self,
        blendshape_target: str,
        source_matrix: str,  # Node name of a matrix output
        multiplier: float = 1.0,
        offset: float = 0.0,
        network_name: str = "Default",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Drive a blendshape from a matrix node output (e.g., from decomposeMatrix).
        This is more advanced and used in modern rigging.

        Args:
            blendshape_target: Target blendshape.
            source_matrix: Matrix node name that provides an output value (like '.outputX').
            multiplier, offset: Scaling/offset.
            network_name: Network to add to.
            blend_mode: Blend mode.

        Returns:
            DriverDefinition.
        """
        # Source matrix could be a compound attribute; we'll use a simple float attribute.
        # In practice, you'd extract a component of the matrix.
        if not cmds.objExists(source_matrix):
            raise MeshNotFoundError(f"Matrix source '{source_matrix}' not found")
        # Assume the node has an attribute 'outputX' for simplicity.
        if cmds.objExists(f"{source_matrix}.outputX"):
            driver_attr = f"{source_matrix}.outputX"
        else:
            # Fallback: use the first float attribute
            attrs = cmds.listAttr(source_matrix, scalar=True) or []
            if attrs:
                driver_attr = f"{source_matrix}.{attrs[0]}"
            else:
                raise BlendshapeError(f"No scalar attributes found on '{source_matrix}'")
        dest_attr = self._resolve_blendshape_target(blendshape_target)
        return self.connect_controller(
            blendshape_target,
            driver_attr,
            multiplier=multiplier,
            offset=offset,
            network_name=network_name,
            blend_mode=blend_mode,
        )

    def connect_expression(
        self,
        blendshape_target: str,
        expression: str,
        network_name: str = "Default",
        blend_mode: BlendMode = BlendMode.ADDITIVE,
    ) -> DriverDefinition:
        """
        Connect a Maya expression node's output to a blendshape target.
        The expression node must have a float output attribute.

        Args:
            blendshape_target: Target blendshape.
            expression: Name of the expression node.
            network_name: Network to add to.
            blend_mode: Blend mode.

        Returns:
            DriverDefinition.
        """
        if not cmds.objExists(expression):
            raise MeshNotFoundError(f"Expression node '{expression}' not found")
        # Assume expression node has an output attribute named 'out'
        if cmds.objExists(f"{expression}.out"):
            driver_attr = f"{expression}.out"
        else:
            # Search for float attributes
            attrs = cmds.listAttr(expression, scalar=True) or []
            if attrs:
                driver_attr = f"{expression}.{attrs[0]}"
            else:
                raise BlendshapeError(f"No suitable output attribute on expression '{expression}'")
        dest_attr = self._resolve_blendshape_target(blendshape_target)
        return self.connect_controller(
            blendshape_target,
            driver_attr,
            multiplier=1.0,
            offset=0.0,
            network_name=network_name,
            blend_mode=blend_mode,
        )

    # ---- Evaluation ----

    def evaluate(self, network_name: str) -> None:
        """
        Evaluate all drivers in a network and apply to blendshape weights.
        """
        if network_name not in self._networks:
            raise BlendshapeError(f"Network '{network_name}' not found")
        network = self._networks[network_name]
        for conn in network.connections:
            if not conn.driver_def.enabled:
                continue
            # Get source value
            try:
                source_val = cmds.getAttr(f"{conn.source_node}.{conn.source_attr}")
            except:
                logger.warning(f"Failed to get source attribute {conn.source_node}.{conn.source_attr}")
                continue
            # Apply driver logic
            processed_val = conn.driver_def.evaluate(source_val)
            # Apply to destination
            try:
                if conn.dest_node and conn.dest_attr:
                    # Direct set on blendshape attribute
                    cmds.setAttr(f"{conn.dest_node}.{conn.dest_attr}", processed_val)
                else:
                    # Use weight manager
                    if conn.weight_manager:
                        conn.weight_manager.set_weight(conn.dest_attr, processed_val)
                    else:
                        # Fallback: set directly if we know the full attr
                        cmds.setAttr(conn.driver_def.destination, processed_val)
            except Exception as e:
                logger.error(f"Failed to set destination {conn.driver_def.destination}: {e}")

    def evaluate_all(self) -> None:
        """Evaluate all networks."""
        for name in self._networks:
            self.evaluate(name)

    def rebuild(self, network_name: str) -> None:
        """Rebuild a network (reconnect nodes if needed)."""
        # For now, just re-evaluate
        self.evaluate(network_name)

    # ---- Utility ----

    def _resolve_blendshape_target(self, target: str) -> str:
        """
        Resolve a blendshape target name to a full attribute path.
        If target is already a full path (node.attr), return it.
        Otherwise, find a blendshape node that has this target and return node.target.
        Raises TargetNotFoundError if not found.
        """
        if '.' in target:
            # Assume it's already a full attribute
            if cmds.objExists(target):
                return target
            else:
                raise TargetNotFoundError(f"Attribute '{target}' not found")
        # Search for a blendshape node that has this target
        bs_nodes = cmds.ls(type='blendShape') or []
        for node in bs_nodes:
            targets = get_blendshape_targets(node)
            if target in targets:
                return f"{node}.{target}"
        # Not found; raise error
        raise TargetNotFoundError(f"Blendshape target '{target}' not found in any blendshape node")

    def _split_attr(self, attr_path: str) -> Tuple[str, str]:
        """Split a full attribute path into node and attr."""
        parts = attr_path.rsplit('.', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return attr_path, ""

    # ---- Diagnostics and Statistics ----

    def get_statistics(self) -> DriverStatistics:
        stats = DriverStatistics()
        total = 0
        by_type = {}
        active = 0
        disabled = 0
        targets = set()
        for network in self._networks.values():
            for conn in network.connections:
                total += 1
                t = conn.driver_def.driver_type.value
                by_type[t] = by_type.get(t, 0) + 1
                if conn.driver_def.enabled:
                    active += 1
                else:
                    disabled += 1
                targets.add(conn.driver_def.destination)
        stats.total_drivers = total
        stats.by_type = by_type
        stats.active_drivers = active
        stats.disabled_drivers = disabled
        stats.blendshape_targets_affected = len(targets)
        self._last_stats = stats
        return stats

    def diagnose(self) -> DriverReport:
        report = DriverReport(success=True)
        report.network_count = len(self._networks)
        total_drivers = 0
        for network in self._networks.values():
            total_drivers += len(network.connections)
            for conn in network.connections:
                # Check source exists
                if not cmds.objExists(f"{conn.source_node}.{conn.source_attr}"):
                    report.errors.append(f"Source attribute missing: {conn.source_node}.{conn.source_attr}")
                    report.success = False
                # Check destination exists
                if conn.dest_node and not cmds.objExists(f"{conn.dest_node}.{conn.dest_attr}"):
                    report.errors.append(f"Destination attribute missing: {conn.dest_node}.{conn.dest_attr}")
                    report.success = False
                elif not conn.dest_node and not cmds.objExists(conn.driver_def.destination):
                    report.errors.append(f"Destination attribute missing: {conn.driver_def.destination}")
                    report.success = False
        report.driver_count = total_drivers
        self._last_report = report
        return report

    # ---- Serialization ----

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "networks": {},
            "driver_defs": {},
        }
        for name, network in self._networks.items():
            network_data = {
                "name": network.name,
                "evaluation_mode": network.evaluation_mode.value,
                "connections": [],
            }
            for conn in network.connections:
                conn_data = {
                    "driver_def": conn.driver_def.name,
                    "source_node": conn.source_node,
                    "source_attr": conn.source_attr,
                    "dest_node": conn.dest_node,
                    "dest_attr": conn.dest_attr,
                }
                network_data["connections"].append(conn_data)
            result["networks"][name] = network_data

        for name, defn in self._driver_defs.items():
            result["driver_defs"][name] = defn.__dict__
        return result

    def from_dict(self, data: Dict[str, Any]) -> None:
        # Reconstruct driver definitions
        self._driver_defs = {}
        for name, def_data in data.get("driver_defs", {}).items():
            # Remove 'driver_type' and 'blend_mode' from dict and convert enums
            # For simplicity, we'll use the dataclass directly if possible.
            # In practice, this would require converting string values back to enums.
            # This is a placeholder.
            pass
        # Rebuild networks
        self._networks = {}
        for name, net_data in data.get("networks", {}).items():
            network = DriverNetwork(name=name)
            # Add connections (simplified)
            self._networks[name] = network


# ---- Part 14: Utilities ------------------------------------------------

def find_drivers_for_target(blendshape_target: str, driver: BlendshapeDriver) -> List[DriverConnection]:
    """Find all driver connections that affect a specific blendshape target."""
    results = []
    for network in driver._networks.values():
        for conn in network.connections:
            if conn.driver_def.destination == blendshape_target or \
               conn.dest_attr == blendshape_target or \
               conn.driver_def.destination.endswith(f".{blendshape_target}"):
                results.append(conn)
    return results


def enable_driver(driver: BlendshapeDriver, network_name: str, driver_name: str, enable: bool = True) -> None:
    """Enable or disable a specific driver by name."""
    if network_name not in driver._networks:
        raise BlendshapeError(f"Network '{network_name}' not found")
    network = driver._networks[network_name]
    for conn in network.connections:
        if conn.driver_def.name == driver_name:
            conn.driver_def.enabled = enable
            return
    raise BlendshapeError(f"Driver '{driver_name}' not found in network '{network_name}'")


# ---- Part 15: Public API -----------------------------------------------

__all__ = [
    "BlendshapeDriver",
    "DriverDefinition",
    "DriverConnection",
    "DriverNetwork",
    "DriverStatistics",
    "DriverReport",
    "DriverType",
    "EvaluationMode",
    "DriverSpace",
    "BlendMode",
    "find_drivers_for_target",
    "enable_driver",
]