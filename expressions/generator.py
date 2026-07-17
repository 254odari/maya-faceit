"""
maya_faceit.expression.generator

Core Expression Creation Engine for Maya Faceit.

This module automatically generates facial expressions as sets of blendshape
coefficients. It supports built-in expressions (smile, blink, brow raise, etc.),
custom expressions, and generation from ARKit coefficients or existing poses.

The generator integrates with:
- Blendshape Builder: to create new blendshape targets on meshes.
- ARKit Mapper: to map ARKit blendshape coefficients to expressions.
- Pose Library: to reuse and combine existing poses.

Responsibilities:
- Generate expression coefficient dictionaries for built-in expressions.
- Create new blendshape targets in Maya from expression definitions.
- Combine expressions using blendshape combiner.
- Validate expressions before generation.
- Provide statistics and diagnostics.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Union, Callable

# Maya imports (with fallback for testing)
try:
    import maya.cmds as cmds
except ImportError:
    # Dummy for testing
    class DummyCmds:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyCmds()

# Imports from other modules (with fallbacks)
try:
    from ..blendshapes.blendshape_creator import BlendShapeCreator, BlendShapeTarget, TargetType
    from ..blendshapes.blendshape_combiner import BlendshapeCombiner, BlendshapeCombination, CombinationMode
    from ..blendshapes.blendshape_generator import BlendshapeGenerator, GenerationTarget, GeneratorType
    from ..blendshapes.blendshape_validator import BlendshapeValidator
    from ..blendshapes.blendshape_pose import BlendshapePoseManager, PoseDefinition
    from ..blendshapes.blendshape_utils import (
        get_blendshape_targets, get_blendshape_weight, set_blendshape_weight,
        sanitize_name, clamp, normalize_weights
    )
    from ..arkit.arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET
    from ..arkit.mapper import ARKitMapper, ARKitMapping
except ImportError:
    # Minimal fallback for development
    class BlendShapeCreator: pass
    class BlendShapeTarget: pass
    class TargetType: pass
    class BlendshapeCombiner: pass
    class BlendshapeCombination: pass
    class CombinationMode: pass
    class BlendshapeGenerator: pass
    class GenerationTarget: pass
    class GeneratorType: pass
    class BlendshapeValidator: pass
    class BlendshapePoseManager: pass
    class PoseDefinition: pass
    def get_blendshape_targets(*args): return []
    def get_blendshape_weight(*args): return 0.0
    def set_blendshape_weight(*args): pass
    def sanitize_name(name): return name
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights): return weights
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    class ARKitMapper: pass
    class ARKitMapping: pass

# ---- Part 1: Foundation ------------------------------------------------

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# Exceptions
class ExpressionError(Exception):
    """Base exception for expression generation."""
    pass

class ExpressionNotFoundError(ExpressionError):
    """Raised when a requested expression is not found."""
    pass

class ExpressionValidationError(ExpressionError):
    """Raised when expression data fails validation."""
    pass

class ExpressionGenerationError(ExpressionError):
    """Raised when generation fails."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class ExpressionType(Enum):
    """Types of expressions."""
    BASIC = "basic"
    ARKIT = "arkit"
    CUSTOM = "custom"
    COMBINATION = "combination"


