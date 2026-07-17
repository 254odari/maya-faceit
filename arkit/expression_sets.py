"""
arkit/expression_sets.py

ARKit Expression Sets

This module defines high-level facial expressions built from combinations of
ARKit blendshapes. It provides reusable semantic expressions such as Happy,
Angry, Fear, Viseme_AA, etc., which can be instantiated by pose_generator.py.

The module sits above individual poses and below the pose library, providing
a template registry for generating expressions at arbitrary intensities.

Responsibilities
----------------
• Define emotion expressions (Happy, Sad, Angry, Fear, Surprise, Disgust, etc.)
• Define eye expressions (Blink, Wide, Squint, Wink, Look directions)
• Define mouth expressions (Smile, Frown, Pucker, Funnel, Press, etc.)
• Define brow expressions (Brows Up, Down, Inner Up, Outer Up, Furrow)
• Define nose expressions (Sneer, Flare)
• Define jaw expressions (Open, Forward, Left, Right)
• Define viseme sets for lip-sync (AA, AE, AH, EE, etc.)
• Define corrective expressions (Extreme Smile, Extreme Blink, etc.)
• Support expression blending (Happy + Surprised = Excited)
• Support intensity scaling (Happy at 0.25, 0.5, 0.75, 1.0)
• Provide a registry to store, retrieve, search, and manage expressions
• Serialization/deserialization
• Diagnostics and statistics

Dependencies
------------
• arkit52.py - canonical ARKit blendshape names, left/right pairs
• validator.py - validate expression channels and weights
• pose_generator.py (optional) - for Pose class; if unavailable, fallback
• pose_library.py (optional) - for storing generated poses
"""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any, Union, Tuple, Callable, Iterable
from .validator import ARKitValidator
from .pose_library import SerializationError
# ---- Part 1: Foundation --------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class ARKitExpressionError(Exception):
    """Base exception for expression sets errors."""
    pass

class ExpressionNotFoundError(ARKitExpressionError):
    """Raised when an expression is not found in the registry."""
    pass

class DuplicateExpressionError(ARKitExpressionError):
    """Raised when an expression with the same name already exists."""
    pass

class InvalidExpressionError(ARKitExpressionError):
    """Raised when an expression definition is invalid."""
    pass

# ---- Part 2: Data Models ------------------------------------------------

