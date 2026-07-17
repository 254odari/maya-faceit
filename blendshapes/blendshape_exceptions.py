"""
blendshapes/blendshape_exceptions.py

Centralized Exception Hierarchy for the Blendshape Subsystem.

This module defines all exceptions raised by blendshape-related modules:
creation, delta computation, transfer, export, validation, ARKit, etc.
Every blendshape module should raise exceptions defined here rather than
generic Exception, RuntimeError, or ValueError.

This provides:
- Consistent error handling across the subsystem.
- Easier debugging with meaningful exception types.
- Better UI error reporting.
- Cleaner logging with error codes and context.
- Reliable API behavior for callers.
- Better unit testing with explicit exception expectations.

The module is lightweight and dependency-free (standard library only).
"""

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

import traceback
from typing import Optional, Dict, Any, List

# ---- Part 2: Base Exceptions -------------------------------------------

class BlendshapeError(Exception):
    """
    Base exception for the entire blendshape subsystem.

    All blendshape-specific exceptions inherit from this class.
    It provides a common catch-all for callers who want to handle
    any blendshape error generically.
    """
    error_code: Optional[str] = None
    """Stable error code for logging and automation (e.g., 'BS101')."""

    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        self.context: Dict[str, Any] = kwargs.get('context', {})
        super().__init__(message, *args)


class BlendshapeWarning(BlendshapeError):
    """Non-fatal warning that may be recoverable."""
    pass


class BlendshapeCriticalError(BlendshapeError):
    """Fatal error that requires immediate attention."""
    pass


class BlendshapeInternalError(BlendshapeError):
    """Internal error (bug) in the blendshape system."""
    pass


class BlendshapeConfigurationError(BlendshapeError):
    """Error in configuration or settings."""
    pass


# ---- Part 3: Mesh Exceptions -------------------------------------------

class MeshError(BlendshapeError):
    """Base for mesh-related errors."""
    pass


class MeshNotFoundError(MeshError):
    """Raised when a referenced mesh does not exist."""
    error_code = "BS101"

    def __init__(self, mesh_name: str, **kwargs):
        self.mesh_name = mesh_name
        message = f"Mesh '{mesh_name}' not found"
        super().__init__(message, context={'mesh': mesh_name}, **kwargs)


class InvalidMeshError(MeshError):
    """Raised when a mesh is invalid (e.g., no vertices, non-mesh shape)."""
    error_code = "BS102"

    def __init__(self, mesh_name: str, reason: Optional[str] = None, **kwargs):
        self.mesh_name = mesh_name
        self.reason = reason
        message = f"Mesh '{mesh_name}' is invalid"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'mesh': mesh_name, 'reason': reason}, **kwargs)


class MeshLockedError(MeshError):
    """Raised when attempting to modify a locked mesh."""
    error_code = "BS103"

    def __init__(self, mesh_name: str, **kwargs):
        self.mesh_name = mesh_name
        message = f"Mesh '{mesh_name}' is locked and cannot be modified"
        super().__init__(message, context={'mesh': mesh_name}, **kwargs)


class MeshDeletedError(MeshError):
    """Raised when a mesh was deleted during an operation."""
    error_code = "BS104"

    def __init__(self, mesh_name: str, **kwargs):
        self.mesh_name = mesh_name
        message = f"Mesh '{mesh_name}' was deleted"
        super().__init__(message, context={'mesh': mesh_name}, **kwargs)


class MeshTypeError(MeshError):
    """Raised when a node is expected to be a mesh but is not."""
    error_code = "BS105"

    def __init__(self, node_name: str, expected_type: str, actual_type: str, **kwargs):
        self.node_name = node_name
        self.expected_type = expected_type
        self.actual_type = actual_type
        message = f"Node '{node_name}' is of type '{actual_type}', expected '{expected_type}'"
        super().__init__(message, context={'node': node_name, 'expected': expected_type, 'actual': actual_type}, **kwargs)