class GenerationMode(Enum):
    """How to generate the expression (coefficients only or create targets)."""
    COEFFICIENTS = "coefficients"
    TARGETS = "targets"
    BOTH = "both"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class ExpressionDefinition:
    """Definition of an expression."""
    name: str
    coefficients: Dict[str, float]  # blendshape target -> weight
    expression_type: ExpressionType = ExpressionType.BASIC
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Basic validation: ensure coefficients are within [0,1]."""
        for k, v in self.coefficients.items():
            if v < 0.0 or v > 1.0:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "coefficients": self.coefficients,
            "type": self.expression_type.value,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpressionDefinition':
        return cls(
            name=data["name"],
            coefficients=data["coefficients"],
            expression_type=ExpressionType(data.get("type", "basic")),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExpressionResult:
    """Result of generating an expression."""
    success: bool
    message: str
    definition: Optional[ExpressionDefinition] = None
    created_targets: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---- Part 4: Expression Generator --------------------------------------

class ExpressionGenerator:
    """
    Core engine for generating facial expressions.

    This class provides methods to generate expression coefficients,
    create blendshape targets, and combine expressions.
    """

    def __init__(
        self,
        blendshape_creator: Optional[BlendShapeCreator] = None,
        combiner: Optional[BlendshapeCombiner] = None,
        generator: Optional[BlendshapeGenerator] = None,
        validator: Optional[BlendshapeValidator] = None,
        pose_manager: Optional[BlendshapePoseManager] = None,
        arkit_mapper: Optional[ARKitMapper] = None,
    ):
        """
        Initialize the expression generator.

        Args:
            blendshape_creator: Used to create blendshape targets on meshes.
            combiner: Used to combine multiple expressions.
            generator: Used to procedurally generate target meshes.
            validator: Used to validate expressions and meshes.
            pose_manager: Used to manage and apply poses.
            arkit_mapper: Used to map ARKit coefficients to expressions.
        """
        self._creator = blendshape_creator or BlendShapeCreator()
        self._combiner = combiner or BlendshapeCombiner()
        self._generator = generator or BlendshapeGenerator()
        self._validator = validator or BlendshapeValidator()
        self._pose_manager = pose_manager or BlendshapePoseManager()
        self._arkit_mapper = arkit_mapper or ARKitMapper()

        # Built-in expression definitions (cached)
        self._builtin_expressions: Dict[str, ExpressionDefinition] = {}
        self._init_builtin_expressions()

        # Generation settings
        self._settings = {
            "normalize_coefficients": True,
            "clamp_to_range": True,
            "validate_before_generation": True,
        }

    # ---- Built-in Expression Definitions ----

    def _init_builtin_expressions(self) -> None:
        """Initialize the built-in expression definitions."""
        # These are base definitions; they may be overridden by custom data.
        # All coefficients are in [0,1].
        self._builtin_expressions = {
            "Neutral": ExpressionDefinition(
                name="Neutral",
                coefficients={},
                description="Neutral expression (all zero).",
                tags=["base"],
            ),
            "Smile": ExpressionDefinition(
                name="Smile",
                coefficients={
                    "mouthSmileLeft": 0.9,
                    "mouthSmileRight": 0.9,
                    "cheekSquintLeft": 0.3,
                    "cheekSquintRight": 0.3,
                    "eyeSquintLeft": 0.15,
                    "eyeSquintRight": 0.15,
                },
                description="Happy smile with cheek and eye squint.",
                tags=["happy", "positive"],
            ),
            "Frown": ExpressionDefinition(
                name="Frown",
                coefficients={
                    "mouthFrownLeft": 0.8,
                    "mouthFrownRight": 0.8,
                    "browInnerUp": 0.5,
                },
                description="Frown expression with brows raised.",
                tags=["sad", "negative"],
            ),
            "Blink": ExpressionDefinition(
                name="Blink",
                coefficients={
                    "eyeBlinkLeft": 1.0,
                    "eyeBlinkRight": 1.0,
                },
                description="Both eyes blink closed.",
                tags=["eye"],
            ),
            "WinkLeft": ExpressionDefinition(
                name="WinkLeft",
                coefficients={
                    "eyeBlinkLeft": 1.0,
                },
                description="Left eye wink.",
                tags=["eye", "left"],
            ),
            "WinkRight": ExpressionDefinition(
                name="WinkRight",
                coefficients={
                    "eyeBlinkRight": 1.0,
                },
                description="Right eye wink.",
                tags=["eye", "right"],
            ),
            "Squint": ExpressionDefinition(
                name="Squint",
                coefficients={
                    "eyeSquintLeft": 1.0,
                    "eyeSquintRight": 1.0,
                },
                description="Eyes squinting.",
                tags=["eye"],
            ),
            "JawOpen": ExpressionDefinition(
                name="JawOpen",
                coefficients={
                    "jawOpen": 1.0,
                },
                description="Jaw open.",
                tags=["jaw"],
            ),
            "JawLeft": ExpressionDefinition(
                name="JawLeft",
                coefficients={
                    "jawLeft": 1.0,
                },
                description="Jaw moved left.",
                tags=["jaw", "left"],
            ),
            "JawRight": ExpressionDefinition(
                name="JawRight",
                coefficients={
                    "jawRight": 1.0,
                },
                description="Jaw moved right.",
                tags=["jaw", "right"],
            ),
            "JawForward": ExpressionDefinition(
                name="JawForward",
                coefficients={
                    "jawForward": 1.0,
                },
                description="Jaw protrusion.",
                tags=["jaw"],
            ),
            "MouthLeft": ExpressionDefinition(
                name="MouthLeft",
                coefficients={
                    "mouthLeft": 1.0,
                },
                description="Mouth moved left (jaw side).",
                tags=["mouth", "left"],
            ),
            "MouthRight": ExpressionDefinition(
                name="MouthRight",
                coefficients={
                    "mouthRight": 1.0,
                },
                description="Mouth moved right (jaw side).",
                tags=["mouth", "right"],
            ),
            "LipRollLower": ExpressionDefinition(
                name="LipRollLower",
                coefficients={
                    "mouthRollLower": 1.0,
                },
                description="Lower lip rolled inward.",
                tags=["mouth"],
            ),
            "LipRollUpper": ExpressionDefinition(
                name="LipRollUpper",
                coefficients={
                    "mouthRollUpper": 1.0,
                },
                description="Upper lip rolled inward.",
                tags=["mouth"],
            ),
            "CheekPuff": ExpressionDefinition(
                name="CheekPuff",
                coefficients={
                    "cheekPuff": 1.0,
                },
                description="Cheeks puffed out.",
                tags=["cheek"],
            ),
            "BrowRaise": ExpressionDefinition(
                name="BrowRaise",
                coefficients={
                    "browInnerUp": 0.8,
                    "browOuterUpLeft": 0.6,
                    "browOuterUpRight": 0.6,
                },
                description="Brows raised (surprise style).",
                tags=["brow", "surprise"],
            ),
            "BrowLower": ExpressionDefinition(
                name="BrowLower",
                coefficients={
                    "browDownLeft": 0.8,
                    "browDownRight": 0.8,
                },
                description="Brows lowered (anger style).",
                tags=["brow", "anger"],
            ),
            "NoseSneer": ExpressionDefinition(
                name="NoseSneer",
                coefficients={
                    "noseSneerLeft": 0.9,
                    "noseSneerRight": 0.9,
                },
                description="Nose sneer (disgust style).",
                tags=["nose", "disgust"],
            ),
            "TongueOut": ExpressionDefinition(
                name="TongueOut",
                coefficients={
                    "tongueOut": 1.0,
                },
                description="Tongue protrusion.",
                tags=["tongue"],
            ),
        }
        # Add ARKit-specific definitions if needed
        # (ARKIT_BLENDSHAPES is imported)

    # ---- Main Generation Methods ----

    def generate(
        self,
        expression_name: str,
        mode: GenerationMode = GenerationMode.COEFFICIENTS,
        base_mesh: Optional[str] = None,
        target_node: Optional[str] = None,
        intensity: float = 1.0,
        custom_coefficients: Optional[Dict[str, float]] = None,
    ) -> ExpressionResult:
        """
        Generate an expression by name, optionally creating blendshape targets.

        Args:
            expression_name: Name of the expression (built-in or custom).
            mode: How to generate (coefficients only, targets, or both).
            base_mesh: The mesh to apply the expression to (required for TARGETS).
            target_node: The blendshape node to add targets to (if None, auto-create).
            intensity: Scale factor for coefficients (0.0 - 1.0).
            custom_coefficients: If provided, use these instead of built-in.

        Returns:
            ExpressionResult with details.
        """
        start_time = time.time()
        result = ExpressionResult(success=False, message="", errors=[], warnings=[])

        # 1. Get the definition
        if custom_coefficients is not None:
            # Use custom coefficients
            defn = ExpressionDefinition(
                name=expression_name,
                coefficients=custom_coefficients,
                expression_type=ExpressionType.CUSTOM,
            )
        else:
            # Look up built-in
            if expression_name not in self._builtin_expressions:
                result.errors.append(f"Expression '{expression_name}' not found.")
                result.elapsed_time = time.time() - start_time
                return result
            defn = copy.deepcopy(self._builtin_expressions[expression_name])

        # 2. Apply intensity
        if intensity != 1.0:
            for k in defn.coefficients:
                defn.coefficients[k] = clamp(defn.coefficients[k] * intensity, 0.0, 1.0)

        # 3. Validate
        if self._settings.get("validate_before_generation", True):
            if not defn.validate():
                result.errors.append("Invalid coefficients (out of range).")
                result.elapsed_time = time.time() - start_time
                return result

        # 4. Normalize (optional)
        if self._settings.get("normalize_coefficients", True):
            defn.coefficients = normalize_weights(defn.coefficients)

        # 5. Generate targets if requested
        if mode in (GenerationMode.TARGETS, GenerationMode.BOTH):
            if not base_mesh:
                result.errors.append("base_mesh is required for target generation.")
                result.elapsed_time = time.time() - start_time
                return result
            try:
                targets = self._create_targets(base_mesh, defn, target_node)
                result.created_targets.extend(targets)
            except Exception as e:
                result.errors.append(f"Failed to create targets: {e}")
                result.elapsed_time = time.time() - start_time
                return result

        # 6. Success
        result.success = True
        result.definition = defn
        result.message = f"Generated expression '{expression_name}'."
        result.elapsed_time = time.time() - start_time
        return result

    def generate_smile(self, **kwargs) -> ExpressionResult:
        """Convenience method to generate a smile."""
        return self.generate("Smile", **kwargs)

    def generate_blink(self, **kwargs) -> ExpressionResult:
        """Convenience method to generate a blink."""
        return self.generate("Blink", **kwargs)

    def generate_wink_left(self, **kwargs) -> ExpressionResult:
        return self.generate("WinkLeft", **kwargs)

    def generate_wink_right(self, **kwargs) -> ExpressionResult:
        return self.generate("WinkRight", **kwargs)

    def generate_squint(self, **kwargs) -> ExpressionResult:
        return self.generate("Squint", **kwargs)

    def generate_jaw_open(self, **kwargs) -> ExpressionResult:
        return self.generate("JawOpen", **kwargs)

    def generate_from_arkit(
        self,
        arkit_coefficients: Dict[str, float],
        base_mesh: str,
        mode: GenerationMode = GenerationMode.COEFFICIENTS,
        mapping: Optional[ARKitMapping] = None,
        target_node: Optional[str] = None,
    ) -> ExpressionResult:
        """
        Generate an expression from ARKit blendshape coefficients.

        This applies the ARKit mapping to convert raw ARKit coefficients to the
        target blendshape system.

        Args:
            arkit_coefficients: Dict of ARKit channel -> value.
            base_mesh: The mesh to apply to.
            mode: Generation mode.
            mapping: Optional custom ARKit mapping; uses default if None.
            target_node: Target blendshape node.

        Returns:
            ExpressionResult.
        """
        start_time = time.time()
        result = ExpressionResult(success=False, message="", errors=[])

        # Validate arkit coefficients
        for k, v in arkit_coefficients.items():
            if k not in ARKIT_SET:
                result.warnings.append(f"Unknown ARKit channel: {k}")
            if v < 0.0 or v > 1.0:
                result.errors.append(f"ARKit coefficient {k} out of range: {v}")
        if result.errors:
            result.elapsed_time = time.time() - start_time
            return result

        # Map to blendshape coefficients
        if mapping:
            mapped = mapping.map(arkit_coefficients)
        else:
            mapped = self._arkit_mapper.map(arkit_coefficients)

        # Generate using the mapped coefficients
        expr_name = "ARKit_Generated"
        custom_result = self.generate(
            expression_name=expr_name,
            mode=mode,
            base_mesh=base_mesh,
            target_node=target_node,
            custom_coefficients=mapped,
        )
        # Merge results
        result.success = custom_result.success
        result.message = custom_result.message
        result.definition = custom_result.definition
        result.created_targets = custom_result.created_targets
        result.warnings.extend(custom_result.warnings)
        result.errors.extend(custom_result.errors)
        result.elapsed_time = time.time() - start_time
        return result

    def generate_from_pose(
        self,
        pose_name: str,
        base_mesh: str,
        mode: GenerationMode = GenerationMode.COEFFICIENTS,
        intensity: float = 1.0,
        target_node: Optional[str] = None,
    ) -> ExpressionResult:
        """
        Generate an expression from a pose stored in the pose library.

        Args:
            pose_name: Name of the pose.
            base_mesh: The mesh to apply to.
            mode: Generation mode.
            intensity: Scale factor.
            target_node: Target blendshape node.

        Returns:
            ExpressionResult.
        """
        start_time = time.time()
        result = ExpressionResult(success=False, message="", errors=[])

        # Get the pose from the pose manager
        pose: Optional[PoseDefinition] = None
        if self._pose_manager:
            pose = self._pose_manager.get_pose(pose_name)
        if pose is None:
            result.errors.append(f"Pose '{pose_name}' not found in library.")
            result.elapsed_time = time.time() - start_time
            return result

        # Use the pose's weights as coefficients
        coefficients = pose.weights
        if intensity != 1.0:
            for k in coefficients:
                coefficients[k] = clamp(coefficients[k] * intensity, 0.0, 1.0)

        # Generate
        custom_result = self.generate(
            expression_name=pose_name,
            mode=mode,
            base_mesh=base_mesh,
            target_node=target_node,
            custom_coefficients=coefficients,
        )
        result.success = custom_result.success
        result.message = custom_result.message
        result.definition = custom_result.definition
        result.created_targets = custom_result.created_targets
        result.warnings.extend(custom_result.warnings)
        result.errors.extend(custom_result.errors)
        result.elapsed_time = time.time() - start_time
        return result

    def generate_all(self, base_mesh: str, mode: GenerationMode = GenerationMode.TARGETS) -> List[ExpressionResult]:
        """
        Generate all built-in expressions and optionally create targets.

        Args:
            base_mesh: The mesh to apply expressions to.
            mode: Generation mode.

        Returns:
            List of ExpressionResult for each expression.
        """
        results = []
        for name in self._builtin_expressions.keys():
            result = self.generate(
                expression_name=name,
                mode=mode,
                base_mesh=base_mesh,
            )
            results.append(result)
            if not result.success:
                logger.error(f"Failed to generate {name}: {result.errors}")
        return results

    def combine(
        self,
        expression_names: List[str],
        base_mesh: str,
        mode: GenerationMode = GenerationMode.COEFFICIENTS,
        weights: Optional[List[float]] = None,
        target_node: Optional[str] = None,
        combination_mode: str = "add",
        output_name: Optional[str] = None,
    ) -> ExpressionResult:
        """
        Combine multiple expressions into a new one using the blendshape combiner.

        Args:
            expression_names: List of expression names to combine.
            base_mesh: The mesh to apply to.
            mode: Generation mode.
            weights: Optional blend weights (default: equal).
            target_node: Target blendshape node.
            combination_mode: How to combine ('add', 'average', etc.).
            output_name: Name for the combined expression.

        Returns:
            ExpressionResult.
        """
        start_time = time.time()
        result = ExpressionResult(success=False, message="", errors=[])

        # Get definitions for each expression
        defs = []
        for name in expression_names:
            if name in self._builtin_expressions:
                defs.append(self._builtin_expressions[name])
            else:
                result.errors.append(f"Expression '{name}' not found.")
                result.elapsed_time = time.time() - start_time
                return result

        # If no weights, use equal weights
        if weights is None:
            weights = [1.0 / len(defs)] * len(defs)

        # Use combiner to blend coefficients
        # We'll create a combined definition
        combined_coeffs = {}
        all_keys = set()
        for d in defs:
            all_keys.update(d.coefficients.keys())
        for key in all_keys:
            total = 0.0
            for d, w in zip(defs, weights):
                total += d.coefficients.get(key, 0.0) * w
            combined_coeffs[key] = clamp(total, 0.0, 1.0)

        # Create combined definition
        combined_def = ExpressionDefinition(
            name=output_name or "_".join(expression_names),
            coefficients=combined_coeffs,
            expression_type=ExpressionType.COMBINATION,
            description=f"Combination of {', '.join(expression_names)}",
        )

        # Generate using the combined coefficients
        custom_result = self.generate(
            expression_name=combined_def.name,
            mode=mode,
            base_mesh=base_mesh,
            target_node=target_node,
            custom_coefficients=combined_def.coefficients,
        )
        result.success = custom_result.success
        result.message = custom_result.message
        result.definition = combined_def
        result.created_targets = custom_result.created_targets
        result.warnings.extend(custom_result.warnings)
        result.errors.extend(custom_result.errors)
        result.elapsed_time = time.time() - start_time
        return result

    # ---- Internal Helpers ----

    def _create_targets(self, base_mesh: str, defn: ExpressionDefinition, target_node: Optional[str] = None) -> List[str]:
        """
        Create blendshape targets for the given expression on the base mesh.

        This uses the blendshape generator to create target meshes from coefficients.

        Args:
            base_mesh: The base mesh.
            defn: Expression definition containing coefficients.
            target_node: Optional existing blendshape node.

        Returns:
            List of created target names.
        """
        if not self._generator:
            raise ExpressionGenerationError("Blendshape generator not available.")

        # For each coefficient, we need to generate a target mesh.
        # This is a placeholder; in a full implementation, we'd use
        # the generator to create actual target meshes for each channel.
        # Here we'll just create a single composite target.
        # We'll use the combiner to create a combined mesh.
        # Since we may not have individual target meshes, we'll use the
        # generator to generate a mesh for the combined coefficients.
        # We'll create a generation target with the coefficients.
        # Use generator to create a target mesh from the coefficients.
        # This is a simplified approach; production would handle each channel.
        # We'll leverage the generator's ability to create a composite target.
        # For now, we'll just create a dummy target.

        # In a real implementation, we would:
        # 1. For each channel in coefficients, check if a target mesh exists.
        # 2. If not, use generator to create it (using ARKit or procedural generation).
        # 3. Create a blendshape target on the node.
        # 4. Return the list of target names.

        # Placeholder: return an empty list.
        # This would be replaced with actual logic.
        logger.warning("_create_targets is a placeholder. No targets created.")
        return []

    # ---- Utility Methods ----

    def get_builtin_names(self) -> List[str]:
        """Return a list of built-in expression names."""
        return list(self._builtin_expressions.keys())

    def get_definition(self, name: str) -> Optional[ExpressionDefinition]:
        """Return the definition for a built-in expression."""
        return self._builtin_expressions.get(name)

    def add_custom_expression(self, definition: ExpressionDefinition) -> None:
        """Add a custom expression definition to the cache."""
        self._builtin_expressions[definition.name] = definition

    def remove_custom_expression(self, name: str) -> None:
        """Remove a custom expression definition."""
        if name in self._builtin_expressions:
            del self._builtin_expressions[name]
        else:
            raise ExpressionNotFoundError(f"Expression '{name}' not found.")

    def set_settings(self, **kwargs) -> None:
        """Update generator settings."""
        self._settings.update(kwargs)

    def get_settings(self) -> Dict[str, Any]:
        """Return current settings."""
        return self._settings.copy()


# ---- Part 5: Public API ------------------------------------------------

__all__ = [
    "ExpressionGenerator",
    "ExpressionDefinition",
    "ExpressionResult",
    "ExpressionType",
    "GenerationMode",
    "ExpressionError",
    "ExpressionNotFoundError",
    "ExpressionValidationError",
    "ExpressionGenerationError",
]