"""
maya_faceit.expression.interpolation

Expression Blending and Interpolation Engine.

This module provides tools for smoothly blending multiple facial expressions
using various interpolation modes. It supports linear, cubic, ease-in/out,
Bezier, ARKit-style interpolation, and corrective interpolation.

The module works with expression coefficient dictionaries (channel -> weight)
and can be used for live facial tracking, animation, and pose blending.

Responsibilities:
- Linear interpolation between two expressions.
- Cubic (smooth) interpolation.
- Ease-in, ease-out, ease-in-out interpolation.
- Bezier curve interpolation with control points.
- ARKit blendshape interpolation with calibration.
- Corrective interpolation for combination expressions.
- Multi-expression blending with weights.

Dependencies:
- expression.generator: ExpressionDefinition.
- expression.editor: ExpressionEditor.
- blendshape_utils: normalize_weights, clamp.
- arkit.mapper: ARKitMapper (optional).

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import logging
import math
from typing import List, Optional, Dict, Any, Tuple, Union, Callable

# Import modules (with fallbacks)
try:
    from .generator import ExpressionDefinition, ExpressionGenerator, ExpressionType
    from .editor import ExpressionEditor
    from ..blendshapes.blendshape_utils import clamp, normalize_weights
    from ..arkit.mapper import ARKitMapper
    from ..arkit.arkit52 import ARKIT_SET
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionGenerator: pass
    class ExpressionType: pass
    class ExpressionEditor: pass
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def normalize_weights(weights): return {k: v / sum(weights.values()) if sum(weights.values()) else 0.0 for k, v in weights.items()}
    class ARKitMapper: pass
    ARKIT_SET = set()
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class InterpolationError(Exception):
    """Base exception for interpolation errors."""
    pass


# ---- Interpolation Modes ----

class InterpolationMode:
    """Constants for interpolation modes."""
    LINEAR = "linear"
    CUBIC = "cubic"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BEZIER = "bezier"
    ARKIT = "arkit"
    CORRECTIVE = "corrective"


# ---- Easing Functions ----

def ease_in(t: float) -> float:
    """Quadratic ease-in: t^2."""
    return t * t

def ease_out(t: float) -> float:
    """Quadratic ease-out: 1 - (1-t)^2."""
    return 1 - (1 - t) * (1 - t)

def ease_in_out(t: float) -> float:
    """Quadratic ease-in-out: t < 0.5 ? 2*t^2 : 1 - 2*(1-t)^2."""
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - 2 * (1 - t) * (1 - t)

def cubic_bezier(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """
    Cubic Bezier evaluation for a single dimension.
    Returns the interpolated value.
    """
    u = 1 - t
    return (u*u*u * p0) + (3*u*u*t * p1) + (3*u*t*t * p2) + (t*t*t * p3)


# ---- ExpressionInterpolator Class ----

class ExpressionInterpolator:
    """
    Blends and interpolates facial expressions.

    Supports various interpolation modes and can work with expression
    definitions, coefficient dictionaries, or ARKit inputs.
    """

    def __init__(
        self,
        generator: Optional[ExpressionGenerator] = None,
        editor: Optional[ExpressionEditor] = None,
        arkit_mapper: Optional[ARKitMapper] = None,
    ):
        """
        Initialize the interpolator.

        Args:
            generator: ExpressionGenerator for accessing definitions.
            editor: ExpressionEditor for modifying expressions.
            arkit_mapper: ARKitMapper for ARKit-specific interpolation.
        """
        self._generator = generator or ExpressionGenerator()
        self._editor = editor
        self._arkit_mapper = arkit_mapper or ARKitMapper()

    # ---- Core Interpolation ----

    def interpolate(
        self,
        expr_a: Union[ExpressionDefinition, Dict[str, float]],
        expr_b: Union[ExpressionDefinition, Dict[str, float]],
        t: float,
        mode: str = InterpolationMode.LINEAR,
        **kwargs,
    ) -> Dict[str, float]:
        """
        Interpolate between two expressions.

        Args:
            expr_a: First expression (definition or coefficient dict).
            expr_b: Second expression.
            t: Blend factor (0.0 = expr_a, 1.0 = expr_b).
            mode: Interpolation mode (linear, cubic, ease_*, bezier, arkit, corrective).
            **kwargs: Additional parameters (e.g., bezier_control_points for Bezier).

        Returns:
            Dictionary of blended coefficients.
        """
        # Validate t
        t = clamp(t, 0.0, 1.0)

        # Convert expressions to coefficient dicts
        coeffs_a = self._to_coefficients(expr_a)
        coeffs_b = self._to_coefficients(expr_b)

        # Compute interpolation factor based on mode
        if mode == InterpolationMode.LINEAR:
            factor = t
        elif mode == InterpolationMode.CUBIC:
            factor = t * t * (3 - 2 * t)  # smoothstep
        elif mode == InterpolationMode.EASE_IN:
            factor = ease_in(t)
        elif mode == InterpolationMode.EASE_OUT:
            factor = ease_out(t)
        elif mode == InterpolationMode.EASE_IN_OUT:
            factor = ease_in_out(t)
        elif mode == InterpolationMode.BEZIER:
            # Expect control points: p1, p2 for the curve (p0=0, p3=1)
            p1 = kwargs.get("bezier_p1", 0.25)
            p2 = kwargs.get("bezier_p2", 0.75)
            factor = cubic_bezier(t, 0.0, p1, p2, 1.0)
        elif mode == InterpolationMode.ARKIT:
            # ARKit interpolation may be calibrated; we'll use a linear blend by default
            # but could apply additional smoothing.
            factor = t
            # Possibly apply ARKit-specific remapping
            if hasattr(self, "_arkit_interp"):
                factor = self._arkit_interp(t)
        elif mode == InterpolationMode.CORRECTIVE:
            # Corrective interpolation: blend with corrective shape adjustments.
            # This could involve additional corrective coefficients.
            factor = t
            # We might need to compute corrective deltas.
            # For now, just linear.
        else:
            raise InterpolationError(f"Unsupported interpolation mode: {mode}")

        # Blend coefficients
        all_keys = set(coeffs_a.keys()) | set(coeffs_b.keys())
        blended = {}
        for key in all_keys:
            val_a = coeffs_a.get(key, 0.0)
            val_b = coeffs_b.get(key, 0.0)
            blended[key] = val_a * (1 - factor) + val_b * factor

        # Clamp to [0,1]
        for k in blended:
            blended[k] = clamp(blended[k], 0.0, 1.0)

        return blended

    def blend_multi(
        self,
        expressions: List[Union[ExpressionDefinition, Dict[str, float]]],
        weights: Optional[List[float]] = None,
        normalize: bool = True,
        mode: str = InterpolationMode.LINEAR,
        **kwargs,
    ) -> Dict[str, float]:
        """
        Blend multiple expressions with given weights.

        Args:
            expressions: List of expressions (definitions or coefficient dicts).
            weights: List of weights (must sum to 1). If None, equal weights.
            normalize: If True, normalize weights to sum to 1.
            mode: Interpolation mode for pair-wise blending (not used for multi?).
            **kwargs: Additional parameters.

        Returns:
            Blended coefficient dictionary.
        """
        if not expressions:
            return {}

        # Default weights
        if weights is None:
            weights = [1.0 / len(expressions)] * len(expressions)
        if len(weights) != len(expressions):
            raise InterpolationError("Number of weights must match number of expressions.")
        if normalize:
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]

        # Convert all to coefficient dicts
        coeffs_list = [self._to_coefficients(expr) for expr in expressions]

        # Collect all keys
        all_keys = set()
        for coeffs in coeffs_list:
            all_keys.update(coeffs.keys())

        # Blend
        blended = {}
        for key in all_keys:
            total_val = 0.0
            for coeffs, w in zip(coeffs_list, weights):
                total_val += coeffs.get(key, 0.0) * w
            blended[key] = clamp(total_val, 0.0, 1.0)

        return blended

    # ---- ARKit-Specific Interpolation ----

    def interpolate_arkit(
        self,
        arkit_coeffs_a: Dict[str, float],
        arkit_coeffs_b: Dict[str, float],
        t: float,
        mapping: Optional[ARKitMapper] = None,
        mode: str = InterpolationMode.LINEAR,
    ) -> Dict[str, float]:
        """
        Interpolate between two ARKit coefficient sets and map to blendshape coefficients.

        Args:
            arkit_coeffs_a: ARKit coefficients (channel -> value).
            arkit_coeffs_b: ARKit coefficients (channel -> value).
            t: Blend factor.
            mapping: Optional ARKitMapper; uses default if None.
            mode: Interpolation mode (linear, ease, etc.).

        Returns:
            Blended and mapped blendshape coefficients.
        """
        # Validate ARKit coefficients
        for k in arkit_coeffs_a:
            if k not in ARKIT_SET:
                logger.warning(f"Unknown ARKit channel: {k}")
        for k in arkit_coeffs_b:
            if k not in ARKIT_SET:
                logger.warning(f"Unknown ARKit channel: {k}")

        # Interpolate ARKit coefficients
        all_keys = set(arkit_coeffs_a.keys()) | set(arkit_coeffs_b.keys())
        blended_arkit = {}
        for key in all_keys:
            val_a = arkit_coeffs_a.get(key, 0.0)
            val_b = arkit_coeffs_b.get(key, 0.0)
            # Apply interpolation factor based on mode
            if mode == InterpolationMode.LINEAR:
                factor = t
            elif mode == InterpolationMode.EASE_IN:
                factor = ease_in(t)
            elif mode == InterpolationMode.EASE_OUT:
                factor = ease_out(t)
            elif mode == InterpolationMode.EASE_IN_OUT:
                factor = ease_in_out(t)
            else:
                factor = t
            blended_arkit[key] = val_a * (1 - factor) + val_b * factor
            blended_arkit[key] = clamp(blended_arkit[key], 0.0, 1.0)

        # Map to blendshape coefficients
        mapper = mapping or self._arkit_mapper
        return mapper.map(blended_arkit)

    # ---- Corrective Interpolation ----

    def interpolate_corrective(
        self,
        base_expr: Union[ExpressionDefinition, Dict[str, float]],
        corrective_expr: Union[ExpressionDefinition, Dict[str, float]],
        t: float,
        base_expression_name: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Apply corrective interpolation: blend base expression with a corrective shape.

        Corrective shapes are typically used to fix deformation artifacts.
        This method blends the base with corrective coefficients,
        optionally clamping or normalizing.

        Args:
            base_expr: Base expression (definition or coefficients).
            corrective_expr: Corrective expression.
            t: Blend factor (0 = base, 1 = fully corrective).
            base_expression_name: If provided, used to fetch corrective definitions.

        Returns:
            Blended coefficients.
        """
        base_coeffs = self._to_coefficients(base_expr)
        corr_coeffs = self._to_coefficients(corrective_expr)

        # Corrective interpolation: typically we add corrective deltas
        # but we can also blend linearly.
        all_keys = set(base_coeffs.keys()) | set(corr_coeffs.keys())
        blended = {}
        for key in all_keys:
            val_base = base_coeffs.get(key, 0.0)
            val_corr = corr_coeffs.get(key, 0.0)
            # We want to add corrective influence, but avoid exceeding 1.0
            # A common approach: blend with additive offset
            # For simplicity, we'll use linear blend
            blended[key] = val_base * (1 - t) + val_corr * t
            blended[key] = clamp(blended[key], 0.0, 1.0)

        return blended

    # ---- Utility Methods ----

    def _to_coefficients(
        self,
        expr: Union[ExpressionDefinition, Dict[str, float]]
    ) -> Dict[str, float]:
        """Convert expression to coefficient dictionary."""
        if isinstance(expr, ExpressionDefinition):
            return expr.coefficients.copy()
        elif isinstance(expr, dict):
            return expr.copy()
        else:
            raise TypeError(f"Expected ExpressionDefinition or dict, got {type(expr)}")

    def get_expression_coefficients(self, name: str) -> Dict[str, float]:
        """Retrieve coefficients of a named expression from the generator."""
        if self._generator:
            defn = self._generator.get_definition(name)
            if defn:
                return defn.coefficients.copy()
        raise InterpolationError(f"Expression '{name}' not found.")


# ---- Public API ----

__all__ = [
    "ExpressionInterpolator",
    "InterpolationMode",
    "InterpolationError",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "cubic_bezier",
]