class MeshHistoryError(MeshError):
    """Raised when mesh history interferes with an operation."""
    error_code = "BS106"

    def __init__(self, mesh_name: str, history: Optional[List[str]] = None, **kwargs):
        self.mesh_name = mesh_name
        self.history = history or []
        message = f"Mesh '{mesh_name}' has construction history that may interfere"
        super().__init__(message, context={'mesh': mesh_name, 'history': history}, **kwargs)


class MeshScaleError(MeshError):
    """Raised when mesh has non-uniform or non-zero scale."""
    error_code = "BS107"

    def __init__(self, mesh_name: str, scale: tuple, **kwargs):
        self.mesh_name = mesh_name
        self.scale = scale
        message = f"Mesh '{mesh_name}' has non-uniform scale: {scale}"
        super().__init__(message, context={'mesh': mesh_name, 'scale': scale}, **kwargs)


class MeshNamespaceError(MeshError):
    """Raised when namespace conflicts prevent operation."""
    error_code = "BS108"

    def __init__(self, mesh_name: str, namespace: str, **kwargs):
        self.mesh_name = mesh_name
        self.namespace = namespace
        message = f"Mesh '{mesh_name}' has namespace conflict with '{namespace}'"
        super().__init__(message, context={'mesh': mesh_name, 'namespace': namespace}, **kwargs)


# ---- Part 4: Topology Exceptions ----------------------------------------

class TopologyError(BlendshapeError):
    """Base for topology-related errors."""
    pass


class VertexCountMismatch(TopologyError):
    """Raised when two meshes have different vertex counts."""
    error_code = "BS201"

    def __init__(self, expected: int, actual: int, **kwargs):
        self.expected = expected
        self.actual = actual
        message = f"Vertex count mismatch: expected {expected}, got {actual}"
        super().__init__(message, context={'expected': expected, 'actual': actual}, **kwargs)


class TopologyMismatch(TopologyError):
    """Raised when topology (connectivity) differs."""
    error_code = "BS202"

    def __init__(self, mesh_a: str, mesh_b: str, **kwargs):
        self.mesh_a = mesh_a
        self.mesh_b = mesh_b
        message = f"Topology mismatch between '{mesh_a}' and '{mesh_b}'"
        super().__init__(message, context={'mesh_a': mesh_a, 'mesh_b': mesh_b}, **kwargs)


class VertexOrderMismatch(TopologyError):
    """Raised when vertex order differs."""
    error_code = "BS203"

    def __init__(self, mesh_a: str, mesh_b: str, **kwargs):
        self.mesh_a = mesh_a
        self.mesh_b = mesh_b
        message = f"Vertex order mismatch between '{mesh_a}' and '{mesh_b}'"
        super().__init__(message, context={'mesh_a': mesh_a, 'mesh_b': mesh_b}, **kwargs)


class NonManifoldMesh(TopologyError):
    """Raised when a mesh is non-manifold."""
    error_code = "BS204"

    def __init__(self, mesh_name: str, details: Optional[str] = None, **kwargs):
        self.mesh_name = mesh_name
        self.details = details
        message = f"Mesh '{mesh_name}' is non-manifold"
        if details:
            message += f": {details}"
        super().__init__(message, context={'mesh': mesh_name, 'details': details}, **kwargs)


class OpenBorderMesh(TopologyError):
    """Raised when a mesh has open borders."""
    error_code = "BS205"

    def __init__(self, mesh_name: str, border_count: Optional[int] = None, **kwargs):
        self.mesh_name = mesh_name
        self.border_count = border_count
        message = f"Mesh '{mesh_name}' has open borders"
        if border_count is not None:
            message += f" ({border_count} borders)"
        super().__init__(message, context={'mesh': mesh_name, 'border_count': border_count}, **kwargs)


