"""
maya_faceit.expression.presets

Built-in Facial Expression Presets.

This module provides a library of predefined facial expression coefficient sets
that can be loaded, installed into the expression generator, and saved/loaded
from JSON files.

The presets include:
- Neutral
- Smile, BigSmile
- Blink, WinkLeft, WinkRight
- Squint
- Angry, Sad, Happy, Fear, Surprise, Disgust
- JawOpen, JawLeft, JawRight, JawForward
- CheekPuff
- TongueOut
- Frown
- LipRollLower, LipRollUpper
- BrowRaise, BrowLower
- NoseSneer

Supports:
- Listing available presets.
- Loading preset coefficients.
- Installing presets into the ExpressionGenerator.
- Saving and loading custom presets to/from JSON.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Import dependencies (with fallbacks)
try:
    from .generator import ExpressionGenerator, ExpressionDefinition, ExpressionType
    from .editor import ExpressionEditor
    from ..blendshapes.blendshape_utils import sanitize_name, normalize_weights
    HAS_DEPS = True
except ImportError:
    # Fallback for development
    class ExpressionGenerator:
        def get_builtin_names(self): return []
        def get_definition(self, name): return None
        def add_custom_expression(self, defn): pass
    class ExpressionDefinition:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class ExpressionType:
        BASIC = "basic"
        CUSTOM = "custom"
    class ExpressionEditor: pass
    def sanitize_name(name): return name
    def normalize_weights(weights): return {k: v / sum(weights.values()) if sum(weights.values()) else 0.0 for k, v in weights.items()}
    HAS_DEPS = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ---- Exceptions ----

class PresetError(Exception):
    """Base exception for preset operations."""
    pass


# ---- PresetManager Class ----

class PresetManager:
    """
    Manages built-in and custom facial expression presets.

    Presets are coefficient dictionaries (channel -> weight) with metadata.
    """

    def __init__(
        self,
        generator: Optional[ExpressionGenerator] = None,
        editor: Optional[ExpressionEditor] = None,
    ):
        """
        Initialize the preset manager.

        Args:
            generator: ExpressionGenerator for installing presets.
            editor: Optional ExpressionEditor for editing.
        """
        self._generator = generator or ExpressionGenerator()
        self._editor = editor

        # Built-in presets (hardcoded)
        self._builtin_presets: Dict[str, Dict[str, Any]] = self._init_builtin_presets()

        # Custom presets (loaded from file or added at runtime)
        self._custom_presets: Dict[str, Dict[str, Any]] = {}

        # Combined presets (built-in + custom; custom override built-in)
        self._presets = self._builtin_presets.copy()
        self._presets.update(self._custom_presets)

    # ---- Built-in Preset Definitions ----

    def _init_builtin_presets(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the built-in preset library."""
        presets = {}

        # Neutral
        presets["Neutral"] = {
            "coefficients": {},
            "description": "Neutral expression (all zero).",
            "category": "Base",
            "tags": ["neutral"],
        }

        # Smiles
        presets["Smile"] = {
            "coefficients": {
                "mouthSmileLeft": 0.9,
                "mouthSmileRight": 0.9,
                "cheekSquintLeft": 0.3,
                "cheekSquintRight": 0.3,
                "eyeSquintLeft": 0.15,
                "eyeSquintRight": 0.15,
            },
            "description": "Happy smile with cheek and eye squint.",
            "category": "Positive",
            "tags": ["smile", "happy"],
        }

        presets["BigSmile"] = {
            "coefficients": {
                "mouthSmileLeft": 1.0,
                "mouthSmileRight": 1.0,
                "cheekSquintLeft": 0.6,
                "cheekSquintRight": 0.6,
                "eyeSquintLeft": 0.4,
                "eyeSquintRight": 0.4,
                "jawOpen": 0.2,
            },
            "description": "Big, wide smile with jaw slightly open.",
            "category": "Positive",
            "tags": ["smile", "big"],
        }

        # Blinks
        presets["Blink"] = {
            "coefficients": {
                "eyeBlinkLeft": 1.0,
                "eyeBlinkRight": 1.0,
            },
            "description": "Both eyes blink closed.",
            "category": "Eyes",
            "tags": ["blink", "eyes"],
        }

        presets["WinkLeft"] = {
            "coefficients": {
                "eyeBlinkLeft": 1.0,
            },
            "description": "Left eye wink.",
            "category": "Eyes",
            "tags": ["wink", "left", "eyes"],
        }

        presets["WinkRight"] = {
            "coefficients": {
                "eyeBlinkRight": 1.0,
            },
            "description": "Right eye wink.",
            "category": "Eyes",
            "tags": ["wink", "right", "eyes"],
        }

        presets["Squint"] = {
            "coefficients": {
                "eyeSquintLeft": 1.0,
                "eyeSquintRight": 1.0,
            },
            "description": "Eyes squinting.",
            "category": "Eyes",
            "tags": ["squint", "eyes"],
        }

        # Jaw
        presets["JawOpen"] = {
            "coefficients": {
                "jawOpen": 1.0,
            },
            "description": "Jaw open.",
            "category": "Jaw",
            "tags": ["jaw", "open"],
        }

        presets["JawLeft"] = {
            "coefficients": {
                "jawLeft": 1.0,
            },
            "description": "Jaw moved left.",
            "category": "Jaw",
            "tags": ["jaw", "left"],
        }

        presets["JawRight"] = {
            "coefficients": {
                "jawRight": 1.0,
            },
            "description": "Jaw moved right.",
            "category": "Jaw",
            "tags": ["jaw", "right"],
        }

        presets["JawForward"] = {
            "coefficients": {
                "jawForward": 1.0,
            },
            "description": "Jaw protrusion.",
            "category": "Jaw",
            "tags": ["jaw", "forward"],
        }

        # Cheek
        presets["CheekPuff"] = {
            "coefficients": {
                "cheekPuff": 1.0,
            },
            "description": "Cheeks puffed out.",
            "category": "Cheeks",
            "tags": ["cheek", "puff"],
        }

        # Tongue
        presets["TongueOut"] = {
            "coefficients": {
                "tongueOut": 1.0,
            },
            "description": "Tongue protrusion.",
            "category": "Tongue",
            "tags": ["tongue"],
        }

        # Mouth shapes
        presets["Frown"] = {
            "coefficients": {
                "mouthFrownLeft": 0.8,
                "mouthFrownRight": 0.8,
                "browInnerUp": 0.5,
            },
            "description": "Frown expression with brows raised.",
            "category": "Mouth",
            "tags": ["frown", "sad"],
        }

        presets["LipRollLower"] = {
            "coefficients": {
                "mouthRollLower": 1.0,
            },
            "description": "Lower lip rolled inward.",
            "category": "Mouth",
            "tags": ["lip", "roll"],
        }

        presets["LipRollUpper"] = {
            "coefficients": {
                "mouthRollUpper": 1.0,
            },
            "description": "Upper lip rolled inward.",
            "category": "Mouth",
            "tags": ["lip", "roll"],
        }

        # Brows
        presets["BrowRaise"] = {
            "coefficients": {
                "browInnerUp": 0.8,
                "browOuterUpLeft": 0.6,
                "browOuterUpRight": 0.6,
            },
            "description": "Brows raised (surprise style).",
            "category": "Brows",
            "tags": ["brow", "raise"],
        }

        presets["BrowLower"] = {
            "coefficients": {
                "browDownLeft": 0.8,
                "browDownRight": 0.8,
            },
            "description": "Brows lowered (anger style).",
            "category": "Brows",
            "tags": ["brow", "lower"],
        }

        # Nose
        presets["NoseSneer"] = {
            "coefficients": {
                "noseSneerLeft": 0.9,
                "noseSneerRight": 0.9,
            },
            "description": "Nose sneer (disgust style).",
            "category": "Nose",
            "tags": ["nose", "sneer"],
        }

        # Emotions
        presets["Angry"] = {
            "coefficients": {
                "browDownLeft": 0.8,
                "browDownRight": 0.8,
                "mouthPressLeft": 0.9,
                "mouthPressRight": 0.9,
                "jawForward": 0.4,
                "eyeSquintLeft": 0.3,
                "eyeSquintRight": 0.3,
            },
            "description": "Angry expression.",
            "category": "Emotions",
            "tags": ["anger", "negative"],
        }

        presets["Sad"] = {
            "coefficients": {
                "browInnerUp": 0.7,
                "mouthFrownLeft": 0.9,
                "mouthFrownRight": 0.9,
                "eyeSquintLeft": 0.2,
                "eyeSquintRight": 0.2,
                "jawOpen": 0.1,
            },
            "description": "Sad expression.",
            "category": "Emotions",
            "tags": ["sad", "negative"],
        }

        presets["Happy"] = {
            "coefficients": {
                "mouthSmileLeft": 1.0,
                "mouthSmileRight": 1.0,
                "cheekSquintLeft": 0.5,
                "cheekSquintRight": 0.5,
                "eyeSquintLeft": 0.3,
                "eyeSquintRight": 0.3,
            },
            "description": "Happy expression.",
            "category": "Emotions",
            "tags": ["happy", "positive"],
        }

        presets["Fear"] = {
            "coefficients": {
                "browOuterUpLeft": 0.8,
                "browOuterUpRight": 0.8,
                "eyeWideLeft": 0.7,
                "eyeWideRight": 0.7,
                "jawOpen": 0.5,
                "mouthStretchLeft": 0.3,
                "mouthStretchRight": 0.3,
            },
            "description": "Fear expression.",
            "category": "Emotions",
            "tags": ["fear", "negative"],
        }

        presets["Surprise"] = {
            "coefficients": {
                "browInnerUp": 0.8,
                "eyeWideLeft": 0.9,
                "eyeWideRight": 0.9,
                "jawOpen": 0.7,
                "mouthUpperUpLeft": 0.2,
                "mouthUpperUpRight": 0.2,
            },
            "description": "Surprise expression.",
            "category": "Emotions",
            "tags": ["surprise", "positive"],
        }

        presets["Disgust"] = {
            "coefficients": {
                "browDownLeft": 0.7,
                "browDownRight": 0.7,
                "noseSneerLeft": 0.9,
                "noseSneerRight": 0.9,
                "mouthUpperUpLeft": 0.6,
                "mouthUpperUpRight": 0.6,
            },
            "description": "Disgust expression.",
            "category": "Emotions",
            "tags": ["disgust", "negative"],
        }

        return presets

    # ---- Core Operations ----

    def list_presets(self) -> List[str]:
        """Return a list of all preset names (built-in + custom)."""
        return list(self._presets.keys())

    def get_preset(self, name: str) -> Optional[Dict[str, float]]:
        """Get the coefficient dictionary for a preset."""
        preset = self._presets.get(name)
        if preset:
            return preset["coefficients"].copy()
        return None

    def get_preset_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full preset info (coefficients, description, category, tags)."""
        return copy.deepcopy(self._presets.get(name))

    def add_custom_preset(
        self,
        name: str,
        coefficients: Dict[str, float],
        description: str = "",
        category: str = "Custom",
        tags: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Add a custom preset.

        Args:
            name: Preset name.
            coefficients: Coefficient dict.
            description: Description.
            category: Category.
            tags: List of tags.
            overwrite: If True, overwrite existing preset (including built-in).
        """
        if not overwrite and name in self._presets:
            raise PresetError(f"Preset '{name}' already exists. Use overwrite=True to replace.")
        self._custom_presets[name] = {
            "coefficients": coefficients.copy(),
            "description": description,
            "category": category,
            "tags": tags or [],
        }
        self._presets[name] = self._custom_presets[name]
        logger.info(f"Added custom preset: {name}")

    def remove_custom_preset(self, name: str) -> bool:
        """Remove a custom preset (cannot remove built-ins)."""
        if name in self._custom_presets:
            del self._custom_presets[name]
            if name in self._presets:
                # If there is a built-in with same name, restore it
                if name in self._builtin_presets:
                    self._presets[name] = self._builtin_presets[name]
                else:
                    del self._presets[name]
            return True
        return False

    # ---- Install to Expression Generator ----

    def install(self, name: str, generator: Optional[ExpressionGenerator] = None) -> bool:
        """
        Install a preset as an expression in the generator.

        Args:
            name: Preset name.
            generator: Optional generator; uses internal if None.

        Returns:
            True if installed successfully.
        """
        if generator is None:
            generator = self._generator

        preset = self._presets.get(name)
        if preset is None:
            logger.warning(f"Preset '{name}' not found.")
            return False

        # Create ExpressionDefinition
        defn = ExpressionDefinition(
            name=name,
            coefficients=preset["coefficients"].copy(),
            expression_type=ExpressionType.BASIC,
            description=preset.get("description", ""),
            tags=preset.get("tags", []),
            metadata={"category": preset.get("category", "Uncategorized")},
        )
        # Add to generator
        generator.add_custom_expression(defn)
        logger.info(f"Installed preset '{name}' as expression.")
        return True

    def install_all(self, generator: Optional[ExpressionGenerator] = None) -> int:
        """
        Install all built-in and custom presets as expressions.

        Args:
            generator: Optional generator; uses internal if None.

        Returns:
            Number of presets installed.
        """
        if generator is None:
            generator = self._generator

        count = 0
        for name in self._presets:
            if self.install(name, generator):
                count += 1
        return count

    # ---- Save / Load ----

    def save_to_file(self, filepath: Union[str, Path]) -> None:
        """
        Save custom presets to a JSON file.

        Args:
            filepath: Path to JSON file.
        """
        path = Path(filepath)
        # Only custom presets are saved
        data = {name: info for name, info in self._custom_presets.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(data)} custom presets to {path}")

    def load_from_file(self, filepath: Union[str, Path], overwrite: bool = False) -> int:
        """
        Load custom presets from a JSON file.

        Args:
            filepath: Path to JSON file.
            overwrite: If True, overwrite existing custom presets.

        Returns:
            Number of presets loaded.
        """
        path = Path(filepath)
        if not path.exists():
            raise PresetError(f"File not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for name, info in data.items():
            if not overwrite and name in self._custom_presets:
                continue
            # Validate required fields
            if "coefficients" not in info:
                logger.warning(f"Preset '{name}' missing coefficients; skipping.")
                continue
            self._custom_presets[name] = {
                "coefficients": info["coefficients"],
                "description": info.get("description", ""),
                "category": info.get("category", "Custom"),
                "tags": info.get("tags", []),
            }
            self._presets[name] = self._custom_presets[name]
            count += 1
        logger.info(f"Loaded {count} custom presets from {path}")
        return count

    # ---- Utility ----

    def get_preset_names_by_category(self, category: str) -> List[str]:
        """Return preset names in a given category."""
        return [name for name, info in self._presets.items() if info.get("category") == category]

    def get_categories(self) -> List[str]:
        """Return all categories used by presets."""
        return sorted(set(info.get("category", "Uncategorized") for info in self._presets.values()))

    def get_preset_coefficients_with_intensity(
        self, name: str, intensity: float = 1.0
    ) -> Optional[Dict[str, float]]:
        """
        Get coefficients scaled by intensity.
        """
        coeffs = self.get_preset(name)
        if coeffs is None:
            return None
        from ..blendshapes.blendshape_utils import clamp
        return {k: clamp(v * intensity, 0.0, 1.0) for k, v in coeffs.items()}


# ---- Public API ----

__all__ = [
    "PresetManager",
    "PresetError",
]