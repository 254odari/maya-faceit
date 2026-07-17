"""
maya_faceit.expression.manager

High-level Expression Controller.

This is the primary API for all expression-related operations in the Faceit system.
It orchestrates the generator, editor, library, presets, interpolator, and mirror
modules, providing a single unified interface for creating, editing, managing,
and exporting facial expressions.

Responsibilities:
- Create new expressions from coefficients, presets, or ARKit.
- Delete, rename, duplicate, and update expressions.
- Load and save expression libraries (JSON).
- Validate expression definitions.
- Search and organize expressions (categories, tags, favorites).
- Mirror expressions left/right.
- Blend and interpolate expressions.
- Install expressions into the blendshape system.
- Provide statistics and diagnostics.

The ExpressionManager is the main entry point for UI and scripting.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Tuple

# Import submodules (with fallbacks)
try:
    from .generator import (
        ExpressionGenerator,
        ExpressionDefinition,
        ExpressionResult,
        ExpressionType,
        GenerationMode,
        ExpressionError,
        ExpressionNotFoundError,
        ExpressionGenerationError,
    )
    from .editor import ExpressionEditor, ExpressionEditorError, ExpressionEditorValidationError
    from .library import ExpressionLibrary, ExpressionEntry, ExpressionMetadata, ExpressionLibraryError
    from .presets import PresetManager, PresetError
    from .interpolation import ExpressionInterpolator, InterpolationMode, InterpolationError
    from .mirror import ExpressionMirror, ExpressionMirrorError
    from ..blendshapes.blendshape_pose import BlendshapePoseManager, PoseDefinition
    from ..blendshapes.blendshape_creator import BlendShapeCreator
    from ..blendshapes.blendshape_utils import sanitize_name, clamp, normalize_weights
    from ..blendshapes.blendshape_validator import BlendshapeValidator
    from ..arkit.mapper import ARKitMapper
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
    class ExpressionResult:
        success = False
        message = ""
        errors = []
    class ExpressionType:
        BASIC = "basic"
        CUSTOM = "custom"
    class GenerationMode: pass
    class ExpressionError(Exception): pass
    class ExpressionNotFoundError(Exception): pass
    class ExpressionGenerationError(Exception): pass
    class ExpressionEditor:
        def rename(self, old, new): return False
        def duplicate(self, src, dst): return False
        def delete(self, name): return False
        def update_coefficients(self, name, coeffs): return False
        def replace_target_mesh(self, name, mesh, base, node): return False
        def reset(self, name): return False
        def get_definition(self, name): return None
        def list_expressions(self): return []
    class ExpressionEditorError(Exception): pass
    class ExpressionEditorValidationError(Exception): pass
    class ExpressionLibrary:
        def add(self, defn, **kwargs): return None
        def remove(self, name): return False
        def get(self, name): return None
        def update(self, entry): pass
        def list_entries(self): return []
        def list_names(self): return []
        def search(self, query): return []
        def filter_by_tags(self, tags): return []
        def filter_by_category(self, cat): return []
        def filter_by_favorite(self): return []
        def export_to_file(self, path): pass
        def import_from_file(self, path): return 0
        def get_statistics(self): return {}
    class ExpressionLibraryError(Exception): pass
    class PresetManager:
        def list_presets(self): return []
        def get_preset(self, name): return None
        def get_preset_info(self, name): return None
        def add_custom_preset(self, name, coeffs, **kwargs): pass
        def install(self, name, generator=None): return False
    class PresetError(Exception): pass
    class ExpressionInterpolator:
        def interpolate(self, a, b, t, mode): return {}
        def blend_multi(self, exprs, weights): return {}
    class InterpolationMode: pass
    class InterpolationError(Exception): pass
    class ExpressionMirror:
        def mirror_coefficients(self, coeffs, direction): return {}
        def mirror_definition(self, defn, direction): return None
        def mirror_selected(self, names, direction): return {}
        def mirror_all(self, direction): return {}
        def get_symmetry_pair(self, ch): return None
    class ExpressionMirrorError(Exception): pass
    class BlendshapePoseManager: pass
    class BlendShapeCreator: pass
    def sanitize_name(name): return name
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights): return weights
    class BlendshapeValidator: pass
    class ARKitMapper: pass
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class ExpressionManagerError(Exception):
    """Base exception for expression manager operations."""
    pass


# ---- ExpressionManager Class ----

class ExpressionManager:
    """
    High-level controller for all expression operations.

    This class provides a unified API for creating, editing, managing, and
    exporting facial expressions. It integrates the generator, editor, library,
    presets, interpolator, and mirror modules.
    """

    def __init__(
        self,
        generator: Optional[ExpressionGenerator] = None,
        editor: Optional[ExpressionEditor] = None,
        library: Optional[ExpressionLibrary] = None,
        preset_manager: Optional[PresetManager] = None,
        interpolator: Optional[ExpressionInterpolator] = None,
        mirror: Optional[ExpressionMirror] = None,
        pose_manager: Optional[BlendshapePoseManager] = None,
        creator: Optional[BlendShapeCreator] = None,
        validator: Optional[BlendshapeValidator] = None,
        arkit_mapper: Optional[ARKitMapper] = None,
    ):
        """
        Initialize the expression manager.

        Args:
            generator: ExpressionGenerator instance.
            editor: ExpressionEditor instance.
            library: ExpressionLibrary instance.
            preset_manager: PresetManager instance.
            interpolator: ExpressionInterpolator instance.
            mirror: ExpressionMirror instance.
            pose_manager: PoseManager for syncing poses.
            creator: BlendShapeCreator for target mesh operations.
            validator: BlendshapeValidator for validation.
            arkit_mapper: ARKitMapper for ARKit mapping.
        """
        self._generator = generator or ExpressionGenerator()
        self._editor = editor or ExpressionEditor(
            generator=self._generator,
            pose_manager=pose_manager,
            creator=creator,
        )
        self._library = library or ExpressionLibrary(
            generator=self._generator,
            editor=self._editor,
            pose_manager=pose_manager,
            preset_manager=preset_manager,
        )
        self._preset_manager = preset_manager or PresetManager(
            generator=self._generator,
            editor=self._editor,
        )
        self._interpolator = interpolator or ExpressionInterpolator(
            generator=self._generator,
            editor=self._editor,
            arkit_mapper=arkit_mapper,
        )
        self._mirror = mirror or ExpressionMirror(
            generator=self._generator,
            editor=self._editor,
        )
        self._pose_manager = pose_manager or BlendshapePoseManager()
        self._creator = creator
        self._validator = validator or BlendshapeValidator()
        self._arkit_mapper = arkit_mapper or ARKitMapper()

        # Keep track of dirty state
        self._dirty = False

        # Register library as dirty listener
        # (We'll just check the library's dirty flag)

    # ---- Core Expression Operations ----

    def create(
        self,
        name: str,
        coefficients: Dict[str, float],
        description: str = "",
        tags: Optional[List[str]] = None,
        category: str = "Custom",
        author: str = "user",
        favorite: bool = False,
        source: str = "user",
        notes: str = "",
        validate: bool = True,
    ) -> ExpressionEntry:
        """
        Create a new expression and add it to the library.

        Args:
            name: Expression name.
            coefficients: Dict of channel -> weight (0-1).
            description: Description.
            tags: List of tags.
            category: Category.
            author: Author name.
            favorite: Whether to mark as favorite.
            source: Source label.
            notes: Additional notes.
            validate: If True, validate coefficients.

        Returns:
            The created ExpressionEntry.

        Raises:
            ExpressionManagerError: If validation fails or name already exists.
        """
        # Sanitize name
        name = sanitize_name(name)
        if not name:
            raise ExpressionManagerError("Expression name cannot be empty.")

        # Validate coefficients
        if validate:
            for k, v in coefficients.items():
                if not 0.0 <= v <= 1.0:
                    raise ExpressionManagerError(f"Coefficient '{k}' out of range: {v}")

        # Create definition
        defn = ExpressionDefinition(
            name=name,
            coefficients=coefficients,
            expression_type=ExpressionType.CUSTOM,
            description=description,
            tags=tags or [],
            metadata={"category": category},
        )

        # Add to library
        try:
            entry = self._library.add(
                definition=defn,
                author=author,
                tags=tags,
                category=category,
                favorite=favorite,
                source=source,
                notes=notes,
            )
            self._dirty = True
            return entry
        except Exception as e:
            raise ExpressionManagerError(f"Failed to create expression: {e}")

    def delete(self, name: str, delete_from_library: bool = True) -> bool:
        """
        Delete an expression.

        Args:
            name: Expression name.
            delete_from_library: If True, remove from library as well.

        Returns:
            True if deleted.
        """
        # Remove from library
        if delete_from_library:
            removed = self._library.remove(name)
            if not removed:
                # Try deleting from generator
                try:
                    self._generator.remove_custom_expression(name)
                    self._dirty = True
                    return True
                except:
                    return False
            self._dirty = True
            return removed
        else:
            # Just remove from generator
            try:
                self._generator.remove_custom_expression(name)
                self._dirty = True
                return True
            except:
                return False

    def rename(self, old_name: str, new_name: str) -> bool:
        """
        Rename an expression.

        Args:
            old_name: Current name.
            new_name: New name.

        Returns:
            True if successful.
        """
        try:
            result = self._editor.rename(old_name, new_name, update_pose_library=True)
            if result:
                self._dirty = True
            return result
        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return False

    def duplicate(self, source_name: str, new_name: str) -> Optional[ExpressionEntry]:
        """
        Duplicate an expression.

        Args:
            source_name: Name to copy from.
            new_name: Name for the copy.

        Returns:
            The new ExpressionEntry, or None if failed.
        """
        try:
            # Use editor to duplicate
            result = self._editor.duplicate(source_name, new_name, update_pose_library=True)
            if not result:
                return None
            # Retrieve from library
            entry = self._library.get(new_name)
            if entry is None:
                # It might be in generator only; let's add to library manually.
                defn = self._generator.get_definition(new_name)
                if defn:
                    entry = self._library.add(
                        definition=defn,
                        author="user",
                        tags=[],
                        category="Custom",
                        source="duplicated",
                        notes=f"Duplicated from {source_name}",
                    )
            self._dirty = True
            return entry
        except Exception as e:
            logger.error(f"Duplicate failed: {e}")
            return None

    def update(
        self,
        name: str,
        coefficients: Optional[Dict[str, float]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        favorite: Optional[bool] = None,
        notes: Optional[str] = None,
        author: Optional[str] = None,
    ) -> bool:
        """
        Update an expression's definition or metadata.

        Args:
            name: Expression name.
            coefficients: New coefficients (if provided).
            description: New description.
            tags: New tags.
            category: New category.
            favorite: New favorite state.
            notes: New notes.
            author: New author.

        Returns:
            True if successful.
        """
        # Get entry from library
        entry = self._library.get(name)
        if entry is None:
            logger.error(f"Expression '{name}' not found in library.")
            return False

        # Update coefficients
        if coefficients is not None:
            # Validate
            for k, v in coefficients.items():
                if not 0.0 <= v <= 1.0:
                    raise ExpressionManagerError(f"Coefficient '{k}' out of range: {v}")
            entry.definition.coefficients = coefficients.copy()
            # Also update generator
            self._generator.add_custom_expression(entry.definition)

        if description is not None:
            entry.definition.description = description
        if tags is not None:
            entry.metadata.tags = tags
        if category is not None:
            entry.metadata.category = category
        if favorite is not None:
            entry.metadata.favorite = favorite
        if notes is not None:
            entry.metadata.notes = notes
        if author is not None:
            entry.metadata.author = author

        entry.metadata.touch()
        self._library.update(entry)
        self._dirty = True
        return True

    def get(self, name: str) -> Optional[ExpressionEntry]:
        """
        Get an expression entry by name.

        Args:
            name: Expression name.

        Returns:
            ExpressionEntry or None.
        """
        entry = self._library.get(name)
        if entry is None:
            # Check if it's a built-in that might not be in library
            defn = self._generator.get_definition(name)
            if defn:
                # Create a temporary entry
                meta = ExpressionMetadata(
                    id="temp",
                    name=name,
                    created="",
                    modified="",
                    author="builtin",
                    tags=defn.tags,
                    category=defn.metadata.get("category", "Builtin"),
                    source="builtin",
                )
                return ExpressionEntry(definition=defn, metadata=meta)
        return entry

    def list_expressions(self) -> List[str]:
        """Return all expression names (built-in + custom)."""
        # Combine library names and built-in names
        lib_names = set(self._library.list_names())
        builtin_names = set(self._generator.get_builtin_names())
        # Also include any custom in generator not in library
        all_names = lib_names | builtin_names
        return sorted(all_names)

    def list_entries(self) -> List[ExpressionEntry]:
        """Return all entries from the library (built-in + user)."""
        return self._library.list_entries()

    # ---- Preset Operations ----

    def load_preset(self, name: str) -> Optional[Dict[str, float]]:
        """
        Load a preset coefficient set.

        Args:
            name: Preset name.

        Returns:
            Coefficient dictionary or None.
        """
        return self._preset_manager.get_preset(name)

    def load_preset_as_expression(self, preset_name: str, expression_name: Optional[str] = None) -> Optional[ExpressionEntry]:
        """
        Load a preset and add it as an expression.

        Args:
            preset_name: Preset name.
            expression_name: Optional name for the expression (defaults to preset name).

        Returns:
            ExpressionEntry or None.
        """
        coeffs = self._preset_manager.get_preset(preset_name)
        if coeffs is None:
            return None
        name = expression_name or preset_name
        # Create expression
        try:
            return self.create(
                name=name,
                coefficients=coeffs,
                description=f"From preset '{preset_name}'",
                tags=["preset"],
                category="Presets",
                source="preset",
            )
        except Exception as e:
            logger.error(f"Failed to load preset as expression: {e}")
            return None

    def install_preset_as_expression(self, preset_name: str) -> bool:
        """
        Install a preset directly into the expression generator.

        Args:
            preset_name: Preset name.

        Returns:
            True if installed.
        """
        return self._preset_manager.install(preset_name, self._generator)

    def install_all_presets(self) -> int:
        """Install all presets as expressions."""
        return self._preset_manager.install_all(self._generator)

    # ---- ARKit Integration ----

    def create_from_arkit(
        self,
        name: str,
        arkit_coefficients: Dict[str, float],
        mapping: Optional[ARKitMapper] = None,
        **kwargs,
    ) -> Optional[ExpressionEntry]:
        """
        Create an expression from ARKit coefficients.

        Args:
            name: Expression name.
            arkit_coefficients: ARKit channel -> value.
            mapping: Optional custom mapping.
            **kwargs: Additional arguments for create().

        Returns:
            ExpressionEntry or None.
        """
        mapper = mapping or self._arkit_mapper
        try:
            mapped = mapper.map(arkit_coefficients)
            return self.create(name=name, coefficients=mapped, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create expression from ARKit: {e}")
            return None

    # ---- Interpolation ----

    def interpolate(
        self,
        expr_a: Union[str, ExpressionDefinition, Dict[str, float]],
        expr_b: Union[str, ExpressionDefinition, Dict[str, float]],
        t: float,
        mode: str = InterpolationMode.LINEAR,
        **kwargs,
    ) -> Dict[str, float]:
        """
        Interpolate between two expressions.

        Args:
            expr_a: Expression name, definition, or coefficient dict.
            expr_b: Expression name, definition, or coefficient dict.
            t: Blend factor (0-1).
            mode: Interpolation mode.
            **kwargs: Additional params for interpolator.

        Returns:
            Blended coefficient dictionary.
        """
        # Resolve names to definitions
        if isinstance(expr_a, str):
            defn_a = self._generator.get_definition(expr_a)
            if defn_a is None:
                raise ExpressionManagerError(f"Expression '{expr_a}' not found.")
            expr_a = defn_a
        if isinstance(expr_b, str):
            defn_b = self._generator.get_definition(expr_b)
            if defn_b is None:
                raise ExpressionManagerError(f"Expression '{expr_b}' not found.")
            expr_b = defn_b

        return self._interpolator.interpolate(expr_a, expr_b, t, mode, **kwargs)

    def blend_multi(
        self,
        expressions: List[Union[str, ExpressionDefinition, Dict[str, float]]],
        weights: Optional[List[float]] = None,
        normalize: bool = True,
    ) -> Dict[str, float]:
        """
        Blend multiple expressions.

        Args:
            expressions: List of expressions (names, definitions, or coeff dicts).
            weights: Optional weights (must sum to 1).
            normalize: If True, normalize weights.

        Returns:
            Blended coefficient dictionary.
        """
        # Resolve strings
        resolved = []
        for expr in expressions:
            if isinstance(expr, str):
                defn = self._generator.get_definition(expr)
                if defn is None:
                    raise ExpressionManagerError(f"Expression '{expr}' not found.")
                resolved.append(defn)
            else:
                resolved.append(expr)
        return self._interpolator.blend_multi(resolved, weights, normalize)

    # ---- Mirroring ----

    def mirror_expression(
        self,
        name: str,
        direction: str = "left_to_right",
        new_name: Optional[str] = None,
        partial_regions: Optional[List[str]] = None,
    ) -> Optional[ExpressionEntry]:
        """
        Mirror an existing expression.

        Args:
            name: Expression name.
            direction: 'left_to_right', 'right_to_left', or 'both'.
            new_name: Name for mirrored copy (default: name + '_mirrored').
            partial_regions: Optional list of regions to mirror.

        Returns:
            Mirrored ExpressionEntry, or None if failed.
        """
        entry = self._library.get(name)
        if entry is None:
            defn = self._generator.get_definition(name)
            if defn is None:
                return None
            # Temporary entry
            meta = ExpressionMetadata(id="temp", name=name, created="", modified="", author="")
            entry = ExpressionEntry(definition=defn, metadata=meta)

        # Mirror definition
        mirrored_defn = self._mirror.mirror_definition(entry.definition, direction, partial_regions)
        if new_name is None:
            new_name = f"{name}_mirrored"

        # Add to library
        try:
            return self.create(
                name=new_name,
                coefficients=mirrored_defn.coefficients,
                description=f"Mirrored from {name}",
                tags=entry.metadata.tags + ["mirrored"],
                category=entry.metadata.category,
                source="mirrored",
            )
        except Exception as e:
            logger.error(f"Failed to mirror expression: {e}")
            return None

    def mirror_coefficients(self, coefficients: Dict[str, float], direction: str = "left_to_right") -> Dict[str, float]:
        """Mirror a coefficient dictionary."""
        return self._mirror.mirror_coefficients(coefficients, direction)

    # ---- Library Management ----

    def import_library(self, filepath: Union[str, Path], source: str = "imported", overwrite: bool = False) -> int:
        """
        Import expressions from a JSON file.

        Args:
            filepath: Path to JSON file.
            source: Source label.
            overwrite: Overwrite existing entries.

        Returns:
            Number of entries imported.
        """
        return self._library.import_from_file(filepath, source, overwrite)

    def export_library(self, filepath: Union[str, Path], include_builtin: bool = False) -> None:
        """Export the library to a JSON file."""
        self._library.export_to_file(filepath, include_builtin)

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics."""
        stats = self._library.get_statistics()
        stats["generator_builtin_count"] = len(self._generator.get_builtin_names())
        return stats

    # ---- Validation ----

    def validate(self, name: str) -> Dict[str, Any]:
        """
        Validate an expression.

        Args:
            name: Expression name.

        Returns:
            Dict with 'valid' (bool), 'errors', 'warnings'.
        """
        entry = self.get(name)
        result = {"valid": True, "errors": [], "warnings": []}
        if entry is None:
            result["valid"] = False
            result["errors"].append(f"Expression '{name}' not found.")
            return result

        # Check coefficients range
        for k, v in entry.definition.coefficients.items():
            if not 0.0 <= v <= 1.0:
                result["valid"] = False
                result["errors"].append(f"Coefficient '{k}' out of range: {v}")

        # Check for unknown channels (optional)
        try:
            from ..arkit.arkit52 import ARKIT_SET
            for k in entry.definition.coefficients:
                if k not in ARKIT_SET:
                    result["warnings"].append(f"Channel '{k}' is not in standard ARKit set.")
        except ImportError:
            pass

        return result

    # ---- Utility ----

    def refresh(self) -> None:
        """Refresh the manager state (reload built-ins, etc.)."""
        # We could reload built-in presets into generator and library
        # For simplicity, we'll just ensure generator has built-ins
        self._preset_manager.install_all(self._generator)
        self._dirty = False

    def clear(self) -> None:
        """Clear all user/imported expressions from the library."""
        self._library.clear()
        self._dirty = True

    def is_dirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self._dirty or self._library.is_dirty()

    def mark_clean(self) -> None:
        """Mark the manager as clean (no unsaved changes)."""
        self._dirty = False
        self._library.mark_clean()

    # ---- Dependency Access ----

    @property
    def generator(self) -> ExpressionGenerator:
        return self._generator

    @property
    def library(self) -> ExpressionLibrary:
        return self._library

    @property
    def editor(self) -> ExpressionEditor:
        return self._editor

    @property
    def presets(self) -> PresetManager:
        return self._preset_manager


# ---- Public API ----

__all__ = [
    "ExpressionManager",
    "ExpressionManagerError",
]