class InvalidNormalsError(TopologyError):
    """Raised when mesh normals are invalid."""
    error_code = "BS206"

    def __init__(self, mesh_name: str, **kwargs):
        self.mesh_name = mesh_name
        message = f"Mesh '{mesh_name}' has invalid normals"
        super().__init__(message, context={'mesh': mesh_name}, **kwargs)


class InvalidUVsError(TopologyError):
    """Raised when UV sets are missing or corrupt."""
    error_code = "BS207"

    def __init__(self, mesh_name: str, detail: Optional[str] = None, **kwargs):
        self.mesh_name = mesh_name
        self.detail = detail
        message = f"Mesh '{mesh_name}' has UV issues"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'mesh': mesh_name, 'detail': detail}, **kwargs)


class ShellMismatch(TopologyError):
    """Raised when the number of shells differs."""
    error_code = "BS208"

    def __init__(self, mesh_a: str, shell_a: int, mesh_b: str, shell_b: int, **kwargs):
        self.mesh_a = mesh_a
        self.shell_a = shell_a
        self.mesh_b = mesh_b
        self.shell_b = shell_b
        message = f"Shell count mismatch: '{mesh_a}' has {shell_a}, '{mesh_b}' has {shell_b}"
        super().__init__(message, context={'mesh_a': mesh_a, 'shell_a': shell_a, 'mesh_b': mesh_b, 'shell_b': shell_b}, **kwargs)


# ---- Part 5: Blendshape Creation Exceptions ----------------------------

class BlendshapeCreationError(BlendshapeError):
    """Raised when blendshape creation fails."""
    error_code = "BS301"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, context={'operation': 'creation'}, **kwargs)


class BlendshapeNodeError(BlendshapeError):
    """Raised when a blendshape node operation fails."""
    error_code = "BS302"

    def __init__(self, node_name: str, operation: str, detail: Optional[str] = None, **kwargs):
        self.node_name = node_name
        self.operation = operation
        self.detail = detail
        message = f"Blendshape node '{node_name}' {operation} failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'node': node_name, 'operation': operation, 'detail': detail}, **kwargs)


class TargetExistsError(BlendshapeError):
    """Raised when trying to add a target that already exists."""
    error_code = "BS303"

    def __init__(self, target_name: str, node: Optional[str] = None, **kwargs):
        self.target_name = target_name
        self.node = node
        message = f"Target '{target_name}' already exists"
        if node:
            message += f" on node '{node}'"
        super().__init__(message, context={'target': target_name, 'node': node}, **kwargs)


class TargetNotFoundError(BlendshapeError):
    """Raised when a target is not found."""
    error_code = "BS304"

    def __init__(self, target_name: str, node: Optional[str] = None, **kwargs):
        self.target_name = target_name
        self.node = node
        message = f"Target '{target_name}' not found"
        if node:
            message += f" on node '{node}'"
        super().__init__(message, context={'target': target_name, 'node': node}, **kwargs)


class TargetRenameError(BlendshapeError):
    """Raised when renaming a target fails."""
    error_code = "BS305"

    def __init__(self, old_name: str, new_name: str, reason: Optional[str] = None, **kwargs):
        self.old_name = old_name
        self.new_name = new_name
        self.reason = reason
        message = f"Failed to rename target '{old_name}' to '{new_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'old_name': old_name, 'new_name': new_name, 'reason': reason}, **kwargs)


class TargetDeleteError(BlendshapeError):
    """Raised when deleting a target fails."""
    error_code = "BS306"

    def __init__(self, target_name: str, reason: Optional[str] = None, **kwargs):
        self.target_name = target_name
        self.reason = reason
        message = f"Failed to delete target '{target_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'target': target_name, 'reason': reason}, **kwargs)


class BlendshapeLockedError(BlendshapeError):
    """Raised when a blendshape node or target is locked."""
    error_code = "BS307"

    def __init__(self, node: str, target: Optional[str] = None, **kwargs):
        self.node = node
        self.target = target
        if target:
            message = f"Target '{target}' on node '{node}' is locked"
        else:
            message = f"Blendshape node '{node}' is locked"
        super().__init__(message, context={'node': node, 'target': target}, **kwargs)