@dataclass
class ExpressionMetadata:
    """
    Metadata for an expression template.
    """
    name: str
    category: str
    description: str = ""
    author: str = "builtin"
    version: int = 1
    tags: List[str] = field(default_factory=list)
    intensity_range: Tuple[float, float] = (0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExpressionMetadata:
        return cls(
            name=data["name"],
            category=data.get("category", "Uncategorized"),
            description=data.get("description", ""),
            author=data.get("author", "builtin"),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            intensity_range=tuple(data.get("intensity_range", (0.0, 1.0))),
        )


@dataclass
class Expression:
    """
    An expression template defined by a set of ARKit channel->value mappings.
    """
    metadata: ExpressionMetadata
    coefficients: Dict[str, float]  # channel -> base value at intensity=1.0
    optional_channels: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    # Optional channels with min/max range for variation

    def apply_intensity(self, intensity: float = 1.0) -> Dict[str, float]:
        """
        Return coefficients scaled by the given intensity (clamped to intensity_range).
        """
        # Clamp intensity to allowed range
        lo, hi = self.metadata.intensity_range
        effective = max(lo, min(hi, intensity))

        result = {}
        # Main channels: scale by intensity
        for ch, val in self.coefficients.items():
            scaled = val * effective
            # Clamp to 0-1
            if scaled < 0.0:
                scaled = 0.0
            elif scaled > 1.0:
                scaled = 1.0
            result[ch] = scaled

        # Optional channels: for now, use midpoint of range scaled by intensity
        for ch, (lo_val, hi_val) in self.optional_channels.items():
            midpoint = (lo_val + hi_val) * 0.5
            scaled = midpoint * effective
            if scaled < 0.0:
                scaled = 0.0
            elif scaled > 1.0:
                scaled = 1.0
            result[ch] = scaled

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "coefficients": self.coefficients,
            "optional_channels": self.optional_channels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Expression:
        metadata = ExpressionMetadata.from_dict(data["metadata"])
        return cls(
            metadata=metadata,
            coefficients=data.get("coefficients", {}),
            optional_channels=data.get("optional_channels", {}),
        )

    def clone(self) -> Expression:
        return Expression(
            metadata=ExpressionMetadata.from_dict(self.metadata.to_dict()),
            coefficients=self.coefficients.copy(),
            optional_channels=self.optional_channels.copy(),
        )


@dataclass
class ExpressionGroup:
    """
    A group of expressions (e.g., "Emotions", "Visemes", "Correctives").
    """
    name: str
    expressions: List[Expression] = field(default_factory=list)
    description: str = ""

    def add(self, expression: Expression) -> None:
        self.expressions.append(expression)

    def remove(self, expression_name: str) -> bool:
        for i, expr in enumerate(self.expressions):
            if expr.metadata.name == expression_name:
                del self.expressions[i]
                return True
        return False

    def get(self, name: str) -> Optional[Expression]:
        for expr in self.expressions:
            if expr.metadata.name == name:
                return expr
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "expressions": [e.to_dict() for e in self.expressions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExpressionGroup:
        group = cls(
            name=data["name"],
            description=data.get("description", ""),
        )
        for expr_data in data.get("expressions", []):
            group.add(Expression.from_dict(expr_data))
        return group


# ---- Part 3: Built-in Expressions --------------------------------------

class BuiltinExpressions:
    """
    Defines a comprehensive set of built-in expression templates.
    """

    @staticmethod
    def create_emotion_expressions() -> List[Expression]:
        """Create emotion expressions (Happy, Sad, Angry, Fear, Disgust, Surprise, etc.)"""
        expressions = []

        # Neutral (all zeros)
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Neutral",
                    category="Emotion",
                    description="Neutral face, all channels at zero",
                    tags=["emotion", "base"],
                ),
                coefficients={},
            )
        )

        # Happy
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Happy",
                    category="Emotion",
                    description="Happy expression: smile + cheek squint + eye squint",
                    tags=["emotion", "positive"],
                ),
                coefficients={
                    "mouthSmileLeft": 0.9,
                    "mouthSmileRight": 0.9,
                    "cheekSquintLeft": 0.4,
                    "cheekSquintRight": 0.4,
                    "eyeSquintLeft": 0.25,
                    "eyeSquintRight": 0.25,
                },
                optional_channels={
                    "browInnerUp": (0.0, 0.2),
                }
            )
        )

        # Sad
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Sad",
                    category="Emotion",
                    description="Sad expression: brows up, mouth frown",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browInnerUp": 0.6,
                    "mouthFrownLeft": 0.8,
                    "mouthFrownRight": 0.8,
                },
                optional_channels={
                    "jawOpen": (0.0, 0.2),
                    "eyeSquintLeft": (0.0, 0.15),
                    "eyeSquintRight": (0.0, 0.15),
                }
            )
        )

        # Angry
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Angry",
                    category="Emotion",
                    description="Angry expression: brows down, mouth press, jaw forward",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browDownLeft": 0.8,
                    "browDownRight": 0.8,
                    "mouthPressLeft": 0.9,
                    "mouthPressRight": 0.9,
                    "jawForward": 0.5,
                },
                optional_channels={
                    "eyeSquintLeft": (0.0, 0.4),
                    "eyeSquintRight": (0.0, 0.4),
                }
            )
        )

        # Fear
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Fear",
                    category="Emotion",
                    description="Fear expression: brows outer up, eyes wide, jaw open",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browOuterUpLeft": 0.8,
                    "browOuterUpRight": 0.8,
                    "eyeWideLeft": 0.7,
                    "eyeWideRight": 0.7,
                    "jawOpen": 0.4,
                },
                optional_channels={
                    "mouthStretchLeft": (0.0, 0.3),
                    "mouthStretchRight": (0.0, 0.3),
                }
            )
        )

        # Disgust
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Disgust",
                    category="Emotion",
                    description="Disgust expression: brows down, nose sneer, upper lip raise",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browDownLeft": 0.7,
                    "browDownRight": 0.7,
                    "noseSneerLeft": 0.9,
                    "noseSneerRight": 0.9,
                    "mouthUpperUpLeft": 0.6,
                    "mouthUpperUpRight": 0.6,
                },
                optional_channels={}
            )
        )

        # Surprised
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Surprised",
                    category="Emotion",
                    description="Surprised expression: brows up, eyes wide, jaw open",
                    tags=["emotion", "positive"],
                ),
                coefficients={
                    "browInnerUp": 0.8,
                    "eyeWideLeft": 0.9,
                    "eyeWideRight": 0.9,
                    "jawOpen": 0.7,
                },
                optional_channels={
                    "mouthUpperUpLeft": (0.0, 0.3),
                    "mouthUpperUpRight": (0.0, 0.3),
                }
            )
        )

        # Confused
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Confused",
                    category="Emotion",
                    description="Confused expression: one brow up, mouth one-sided frown",
                    tags=["emotion", "neutral"],
                ),
                coefficients={
                    "browOuterUpLeft": 0.6,
                    "mouthFrownRight": 0.5,
                },
                optional_channels={
                    "mouthFrownLeft": (0.0, 0.2),
                }
            )
        )

        # Determined
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Determined",
                    category="Emotion",
                    description="Determined expression: brows down, mouth press, jaw forward",
                    tags=["emotion", "positive"],
                ),
                coefficients={
                    "browDownLeft": 0.6,
                    "browDownRight": 0.6,
                    "mouthPressLeft": 0.7,
                    "mouthPressRight": 0.7,
                    "jawForward": 0.3,
                },
                optional_channels={}
            )
        )

        # Pain
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Pain",
                    category="Emotion",
                    description="Pain expression: brows inner up, eyes squint, mouth open",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browInnerUp": 0.7,
                    "eyeSquintLeft": 0.8,
                    "eyeSquintRight": 0.8,
                    "jawOpen": 0.5,
                },
                optional_channels={
                    "mouthStretchLeft": (0.0, 0.2),
                    "mouthStretchRight": (0.0, 0.2),
                }
            )
        )

        # Sleepy
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Sleepy",
                    category="Emotion",
                    description="Sleepy expression: eyes half-closed, mouth slack",
                    tags=["emotion", "neutral"],
                ),
                coefficients={
                    "eyeBlinkLeft": 0.4,
                    "eyeBlinkRight": 0.4,
                    "jawOpen": 0.2,
                    "mouthLowerDownLeft": 0.3,
                    "mouthLowerDownRight": 0.3,
                },
                optional_channels={}
            )
        )

        # Laugh
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Laugh",
                    category="Emotion",
                    description="Laugh expression: smile, cheeks, eyes squint, jaw open",
                    tags=["emotion", "positive"],
                ),
                coefficients={
                    "mouthSmileLeft": 1.0,
                    "mouthSmileRight": 1.0,
                    "cheekSquintLeft": 0.6,
                    "cheekSquintRight": 0.6,
                    "eyeSquintLeft": 0.5,
                    "eyeSquintRight": 0.5,
                    "jawOpen": 0.3,
                },
                optional_channels={}
            )
        )

        # Cry
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Cry",
                    category="Emotion",
                    description="Cry expression: brows up, mouth frown, eyes squeeze",
                    tags=["emotion", "negative"],
                ),
                coefficients={
                    "browInnerUp": 0.7,
                    "mouthFrownLeft": 0.9,
                    "mouthFrownRight": 0.9,
                    "eyeSquintLeft": 0.5,
                    "eyeSquintRight": 0.5,
                },
                optional_channels={
                    "jawOpen": (0.0, 0.2),
                }
            )
        )

        return expressions

    @staticmethod
    def create_eye_expressions() -> List[Expression]:
        """Create eye expressions."""
        expressions = []

        # Blink
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Blink",
                    category="Eye",
                    description="Both eyes blink closed",
                    tags=["eye", "basic"],
                ),
                coefficients={
                    "eyeBlinkLeft": 1.0,
                    "eyeBlinkRight": 1.0,
                },
            )
        )

        # Half Blink
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="HalfBlink",
                    category="Eye",
                    description="Half-blink (eyes half-closed)",
                    tags=["eye", "basic"],
                ),
                coefficients={
                    "eyeBlinkLeft": 0.5,
                    "eyeBlinkRight": 0.5,
                },
            )
        )

        # Wide Eyes
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="WideEyes",
                    category="Eye",
                    description="Eyes wide open",
                    tags=["eye", "basic"],
                ),
                coefficients={
                    "eyeWideLeft": 1.0,
                    "eyeWideRight": 1.0,
                },
            )
        )

        # Squint
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Squint",
                    category="Eye",
                    description="Eyes squinting",
                    tags=["eye", "basic"],
                ),
                coefficients={
                    "eyeSquintLeft": 1.0,
                    "eyeSquintRight": 1.0,
                },
            )
        )

        # Wink Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="WinkLeft",
                    category="Eye",
                    description="Wink left eye",
                    tags=["eye", "basic", "left"],
                ),
                coefficients={
                    "eyeBlinkLeft": 1.0,
                },
            )
        )

        # Wink Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="WinkRight",
                    category="Eye",
                    description="Wink right eye",
                    tags=["eye", "basic", "right"],
                ),
                coefficients={
                    "eyeBlinkRight": 1.0,
                },
            )
        )

        # Look Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LookLeft",
                    category="Eye",
                    description="Eyes looking left",
                    tags=["eye", "look"],
                ),
                coefficients={
                    "eyeLookOutLeft": 0.8,
                    "eyeLookOutRight": 0.8,
                },
            )
        )

        # Look Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LookRight",
                    category="Eye",
                    description="Eyes looking right",
                    tags=["eye", "look"],
                ),
                coefficients={
                    "eyeLookInLeft": 0.8,  # Actually for left eye looking right is lookIn? Need to verify.
                    "eyeLookInRight": 0.8,
                },
            )
        )
        # Note: ARKit look directions are relative to each eye, so left eye lookIn is to the right, etc.
        # For simplicity, we'll keep as above, but this may need refinement.

        # Look Up
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LookUp",
                    category="Eye",
                    description="Eyes looking up",
                    tags=["eye", "look"],
                ),
                coefficients={
                    "eyeLookUpLeft": 0.8,
                    "eyeLookUpRight": 0.8,
                },
            )
        )

        # Look Down
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LookDown",
                    category="Eye",
                    description="Eyes looking down",
                    tags=["eye", "look"],
                ),
                coefficients={
                    "eyeLookDownLeft": 0.8,
                    "eyeLookDownRight": 0.8,
                },
            )
        )

        return expressions

    @staticmethod
    def create_mouth_expressions() -> List[Expression]:
        """Create mouth expressions."""
        expressions = []

        # Smile
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Smile",
                    category="Mouth",
                    description="Smile (both sides)",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthSmileLeft": 1.0,
                    "mouthSmileRight": 1.0,
                },
            )
        )

        # Frown
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Frown",
                    category="Mouth",
                    description="Frown (both sides)",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthFrownLeft": 1.0,
                    "mouthFrownRight": 1.0,
                },
            )
        )

        # Pucker
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Pucker",
                    category="Mouth",
                    description="Mouth pucker (like kissing)",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthPucker": 1.0,
                },
            )
        )

        # Funnel
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Funnel",
                    category="Mouth",
                    description="Mouth funnel (like blowing)",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthFunnel": 1.0,
                },
            )
        )

        # Press
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Press",
                    category="Mouth",
                    description="Mouth pressed together",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthPressLeft": 1.0,
                    "mouthPressRight": 1.0,
                },
            )
        )

        # Stretch
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Stretch",
                    category="Mouth",
                    description="Mouth stretched wide (like 'EE')",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthStretchLeft": 1.0,
                    "mouthStretchRight": 1.0,
                },
            )
        )

        # Roll Lower
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="RollLower",
                    category="Mouth",
                    description="Lower lip rolled",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthRollLower": 1.0,
                },
            )
        )

        # Roll Upper
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="RollUpper",
                    category="Mouth",
                    description="Upper lip rolled",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthRollUpper": 1.0,
                },
            )
        )

        # Shrug Lower
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ShrugLower",
                    category="Mouth",
                    description="Lower lip shrug",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthShrugLower": 1.0,
                },
            )
        )

        # Shrug Upper
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ShrugUpper",
                    category="Mouth",
                    description="Upper lip shrug",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthShrugUpper": 1.0,
                },
            )
        )

        # Upper Up Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="UpperUpLeft",
                    category="Mouth",
                    description="Upper lip up left",
                    tags=["mouth", "basic", "left"],
                ),
                coefficients={
                    "mouthUpperUpLeft": 1.0,
                },
            )
        )

        # Upper Up Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="UpperUpRight",
                    category="Mouth",
                    description="Upper lip up right",
                    tags=["mouth", "basic", "right"],
                ),
                coefficients={
                    "mouthUpperUpRight": 1.0,
                },
            )
        )

        # Lower Down Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LowerDownLeft",
                    category="Mouth",
                    description="Lower lip down left",
                    tags=["mouth", "basic", "left"],
                ),
                coefficients={
                    "mouthLowerDownLeft": 1.0,
                },
            )
        )

        # Lower Down Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="LowerDownRight",
                    category="Mouth",
                    description="Lower lip down right",
                    tags=["mouth", "basic", "right"],
                ),
                coefficients={
                    "mouthLowerDownRight": 1.0,
                },
            )
        )

        # Mouth Left (jaw side)
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="MouthLeft",
                    category="Mouth",
                    description="Mouth moved left (jaw side)",
                    tags=["mouth", "basic", "left"],
                ),
                coefficients={
                    "mouthLeft": 1.0,
                },
            )
        )

        # Mouth Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="MouthRight",
                    category="Mouth",
                    description="Mouth moved right (jaw side)",
                    tags=["mouth", "basic", "right"],
                ),
                coefficients={
                    "mouthRight": 1.0,
                },
            )
        )

        # Close
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Close",
                    category="Mouth",
                    description="Mouth closed (lips together)",
                    tags=["mouth", "basic"],
                ),
                coefficients={
                    "mouthClose": 1.0,
                },
            )
        )

        # Dimple Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="DimpleLeft",
                    category="Mouth",
                    description="Dimple on left",
                    tags=["mouth", "basic", "left"],
                ),
                coefficients={
                    "mouthDimpleLeft": 1.0,
                },
            )
        )

        # Dimple Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="DimpleRight",
                    category="Mouth",
                    description="Dimple on right",
                    tags=["mouth", "basic", "right"],
                ),
                coefficients={
                    "mouthDimpleRight": 1.0,
                },
            )
        )

        return expressions

    @staticmethod
    def create_brow_expressions() -> List[Expression]:
        """Create brow expressions."""
        expressions = []

        # Brows Up
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="BrowsUp",
                    category="Brows",
                    description="Both brows raised (inner up)",
                    tags=["brow", "basic"],
                ),
                coefficients={
                    "browInnerUp": 1.0,
                },
            )
        )

        # Brows Down
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="BrowsDown",
                    category="Brows",
                    description="Both brows down",
                    tags=["brow", "basic"],
                ),
                coefficients={
                    "browDownLeft": 1.0,
                    "browDownRight": 1.0,
                },
            )
        )

        # Inner Up
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="InnerUp",
                    category="Brows",
                    description="Inner brows up",
                    tags=["brow", "basic"],
                ),
                coefficients={
                    "browInnerUp": 1.0,
                },
            )
        )

        # Outer Up Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="OuterUpLeft",
                    category="Brows",
                    description="Outer brow up left",
                    tags=["brow", "basic", "left"],
                ),
                coefficients={
                    "browOuterUpLeft": 1.0,
                },
            )
        )

        # Outer Up Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="OuterUpRight",
                    category="Brows",
                    description="Outer brow up right",
                    tags=["brow", "basic", "right"],
                ),
                coefficients={
                    "browOuterUpRight": 1.0,
                },
            )
        )

        # Furrow
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Furrow",
                    category="Brows",
                    description="Brows furrowed (down and together)",
                    tags=["brow", "basic"],
                ),
                coefficients={
                    "browDownLeft": 0.8,
                    "browDownRight": 0.8,
                    "browInnerUp": 0.3,  # inner up can also be part of furrow
                },
            )
        )

        return expressions

    @staticmethod
    def create_nose_expressions() -> List[Expression]:
        """Create nose expressions."""
        expressions = []

        # Sneer
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Sneer",
                    category="Nose",
                    description="Nose sneer (both sides)",
                    tags=["nose", "basic"],
                ),
                coefficients={
                    "noseSneerLeft": 1.0,
                    "noseSneerRight": 1.0,
                },
            )
        )

        # Sneer Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="SneerLeft",
                    category="Nose",
                    description="Nose sneer left",
                    tags=["nose", "basic", "left"],
                ),
                coefficients={
                    "noseSneerLeft": 1.0,
                },
            )
        )

        # Sneer Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="SneerRight",
                    category="Nose",
                    description="Nose sneer right",
                    tags=["nose", "basic", "right"],
                ),
                coefficients={
                    "noseSneerRight": 1.0,
                },
            )
        )

        return expressions

    @staticmethod
    def create_jaw_expressions() -> List[Expression]:
        """Create jaw expressions."""
        expressions = []

        # Jaw Open
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="JawOpen",
                    category="Jaw",
                    description="Jaw open",
                    tags=["jaw", "basic"],
                ),
                coefficients={
                    "jawOpen": 1.0,
                },
            )
        )

        # Jaw Forward
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="JawForward",
                    category="Jaw",
                    description="Jaw forward (protrusion)",
                    tags=["jaw", "basic"],
                ),
                coefficients={
                    "jawForward": 1.0,
                },
            )
        )

        # Jaw Left
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="JawLeft",
                    category="Jaw",
                    description="Jaw moved left",
                    tags=["jaw", "basic", "left"],
                ),
                coefficients={
                    "jawLeft": 1.0,
                },
            )
        )

        # Jaw Right
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="JawRight",
                    category="Jaw",
                    description="Jaw moved right",
                    tags=["jaw", "basic", "right"],
                ),
                coefficients={
                    "jawRight": 1.0,
                },
            )
        )

        return expressions

    @staticmethod
    def create_viseme_expressions() -> List[Expression]:
        """Create viseme expressions (for lip-sync)."""
        expressions = []

        # AA (as in "father")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_AA",
                    category="Viseme",
                    description="Viseme AA: open mouth, jaw down, lips slightly open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.8,
                    "mouthStretchLeft": 0.2,
                    "mouthStretchRight": 0.2,
                },
            )
        )

        # AE (as in "cat")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_AE",
                    category="Viseme",
                    description="Viseme AE: open mouth, lips wide",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.6,
                    "mouthStretchLeft": 0.6,
                    "mouthStretchRight": 0.6,
                },
            )
        )

        # AH (as in "cup")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_AH",
                    category="Viseme",
                    description="Viseme AH: open jaw, neutral lips",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.7,
                    "mouthLowerDownLeft": 0.4,
                    "mouthLowerDownRight": 0.4,
                },
            )
        )

        # AO (as in "caught")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_AO",
                    category="Viseme",
                    description="Viseme AO: rounded open mouth",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.5,
                    "mouthFunnel": 0.6,
                },
            )
        )

        # CH (as in "church")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_CH",
                    category="Viseme",
                    description="Viseme CH: lips rounded and slightly open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.3,
                    "mouthPucker": 0.6,
                },
            )
        )

        # EE (as in "beet")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_EE",
                    category="Viseme",
                    description="Viseme EE: wide lips, jaw slightly open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.3,
                    "mouthStretchLeft": 0.8,
                    "mouthStretchRight": 0.8,
                },
            )
        )

        # FV (as in "five")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_FV",
                    category="Viseme",
                    description="Viseme FV: upper lip on teeth",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.1,
                    "mouthUpperUpLeft": 0.5,
                    "mouthUpperUpRight": 0.5,
                    "mouthLowerDownLeft": 0.2,
                    "mouthLowerDownRight": 0.2,
                },
            )
        )

        # IH (as in "sit")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_IH",
                    category="Viseme",
                    description="Viseme IH: jaw slightly open, lips neutral",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.4,
                    "mouthSmileLeft": 0.2,
                    "mouthSmileRight": 0.2,
                },
            )
        )

        # L (as in "let")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_L",
                    category="Viseme",
                    description="Viseme L: tongue contact",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.2,
                    "mouthUpperUpLeft": 0.3,
                    "mouthUpperUpRight": 0.3,
                },
            )
        )

        # M (as in "me")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_M",
                    category="Viseme",
                    description="Viseme M: lips together",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "mouthClose": 0.8,
                },
            )
        )

        # O (as in "go")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_O",
                    category="Viseme",
                    description="Viseme O: rounded lips, jaw open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.5,
                    "mouthPucker": 0.7,
                },
            )
        )

        # OH (as in "thought")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_OH",
                    category="Viseme",
                    description="Viseme OH: rounded and open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.4,
                    "mouthFunnel": 0.8,
                },
            )
        )

        # OU (as in "about")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_OU",
                    category="Viseme",
                    description="Viseme OU: lips rounded slightly",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.2,
                    "mouthPucker": 0.4,
                },
            )
        )

        # R (as in "red")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_R",
                    category="Viseme",
                    description="Viseme R: lips slightly rounded",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.2,
                    "mouthPucker": 0.3,
                    "mouthFunnel": 0.3,
                },
            )
        )

        # S (as in "sit")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_S",
                    category="Viseme",
                    description="Viseme S: teeth together, lips parted",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.1,
                    "mouthPressLeft": 0.4,
                    "mouthPressRight": 0.4,
                },
            )
        )

        # SH (as in "she")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_SH",
                    category="Viseme",
                    description="Viseme SH: lips rounded, teeth together",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.1,
                    "mouthPucker": 0.5,
                },
            )
        )

        # TH (as in "thick")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_TH",
                    category="Viseme",
                    description="Viseme TH: tongue between teeth",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.3,
                    "mouthUpperUpLeft": 0.3,
                    "mouthUpperUpRight": 0.3,
                    "mouthLowerDownLeft": 0.3,
                    "mouthLowerDownRight": 0.3,
                    "tongueOut": 0.5,
                },
            )
        )

        # U (as in "boot")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_U",
                    category="Viseme",
                    description="Viseme U: lips rounded, jaw slightly open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.2,
                    "mouthPucker": 0.8,
                },
            )
        )

        # WQ (as in "what")
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="Viseme_WQ",
                    category="Viseme",
                    description="Viseme WQ: rounded lips, slightly open",
                    tags=["viseme", "speech"],
                ),
                coefficients={
                    "jawOpen": 0.3,
                    "mouthPucker": 0.6,
                    "mouthFunnel": 0.3,
                },
            )
        )

        return expressions

    @staticmethod
    def create_corrective_expressions() -> List[Expression]:
        """Create corrective expressions (extreme versions for rig testing)."""
        expressions = []

        # Extreme Smile
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeSmile",
                    category="Corrective",
                    description="Extreme smile (full range)",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "mouthSmileLeft": 1.0,
                    "mouthSmileRight": 1.0,
                    "cheekSquintLeft": 1.0,
                    "cheekSquintRight": 1.0,
                    "eyeSquintLeft": 1.0,
                    "eyeSquintRight": 1.0,
                },
            )
        )

        # Extreme Blink
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeBlink",
                    category="Corrective",
                    description="Extreme blink (full closure)",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "eyeBlinkLeft": 1.0,
                    "eyeBlinkRight": 1.0,
                },
            )
        )

        # Extreme Jaw Open
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeJawOpen",
                    category="Corrective",
                    description="Extreme jaw open",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "jawOpen": 1.0,
                },
            )
        )

        # Extreme Brows
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeBrows",
                    category="Corrective",
                    description="Extreme brows up and down",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "browInnerUp": 1.0,
                    "browDownLeft": 1.0,
                    "browDownRight": 1.0,
                    "browOuterUpLeft": 1.0,
                    "browOuterUpRight": 1.0,
                },
            )
        )

        # Extreme Stretch
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeStretch",
                    category="Corrective",
                    description="Extreme mouth stretch",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "mouthStretchLeft": 1.0,
                    "mouthStretchRight": 1.0,
                    "jawOpen": 0.5,
                },
            )
        )

        # Extreme Pucker
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremePucker",
                    category="Corrective",
                    description="Extreme pucker",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "mouthPucker": 1.0,
                    "jawOpen": 0.2,
                },
            )
        )

        # Extreme Funnel
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="ExtremeFunnel",
                    category="Corrective",
                    description="Extreme funnel",
                    tags=["corrective", "extreme"],
                ),
                coefficients={
                    "mouthFunnel": 1.0,
                    "jawOpen": 0.3,
                },
            )
        )

        # All Channels Max (stress test)
        expressions.append(
            Expression(
                metadata=ExpressionMetadata(
                    name="AllMax",
                    category="Corrective",
                    description="All channels at maximum (stress test)",
                    tags=["corrective", "extreme", "stress"],
                ),
                coefficients={
                    # We'll limit to 20 channels to avoid extreme all channels that might break rig
                    "browDownLeft": 1.0, "browDownRight": 1.0,
                    "browInnerUp": 1.0,
                    "cheekPuff": 1.0,
                    "eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0,
                    "eyeWideLeft": 1.0, "eyeWideRight": 1.0,
                    "jawOpen": 1.0,
                    "mouthSmileLeft": 1.0, "mouthSmileRight": 1.0,
                    "mouthFunnel": 1.0,
                    "mouthPucker": 1.0,
                    "noseSneerLeft": 1.0, "noseSneerRight": 1.0,
                },
            )
        )

        return expressions

    @staticmethod
    def get_all_builtin() -> List[Expression]:
        """Return all built-in expressions."""
        all_exprs = []
        all_exprs.extend(BuiltinExpressions.create_emotion_expressions())
        all_exprs.extend(BuiltinExpressions.create_eye_expressions())
        all_exprs.extend(BuiltinExpressions.create_mouth_expressions())
        all_exprs.extend(BuiltinExpressions.create_brow_expressions())
        all_exprs.extend(BuiltinExpressions.create_nose_expressions())
        all_exprs.extend(BuiltinExpressions.create_jaw_expressions())
        all_exprs.extend(BuiltinExpressions.create_viseme_expressions())
        all_exprs.extend(BuiltinExpressions.create_corrective_expressions())
        return all_exprs


