"""
blendshapes/blendshape_delta.py

Blendshape Delta Engine for Maya.

This module is the mathematical backbone of the blendshape system. It handles
the computation, storage, manipulation, compression, reconstruction, and
validation of vertex deltas—the geometric differences between a base mesh
and one or more target meshes.

Every advanced blendshape feature (correctives, transfer, mirroring,
optimization, compression, ARKit retargeting, machine learning) depends on
accurate delta data. This module provides a reusable and extensible foundation
for all geometry-difference operations.

Responsibilities:
- Compute vertex deltas between two meshes.
- Store, retrieve, and manage delta sets.
- Apply deltas to reconstruct target meshes.
- Perform operations: scale, mirror, normalize, combine, average.
- Compress delta data (sparse storage, quantization, lossless/lossy).
- Validate delta integrity (vertex count, NaN, topology, compression).
- Provide diagnostics, statistics, and reports.

Mathematical Foundation:
    delta = target_position - base_position
    For each vertex: (dx, dy, dz)

Dependencies:
- blendshape_utils.py: shared math, mesh, and serialization helpers.
- blendshape_validator.py: mesh compatibility checks.
- blendshape_transfer.py: delta transfer between meshes (optional).
- NumPy: optional for accelerated vector math.

The module uses Maya's Python API and may optionally leverage NumPy
for performance in production environments.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Try importing NumPy for accelerated math
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# Maya imports
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    from pymel.core import PyNode, selected, ls, exists, currentTime, setKeyframe # type: ignore
    import pymel.core as pm # type: ignore
except ImportError:
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# Optional imports from other blendshape modules
try:
    from .blendshape_utils import MeshUtils, VectorUtils, SerializationUtils
except ImportError:
    class MeshUtils:
        @staticmethod
        def get_vertex_positions(mesh):
            return []
        @staticmethod
        def get_vertex_count(mesh):
            return 0
    VectorUtils = None
    SerializationUtils = None

try:
    from .blendshape_validator import BlendShapeValidator
except ImportError:
    class BlendShapeValidator:
        def validate_mesh(self, mesh):
            from dataclasses import dataclass
            @dataclass
            class DummyReport:
                is_valid = True
                errors = []
                warnings = []
            return DummyReport()

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class DeltaError(Exception):
    """Base exception for delta operations."""
    pass

class DeltaComputationError(DeltaError):
    """Raised when delta computation fails."""
    pass

class DeltaValidationError(DeltaError):
    """Raised when delta validation fails."""
    pass

class DeltaCompressionError(DeltaError):
    """Raised when compression/decompression fails."""
    pass

class DeltaNotFoundError(DeltaError):
    """Raised when a delta set is not found."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class DeltaFormat(Enum):
    """Storage format for delta data."""
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    COMPRESSED = "compressed"
    SPARSE = "sparse"
    BINARY = "binary"


class CompressionMode(Enum):
    """Compression modes for delta data."""
    NONE = "none"
    SPARSE = "sparse"           # Store only non-zero deltas
    QUANTIZED = "quantized"     # Quantize to lower precision
    LOSSLESS = "lossless"       # Lossless compression (e.g., zlib)
    LOSSY = "lossy"             # Lossy compression with tolerance


class MirrorMode(Enum):
    """Mirror modes for delta data."""
    X = "x"                     # Mirror across X axis
    Y = "y"                     # Mirror across Y axis
    Z = "z"                     # Mirror across Z axis
    TOPOLOGY = "topology"       # Mirror based on mesh topology (symmetry map)
    NAME_BASED = "name_based"   # Mirror based on naming convention (left/right)