class BlendshapeCorruptError(BlendshapeError):
    """Raised when a blendshape node is corrupt."""
    error_code = "BS308"

    def __init__(self, node: str, detail: Optional[str] = None, **kwargs):
        self.node = node
        self.detail = detail
        message = f"Blendshape node '{node}' is corrupt"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'node': node, 'detail': detail}, **kwargs)


# ---- Part 6: Delta Exceptions ------------------------------------------

class DeltaError(BlendshapeError):
    """Base for delta-related errors."""
    pass


class DeltaCalculationError(DeltaError):
    """Raised when delta computation fails."""
    error_code = "BS401"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, context={'operation': 'delta_calculation'}, **kwargs)


class DeltaCompressionError(DeltaError):
    """Raised when delta compression fails."""
    error_code = "BS402"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Delta compression failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class DeltaReconstructionError(DeltaError):
    """Raised when delta reconstruction (applying) fails."""
    error_code = "BS403"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, context={'operation': 'delta_reconstruction'}, **kwargs)


class DeltaNormalizationError(DeltaError):
    """Raised when delta normalization fails."""
    error_code = "BS404"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Delta normalization failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class SparseDeltaError(DeltaError):
    """Raised when sparse delta operations fail."""
    error_code = "BS405"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Sparse delta operation failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class InvalidDeltaError(DeltaError):
    """Raised when a delta is invalid (e.g., vertex count mismatch)."""
    error_code = "BS406"

    def __init__(self, reason: str, **kwargs):
        self.reason = reason
        message = f"Invalid delta: {reason}"
        super().__init__(message, context={'reason': reason}, **kwargs)


# ---- Part 7: Weight Exceptions -----------------------------------------

class WeightError(BlendshapeError):
    """Base for weight-related errors."""
    pass


class InvalidWeightError(WeightError):
    """Raised when a weight is out of valid range."""
    error_code = "BS501"

    def __init__(self, weight: float, min_val: float = 0.0, max_val: float = 1.0, **kwargs):
        self.weight = weight
        self.min_val = min_val
        self.max_val = max_val
        message = f"Weight {weight} is outside valid range [{min_val}, {max_val}]"
        super().__init__(message, context={'weight': weight, 'min': min_val, 'max': max_val}, **kwargs)


class WeightOverflowError(WeightError):
    """Raised when weight sum exceeds allowed limits."""
    error_code = "BS502"

    def __init__(self, total: float, limit: float, **kwargs):
        self.total = total
        self.limit = limit
        message = f"Total weight {total} exceeds limit {limit}"
        super().__init__(message, context={'total': total, 'limit': limit}, **kwargs)


class WeightNormalizationError(WeightError):
    """Raised when weight normalization fails."""
    error_code = "BS503"

    def __init__(self, reason: Optional[str] = None, **kwargs):
        message = "Weight normalization failed"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'reason': reason}, **kwargs)


class WeightConnectionError(WeightError):
    """Raised when a weight attribute connection is invalid."""
    error_code = "BS504"

    def __init__(self, target: str, detail: Optional[str] = None, **kwargs):
        self.target = target
        self.detail = detail
        message = f"Invalid weight connection for '{target}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'target': target, 'detail': detail}, **kwargs)


class WeightLockedError(WeightError):
    """Raised when attempting to modify a locked weight."""
    error_code = "BS505"

    def __init__(self, target: str, **kwargs):
        self.target = target
        message = f"Weight for target '{target}' is locked"
        super().__init__(message, context={'target': target}, **kwargs)


# ---- Part 8: Transfer Exceptions ---------------------------------------

class TransferError(BlendshapeError):
    """Base for transfer-related errors."""
    pass