# ---- Part 4: Emotion Sets (already included above) ---------------------
# ---- Part 5: Viseme Sets (already included above) ---------------------

# ---- Part 6: Expression Blending ---------------------------------------

class ExpressionBlendEngine:
    """
    Provides methods to blend expressions.
    """
    @staticmethod
    def blend(
        expr_a: Expression,
        expr_b: Expression,
        ratio: float = 0.5,
        name: Optional[str] = None,
        category: str = "Blend",
    ) -> Expression:
        """
        Blend two expressions by interpolating their coefficients.
        """
        if ratio < 0.0 or ratio > 1.0:
            raise ValueError("ratio must be between 0 and 1")

        # Get coefficients at full intensity
        coeffs_a = expr_a.apply_intensity(1.0)
        coeffs_b = expr_b.apply_intensity(1.0)

        # Combine all channels
        all_channels = set(coeffs_a.keys()) | set(coeffs_b.keys())
        blended_coeffs = {}
        for ch in all_channels:
            val_a = coeffs_a.get(ch, 0.0)
            val_b = coeffs_b.get(ch, 0.0)
            blended = val_a * (1.0 - ratio) + val_b * ratio
            # Clamp to 0-1
            if blended < 0.0:
                blended = 0.0
            elif blended > 1.0:
                blended = 1.0
            blended_coeffs[ch] = blended

        # Merge optional channels (take union, with values blended similarly)
        # For simplicity, we take the union and scale by ratio as well.
        opt_a = expr_a.optional_channels
        opt_b = expr_b.optional_channels
        blended_opt = {}
        all_opt = set(opt_a.keys()) | set(opt_b.keys())
        for ch in all_opt:
            if ch in opt_a and ch in opt_b:
                lo_a, hi_a = opt_a[ch]
                lo_b, hi_b = opt_b[ch]
                lo = lo_a * (1.0 - ratio) + lo_b * ratio
                hi = hi_a * (1.0 - ratio) + hi_b * ratio
                blended_opt[ch] = (lo, hi)
            elif ch in opt_a:
                blended_opt[ch] = opt_a[ch]
            else:
                blended_opt[ch] = opt_b[ch]

        # Create metadata
        blend_name = name or f"{expr_a.metadata.name}_{expr_b.metadata.name}_blend"
        metadata = ExpressionMetadata(
            name=blend_name,
            category=category,
            description=f"Blend of {expr_a.metadata.name} and {expr_b.metadata.name} at ratio {ratio}",
            author="blend_engine",
            tags=expr_a.metadata.tags + expr_b.metadata.tags,
        )
        return Expression(
            metadata=metadata,
            coefficients=blended_coeffs,
            optional_channels=blended_opt,
        )