class BlendMode(Enum):
    """Blending modes for combining deltas."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    AVERAGE = "average"
    MAXIMUM = "max"
    MINIMUM = "min"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class VertexDelta:
    """
    A single vertex delta (offset vector).
    """
    index: int
    offset: Tuple[float, float, float]  # (dx, dy, dz)

    def __post_init__(self):
        # Ensure offsets are finite
        if not all(math.isfinite(v) for v in self.offset):
            raise ValueError(f"Offset contains non-finite values: {self.offset}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "offset": list(self.offset),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VertexDelta:
        return cls(
            index=data["index"],
            offset=tuple(data["offset"]),
        )

    def magnitude(self) -> float:
        """Return the magnitude (length) of the delta vector."""
        dx, dy, dz = self.offset
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def is_zero(self, tolerance: float = 1e-8) -> bool:
        """Check if the delta is effectively zero."""
        return self.magnitude() < tolerance


@dataclass
class BlendshapeDelta:
    """
    A complete delta set for a blendshape target.
    """
    name: str
    vertex_count: int
    deltas: List[VertexDelta]
    base_mesh: Optional[str] = None
    target_mesh: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure all vertex indices are within bounds
        for d in self.deltas:
            if d.index < 0 or d.index >= self.vertex_count:
                raise ValueError(f"Vertex index {d.index} out of range (0-{self.vertex_count-1})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "vertex_count": self.vertex_count,
            "deltas": [d.to_dict() for d in self.deltas],
            "base_mesh": self.base_mesh,
            "target_mesh": self.target_mesh,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BlendshapeDelta:
        return cls(
            name=data["name"],
            vertex_count=data["vertex_count"],
            deltas=[VertexDelta.from_dict(d) for d in data.get("deltas", [])],
            base_mesh=data.get("base_mesh"),
            target_mesh=data.get("target_mesh"),
            metadata=data.get("metadata", {}),
        )

    def get_delta(self, index: int) -> Optional[VertexDelta]:
        """Get delta for a specific vertex index."""
        for d in self.deltas:
            if d.index == index:
                return d
        return None

    def is_zero(self, tolerance: float = 1e-8) -> bool:
        """Check if the entire delta set is effectively zero."""
        return all(d.is_zero(tolerance) for d in self.deltas)

    def get_active_count(self, tolerance: float = 1e-8) -> int:
        """Return the number of non-zero deltas."""
        return sum(1 for d in self.deltas if not d.is_zero(tolerance))


@dataclass
class SparseDelta:
    """
    A sparse representation of a delta set.
    Stores only non-zero deltas with their indices.
    """
    vertex_count: int
    deltas: Dict[int, Tuple[float, float, float]]  # index -> (dx, dy, dz)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vertex_count": self.vertex_count,
            "deltas": {str(k): list(v) for k, v in self.deltas.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SparseDelta:
        return cls(
            vertex_count=data["vertex_count"],
            deltas={int(k): tuple(v) for k, v in data.get("deltas", {}).items()},
        )


@dataclass
class CompressedDelta:
    """
    A compressed delta set.
    """
    format: DeltaFormat
    data: bytes
    vertex_count: int
    compression_mode: CompressionMode
    original_size: int
    compressed_size: int


@dataclass
class DeltaStatistics:
    """
    Statistics for a delta set or operation.
    """
    vertex_count: int = 0
    active_vertices: int = 0
    total_deltas: int = 0
    magnitude_min: float = 0.0
    magnitude_max: float = 0.0
    magnitude_mean: float = 0.0
    magnitude_std: float = 0.0
    compression_ratio: float = 1.0
    original_size_bytes: int = 0
    compressed_size_bytes: int = 0
    runtime_seconds: float = 0.0


@dataclass
class DeltaReport:
    """
    Diagnostic report for delta validation.
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    vertex_count: int = 0
    active_vertices: int = 0
    total_deltas: int = 0
    zero_deltas: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Delta Engine ----------------------------------------------