class TransferMappingError(TransferError):
    """Raised when mapping between source and target fails."""
    error_code = "BS601"

    def __init__(self, source: str, target: str, detail: Optional[str] = None, **kwargs):
        self.source = source
        self.target = target
        self.detail = detail
        message = f"Transfer mapping failed from '{source}' to '{target}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'source': source, 'target': target, 'detail': detail}, **kwargs)


class TransferTopologyError(TransferError):
    """Raised when topology prevents transfer."""
    error_code = "BS602"

    def __init__(self, source: str, target: str, detail: Optional[str] = None, **kwargs):
        self.source = source
        self.target = target
        self.detail = detail
        message = f"Transfer topology error between '{source}' and '{target}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'source': source, 'target': target, 'detail': detail}, **kwargs)


class TransferCancelled(TransferError):
    """Raised when a transfer operation is cancelled."""
    error_code = "BS603"

    def __init__(self, message: str = "Transfer cancelled by user", **kwargs):
        super().__init__(message, context={'cancelled': True}, **kwargs)


class TransferConflict(TransferError):
    """Raised when target already has conflicting data."""
    error_code = "BS604"

    def __init__(self, target: str, conflict: str, **kwargs):
        self.target = target
        self.conflict = conflict
        message = f"Transfer conflict on '{target}': {conflict}"
        super().__init__(message, context={'target': target, 'conflict': conflict}, **kwargs)


class TransferTimeout(TransferError):
    """Raised when transfer exceeds time limit."""
    error_code = "BS605"

    def __init__(self, timeout_seconds: float, **kwargs):
        self.timeout_seconds = timeout_seconds
        message = f"Transfer timed out after {timeout_seconds} seconds"
        super().__init__(message, context={'timeout': timeout_seconds}, **kwargs)


class TransferValidationError(TransferError):
    """Raised when transfer validation fails."""
    error_code = "BS606"

    def __init__(self, message: str, **kwargs):
        super().__init__(message, context={'operation': 'transfer_validation'}, **kwargs)


# ---- Part 9: Export Exceptions -----------------------------------------

class ExportError(BlendshapeError):
    """Base for export-related errors."""
    pass


class ExportCancelled(ExportError):
    """Raised when an export operation is cancelled."""
    error_code = "BS701"

    def __init__(self, message: str = "Export cancelled by user", **kwargs):
        super().__init__(message, context={'cancelled': True}, **kwargs)


class ExportFormatError(ExportError):
    """Raised when an unsupported export format is requested."""
    error_code = "BS702"

    def __init__(self, format_name: str, supported_formats: Optional[List[str]] = None, **kwargs):
        self.format_name = format_name
        self.supported_formats = supported_formats or []
        message = f"Unsupported export format: '{format_name}'"
        if self.supported_formats:
            message += f" (supported: {', '.join(self.supported_formats)})"
        super().__init__(message, context={'format': format_name, 'supported': self.supported_formats}, **kwargs)


class ExportPermissionError(ExportError):
    """Raised when file permissions prevent export."""
    error_code = "BS703"

    def __init__(self, path: str, detail: Optional[str] = None, **kwargs):
        self.path = path
        self.detail = detail
        message = f"Permission denied to write to '{path}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'path': path, 'detail': detail}, **kwargs)


class ExportVersionError(ExportError):
    """Raised when version mismatch occurs during export."""
    error_code = "BS704"

    def __init__(self, expected_version: str, actual_version: str, **kwargs):
        self.expected_version = expected_version
        self.actual_version = actual_version
        message = f"Version mismatch: expected {expected_version}, got {actual_version}"
        super().__init__(message, context={'expected': expected_version, 'actual': actual_version}, **kwargs)


class ExportPathError(ExportError):
    """Raised when the export path is invalid."""
    error_code = "BS705"

    def __init__(self, path: str, reason: Optional[str] = None, **kwargs):
        self.path = path
        self.reason = reason
        message = f"Invalid export path: '{path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'path': path, 'reason': reason}, **kwargs)