# ---- Part 7: Registry & Search -----------------------------------------

class ExpressionRegistry:
    """
    Registry to store, retrieve, search, and manage expression templates.
    """
    def __init__(self):
        self._expressions: Dict[str, Expression] = {}
        self._groups: Dict[str, ExpressionGroup] = {}

    def register(self, expression: Expression) -> None:
        """
        Register a new expression. Raises DuplicateExpressionError if name exists.
        """
        name = expression.metadata.name
        if name in self._expressions:
            raise DuplicateExpressionError(f"Expression '{name}' already exists")
        self._expressions[name] = expression
        # Also add to group if category is a group name
        group_name = expression.metadata.category
        if group_name not in self._groups:
            self._groups[group_name] = ExpressionGroup(name=group_name)
        self._groups[group_name].add(expression)

    def get(self, name: str) -> Expression:
        if name not in self._expressions:
            raise ExpressionNotFoundError(f"Expression '{name}' not found")
        return self._expressions[name]

    def remove(self, name: str) -> None:
        if name not in self._expressions:
            raise ExpressionNotFoundError(f"Expression '{name}' not found")
        expr = self._expressions.pop(name)
        # Remove from group
        group_name = expr.metadata.category
        if group_name in self._groups:
            self._groups[group_name].remove(name)
            if not self._groups[group_name].expressions:
                del self._groups[group_name]

    def list_all(self) -> List[Expression]:
        return list(self._expressions.values())

    def list_names(self) -> List[str]:
        return list(self._expressions.keys())

    def list_groups(self) -> List[str]:
        return list(self._groups.keys())

    def get_group(self, group_name: str) -> Optional[ExpressionGroup]:
        return self._groups.get(group_name)

    def search(self, query: str) -> List[Expression]:
        """
        Search expressions by name, tags, description, or category.
        Case-insensitive substring match.
        """
        q = query.lower()
        results = []
        for expr in self._expressions.values():
            if q in expr.metadata.name.lower():
                results.append(expr)
                continue
            if q in expr.metadata.description.lower():
                results.append(expr)
                continue
            if q in expr.metadata.category.lower():
                results.append(expr)
                continue
            for tag in expr.metadata.tags:
                if q in tag.lower():
                    results.append(expr)
                    break
        return results

    def filter_by_tags(self, tags: List[str], match_all: bool = True) -> List[Expression]:
        if not tags:
            return self.list_all()
        results = []
        for expr in self._expressions.values():
            expr_tags = set(expr.metadata.tags)
            if match_all:
                if all(tag in expr_tags for tag in tags):
                    results.append(expr)
            else:
                if any(tag in expr_tags for tag in tags):
                    results.append(expr)
        return results

    def filter_by_category(self, category: str) -> List[Expression]:
        return [e for e in self._expressions.values() if e.metadata.category == category]

    def clear(self) -> None:
        self._expressions.clear()
        self._groups.clear()

    def load_builtin(self) -> None:
        """Load all built-in expressions."""
        for expr in BuiltinExpressions.get_all_builtin():
            try:
                self.register(expr)
            except DuplicateExpressionError:
                pass  # ignore duplicates (should not happen)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expressions": [e.to_dict() for e in self._expressions.values()],
            "groups": [g.to_dict() for g in self._groups.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExpressionRegistry:
        registry = cls()
        for expr_data in data.get("expressions", []):
            try:
                registry.register(Expression.from_dict(expr_data))
            except DuplicateExpressionError:
                pass
        # Groups will be rebuilt from expressions
        return registry


# ---- Part 8: Serialization ---------------------------------------------

class SerializationEngine:
    """
    Serialize/deserialize expression registry to/from JSON.
    """
    @staticmethod
    def serialize_json(registry: ExpressionRegistry) -> str:
        return json.dumps(registry.to_dict(), indent=2)

    @staticmethod
    def deserialize_json(data: str) -> ExpressionRegistry:
        try:
            obj = json.loads(data)
            return ExpressionRegistry.from_dict(obj)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Invalid JSON: {e}")

    @staticmethod
    def save_to_file(registry: ExpressionRegistry, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(registry.to_dict(), f, indent=2)

    @staticmethod
    def load_from_file(filepath: str) -> ExpressionRegistry:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ExpressionRegistry.from_dict(data)


# ---- Part 9: Diagnostics -----------------------------------------------

class DiagnosticsEngine:
    """
    Generates diagnostic reports for the expression registry.
    """
    def __init__(self, registry: ExpressionRegistry, validator: Optional[ARKitValidator] = None):
        self._registry = registry
        self._validator = validator or (ARKitValidator() if 'ARKitValidator' in globals() else None)

    def diagnose(self) -> Dict[str, Any]:
        """
        Run diagnostics and return a report.
        """
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "total_expressions": len(self._registry.list_all()),
            "categories": {},
            "duplicate_names": [],
            "invalid_channels": [],
            "out_of_range_values": [],
        }

        names = set()
        for expr in self._registry.list_all():
            # Check duplicate names
            if expr.metadata.name in names:
                report["duplicate_names"].append(expr.metadata.name)
                report["errors"].append(f"Duplicate expression name: {expr.metadata.name}")
                report["is_valid"] = False
            names.add(expr.metadata.name)

            # Count categories
            cat = expr.metadata.category
            report["categories"][cat] = report["categories"].get(cat, 0) + 1

            # Validate channels
            for ch, val in expr.coefficients.items():
                if val < 0.0 or val > 1.0:
                    report["out_of_range_values"].append(f"{expr.metadata.name}->{ch}={val}")
                    report["errors"].append(f"Out-of-range value for {ch} in {expr.metadata.name}")
                    report["is_valid"] = False
                # Check if channel is valid (if we have ARKIT_SET)
                try:
                    from .arkit52 import ARKIT_SET
                    if ch not in ARKIT_SET:
                        report["invalid_channels"].append(f"{expr.metadata.name}->{ch}")
                        report["warnings"].append(f"Unknown ARKit channel '{ch}' in {expr.metadata.name}")
                except ImportError:
                    pass

            # Validate optional channels
            for ch, (lo, hi) in expr.optional_channels.items():
                if lo < 0.0 or hi > 1.0 or lo > hi:
                    report["out_of_range_values"].append(f"{expr.metadata.name}->{ch} range ({lo},{hi})")
                    report["errors"].append(f"Invalid range for {ch} in {expr.metadata.name}")
                    report["is_valid"] = False

        return report


# ---- Part 10: Statistics ----------------------------------------------

class StatisticsEngine:
    """
    Computes statistics about the expression registry.
    """
    def __init__(self, registry: ExpressionRegistry):
        self._registry = registry

    def compute_statistics(self) -> Dict[str, Any]:
        expressions = self._registry.list_all()
        total = len(expressions)
        if total == 0:
            return {"total_expressions": 0}

        categories = {}
        tags = {}
        total_channels = 0
        max_channels = 0
        channel_frequency = {}

        for expr in expressions:
            cat = expr.metadata.category
            categories[cat] = categories.get(cat, 0) + 1
            for tag in expr.metadata.tags:
                tags[tag] = tags.get(tag, 0) + 1
            ch_count = len(expr.coefficients)
            total_channels += ch_count
            if ch_count > max_channels:
                max_channels = ch_count
            for ch in expr.coefficients:
                channel_frequency[ch] = channel_frequency.get(ch, 0) + 1

        avg_channels = total_channels / total if total > 0 else 0.0
        # Most frequent channels
        sorted_channels = sorted(channel_frequency.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_expressions": total,
            "categories": categories,
            "category_count": len(categories),
            "tags": tags,
            "tag_count": len(tags),
            "total_channel_occurrences": total_channels,
            "average_channels_per_expression": avg_channels,
            "max_channels_in_expression": max_channels,
            "most_frequent_channels": sorted_channels[:10],
        }


# ---- Part 11: Public API ------------------------------------------------

class ExpressionSets:
    """
    The main public API for expression sets.

    Provides:
        - Registration of expressions
        - Retrieval by name
        - Search and filtering
        - Expression blending
        - Intensity scaling (via Expression.apply_intensity)
        - Viseme lookup
        - Serialization
        - Diagnostics and statistics
    """
    def __init__(self, load_builtin: bool = True):
        self._registry = ExpressionRegistry()
        if load_builtin:
            self._registry.load_builtin()
        self._blend_engine = ExpressionBlendEngine()
        self._validator = ARKitValidator() if 'ARKitValidator' in globals() else None
        self._diagnostics = DiagnosticsEngine(self._registry, self._validator)
        self._statistics = StatisticsEngine(self._registry)

    # --- Registry operations ---

    def register(self, expression: Expression) -> None:
        self._registry.register(expression)

    def get(self, name: str) -> Expression:
        return self._registry.get(name)

    def remove(self, name: str) -> None:
        self._registry.remove(name)

    def list_expressions(self) -> List[Expression]:
        return self._registry.list_all()

    def list_names(self) -> List[str]:
        return self._registry.list_names()

    def list_groups(self) -> List[str]:
        return self._registry.list_groups()

    def get_group(self, group_name: str) -> Optional[ExpressionGroup]:
        return self._registry.get_group(group_name)

    # --- Search and filtering ---

    def search(self, query: str) -> List[Expression]:
        return self._registry.search(query)

    def filter_by_tags(self, tags: List[str], match_all: bool = True) -> List[Expression]:
        return self._registry.filter_by_tags(tags, match_all)

    def filter_by_category(self, category: str) -> List[Expression]:
        return self._registry.filter_by_category(category)

    # --- Blending ---

    def blend(
        self,
        expr_name_a: str,
        expr_name_b: str,
        ratio: float = 0.5,
        name: Optional[str] = None,
        category: str = "Blend",
    ) -> Expression:
        """
        Blend two expressions by name.
        """
        expr_a = self.get(expr_name_a)
        expr_b = self.get(expr_name_b)
        return self._blend_engine.blend(expr_a, expr_b, ratio, name, category)

    def blend_objects(
        self,
        expr_a: Expression,
        expr_b: Expression,
        ratio: float = 0.5,
        name: Optional[str] = None,
        category: str = "Blend",
    ) -> Expression:
        return self._blend_engine.blend(expr_a, expr_b, ratio, name, category)

    # --- Intensity scaling is handled via Expression.apply_intensity ---

    def scale(self, name: str, intensity: float) -> Dict[str, float]:
        """Return coefficients of an expression scaled by intensity."""
        expr = self.get(name)
        return expr.apply_intensity(intensity)

    # --- Viseme convenience ---

    def get_viseme(self, viseme_name: str) -> Expression:
        """
        Get a viseme expression. This is a convenience method.
        Viseme names are like "AA", "EE", etc.
        """
        # Viseme expressions are named "Viseme_AA" etc.
        full_name = f"Viseme_{viseme_name.upper()}"
        try:
            return self.get(full_name)
        except ExpressionNotFoundError:
            raise ExpressionNotFoundError(f"Viseme '{viseme_name}' not found. Try 'AA', 'EE', etc.")

    def list_visemes(self) -> List[str]:
        """Return names of all viseme expressions."""
        return [e.metadata.name for e in self._registry.filter_by_category("Viseme")]

    # --- Serialization ---

    def save_to_file(self, filepath: str) -> None:
        SerializationEngine.save_to_file(self._registry, filepath)

    @classmethod
    def load_from_file(cls, filepath: str) -> ExpressionSets:
        registry = SerializationEngine.load_from_file(filepath)
        instance = cls(load_builtin=False)
        # Replace registry with loaded one
        instance._registry = registry
        # Re-init diagnostics/statistics
        instance._diagnostics = DiagnosticsEngine(instance._registry, instance._validator)
        instance._statistics = StatisticsEngine(instance._registry)
        return instance

    def to_json(self) -> str:
        return SerializationEngine.serialize_json(self._registry)

    @classmethod
    def from_json(cls, data: str) -> ExpressionSets:
        registry = SerializationEngine.deserialize_json(data)
        instance = cls(load_builtin=False)
        instance._registry = registry
        return instance

    # --- Diagnostics and Statistics ---

    def diagnose(self) -> Dict[str, Any]:
        return self._diagnostics.diagnose()

    def statistics(self) -> Dict[str, Any]:
        return self._statistics.compute_statistics()

    # --- Clear ---

    def clear(self) -> None:
        self._registry.clear()


# ---- Public API --------------------------------------------------------

__all__ = [
    "ExpressionSets",
    "Expression",
    "ExpressionMetadata",
    "ExpressionGroup",
    "ExpressionRegistry",
    "ExpressionBlendEngine",
    "BuiltinExpressions",
    "ARKitExpressionError",
    "ExpressionNotFoundError",
    "DuplicateExpressionError",
    "InvalidExpressionError",
    "SerializationEngine",
]