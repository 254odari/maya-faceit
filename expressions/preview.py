"""
maya_faceit.expression.preview

Preview Facial Expressions.

This module provides tools for previewing facial expressions in the Maya viewport,
with live updates, sliders, animation preview, comparison, and thumbnail generation.

It integrates with Maya's blendshape nodes and viewport to provide real-time feedback.

Responsibilities:
- Apply expression coefficients to a blendshape node on a target mesh.
- Update viewport with live preview.
- Provide slider-based preview for fine-tuning.
- Animate between expressions (timeline preview).
- Compare expressions side-by-side or with before/after.
- Generate thumbnails (viewport capture).
- Preview ARKit coefficients mapped to expressions.

Dependencies:
- Maya API (cmds, pymel) for viewport and blendshape manipulation.
- expression.generator: ExpressionDefinition.
- expression.manager: ExpressionManager.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

# Maya imports
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode
    HAS_MAYA = True
except ImportError:
    HAS_MAYA = False
    # Dummy for testing
    class DummyCmds:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyCmds()
    mel = DummyCmds()

# Imports from other modules (with fallbacks)
try:
    from .generator import ExpressionDefinition, ExpressionGenerator, ExpressionType
    from .manager import ExpressionManager
    from ..blendshapes.blendshape_utils import clamp, sanitize_name
    HAS_DEPS = True
except ImportError:
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionManager: pass
    def clamp(val, lo, hi): return max(lo, min(hi, val))
    def sanitize_name(name): return name
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class PreviewError(Exception):
    """Base exception for preview operations."""
    pass


# ---- Preview Modes ----

class PreviewMode:
    """Constants for preview modes."""
    STATIC = "static"          # Single expression
    SLIDER = "slider"          # Slider-based blending
    ANIMATION = "animation"    # Animated sequence
    COMPARE = "compare"        # Side-by-side comparison
    ARKIT = "arkit"            # ARKit live preview


# ---- ExpressionPreview Class ----

class ExpressionPreview:
    """
    Preview facial expressions in Maya viewport.

    This class manages the application of expression coefficients to a blendshape
    node, provides live updates, and supports various preview modes.

    Usage:
        preview = ExpressionPreview(mesh="faceMesh", blendshape_node="faceBS")
        preview.apply("Smile")
        preview.animate(["Smile", "Blink"], duration=2.0)
        preview.show_slider("Smile", 0.0, 1.0)
        preview.capture_thumbnail("smile.png")
    """

    def __init__(
        self,
        mesh: str,
        blendshape_node: Optional[str] = None,
        manager: Optional[ExpressionManager] = None,
        viewport_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the preview.

        Args:
            mesh: The mesh to apply blendshapes to (transform or shape).
            blendshape_node: Optional existing blendshape node; will find or create.
            manager: Optional ExpressionManager to resolve expression names.
            viewport_callback: Optional callback to update viewport after changes.
        """
        if not HAS_MAYA:
            raise PreviewError("Maya is not available for preview.")

        self._mesh = mesh
        self._blendshape_node = blendshape_node
        self._manager = manager

        # Ensure blendshape node exists
        self._ensure_blendshape_node()

        # Store current weights for blending
        self._current_weights: Dict[str, float] = {}

        # For animation preview
        self._anim_playing = False
        self._anim_start_time = 0.0
        self._anim_duration = 1.0
        self._anim_expressions: List[ExpressionDefinition] = []
        self._anim_callback = None

        # For slider preview
        self._slider_active = False

        # Thumbnail cache
        self._thumbnail_cache: Dict[str, Path] = {}

        # Viewport update callback
        self._viewport_callback = viewport_callback

    # ---- Blendshape Setup ----

    def _ensure_blendshape_node(self) -> None:
        """Ensure a blendshape node exists on the mesh."""
        if self._blendshape_node and cmds.objExists(self._blendshape_node):
            return

        # Find existing blendshape node connected to mesh
        bs_nodes = cmds.listConnections(self._mesh, type='blendShape') or []
        if bs_nodes:
            self._blendshape_node = bs_nodes[0]
            logger.info(f"Using existing blendshape node: {self._blendshape_node}")
            return

        # Create new node
        node_name = f"{sanitize_name(self._mesh)}_blendShape"
        if cmds.objExists(node_name):
            # Find unique name
            i = 1
            while cmds.objExists(f"{node_name}{i:02d}"):
                i += 1
            node_name = f"{node_name}{i:02d}"
        self._blendshape_node = cmds.blendShape(self._mesh, name=node_name)[0]
        logger.info(f"Created blendshape node: {self._blendshape_node}")

    # ---- Core Preview ----

    def apply(self, expression: Union[str, ExpressionDefinition, Dict[str, float]]) -> None:
        """
        Apply an expression to the blendshape node.

        Args:
            expression: Name (str), ExpressionDefinition, or coefficient dict.
        """
        # Resolve expression
        coeffs = self._resolve_coefficients(expression)

        # Reset all weights to 0 first (optional)
        # We'll set only the coefficients present, leaving others unchanged? Better to reset to 0 then apply.
        # But we want to keep non-zero weights? Usually we want to set the expression.
        # We'll reset all targets to 0 and then set the coefficients.
        targets = self._get_all_targets()
        for t in targets:
            cmds.setAttr(f"{self._blendshape_node}.{t}", 0.0)

        # Apply coefficients
        for target, weight in coeffs.items():
            if cmds.objExists(f"{self._blendshape_node}.{target}"):
                cmds.setAttr(f"{self._blendshape_node}.{target}", clamp(weight, 0.0, 1.0))
            else:
                # Target doesn't exist on this blendshape node; we might need to add it.
                logger.warning(f"Target '{target}' not found on blendshape node. Skipping.")

        self._current_weights = coeffs
        self._update_viewport()

    def apply_coefficients(self, coefficients: Dict[str, float]) -> None:
        """Apply a coefficient dictionary directly."""
        self.apply(coefficients)

    def reset(self) -> None:
        """Reset all blendshape weights to 0."""
        targets = self._get_all_targets()
        for t in targets:
            cmds.setAttr(f"{self._blendshape_node}.{t}", 0.0)
        self._current_weights = {}
        self._update_viewport()

    def get_current_weights(self) -> Dict[str, float]:
        """Return the current weights (as applied)."""
        return self._current_weights.copy()

    # ---- Slider Preview ----

    def show_slider(
        self,
        expression: Union[str, ExpressionDefinition, Dict[str, float]],
        min_val: float = 0.0,
        max_val: float = 1.0,
        initial: float = 0.5,
        callback: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Show a slider preview (interactive blending).

        Note: This is typically UI-driven. Here we provide a mechanism to update
        the blend factor programmatically.

        Args:
            expression: Expression to blend.
            min_val: Minimum slider value.
            max_val: Maximum slider value.
            initial: Initial value.
            callback: Optional callback for value changes.
        """
        self._slider_active = True
        # Store expression for blending
        self._slider_expression = expression
        self._slider_min = min_val
        self._slider_max = max_val
        self._slider_callback = callback
        # Apply at initial value
        self._update_slider(initial)

    def _update_slider(self, value: float) -> None:
        """Update slider preview with a new value."""
        if not hasattr(self, '_slider_expression'):
            return
        # Compute blend factor (0-1 mapped to min-max)
        t = (value - self._slider_min) / (self._slider_max - self._slider_min)
        t = clamp(t, 0.0, 1.0)
        # Get coefficients of the expression
        coeffs = self._resolve_coefficients(self._slider_expression)
        # Scale by t
        scaled = {k: v * t for k, v in coeffs.items()}
        # Apply
        self.apply(scaled)
        if self._slider_callback:
            self._slider_callback(value)

    # ---- Animation Preview ----

    def animate(
        self,
        expressions: List[Union[str, ExpressionDefinition, Dict[str, float]]],
        duration: float = 1.0,
        loop: bool = False,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Animate between multiple expressions.

        Args:
            expressions: List of expressions (names, definitions, or coeff dicts).
            duration: Total duration in seconds.
            loop: If True, loop the animation.
            callback: Optional callback when animation ends.
        """
        self._anim_expressions = []
        for expr in expressions:
            if isinstance(expr, str):
                defn = self._resolve_definition(expr)
                if defn:
                    self._anim_expressions.append(defn)
                else:
                    logger.warning(f"Expression '{expr}' not found; skipping.")
            elif isinstance(expr, ExpressionDefinition):
                self._anim_expressions.append(expr)
            elif isinstance(expr, dict):
                # Create a temporary definition
                self._anim_expressions.append(ExpressionDefinition(
                    name="temp",
                    coefficients=expr,
                ))
            else:
                logger.warning(f"Unsupported expression type: {type(expr)}")

        if not self._anim_expressions:
            raise PreviewError("No valid expressions to animate.")

        self._anim_duration = duration
        self._anim_loop = loop
        self._anim_callback = callback

        # Start animation
        self._anim_playing = True
        self._anim_start_time = time.time()

        # Set up a Maya scriptJob to update the animation each frame
        if HAS_MAYA:
            # We'll use a time change callback or a periodic update.
            # For simplicity, we can use Maya's animation playback.
            # But we want independent control. We'll use a scriptJob on timeChanged.
            # Alternatively, we can use a simple polling loop, but that blocks Maya.
            # We'll set up a scriptJob that calls update_animation on timeChange.
            # However, the time change may not be suitable for continuous updates.
            # We'll use a combination of frame update and eval.
            # For now, we'll just provide a method to update each frame.
            # The caller can call update_animation() each frame.
            # We'll also provide a start_animation() method.
            pass

    def update_animation(self) -> None:
        """Update animation progress (call each frame)."""
        if not self._anim_playing:
            return
        elapsed = time.time() - self._anim_start_time
        if elapsed >= self._anim_duration:
            if self._anim_loop:
                self._anim_start_time = time.time()
                elapsed = 0.0
            else:
                self._anim_playing = False
                if self._anim_callback:
                    self._anim_callback()
                return
        t = elapsed / self._anim_duration
        # Determine which segment we're in
        num_segments = len(self._anim_expressions) - 1
        if num_segments <= 0:
            # Only one expression, just apply it
            self.apply(self._anim_expressions[0])
            return
        seg_length = 1.0 / num_segments
        seg_index = int(t / seg_length)
        if seg_index >= num_segments:
            seg_index = num_segments - 1
        local_t = (t - seg_index * seg_length) / seg_length
        local_t = clamp(local_t, 0.0, 1.0)
        # Blend between seg_index and seg_index+1
        expr_a = self._anim_expressions[seg_index]
        expr_b = self._anim_expressions[seg_index + 1]
        # Interpolate coefficients
        blended = self._interpolate_coeffs(expr_a.coefficients, expr_b.coefficients, local_t)
        self.apply(blended)

    def stop_animation(self) -> None:
        """Stop the current animation."""
        self._anim_playing = False
        if self._anim_callback:
            self._anim_callback()

    def is_animating(self) -> bool:
        """Return True if animation is playing."""
        return self._anim_playing

    # ---- Comparison ----

    def compare(
        self,
        expr_a: Union[str, ExpressionDefinition, Dict[str, float]],
        expr_b: Union[str, ExpressionDefinition, Dict[str, float]],
        mode: str = "split",  # "split", "overlay", "before_after"
        split_axis: str = "horizontal",
    ) -> None:
        """
        Compare two expressions.

        Args:
            expr_a: First expression.
            expr_b: Second expression.
            mode: 'split', 'overlay', 'before_after'.
            split_axis: 'horizontal' or 'vertical' for split mode.
        """
        # For comparison, we might need to apply expressions to different meshes
        # or use a temporary mesh. This is complex in Maya.
        # We'll implement a simple version: apply expr_a, then expr_b, and allow
        # the user to toggle between them.
        # For more advanced (split screen), we might need a shader or two meshes.
        # We'll keep it simple: store both expressions and provide a method to
        # switch between them.
        self._compare_a = self._resolve_coefficients(expr_a)
        self._compare_b = self._resolve_coefficients(expr_b)
        self._compare_index = 0
        self._compare_mode = mode
        # Show first
        self.apply(self._compare_a)
        logger.info(f"Comparison ready. Use switch_comparison() to toggle.")

    def switch_comparison(self) -> None:
        """Switch between the two expressions in comparison mode."""
        if not hasattr(self, '_compare_a'):
            return
        self._compare_index = 1 - self._compare_index
        if self._compare_index == 0:
            self.apply(self._compare_a)
        else:
            self.apply(self._compare_b)

    # ---- ARKit Preview ----

    def preview_arkit(
        self,
        arkit_coeffs: Dict[str, float],
        mapping: Optional[Callable[[Dict[str, float]], Dict[str, float]]] = None,
    ) -> None:
        """
        Preview ARKit coefficients mapped to blendshapes.

        Args:
            arkit_coeffs: ARKit channel -> value.
            mapping: Optional mapping function.
        """
        if mapping:
            mapped = mapping(arkit_coeffs)
        else:
            # Use default ARKit mapper if available
            try:
                from ..arkit.mapper import ARKitMapper
                mapper = ARKitMapper()
                mapped = mapper.map(arkit_coeffs)
            except ImportError:
                # Fallback: assume direct mapping (same channels)
                mapped = arkit_coeffs
        self.apply(mapped)

    # ---- Thumbnail Generation ----

    def capture_thumbnail(
        self,
        expression: Union[str, ExpressionDefinition, Dict[str, float]],
        output_path: Union[str, Path],
        width: int = 256,
        height: int = 256,
        background_color: Tuple[float, float, float] = (0.2, 0.2, 0.2),
    ) -> Path:
        """
        Capture a thumbnail image of the expression.

        Args:
            expression: Expression to capture.
            output_path: Output file path (PNG recommended).
            width: Image width.
            height: Image height.
            background_color: Background color (RGB 0-1).

        Returns:
            Path to the saved thumbnail.
        """
        # Apply the expression
        self.apply(expression)

        # Set viewport settings for capture
        # We'll use cmds.viewFit to frame the mesh, then render viewport snapshot.
        # We need to temporarily set background color, maybe use a standalone renderer.
        # Maya's viewport capture can be done with `cmds.renderWindowSnapshot`.
        # We'll use `cmds.playblast` with `format='image'` or `cmds.renderWindowSnapshot`.

        # For simplicity, we'll use the viewport capture.
        # We'll need to ensure the viewport is active and the mesh is visible.
        # We'll fit the view to the mesh.
        cmds.select(self._mesh)
        cmds.viewFit(self._mesh, all=True)

        # Capture
        # cmds.renderWindowSnapshot may not be reliable; we'll use playblast.
        # But playblast creates video; we can use -format image.
        # Actually, we can use `cmds.renderWindowSnapshot` with `frame` param.
        # We'll use a common technique: set the current time, then use `cmds.renderWindowSnapshot`.
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use Maya's renderWindowSnapshot
        try:
            # Set background color (temporarily)
            # Store current settings
            # We'll not change background color to keep it simple.
            # We'll capture the viewport as is.
            snapshot = cmds.renderWindowSnapshot(
                width=width,
                height=height,
                format='png',
                filename=str(output_path.with_suffix('')),
            )
            # The snapshot may be saved with a different name; we'll just return the path.
            # Check if file exists
            if output_path.exists():
                return output_path
            # Otherwise, try to find the file
            possible = output_path.parent / f"{output_path.stem}.png"
            if possible.exists():
                return possible
            # Fallback: save as is
            logger.warning("Thumbnail capture may have failed; file not found.")
            return output_path
        except Exception as e:
            logger.error(f"Thumbnail capture failed: {e}")
            # Try fallback using playblast
            try:
                cmds.playblast(
                    frame=1,
                    format='image',
                    filename=str(output_path),
                    width=width,
                    height=height,
                    view=cmds.getPanel(withFocus=True),
                    startTime=1,
                    endTime=1,
                    viewer=False,
                    showOrnaments=False,
                )
                return output_path
            except:
                raise PreviewError(f"Failed to capture thumbnail: {e}")

    # ---- Viewport Management ----

    def _update_viewport(self) -> None:
        """Update the Maya viewport."""
        if self._viewport_callback:
            self._viewport_callback()
        else:
            # Refresh viewport
            cmds.refresh()

    def set_viewport_callback(self, callback: Callable[[], None]) -> None:
        """Set a callback to be called after each update."""
        self._viewport_callback = callback

    # ---- Helper Methods ----

    def _resolve_coefficients(self, expr: Union[str, ExpressionDefinition, Dict[str, float]]) -> Dict[str, float]:
        """Resolve an expression to coefficients."""
        if isinstance(expr, str):
            defn = self._resolve_definition(expr)
            if defn:
                return defn.coefficients
            else:
                # Try to treat as a raw dictionary (if string is JSON?)
                # For simplicity, raise error
                raise PreviewError(f"Expression '{expr}' not found.")
        elif isinstance(expr, ExpressionDefinition):
            return expr.coefficients.copy()
        elif isinstance(expr, dict):
            return expr.copy()
        else:
            raise TypeError(f"Unsupported expression type: {type(expr)}")

    def _resolve_definition(self, name: str) -> Optional[ExpressionDefinition]:
        """Resolve an expression name to an ExpressionDefinition."""
        if self._manager:
            entry = self._manager.get(name)
            if entry:
                return entry.definition
        # Fallback: try generator
        try:
            from .generator import ExpressionGenerator
            gen = ExpressionGenerator()
            return gen.get_definition(name)
        except:
            return None

    def _get_all_targets(self) -> List[str]:
        """Return all target names on the blendshape node."""
        if not self._blendshape_node:
            return []
        return cmds.listAttr(self._blendshape_node, m=True, string='weight') or []

    def _interpolate_coeffs(self, a: Dict[str, float], b: Dict[str, float], t: float) -> Dict[str, float]:
        """Interpolate two coefficient dicts."""
        all_keys = set(a.keys()) | set(b.keys())
        result = {}
        for key in all_keys:
            val_a = a.get(key, 0.0)
            val_b = b.get(key, 0.0)
            result[key] = val_a * (1 - t) + val_b * t
            result[key] = clamp(result[key], 0.0, 1.0)
        return result

    # ---- Cleanup ----

    def cleanup(self) -> None:
        """Clean up resources (e.g., stop animation)."""
        if self._anim_playing:
            self.stop_animation()
        self.reset()


# ---- Public API ----

__all__ = [
    "ExpressionPreview",
    "PreviewMode",
    "PreviewError",
]