class ExportSerializationError(ExportError):
    """Raised when serialization of data fails."""
    error_code = "BS706"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Export serialization failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class ExportCompressionError(ExportError):
    """Raised when compression fails."""
    error_code = "BS707"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Export compression failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


# ---- Part 10: ARKit Exceptions -----------------------------------------

class ARKitError(BlendshapeError):
    """Base for ARKit-related errors."""
    pass


class MissingARKitShape(ARKitError):
    """Raised when an expected ARKit shape is missing."""
    error_code = "BS801"

    def __init__(self, shape_name: str, **kwargs):
        self.shape_name = shape_name
        message = f"Missing ARKit shape: '{shape_name}'"
        super().__init__(message, context={'shape': shape_name}, **kwargs)


class InvalidARKitName(ARKitError):
    """Raised when an ARKit name does not comply with specification."""
    error_code = "BS802"

    def __init__(self, name: str, reason: Optional[str] = None, **kwargs):
        self.name = name
        self.reason = reason
        message = f"Invalid ARKit name: '{name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'name': name, 'reason': reason}, **kwargs)


class CalibrationError(ARKitError):
    """Raised when calibration fails."""
    error_code = "BS803"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Calibration error"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class ExpressionSetError(ARKitError):
    """Raised when expression set operations fail."""
    error_code = "BS804"

    def __init__(self, expression_name: str, detail: Optional[str] = None, **kwargs):
        self.expression_name = expression_name
        self.detail = detail
        message = f"Expression set error for '{expression_name}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'expression': expression_name, 'detail': detail}, **kwargs)


class MappingError(ARKitError):
    """Raised when mapping between ARKit and blendshape fails."""
    error_code = "BS805"

    def __init__(self, source: str, target: str, detail: Optional[str] = None, **kwargs):
        self.source = source
        self.target = target
        self.detail = detail
        message = f"Mapping error from '{source}' to '{target}'"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'source': source, 'target': target, 'detail': detail}, **kwargs)


class RemappingError(ARKitError):
    """Raised when remapping ARKit data fails."""
    error_code = "BS806"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Remapping error"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


# ---- Part 11: Validation Exceptions ------------------------------------

class ValidationError(BlendshapeError):
    """Base for validation-related errors."""
    pass


class SceneValidationError(ValidationError):
    """Raised when scene validation fails."""
    error_code = "BS901"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Scene validation failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class NamingValidationError(ValidationError):
    """Raised when naming validation fails."""
    error_code = "BS902"

    def __init__(self, name: str, reason: Optional[str] = None, **kwargs):
        self.name = name
        self.reason = reason
        message = f"Invalid name: '{name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, context={'name': name, 'reason': reason}, **kwargs)


class TopologyValidationError(ValidationError):
    """Raised when topology validation fails."""
    error_code = "BS903"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Topology validation failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class WeightValidationError(ValidationError):
    """Raised when weight validation fails."""
    error_code = "BS904"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Weight validation failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class MetadataValidationError(ValidationError):
    """Raised when metadata validation fails."""
    error_code = "BS905"

    def __init__(self, detail: Optional[str] = None, **kwargs):
        message = "Metadata validation failed"
        if detail:
            message += f": {detail}"
        super().__init__(message, context={'detail': detail}, **kwargs)


class VersionValidationError(ValidationError):
    """Raised when version validation fails."""
    error_code = "BS906"

    def __init__(self, expected: str, actual: str, **kwargs):
        self.expected = expected
        self.actual = actual
        message = f"Version validation failed: expected {expected}, got {actual}"
        super().__init__(message, context={'expected': expected, 'actual': actual}, **kwargs)


# ---- Part 12: Utility Functions ----------------------------------------

