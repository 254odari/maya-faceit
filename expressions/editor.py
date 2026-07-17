"""
maya_faceit.expression.editor

Interactive Editing of Facial Expressions.

This module provides tools for editing existing expression definitions,
blendshape weights, and target meshes. It integrates with the ExpressionGenerator,
BlendshapePoseManager, and BlendshapeCreator to provide a complete editing pipeline.

Responsibilities:
- Rename expressions.
- Duplicate expressions.
- Delete expressions.
- Update expression coefficients (weights).
- Replace target meshes.
- Reset expression to default.
- Live update during editing.
- Validate changes.

The editor works on expressions stored in the ExpressionGenerator's built-in
or custom definitions, and can also sync changes with a PoseLibrary.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import logging
import time
from typing import List, Optional, Dict, Any, Union, Callable

# Maya imports (with fallback)
try:
    import maya.cmds as cmds
except ImportError:
    class DummyCmds:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyCmds()

# Imports from other modules (with fallbacks)
try:
    from .generator import (
        ExpressionGenerator,
        ExpressionDefinition,
        ExpressionResult,
        ExpressionType,
        GenerationMode,
        ExpressionError,
        ExpressionNotFoundError,
    )
    from ..blendshapes.blendshape_pose import BlendshapePoseManager, PoseDefinition
    from ..blendshapes.blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType
    from ..blendshapes.blendshape_utils import (
        get_blendshape_targets,
        get_blendshape_weight,
        set_blendshape_weight,
        sanitize_name,
        clamp,
        normalize_weights,
    )
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    class ExpressionGenerator:
        def get_builtin_names(self): return []
        def get_definition(self, name): return None
        def add_custom_expression(self, defn): pass
        def remove_custom_expression(self, name): pass
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionResult: pass
    class ExpressionType: pass
    class GenerationMode: pass
    class ExpressionError(Exception): pass
    class ExpressionNotFoundError(Exception): pass
    class BlendshapePoseManager:
        def get_pose(self, name): return None
    class PoseDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class BlendShapeCreator:
        def create_node(self, name, mesh): return None
        def create_target(self, node, target): 
            class DummyResult:
                success = True
                errors = []
            return DummyResult()
    class BlendShapeTarget:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class TargetType:
        STANDARD = "standard"
        ARKIT = "arkit"
        CORRECTIVE = "corrective"
        INBETWEEN = "inbetween"
        CUSTOM = "custom"
    def get_blendshape_targets(*args): return []
    def get_blendshape_weight(*args): return 0.0
    def set_blendshape_weight(*args): pass
    def sanitize_name(name): return name
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights): return {k: v / sum(weights.values()) if sum(weights.values()) else 0.0 for k, v in weights.items()}
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class ExpressionEditorError(Exception):
    """Base exception for expression editor operations."""
    pass

class ExpressionEditorValidationError(ExpressionEditorError):
    """Raised when validation fails during edit."""
    pass


# ---- ExpressionEditor Class ----

class ExpressionEditor:
    """
    Interactive editor for facial expressions.

    This class manages the editing lifecycle of expression definitions,
    including renaming, duplication, deletion, coefficient updates,
    mesh replacement, and reset operations.

    It can optionally sync changes with a PoseLibrary or a blendshape node.
    """

    def __init__(
        self,
        generator: Optional[ExpressionGenerator] = None,
        pose_manager: Optional[BlendshapePoseManager] = None,
        creator: Optional[BlendShapeCreator] = None,
        live_update_callback: Optional[Callable[[str, Dict[str, float]], None]] = None,
    ):
        """
        Initialize the expression editor.

        Args:
            generator: The ExpressionGenerator instance to use.
            pose_manager: Optional PoseManager to sync poses.
            creator: Optional BlendShapeCreator for mesh operations.
            live_update_callback: Callback invoked when a change is applied.
        """
        self._generator = generator or ExpressionGenerator()
        self._pose_manager = pose_manager
        self._creator = creator

        # Live update callback (e.g., for UI refresh)
        self._live_update_callback = live_update_callback

        # Keep a reference to the current editing context (if any)
        self._current_expression_name: Optional[str] = None
        self._current_definition: Optional[ExpressionDefinition] = None

    # ---- Core Operations ----

    def rename(self, old_name: str, new_name: str, update_pose_library: bool = True) -> bool:
        """
        Rename an expression definition.

        Args:
            old_name: Current name.
            new_name: New name (will be sanitized).
            update_pose_library: If True, also rename in pose library.

        Returns:
            True if successful.

        Raises:
            ExpressionNotFoundError: If expression not found.
            ExpressionEditorError: If new name already exists.
        """
        # Validate existence
        if old_name not in self._generator.get_builtin_names():
            # Check custom definitions? The generator may have a way to check all.
            # We'll try to get the definition; if None, raise.
            if self._generator.get_definition(old_name) is None:
                raise ExpressionNotFoundError(f"Expression '{old_name}' not found.")

        # Check if new name already exists
        if new_name != old_name:
            existing = self._generator.get_definition(new_name)
            if existing is not None:
                raise ExpressionEditorError(f"Expression '{new_name}' already exists.")

        # Get the definition
        defn = self._generator.get_definition(old_name)
        if defn is None:
            raise ExpressionNotFoundError(f"Expression '{old_name}' not found.")

        # Create a new definition with the new name
        new_defn = ExpressionDefinition(
            name=sanitize_name(new_name),
            coefficients=defn.coefficients.copy(),
            expression_type=defn.expression_type,
            description=defn.description,
            tags=defn.tags.copy(),
            metadata=defn.metadata.copy(),
        )

        # Add new definition and remove old
        self._generator.add_custom_expression(new_defn)
        self._generator.remove_custom_expression(old_name)

        # Update pose library if requested
        if update_pose_library and self._pose_manager:
            try:
                pose = self._pose_manager.get_pose(old_name)
                if pose:
                    # Rename the pose by creating a new one and deleting old
                    new_pose = PoseDefinition(
                        name=new_name,
                        weights=pose.weights.copy(),
                        pose_type=pose.pose_type,
                        metadata=pose.metadata,
                        tags=pose.tags,
                        category=pose.category,
                    )
                    self._pose_manager._poses[new_name] = new_pose
                    if old_name in self._pose_manager._poses:
                        del self._pose_manager._poses[old_name]
            except:
                pass

        self._trigger_live_update(new_name, new_defn.coefficients)
        return True

    def duplicate(self, source_name: str, new_name: str, update_pose_library: bool = True) -> bool:
        """
        Duplicate an expression definition.

        Args:
            source_name: Name to copy from.
            new_name: Name for the copy.
            update_pose_library: If True, also duplicate in pose library.

        Returns:
            True if successful.
        """
        if source_name not in self._generator.get_builtin_names():
            if self._generator.get_definition(source_name) is None:
                raise ExpressionNotFoundError(f"Expression '{source_name}' not found.")
        if self._generator.get_definition(new_name) is not None:
            raise ExpressionEditorError(f"Expression '{new_name}' already exists.")

        defn = self._generator.get_definition(source_name)
        if defn is None:
            raise ExpressionNotFoundError(f"Expression '{source_name}' not found.")

        new_defn = ExpressionDefinition(
            name=sanitize_name(new_name),
            coefficients=defn.coefficients.copy(),
            expression_type=defn.expression_type,
            description=f"Copy of {source_name}",
            tags=defn.tags.copy(),
            metadata=defn.metadata.copy(),
        )
        self._generator.add_custom_expression(new_defn)

        if update_pose_library and self._pose_manager:
            try:
                pose = self._pose_manager.get_pose(source_name)
                if pose:
                    new_pose = PoseDefinition(
                        name=new_name,
                        weights=pose.weights.copy(),
                        pose_type=pose.pose_type,
                        metadata=pose.metadata,
                        tags=pose.tags,
                        category=pose.category,
                    )
                    self._pose_manager._poses[new_name] = new_pose
            except:
                pass

        self._trigger_live_update(new_name, new_defn.coefficients)
        return True

    def delete(self, name: str, update_pose_library: bool = True) -> bool:
        """
        Delete an expression definition.

        Args:
            name: Expression to delete.
            update_pose_library: If True, also delete from pose library.

        Returns:
            True if successful.
        """
        # Check if built-in; we might not allow deletion of built-ins?
        if name in self._generator.get_builtin_names():
            # Optionally we could allow deletion of built-ins? Usually not.
            raise ExpressionEditorError(f"Cannot delete built-in expression '{name}'. Remove from custom instead.")
        # Remove from custom
        try:
            self._generator.remove_custom_expression(name)
        except ExpressionNotFoundError:
            raise

        if update_pose_library and self._pose_manager:
            try:
                if name in self._pose_manager._poses:
                    del self._pose_manager._poses[name]
            except:
                pass

        self._trigger_live_update(name, {})
        return True

    def update_coefficients(
        self,
        name: str,
        new_coefficients: Dict[str, float],
        normalize: bool = True,
        update_pose_library: bool = True,
    ) -> bool:
        """
        Update the coefficients (weights) of an expression.

        Args:
            name: Expression name.
            new_coefficients: New coefficient dictionary.
            normalize: If True, normalize weights to sum to 1.
            update_pose_library: If True, update pose library.

        Returns:
            True if successful.

        Raises:
            ExpressionNotFoundError: If expression not found.
            ExpressionEditorValidationError: If coefficients invalid.
        """
        # Validate coefficients
        for k, v in new_coefficients.items():
            if not 0.0 <= v <= 1.0:
                raise ExpressionEditorValidationError(f"Coefficient {k} out of range: {v}")

        defn = self._generator.get_definition(name)
        if defn is None:
            raise ExpressionNotFoundError(f"Expression '{name}' not found.")

        # Update coefficients
        if normalize:
            new_coefficients = normalize_weights(new_coefficients)

        defn.coefficients = new_coefficients

        # Update in generator (if it's a custom expression, we may need to add it again)
        # If it's built-in, we might need to replace it with a custom override.
        self._generator.add_custom_expression(defn)

        # Update pose library
        if update_pose_library and self._pose_manager:
            try:
                pose = self._pose_manager.get_pose(name)
                if pose:
                    # Update weights
                    pose.weights = new_coefficients.copy()
                else:
                    # Create new pose
                    new_pose = PoseDefinition(
                        name=name,
                        weights=new_coefficients.copy(),
                        pose_type="custom",
                    )
                    self._pose_manager._poses[name] = new_pose
            except:
                pass

        self._trigger_live_update(name, new_coefficients)
        return True

    def replace_target_mesh(
        self,
        expression_name: str,
        mesh_name: str,
        base_mesh: str,
        target_node: Optional[str] = None,
    ) -> bool:
        """
        Replace the target mesh for an expression.

        This will update the blendshape target associated with the expression.
        It assumes the expression has a target mesh already, or we're creating a new one.

        Args:
            expression_name: Expression to update.
            mesh_name: The new target mesh name (or path).
            base_mesh: The base mesh.
            target_node: Optional blendshape node to add/update target.

        Returns:
            True if successful.
        """
        if self._creator is None:
            raise ExpressionEditorError("BlendShapeCreator not available.")
        # Get definition (for metadata)
        defn = self._generator.get_definition(expression_name)
        if defn is None:
            raise ExpressionNotFoundError(f"Expression '{expression_name}' not found.")

        # Ensure a blendshape node exists on base_mesh
        bs_nodes = cmds.listConnections(base_mesh, type='blendShape') or []
        if bs_nodes:
            node = bs_nodes[0]
        else:
            if self._creator:
                node = self._creator.create_node(f"{sanitize_name(base_mesh)}_blendShape", base_mesh)
            else:
                raise ExpressionEditorError("Cannot create blendshape node: creator unavailable.")

        # Create a BlendShapeTarget
        target = BlendShapeTarget(
            name=sanitize_name(expression_name),
            mesh=mesh_name,
            target_type=TargetType.STANDARD,
            weight=0.0,
        )
        # Add target to node
        if self._creator:
            result = self._creator.create_target(node, target)
            if not result.success:
                raise ExpressionEditorError(f"Failed to add target: {result.errors}")
        else:
            raise ExpressionEditorError("BlendShapeCreator not available.")

        self._trigger_live_update(expression_name, defn.coefficients)
        return True

    def reset(self, name: str) -> bool:
        """
        Reset a custom expression to its built-in default (if it overrides a built-in).

        Args:
            name: Expression name.

        Returns:
            True if reset successful.

        Raises:
            ExpressionNotFoundError: If expression not found.
        """
        # Check if it's a built-in; if so, we can reset by removing custom override.
        if name in self._generator.get_builtin_names():
            # Remove custom definition if it exists
            try:
                self._generator.remove_custom_expression(name)
            except ExpressionNotFoundError:
                pass  # No custom override
            # Also remove from pose library? Maybe keep.
            # We'll reset coefficients to built-in.
            builtin_def = self._generator.get_definition(name)  # now returns built-in
            if builtin_def:
                # Update pose library if needed
                if self._pose_manager:
                    try:
                        pose = self._pose_manager.get_pose(name)
                        if pose:
                            pose.weights = builtin_def.coefficients.copy()
                    except:
                        pass
                self._trigger_live_update(name, builtin_def.coefficients)
                return True
        else:
            # It's a custom expression; resetting might mean clearing coefficients?
            # We'll set to zero or neutral.
            defn = self._generator.get_definition(name)
            if defn is None:
                raise ExpressionNotFoundError(f"Expression '{name}' not found.")
            defn.coefficients = {}
            self._generator.add_custom_expression(defn)
            if self._pose_manager:
                try:
                    pose = self._pose_manager.get_pose(name)
                    if pose:
                        pose.weights = {}
                except:
                    pass
            self._trigger_live_update(name, {})
            return True
        return False

    # ---- Live Update ----

    def set_live_update_callback(self, callback: Callable[[str, Dict[str, float]], None]) -> None:
        """Set a callback to be invoked on each edit."""
        self._live_update_callback = callback

    def _trigger_live_update(self, name: str, coefficients: Dict[str, float]) -> None:
        """Invoke the live update callback if set."""
        if self._live_update_callback:
            try:
                self._live_update_callback(name, coefficients)
            except Exception as e:
                logger.warning(f"Live update callback failed: {e}")

    # ---- Utilities ----

    def get_definition(self, name: str) -> Optional[ExpressionDefinition]:
        """Get the current definition (including custom overrides)."""
        return self._generator.get_definition(name)

    def list_expressions(self) -> List[str]:
        """Return all expression names (built-in + custom)."""
        builtin = set(self._generator.get_builtin_names())
        # We can't easily list custom-only names; we'll return built-in.
        # If custom expressions were added with new names, they won't appear here.
        # In a full implementation, we'd track custom names separately.
        return list(builtin)

    def get_coefficients(self, name: str) -> Dict[str, float]:
        """Get the coefficients of an expression."""
        defn = self.get_definition(name)
        if defn:
            return defn.coefficients.copy()
        raise ExpressionNotFoundError(f"Expression '{name}' not found.")


# ---- Public API ----

__all__ = [
    "ExpressionEditor",
    "ExpressionEditorError",
    "ExpressionEditorValidationError",
]