class BlendshapeDeltaEngine:
    """
    Main controller for all delta operations.
    """
    def __init__(self):
        self._validator = BlendShapeValidator()
        self._utils = MeshUtils() if MeshUtils else None
        self._last_stats: Optional[DeltaStatistics] = None
        self._last_report: Optional[DeltaReport] = None
        self._cache: Dict[str, BlendshapeDelta] = {}
        self._sparse_cache: Dict[str, SparseDelta] = {}

    # ---- Delta Computation ----

    def compute(
        self,
        base_mesh: str,
        target_mesh: str,
        name: str,
        compute_active_only: bool = True,
        tolerance: float = 1e-8,
        use_numpy: bool = True,
    ) -> BlendshapeDelta:
        """
        Compute the delta between two meshes.

        Args:
            base_mesh: The base mesh (transform or shape).
            target_mesh: The target mesh (transform or shape).
            name: Name for the delta set.
            compute_active_only: If True, only store non-zero deltas.
            tolerance: Tolerance for zero detection.
            use_numpy: Use NumPy for accelerated computation.

        Returns:
            BlendshapeDelta object containing the vertex offsets.

        Raises:
            DeltaComputationError: If computation fails.
        """
        start_time = time.time()

        # Validate meshes
        base_report = self._validator.validate_mesh(base_mesh)
        if not base_report.is_valid:
            raise DeltaComputationError(f"Base mesh invalid: {', '.join(base_report.errors)}")

        target_report = self._validator.validate_mesh(target_mesh)
        if not target_report.is_valid:
            raise DeltaComputationError(f"Target mesh invalid: {', '.join(target_report.errors)}")

        # Get vertex count
        base_count = self._get_vertex_count(base_mesh)
        target_count = self._get_vertex_count(target_mesh)

        if base_count != target_count:
            raise DeltaComputationError(f"Vertex count mismatch: base={base_count}, target={target_count}")

        # Get positions
        base_positions = self._get_vertex_positions(base_mesh)
        target_positions = self._get_vertex_positions(target_mesh)

        if len(base_positions) != base_count or len(target_positions) != target_count:
            raise DeltaComputationError("Failed to get vertex positions")

        # Compute deltas
        deltas = []
        if use_numpy and HAS_NUMPY:
            # NumPy accelerated computation
            np_base = np.array(base_positions, dtype=np.float32)
            np_target = np.array(target_positions, dtype=np.float32)
            np_delta = np_target - np_base
            # Find non-zero deltas if requested
            if compute_active_only:
                mask = np.linalg.norm(np_delta, axis=1) > tolerance
                indices = np.where(mask)[0]
                for idx in indices:
                    offset = tuple(np_delta[idx].tolist())
                    deltas.append(VertexDelta(index=int(idx), offset=offset))
            else:
                for idx, offset in enumerate(np_delta):
                    if any(abs(v) > tolerance for v in offset):
                        deltas.append(VertexDelta(index=idx, offset=tuple(offset.tolist())))
        else:
            # Python implementation (fallback)
            for idx in range(base_count):
                base = base_positions[idx]
                target = target_positions[idx]
                dx = target[0] - base[0]
                dy = target[1] - base[1]
                dz = target[2] - base[2]
                if compute_active_only and abs(dx) < tolerance and abs(dy) < tolerance and abs(dz) < tolerance:
                    continue
                deltas.append(VertexDelta(index=idx, offset=(dx, dy, dz)))

        # Create delta object
        delta = BlendshapeDelta(
            name=name,
            vertex_count=base_count,
            deltas=deltas,
            base_mesh=base_mesh,
            target_mesh=target_mesh,
            metadata={
                "computed_with_numpy": use_numpy and HAS_NUMPY,
                "active_only": compute_active_only,
                "tolerance": tolerance,
            }
        )

        # Cache
        self._cache[name] = delta

        # Statistics
        elapsed = time.time() - start_time
        self._last_stats = self._compute_statistics(delta)
        self._last_stats.runtime_seconds = elapsed

        return delta

    def compute_batch(
        self,
        base_mesh: str,
        target_meshes: Dict[str, str],
        compute_active_only: bool = True,
        tolerance: float = 1e-8,
        use_numpy: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, BlendshapeDelta]:
        """
        Compute deltas for multiple target meshes against a single base mesh.

        Args:
            base_mesh: The base mesh.
            target_meshes: Dict of name -> target_mesh_path.
            compute_active_only: If True, only store non-zero deltas.
            tolerance: Tolerance for zero detection.
            use_numpy: Use NumPy acceleration.
            progress_callback: Optional progress callback.

        Returns:
            Dict of name -> BlendshapeDelta.
        """
        results = {}
        total = len(target_meshes)
        for i, (name, target) in enumerate(target_meshes.items()):
            if progress_callback:
                progress_callback(i / total, f"Computing {name}")
            try:
                delta = self.compute(base_mesh, target, name, compute_active_only, tolerance, use_numpy)
                results[name] = delta
            except Exception as e:
                logger.error(f"Failed to compute delta for {name}: {e}")
                continue
        return results

    # ---- Delta Application (Reconstruction) ----

    def apply(
        self,
        base_mesh: str,
        delta: Union[BlendshapeDelta, str],
        output_mesh: Optional[str] = None,
        weight: float = 1.0,
        modify_in_place: bool = False,
    ) -> Optional[str]:
        """
        Apply a delta to a base mesh to reconstruct the target mesh.

        Args:
            base_mesh: The base mesh to apply to.
            delta: BlendshapeDelta object or name (cached).
            output_mesh: Name for the output mesh. If None, a new name is generated.
            weight: Scale factor for the delta.
            modify_in_place: If True, modify the base mesh in place.

        Returns:
            Name of the resulting mesh, or None if failed.
        """
        # Get delta object
        if isinstance(delta, str):
            delta = self.get(delta)
            if delta is None:
                raise DeltaNotFoundError(f"Delta '{delta}' not found")

        # Validate mesh exists
        if not cmds.objExists(base_mesh):
            raise DeltaComputationError(f"Base mesh '{base_mesh}' does not exist")

        # Get base mesh positions
        base_positions = self._get_vertex_positions(base_mesh)
        if len(base_positions) != delta.vertex_count:
            raise DeltaComputationError(f"Vertex count mismatch: base={len(base_positions)}, delta={delta.vertex_count}")

        # Apply deltas
        new_positions = list(base_positions)
        for d in delta.deltas:
            idx = d.index
            if idx >= len(new_positions):
                continue
            dx, dy, dz = d.offset
            new_positions[idx] = (
                new_positions[idx][0] + dx * weight,
                new_positions[idx][1] + dy * weight,
                new_positions[idx][2] + dz * weight,
            )

        # Create new mesh or modify existing
        if modify_in_place:
            # Modify the base mesh in place (requires Maya API)
            self._set_vertex_positions(base_mesh, new_positions)
            return base_mesh
        else:
            # Create a new mesh
            if output_mesh is None:
                output_mesh = f"{delta.name}_reconstructed"
            return self._create_mesh_from_positions(output_mesh, new_positions, base_mesh)

    # ---- Delta Operations ----

    def scale(self, delta: Union[BlendshapeDelta, str], scale: float) -> BlendshapeDelta:
        """
        Scale all delta vectors by a factor.
        """
        delta_obj = self._get_delta_obj(delta)
        new_deltas = []
        for d in delta_obj.deltas:
            dx, dy, dz = d.offset
            new_deltas.append(VertexDelta(
                index=d.index,
                offset=(dx * scale, dy * scale, dz * scale)
            ))
        return BlendshapeDelta(
            name=f"{delta_obj.name}_scaled",
            vertex_count=delta_obj.vertex_count,
            deltas=new_deltas,
            metadata={"original": delta_obj.name, "scale": scale}
        )

    def mirror(
        self,
        delta: Union[BlendshapeDelta, str],
        mode: MirrorMode = MirrorMode.X,
        symmetry_map: Optional[Dict[int, int]] = None,
    ) -> BlendshapeDelta:
        """
        Mirror delta across an axis or using topology symmetry.
        """
        delta_obj = self._get_delta_obj(delta)

        if mode == MirrorMode.X:
            # Mirror across X axis: dx = -dx, dy stays, dz stays
            new_deltas = []
            for d in delta_obj.deltas:
                dx, dy, dz = d.offset
                new_deltas.append(VertexDelta(
                    index=d.index,
                    offset=(-dx, dy, dz)
                ))
            # Note: this mirrors the vector, but the vertex index remains the same.
            # For proper mirroring, you also need to map indices to mirrored positions.
            # This is a simplified version.
            return BlendshapeDelta(
                name=f"{delta_obj.name}_mirrored_x",
                vertex_count=delta_obj.vertex_count,
                deltas=new_deltas,
                metadata={"original": delta_obj.name, "mirror_mode": "x"}
            )

        elif mode == MirrorMode.TOPOLOGY and symmetry_map:
            # Mirror using topology mapping: map vertex indices to mirror positions.
            # This requires a symmetry map that pairs left/right vertices.
            # We'll create a new delta by applying the symmetry map.
            new_deltas = []
            # We need to map each vertex to its mirror, and also mirror the vector components.
            for d in delta_obj.deltas:
                # Get the mirror index
                mirror_idx = symmetry_map.get(d.index)
                if mirror_idx is None:
                    continue
                dx, dy, dz = d.offset
                # Mirror across X (assuming left/right is X)
                new_deltas.append(VertexDelta(
                    index=mirror_idx,
                    offset=(-dx, dy, dz)
                ))
            return BlendshapeDelta(
                name=f"{delta_obj.name}_mirrored_topology",
                vertex_count=delta_obj.vertex_count,
                deltas=new_deltas,
                metadata={"original": delta_obj.name, "mirror_mode": "topology"}
            )

        else:
            raise ValueError(f"Unsupported mirror mode: {mode}")

    def blend(
        self,
        deltas: List[Union[BlendshapeDelta, str]],
        weights: Optional[List[float]] = None,
        mode: BlendMode = BlendMode.ADD,
    ) -> BlendshapeDelta:
        """
        Blend multiple deltas together.

        Args:
            deltas: List of delta objects or names.
            weights: Optional list of weights (must match deltas length).
            mode: Blend mode (ADD, AVERAGE, MAX, MIN, etc.)

        Returns:
            Blended delta set.
        """
        # Get delta objects
        delta_objs = [self._get_delta_obj(d) for d in deltas]
        if not delta_objs:
            raise ValueError("No deltas to blend")

        # Validate all have same vertex count
        vertex_count = delta_objs[0].vertex_count
        for d in delta_objs:
            if d.vertex_count != vertex_count:
                raise DeltaComputationError(f"Vertex count mismatch: {d.vertex_count} vs {vertex_count}")

        # Normalize weights
        if weights is None:
            weights = [1.0 / len(delta_objs)] * len(delta_objs)
        elif len(weights) != len(delta_objs):
            raise ValueError("Number of weights must match number of deltas")

        # Blend based on mode
        # We'll use a dictionary to accumulate per-vertex offsets
        if mode == BlendMode.ADD:
            # Sum weighted deltas
            accum = {}  # index -> (dx, dy, dz)
            for d_obj, w in zip(delta_objs, weights):
                for vd in d_obj.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    if idx not in accum:
                        accum[idx] = (0.0, 0.0, 0.0)
                    ax, ay, az = accum[idx]
                    accum[idx] = (ax + dx * w, ay + dy * w, az + dz * w)

        elif mode == BlendMode.AVERAGE:
            # Average weighted deltas
            accum = {}
            for d_obj, w in zip(delta_objs, weights):
                for vd in d_obj.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    if idx not in accum:
                        accum[idx] = (0.0, 0.0, 0.0, 0.0)  # sum, count
                    sx, sy, sz, count = accum[idx]
                    accum[idx] = (sx + dx * w, sy + dy * w, sz + dz * w, count + w)
            # Divide by total weight sum
            total_weight = sum(weights)
            if total_weight > 0:
                for idx in accum:
                    sx, sy, sz, count = accum[idx]
                    accum[idx] = (sx / total_weight, sy / total_weight, sz / total_weight)

        elif mode == BlendMode.MAXIMUM:
            # Take element-wise maximum (weighted by magnitude? We'll use weighted)
            accum = {}
            for d_obj, w in zip(delta_objs, weights):
                for vd in d_obj.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    mag = math.sqrt(dx*dx + dy*dy + dz*dz) * w
                    if idx not in accum or mag > accum[idx][3]:
                        accum[idx] = (dx * w, dy * w, dz * w, mag)

        elif mode == BlendMode.MINIMUM:
            # Take element-wise minimum
            accum = {}
            for d_obj, w in zip(delta_objs, weights):
                for vd in d_obj.deltas:
                    idx = vd.index
                    dx, dy, dz = vd.offset
                    mag = math.sqrt(dx*dx + dy*dy + dz*dz) * w
                    if idx not in accum or mag < accum[idx][3]:
                        accum[idx] = (dx * w, dy * w, dz * w, mag)

        else:
            raise ValueError(f"Unsupported blend mode: {mode}")

        # Build new deltas
        new_deltas = []
        for idx, (dx, dy, dz) in accum.items():
            # Clamp if needed (not clamping, just store)
            new_deltas.append(VertexDelta(index=idx, offset=(dx, dy, dz)))

        # Create name
        name = "_".join([d.name for d in delta_objs]) + f"_{mode.value}"

        return BlendshapeDelta(
            name=name,
            vertex_count=vertex_count,
            deltas=new_deltas,
            metadata={"blend_mode": mode.value, "sources": [d.name for d in delta_objs]},
        )

    def normalize(self, delta: Union[BlendshapeDelta, str]) -> BlendshapeDelta:
        """
        Normalize deltas so the maximum magnitude is 1.0.
        """
        delta_obj = self._get_delta_obj(delta)
        # Find max magnitude
        max_mag = 0.0
        for d in delta_obj.deltas:
            mag = d.magnitude()
            if mag > max_mag:
                max_mag = mag
        if max_mag == 0:
            return delta_obj
        scale = 1.0 / max_mag
        return self.scale(delta_obj, scale)

    # ---- Delta Compression ----

    def compress(
        self,
        delta: Union[BlendshapeDelta, str],
        mode: CompressionMode = CompressionMode.SPARSE,
        tolerance: float = 1e-8,
        quantize_bits: int = 16,
    ) -> CompressedDelta:
        """
        Compress a delta set.

        Args:
            delta: Delta object or name.
            mode: Compression mode.
            tolerance: Tolerance for zero detection (for sparse compression).
            quantize_bits: Bits for quantization (for lossy compression).

        Returns:
            CompressedDelta object.
        """
        delta_obj = self._get_delta_obj(delta)

        original_size = len(delta_obj.deltas) * 3 * 4  # float32 * 3

        if mode == CompressionMode.NONE:
            # Store as JSON (minimal)
            data = json.dumps(delta_obj.to_dict()).encode('utf-8')
            return CompressedDelta(
                format=DeltaFormat.FLOAT32,
                data=data,
                vertex_count=delta_obj.vertex_count,
                compression_mode=CompressionMode.NONE,
                original_size=original_size,
                compressed_size=len(data),
            )

        elif mode == CompressionMode.SPARSE:
            # Only store non-zero deltas
            sparse = []
            for d in delta_obj.deltas:
                if not d.is_zero(tolerance):
                    sparse.append(d)
            sparse_data = {
                "vertex_count": delta_obj.vertex_count,
                "deltas": [d.to_dict() for d in sparse],
            }
            data = json.dumps(sparse_data).encode('utf-8')
            return CompressedDelta(
                format=DeltaFormat.SPARSE,
                data=data,
                vertex_count=delta_obj.vertex_count,
                compression_mode=CompressionMode.SPARSE,
                original_size=original_size,
                compressed_size=len(data),
            )

        elif mode == CompressionMode.QUANTIZED:
            # Quantize to lower precision
            # We'll store as int16 with scaling
            # Find max magnitude
            max_mag = max([d.magnitude() for d in delta_obj.deltas]) if delta_obj.deltas else 1.0
            scale = (2 ** (quantize_bits - 1) - 1) / max_mag
            quantized = []
            for d in delta_obj.deltas:
                dx, dy, dz = d.offset
                qx = int(round(dx * scale))
                qy = int(round(dy * scale))
                qz = int(round(dz * scale))
                quantized.append({
                    "index": d.index,
                    "qx": qx,
                    "qy": qy,
                    "qz": qz,
                })
            quant_data = {
                "vertex_count": delta_obj.vertex_count,
                "scale": scale,
                "bits": quantize_bits,
                "deltas": quantized,
            }
            data = json.dumps(quant_data).encode('utf-8')
            return CompressedDelta(
                format=DeltaFormat.COMPRESSED,
                data=data,
                vertex_count=delta_obj.vertex_count,
                compression_mode=CompressionMode.QUANTIZED,
                original_size=original_size,
                compressed_size=len(data),
            )

        else:
            raise NotImplementedError(f"Compression mode {mode} not implemented")

    def decompress(self, compressed: CompressedDelta) -> BlendshapeDelta:
        """
        Decompress a compressed delta set.
        """
        if compressed.compression_mode == CompressionMode.NONE:
            data = json.loads(compressed.data.decode('utf-8'))
            return BlendshapeDelta.from_dict(data)

        elif compressed.compression_mode == CompressionMode.SPARSE:
            data = json.loads(compressed.data.decode('utf-8'))
            deltas = [VertexDelta.from_dict(d) for d in data["deltas"]]
            return BlendshapeDelta(
                name="decompressed",
                vertex_count=data["vertex_count"],
                deltas=deltas,
            )

        elif compressed.compression_mode == CompressionMode.QUANTIZED:
            data = json.loads(compressed.data.decode('utf-8'))
            scale = data["scale"]
            vertex_count = data["vertex_count"]
            deltas = []
            for item in data["deltas"]:
                dx = item["qx"] / scale
                dy = item["qy"] / scale
                dz = item["qz"] / scale
                deltas.append(VertexDelta(index=item["index"], offset=(dx, dy, dz)))
            return BlendshapeDelta(
                name="decompressed",
                vertex_count=vertex_count,
                deltas=deltas,
                metadata={"compressed_from": "quantized"},
            )

        else:
            raise NotImplementedError(f"Decompression for {compressed.compression_mode} not implemented")

    # ---- Delta Validation ----

    def validate(self, delta: Union[BlendshapeDelta, str]) -> DeltaReport:
        """
        Validate a delta set for integrity issues.
        """
        delta_obj = self._get_delta_obj(delta)
        report = DeltaReport(is_valid=True, vertex_count=delta_obj.vertex_count)

        # Check vertex indices
        seen = set()
        for d in delta_obj.deltas:
            if d.index < 0 or d.index >= delta_obj.vertex_count:
                report.errors.append(f"Vertex index {d.index} out of range [0, {delta_obj.vertex_count-1}]")
                report.is_valid = False
            if d.index in seen:
                report.errors.append(f"Duplicate vertex index {d.index}")
                report.is_valid = False
            seen.add(d.index)

            # Check for NaN/infinite
            dx, dy, dz = d.offset
            if not (math.isfinite(dx) and math.isfinite(dy) and math.isfinite(dz)):
                report.errors.append(f"Non-finite value at vertex {d.index}: ({dx}, {dy}, {dz})")
                report.is_valid = False

        report.total_deltas = len(delta_obj.deltas)
        report.active_vertices = len(delta_obj.deltas)
        report.zero_deltas = sum(1 for d in delta_obj.deltas if d.is_zero())

        return report

    # ---- Cache Management ----

    def add(self, delta: BlendshapeDelta) -> None:
        """Add a delta to the cache."""
        self._cache[delta.name] = delta

    def get(self, name: str) -> Optional[BlendshapeDelta]:
        """Get a delta from the cache."""
        return self._cache.get(name)

    def remove(self, name: str) -> None:
        """Remove a delta from the cache."""
        if name in self._cache:
            del self._cache[name]
        if name in self._sparse_cache:
            del self._sparse_cache[name]

    def clear(self) -> None:
        """Clear all cached deltas."""
        self._cache.clear()
        self._sparse_cache.clear()

    def list(self) -> List[str]:
        """List all cached delta names."""
        return list(self._cache.keys())

    # ---- Statistics ----

    def statistics(self, delta: Union[BlendshapeDelta, str]) -> DeltaStatistics:
        """Compute statistics for a delta set."""
        delta_obj = self._get_delta_obj(delta)
        return self._compute_statistics(delta_obj)

    def _compute_statistics(self, delta: BlendshapeDelta) -> DeltaStatistics:
        """Internal method to compute statistics."""
        stats = DeltaStatistics()
        stats.vertex_count = delta.vertex_count
        stats.total_deltas = len(delta.deltas)
        stats.active_vertices = len(delta.deltas)

        if delta.deltas:
            magnitudes = [d.magnitude() for d in delta.deltas]
            stats.magnitude_min = min(magnitudes)
            stats.magnitude_max = max(magnitudes)
            stats.magnitude_mean = sum(magnitudes) / len(magnitudes)
            # Standard deviation
            variance = sum((m - stats.magnitude_mean) ** 2 for m in magnitudes) / len(magnitudes)
            stats.magnitude_std = math.sqrt(variance)
        else:
            stats.magnitude_min = 0.0
            stats.magnitude_max = 0.0
            stats.magnitude_mean = 0.0
            stats.magnitude_std = 0.0

        return stats

    # ---- Utility Methods ----

    def _get_delta_obj(self, delta: Union[BlendshapeDelta, str]) -> BlendshapeDelta:
        """Helper to get a delta object from either a string or object."""
        if isinstance(delta, BlendshapeDelta):
            return delta
        elif isinstance(delta, str):
            cached = self.get(delta)
            if cached is not None:
                return cached
            raise DeltaNotFoundError(f"Delta '{delta}' not found in cache")
        else:
            raise TypeError(f"Expected BlendshapeDelta or str, got {type(delta)}")

    def _get_vertex_count(self, mesh: str) -> int:
        """Get vertex count of a mesh."""
        if cmds.nodeType(mesh) != 'mesh':
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if shapes:
                mesh = shapes[0]
        return cmds.polyEvaluate(mesh, vertex=True) or 0

    def _get_vertex_positions(self, mesh: str) -> List[Tuple[float, float, float]]:
        """Get vertex positions of a mesh."""
        if cmds.nodeType(mesh) != 'mesh':
            shapes = cmds.listRelatives(mesh, shapes=True) or []
            if shapes:
                mesh = shapes[0]
        # Use polyListComponentConversion to get vertex positions
        verts = cmds.polyListComponentConversion(mesh, toVertex=True)
        positions = cmds.xform(verts, q=True, ws=True, t=True)
        # positions is a flat list: [x1,y1,z1, x2,y2,z2, ...]
        return [(positions[i], positions[i+1], positions[i+2]) for i in range(0, len(positions), 3)]

    def _set_vertex_positions(self, mesh: str, positions: List[Tuple[float, float, float]]) -> None:
        """Set vertex positions of a mesh (modifies in place)."""
        # This is complex in Maya; for now, we'll implement a basic version
        # using `cmds.polyMoveVertex` or `cmds.xform` with component selection.
        # We'll use polyMoveVertex with relative offsets.
        # Since we have absolute positions, we need to move each vertex.
        # We'll compute deltas from current positions.
        current = self._get_vertex_positions(mesh)
        for idx, (cx, cy, cz) in enumerate(current):
            tx, ty, tz = positions[idx]
            dx, dy, dz = tx - cx, ty - cy, tz - cz
            if abs(dx) > 1e-6 or abs(dy) > 1e-6 or abs(dz) > 1e-6:
                # Move the vertex
                vert = f"{mesh}.vtx[{idx}]"
                cmds.polyMoveVertex(vert, x=dx, y=dy, z=dz, relative=True, ws=True)

    def _create_mesh_from_positions(self, name: str, positions: List[Tuple[float, float, float]], base_mesh: str) -> str:
        """Create a new mesh from vertex positions."""
        # We'll duplicate the base mesh and modify its vertices
        dup = cmds.duplicate(base_mesh, name=name)[0]
        self._set_vertex_positions(dup, positions)
        return dup

    # ---- Diagnostics ----

    def get_last_stats(self) -> Optional[DeltaStatistics]:
        """Return the last computed statistics."""
        return self._last_stats

    def get_last_report(self) -> Optional[DeltaReport]:
        """Return the last validation report."""
        return self._last_report

    def reset(self) -> None:
        """Reset internal state."""
        self._last_stats = None
        self._last_report = None

    # ---- Serialization ----

    def to_json(self, delta: Union[BlendshapeDelta, str]) -> str:
        """Serialize a delta to JSON."""
        delta_obj = self._get_delta_obj(delta)
        return json.dumps(delta_obj.to_dict(), indent=2)

    def from_json(self, data: str) -> BlendshapeDelta:
        """Deserialize a delta from JSON."""
        obj = json.loads(data)
        return BlendshapeDelta.from_dict(obj)

    def save_to_file(self, delta: Union[BlendshapeDelta, str], filepath: str) -> None:
        """Save a delta to a file."""
        delta_obj = self._get_delta_obj(delta)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(delta_obj.to_dict(), f, indent=2)

    def load_from_file(self, filepath: str) -> BlendshapeDelta:
        """Load a delta from a file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return BlendshapeDelta.from_dict(data)


# ---- Part 11: Utility Functions --------------------------------------

def compute_delta_stats(delta: BlendshapeDelta) -> Dict[str, Any]:
    """Compute a simplified statistics dictionary for a delta."""
    stats = {}
    stats["vertex_count"] = delta.vertex_count
    stats["total_deltas"] = len(delta.deltas)
    if delta.deltas:
        magnitudes = [d.magnitude() for d in delta.deltas]
        stats["min_magnitude"] = min(magnitudes)
        stats["max_magnitude"] = max(magnitudes)
        stats["mean_magnitude"] = sum(magnitudes) / len(magnitudes)
    return stats


def get_symmetry_map(mesh: str, axis: str = "x", tolerance: float = 0.001) -> Dict[int, int]:
    """
    Generate a symmetry map for a mesh across the specified axis.
    Returns dict mapping vertex index -> mirror vertex index.
    """
    if not cmds.objExists(mesh):
        return {}

    # Get vertex positions
    positions = []
    for i in range(cmds.polyEvaluate(mesh, vertex=True)):
        pos = cmds.xform(f"{mesh}.vtx[{i}]", q=True, ws=True, t=True)
        positions.append(pos)

    # Build map
    sym_map = {}
    used = set()

    for i, pos in enumerate(positions):
        if i in used:
            continue
        # Find mirror position
        if axis == "x":
            mirror_pos = (-pos[0], pos[1], pos[2])
        elif axis == "y":
            mirror_pos = (pos[0], -pos[1], pos[2])
        elif axis == "z":
            mirror_pos = (pos[0], pos[1], -pos[2])
        else:
            continue

        # Find vertex closest to mirror position
        best_idx = None
        best_dist = float('inf')
        for j, pos2 in enumerate(positions):
            if j == i or j in used:
                continue
            dist = math.sqrt(
                (mirror_pos[0] - pos2[0])**2 +
                (mirror_pos[1] - pos2[1])**2 +
                (mirror_pos[2] - pos2[2])**2
            )
            if dist < best_dist:
                best_dist = dist
                best_idx = j

        if best_idx is not None and best_dist < tolerance:
            sym_map[i] = best_idx
            sym_map[best_idx] = i
            used.add(i)
            used.add(best_idx)

    return sym_map


# ---- Part 12: Public API -----------------------------------------------

__all__ = [
    "BlendshapeDeltaEngine",
    "BlendshapeDelta",
    "VertexDelta",
    "SparseDelta",
    "CompressedDelta",
    "DeltaStatistics",
    "DeltaReport",
    "DeltaFormat",
    "CompressionMode",
    "MirrorMode",
    "BlendMode",
    "DeltaError",
    "DeltaComputationError",
    "DeltaValidationError",
    "DeltaCompressionError",
    "DeltaNotFoundError",
    "compute_delta_stats",
    "get_symmetry_map",
]