def format_exception(exc: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception into a human-readable string.

    Args:
        exc: The exception to format.
        include_traceback: Whether to include the full traceback.

    Returns:
        Formatted exception string.
    """
    if include_traceback:
        return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        msg = str(exc)
        if hasattr(exc, 'error_code') and exc.error_code:
            msg = f"[{exc.error_code}] {msg}"
        return msg


def exception_to_dict(exc: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a dictionary for logging or JSON serialization.

    Returns:
        Dict with keys: 'type', 'message', 'error_code', 'context', 'traceback'.
    """
    result = {
        'type': exc.__class__.__name__,
        'message': str(exc),
        'error_code': getattr(exc, 'error_code', None),
        'context': getattr(exc, 'context', {}),
        'traceback': traceback.format_exc(),
    }
    return result


def exception_from_dict(data: Dict[str, Any]) -> Optional[Exception]:
    """
    Reconstruct an exception from a dictionary (inverse of exception_to_dict).
    This is useful for serializing exceptions across processes.

    Returns:
        The reconstructed exception, or None if the type cannot be resolved.
    """
    try:
        exc_type = data.get('type')
        message = data.get('message', '')
        context = data.get('context', {})
        if exc_type in globals():
            cls = globals()[exc_type]
            if issubclass(cls, Exception):
                # Attempt to instantiate with context as kwargs
                return cls(message, context=context)
    except:
        pass
    return None


def error_summary(exc: Exception) -> str:
    """
    Return a short summary of the exception (type + message + code).
    """
    code = f"[{exc.error_code}]" if hasattr(exc, 'error_code') and exc.error_code else ""
    return f"{code} {exc.__class__.__name__}: {str(exc)}"


# ---- Part 13: Public API -----------------------------------------------

__all__ = [
    # Base
    "BlendshapeError",
    "BlendshapeWarning",
    "BlendshapeCriticalError",
    "BlendshapeInternalError",
    "BlendshapeConfigurationError",

    # Mesh
    "MeshError",
    "MeshNotFoundError",
    "InvalidMeshError",
    "MeshLockedError",
    "MeshDeletedError",
    "MeshTypeError",
    "MeshHistoryError",
    "MeshScaleError",
    "MeshNamespaceError",

    # Topology
    "TopologyError",
    "VertexCountMismatch",
    "TopologyMismatch",
    "VertexOrderMismatch",
    "NonManifoldMesh",
    "OpenBorderMesh",
    "InvalidNormalsError",
    "InvalidUVsError",
    "ShellMismatch",

    # Blendshape Creation
    "BlendshapeCreationError",
    "BlendshapeNodeError",
    "TargetExistsError",
    "TargetNotFoundError",
    "TargetRenameError",
    "TargetDeleteError",
    "BlendshapeLockedError",
    "BlendshapeCorruptError",

    # Delta
    "DeltaError",
    "DeltaCalculationError",
    "DeltaCompressionError",
    "DeltaReconstructionError",
    "DeltaNormalizationError",
    "SparseDeltaError",
    "InvalidDeltaError",

    # Weights
    "WeightError",
    "InvalidWeightError",
    "WeightOverflowError",
    "WeightNormalizationError",
    "WeightConnectionError",
    "WeightLockedError",

    # Transfer
    "TransferError",
    "TransferMappingError",
    "TransferTopologyError",
    "TransferCancelled",
    "TransferConflict",
    "TransferTimeout",
    "TransferValidationError",

    # Export
    "ExportError",
    "ExportCancelled",
    "ExportFormatError",
    "ExportPermissionError",
    "ExportVersionError",
    "ExportPathError",
    "ExportSerializationError",
    "ExportCompressionError",

    # ARKit
    "ARKitError",
    "MissingARKitShape",
    "InvalidARKitName",
    "CalibrationError",
    "ExpressionSetError",
    "MappingError",
    "RemappingError",

    # Validation
    "ValidationError",
    "SceneValidationError",
    "NamingValidationError",
    "TopologyValidationError",
    "WeightValidationError",
    "MetadataValidationError",
    "VersionValidationError",

    # Utility
    "format_exception",
    "exception_to_dict",
    "exception_from_dict",
    "error_summary",
]