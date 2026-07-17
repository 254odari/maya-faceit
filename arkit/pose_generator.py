"""
arkit/pose_generator.py

ARKit Pose Generator

This module is an automatic pose synthesis engine for the maya_faceit system.
It generates facial poses from ARKit channels, blends poses together, creates
intermediate poses, and produces pose libraries for rig testing and animation.

The generator sits above mapper.py and below pose_library.py, providing
procedural pose creation that reduces the need for manual authoring.

Responsibilities
----------------
• Generate single poses from coefficient dictionaries
• Synthesize complex expressions from templates (happy, angry, surprise, etc.)
• Blend multiple poses with configurable weights
• Mirror poses (swap left/right)
• Generate pose sequences (animation clips)
• Create random poses for stress testing
• Enforce constraints to avoid impossible configurations
• Provide diagnostics and statistics

Architecture
------------
Foundation (imports, constants, exceptions, logging)
↓
Data Models (Pose, PoseFrame, PoseSequence, ExpressionTemplate, PoseBlend)
↓
Single Pose Generation (from coefficients)
↓
Expression Generation (predefined expression templates)
↓
Pose Blending (combine poses with weights)
↓
Pose Mirroring (swap left/right)
↓
Pose Sequences (interpolation between poses)
↓
Random Pose Generator (with constraints)
↓
Diagnostics
↓
Statistics
↓
Public API (PoseGenerator)

Dependencies
------------
• arkit52.py - for channel names, left/right pairs, regions
• validator.py - for validating generated poses
• mapper.py - optional, for converting to rig weights
• remapper.py - optional, for naming conversions
"""

from __future__ import annotations

import copy
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Callable, Union, Iterable

# Import ARKit constants from canonical module
try:
    from .arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS, FACIAL_REGIONS, EXPRESSION_CATEGORIES
except ImportError:
    # Fallback definitions (should not happen in production)
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}
    FACIAL_REGIONS = {}
    EXPRESSION_CATEGORIES = {}

# Import validator
try:
    from .validator import ARKitValidator, ValidationLevel
except ImportError:
    # Fallback dummy validator for development
    class ARKitValidator:
        def validate_coefficients(self, coeffs, level=None, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class DummyReport:
                is_valid = True
                errors = []
                warnings = []
            return DummyReport()
    ValidationLevel = None

# Import mapper (optional)
try:
    from .mapper import ARKitMapper
except ImportError:
    ARKitMapper = None

# ---- Part 1: Foundation --------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class ARKitPoseGeneratorError(Exception):
    """Base exception for pose generator errors."""
    pass

class PoseDefinitionError(ARKitPoseGeneratorError):
    """Raised when a pose definition is invalid."""
    pass

class ExpressionTemplateError(ARKitPoseGeneratorError):
    """Raised when an expression template is malformed."""
    pass

class PoseBlendError(ARKitPoseGeneratorError):
    """Raised when blending fails."""
    pass

# ---- Part 2: Data Models ------------------------------------------------

@dataclass
class Pose:
    """
    A pose defined by a set of ARKit coefficients (channel -> value).
    Can include metadata like name, timestamp, and whether it's mirrored.
    """
    name: str
    coefficients: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_mirrored: bool = False
    normalized: bool = False

    def __post_init__(self):
        # Ensure coefficients are clamped to [0,1]
        for key in list(self.coefficients.keys()):
            if self.coefficients[key] < 0.0:
                self.coefficients[key] = 0.0
            elif self.coefficients[key] > 1.0:
                self.coefficients[key] = 1.0

    def get_active_channels(self, threshold: float = 0.01) -> List[str]:
        """Return channels with value > threshold."""
        return [k for k, v in self.coefficients.items() if v > threshold]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "coefficients": self.coefficients,
            "metadata": self.metadata,
            "is_mirrored": self.is_mirrored,
            "normalized": self.normalized,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pose:
        return cls(
            name=data.get("name", "unnamed"),
            coefficients=data.get("coefficients", {}),
            metadata=data.get("metadata", {}),
            is_mirrored=data.get("is_mirrored", False),
            normalized=data.get("normalized", False),
        )

    def clone(self) -> Pose:
        return Pose(
            name=self.name,
            coefficients=self.coefficients.copy(),
            metadata=self.metadata.copy(),
            is_mirrored=self.is_mirrored,
            normalized=self.normalized,
        )


@dataclass
class PoseFrame:
    """
    A single frame in a pose sequence, with a time offset.
    """
    time: float  # seconds from start
    pose: Pose
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoseSequence:
    """
    A sequence of pose frames (animation clip).
    """
    name: str
    frames: List[PoseFrame] = field(default_factory=list)
    loop: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_frame(self, time: float, pose: Pose) -> None:
        self.frames.append(PoseFrame(time, pose))
        # Sort by time
        self.frames.sort(key=lambda f: f.time)

    def get_duration(self) -> float:
        if not self.frames:
            return 0.0
        return max(f.time for f in self.frames)


@dataclass
class ExpressionTemplate:
    """
    Template for generating an expression.
    Defines which channels to affect and their target values or ranges.
    """
    name: str
    channels: Dict[str, float]  # target value for each channel (0-1)
    optional_channels: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # min, max for variation
    intensity: float = 1.0  # overall scale
    symmetry: str = "both"  # "both", "left", "right"
    constraints: List[Tuple[str, str]] = field(default_factory=list)  # pairs that cannot both be high

    def get_coefficients(self, intensity_override: Optional[float] = None) -> Dict[str, float]:
        """Generate a coefficient dict from this template, applying intensity."""
        coeffs = {}
        effective_intensity = intensity_override if intensity_override is not None else self.intensity

        # Apply main channels
        for channel, value in self.channels.items():
            # Scale by intensity, clamp to [0,1]
            scaled = min(1.0, value * effective_intensity)
            coeffs[channel] = scaled

        # Apply optional channels (use random if within range, or use the min? For deterministic, we use midpoint)
        # For deterministic generation, we'll use the midpoint of the range.
        for channel, (lo, hi) in self.optional_channels.items():
            midpoint = (lo + hi) * 0.5
            scaled = min(1.0, midpoint * effective_intensity)
            coeffs[channel] = scaled

        return coeffs


@dataclass
class PoseBlend:
    """
    Definition of a blend between two or more poses.
    """
    name: str
    source_poses: List[Pose]
    weights: List[float]  # must sum to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---- Part 3: Single Pose Generation -------------------------------------

class PoseGeneratorCore:
    """
    Core functions for generating poses from coefficients.
    """
    @staticmethod
    def from_coefficients(coefficients: Dict[str, float], name: str = "Pose") -> Pose:
        """
        Create a Pose from a dictionary of ARKit coefficients.
        Validates and clamps values.
        """
        # Validate coefficients (basic clamping and type check)
        cleaned = {}
        for key, val in coefficients.items():
            if not isinstance(val, (int, float)):
                logger.warning(f"Non-numeric value for '{key}': {val}, using 0.0")
                val = 0.0
            if val < 0.0:
                val = 0.0
            elif val > 1.0:
                val = 1.0
            cleaned[key] = val

        return Pose(name=name, coefficients=cleaned)

    @staticmethod
    def from_mapping_result(mapping_result: Dict[str, float], name: str = "MappedPose") -> Pose:
        """
        Create a Pose from the output of ARKitMapper (rig weights).
        Note: these are not raw ARKit coefficients but rig targets.
        This is useful for generating poses that are already in rig space.
        We treat them as coefficients for the purpose of this generator.
        """
        # No clamping to 0-1 if rig weights can be beyond? We'll clamp anyway.
        cleaned = {}
        for key, val in mapping_result.items():
            if not isinstance(val, (int, float)):
                continue
            if val < 0.0:
                val = 0.0
            elif val > 1.0:
                val = 1.0
            cleaned[key] = val
        return Pose(name=name, coefficients=cleaned)


# ---- Part 4: Expression Generation -------------------------------------

class ExpressionEngine:
    """
    Generates poses from predefined expression templates.
    """
    # Internal registry of templates
    _templates: Dict[str, ExpressionTemplate] = {}

    @classmethod
    def register_template(cls, template: ExpressionTemplate) -> None:
        cls._templates[template.name] = template

    @classmethod
    def get_template(cls, name: str) -> Optional[ExpressionTemplate]:
        return cls._templates.get(name)

    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls._templates.keys())

    @classmethod
    def generate(cls, expression_name: str, intensity: float = 1.0) -> Pose:
        """
        Generate a pose for a named expression.
        """
        template = cls.get_template(expression_name)
        if template is None:
            raise ExpressionTemplateError(f"Unknown expression template: '{expression_name}'")
        coeffs = template.get_coefficients(intensity)
        return Pose(name=expression_name, coefficients=coeffs)

    @classmethod
    def initialize_default_templates(cls):
        """Register a set of default expression templates."""
        # Neutral (all zero)
        cls.register_template(ExpressionTemplate(
            name="Neutral",
            channels={},
            optional_channels={}
        ))

        # Smile
        cls.register_template(ExpressionTemplate(
            name="Smile",
            channels={
                "mouthSmileLeft": 1.0,
                "mouthSmileRight": 1.0,
            },
            optional_channels={
                "cheekSquintLeft": (0.0, 0.4),
                "cheekSquintRight": (0.0, 0.4),
                "eyeSquintLeft": (0.0, 0.2),
                "eyeSquintRight": (0.0, 0.2),
            },
            symmetry="both"
        ))

        # Smile Left (asymmetric)
        cls.register_template(ExpressionTemplate(
            name="SmileLeft",
            channels={
                "mouthSmileLeft": 1.0,
            },
            optional_channels={
                "cheekSquintLeft": (0.0, 0.3),
            },
            symmetry="left"
        ))

        # Smile Right
        cls.register_template(ExpressionTemplate(
            name="SmileRight",
            channels={
                "mouthSmileRight": 1.0,
            },
            optional_channels={
                "cheekSquintRight": (0.0, 0.3),
            },
            symmetry="right"
        ))

        # Blink
        cls.register_template(ExpressionTemplate(
            name="Blink",
            channels={
                "eyeBlinkLeft": 1.0,
                "eyeBlinkRight": 1.0,
            },
            optional_channels={},
            symmetry="both"
        ))

        # Wink Left
        cls.register_template(ExpressionTemplate(
            name="WinkLeft",
            channels={
                "eyeBlinkLeft": 1.0,
            },
            optional_channels={},
            symmetry="left"
        ))

        # Wink Right
        cls.register_template(ExpressionTemplate(
            name="WinkRight",
            channels={
                "eyeBlinkRight": 1.0,
            },
            optional_channels={},
            symmetry="right"
        ))

        # Surprise
        cls.register_template(ExpressionTemplate(
            name="Surprise",
            channels={
                "browInnerUp": 0.8,
                "eyeWideLeft": 0.9,
                "eyeWideRight": 0.9,
                "jawOpen": 0.7,
            },
            optional_channels={
                "mouthUpperUpLeft": (0.0, 0.3),
                "mouthUpperUpRight": (0.0, 0.3),
            },
            symmetry="both"
        ))

        # Anger
        cls.register_template(ExpressionTemplate(
            name="Anger",
            channels={
                "browDownLeft": 0.8,
                "browDownRight": 0.8,
                "mouthPressLeft": 0.9,
                "mouthPressRight": 0.9,
                "jawForward": 0.5,
            },
            optional_channels={
                "eyeSquintLeft": (0.0, 0.4),
                "eyeSquintRight": (0.0, 0.4),
            },
            symmetry="both"
        ))

        # Sad
        cls.register_template(ExpressionTemplate(
            name="Sad",
            channels={
                "browInnerUp": 0.6,
                "mouthFrownLeft": 0.8,
                "mouthFrownRight": 0.8,
            },
            optional_channels={
                "jawOpen": (0.0, 0.3),
            },
            symmetry="both"
        ))

        # Disgust
        cls.register_template(ExpressionTemplate(
            name="Disgust",
            channels={
                "browDownLeft": 0.7,
                "browDownRight": 0.7,
                "noseSneerLeft": 0.9,
                "noseSneerRight": 0.9,
                "mouthUpperUpLeft": 0.6,
                "mouthUpperUpRight": 0.6,
            },
            optional_channels={},
            symmetry="both"
        ))

        # Fear
        cls.register_template(ExpressionTemplate(
            name="Fear",
            channels={
                "browOuterUpLeft": 0.8,
                "browOuterUpRight": 0.8,
                "eyeWideLeft": 0.7,
                "eyeWideRight": 0.7,
                "jawOpen": 0.4,
            },
            optional_channels={
                "mouthOpen": (0.0, 0.3),  # not in standard 52; we'll map to mouthStretch?
            },
            symmetry="both"
        ))

        # Joy (happy)
        cls.register_template(ExpressionTemplate(
            name="Joy",
            channels={
                "mouthSmileLeft": 1.0,
                "mouthSmileRight": 1.0,
                "cheekSquintLeft": 0.6,
                "cheekSquintRight": 0.6,
                "eyeSquintLeft": 0.3,
                "eyeSquintRight": 0.3,
            },
            optional_channels={},
            symmetry="both"
        ))

        # Visemes (approximations)
        # AH
        cls.register_template(ExpressionTemplate(
            name="Viseme_AH",
            channels={
                "jawOpen": 0.6,
                "mouthLowerDownLeft": 0.5,
                "mouthLowerDownRight": 0.5,
            },
            optional_channels={}
        ))
        # EE
        cls.register_template(ExpressionTemplate(
            name="Viseme_EE",
            channels={
                "jawOpen": 0.3,
                "mouthStretchLeft": 0.7,
                "mouthStretchRight": 0.7,
            },
            optional_channels={}
        ))
        # OH
        cls.register_template(ExpressionTemplate(
            name="Viseme_OH",
            channels={
                "jawOpen": 0.4,
                "mouthPucker": 0.6,
            },
            optional_channels={}
        ))
        # OO
        cls.register_template(ExpressionTemplate(
            name="Viseme_OO",
            channels={
                "jawOpen": 0.2,
                "mouthFunnel": 0.8,
            },
            optional_channels={}
        ))
        # FF
        cls.register_template(ExpressionTemplate(
            name="Viseme_FF",
            channels={
                "jawOpen": 0.1,
                "mouthUpperUpLeft": 0.4,
                "mouthUpperUpRight": 0.4,
                "mouthLowerDownLeft": 0.3,
                "mouthLowerDownRight": 0.3,
            },
            optional_channels={}
        ))


# ---- Part 5: Pose Blending ---------------------------------------------

class PoseBlendEngine:
    """
    Blend multiple poses together using weighted sum.
    """
    @staticmethod
    def blend(poses: List[Pose], weights: List[float], name: str = "Blend") -> Pose:
        """
        Blend a list of poses with corresponding weights.
        Weights must sum to 1.0 (will be normalized if not).
        """
        if not poses:
            raise PoseBlendError("No poses provided for blend")
        if len(poses) != len(weights):
            raise PoseBlendError("Number of poses and weights must match")

        # Normalize weights to sum to 1.0
        total = sum(weights)
        if total == 0.0:
            raise PoseBlendError("Total weight is zero")
        norm_weights = [w / total for w in weights]

        # Collect all channels from all poses
        all_channels = set()
        for pose in poses:
            all_channels.update(pose.coefficients.keys())

        blended_coeffs = {}
        for ch in all_channels:
            value = 0.0
            for pose, w in zip(poses, norm_weights):
                value += w * pose.coefficients.get(ch, 0.0)
            # Clamp to [0,1]
            if value < 0.0:
                value = 0.0
            elif value > 1.0:
                value = 1.0
            blended_coeffs[ch] = value

        return Pose(name=name, coefficients=blended_coeffs)

    @staticmethod
    def blend_with_pose(pose_a: Pose, pose_b: Pose, weight_a: float = 0.5, weight_b: float = 0.5, name: str = "Blend") -> Pose:
        """
        Convenience method to blend two poses.
        """
        return PoseBlendEngine.blend([pose_a, pose_b], [weight_a, weight_b], name)


# ---- Part 6: Pose Mirroring --------------------------------------------

class PoseMirrorEngine:
    """
    Mirror a pose using LEFT_RIGHT_PAIRS from arkit52.py.
    """
    def __init__(self, pair_map: Dict[str, str] = None):
        self.pair_map = pair_map or LEFT_RIGHT_PAIRS
        # Build reverse mapping for completeness
        self.reverse_map = {v: k for k, v in self.pair_map.items()}

    def mirror_pose(self, pose: Pose, name: Optional[str] = None) -> Pose:
        """
        Return a mirrored copy of the pose.
        Channels that have no left-right pair remain unchanged.
        """
        new_coeffs = {}
        for channel, value in pose.coefficients.items():
            mirror_ch = self.pair_map.get(channel)
            if mirror_ch:
                new_coeffs[mirror_ch] = value
            else:
                # Try reverse map
                mirror_ch = self.reverse_map.get(channel)
                if mirror_ch:
                    new_coeffs[mirror_ch] = value
                else:
                    # No mirror, keep as is
                    new_coeffs[channel] = value

        new_name = name or f"{pose.name}_Mirrored"
        new_pose = Pose(name=new_name, coefficients=new_coeffs, is_mirrored=True)
        return new_pose

    def ensure_symmetry(self, pose: Pose, name: Optional[str] = None) -> Pose:
        """
        Make a pose fully symmetric by averaging left and right pairs.
        """
        new_coeffs = pose.coefficients.copy()
        # Process each pair
        processed = set()
        for left, right in self.pair_map.items():
            if left in processed or right in processed:
                continue
            lval = new_coeffs.get(left, 0.0)
            rval = new_coeffs.get(right, 0.0)
            avg = (lval + rval) * 0.5
            new_coeffs[left] = avg
            new_coeffs[right] = avg
            processed.add(left)
            processed.add(right)

        new_name = name or f"{pose.name}_Symmetric"
        return Pose(name=new_name, coefficients=new_coeffs, is_mirrored=pose.is_mirrored)


# ---- Part 7: Pose Sequences -------------------------------------------

class SequenceGenerator:
    """
    Generate pose sequences (animation clips) via interpolation.
    """
    @staticmethod
    def interpolate_linear(pose_a: Pose, pose_b: Pose, steps: int, name: str = "Interpolate") -> PoseSequence:
        """
        Generate a sequence of poses linearly interpolating between pose_a and pose_b.
        Returns a PoseSequence with `steps+1` frames (including endpoints).
        """
        if steps < 1:
            raise ValueError("steps must be at least 1")
        seq = PoseSequence(name=name)
        for i in range(steps + 1):
            t = i / steps
            # Blend
            blend_pose = PoseBlendEngine.blend(
                [pose_a, pose_b],
                [1.0 - t, t],
                name=f"{name}_frame_{i}"
            )
            seq.add_frame(float(i) * 1.0 / 30.0, blend_pose)  # assume 30 fps
        return seq

    @staticmethod
    def create_blink_sequence(duration: float = 1.0, fps: float = 30.0) -> PoseSequence:
        """
        Generate a blink sequence: neutral -> half-close -> closed -> half-close -> neutral.
        """
        neutral = Pose("Neutral", {})
        half = Pose("HalfBlink", {"eyeBlinkLeft": 0.5, "eyeBlinkRight": 0.5})
        closed = Pose("Closed", {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0})

        seq = PoseSequence(name="Blink")
        # neutral at start
        seq.add_frame(0.0, neutral.clone())
        # half at 25% duration
        t1 = duration * 0.25
        seq.add_frame(t1, half.clone())
        # closed at 50%
        t2 = duration * 0.5
        seq.add_frame(t2, closed.clone())
        # half at 75%
        t3 = duration * 0.75
        seq.add_frame(t3, half.clone())
        # neutral at end
        seq.add_frame(duration, neutral.clone())
        return seq

    @staticmethod
    def create_smile_sequence(duration: float = 1.5, fps: float = 30.0) -> PoseSequence:
        """
        Generate a smile sequence: hold smile.
        """
        neutral = Pose("Neutral", {})
        smile = ExpressionEngine.generate("Smile", intensity=1.0)

        seq = PoseSequence(name="Smile")
        seq.add_frame(0.0, neutral.clone())
        seq.add_frame(duration * 0.3, smile.clone())
        seq.add_frame(duration * 0.7, smile.clone())
        seq.add_frame(duration, neutral.clone())
        return seq

    @staticmethod
    def create_sequence_from_poses(poses: List[Pose], timings: List[float], name: str = "Custom") -> PoseSequence:
        """
        Create a sequence from a list of poses with specified times.
        """
        if len(poses) != len(timings):
            raise ValueError("Number of poses and timings must match")
        seq = PoseSequence(name=name)
        for pose, t in zip(poses, timings):
            seq.add_frame(t, pose.clone())
        return seq


# ---- Part 8: Random Pose Generator ------------------------------------

class RandomPoseGenerator:
    """
    Generate random poses with constraints to avoid impossible configurations.
    """
    # Define conflicting pairs: channels that cannot both be high.
    # For example, eyeBlink and eyeWide cannot both be 1.0.
    CONFLICT_PAIRS = [
        ("eyeBlinkLeft", "eyeWideLeft"),
        ("eyeBlinkRight", "eyeWideRight"),
        ("jawOpen", "mouthClose"),  # though mouthClose may not exist
        ("mouthPucker", "mouthFunnel"),  # mutually exclusive
        ("mouthSmileLeft", "mouthFrownLeft"),
        ("mouthSmileRight", "mouthFrownRight"),
        ("mouthPressLeft", "mouthUpperUpLeft"),  # approx
        ("mouthPressRight", "mouthUpperUpRight"),
    ]

    @classmethod
    def generate_random_pose(
        cls,
        intensity: float = 0.5,
        active_channels: int = 8,
        symmetric: bool = True,
        seed: Optional[int] = None,
        name: str = "Random"
    ) -> Pose:
        """
        Generate a random pose.

        Args:
            intensity: overall scale of values (0-1).
            active_channels: number of channels to activate.
            symmetric: if True, ensure left-right symmetry.
            seed: optional random seed.
        """
        if seed is not None:
            random.seed(seed)

        # Choose random channels from ARKIT_SET (excluding those that are paired if symmetric)
        all_channels = list(ARKIT_SET) if ARKIT_SET else []
        if not all_channels:
            # Fallback: use a default set
            all_channels = [
                "browDownLeft", "browDownRight", "browInnerUp",
                "eyeBlinkLeft", "eyeBlinkRight", "jawOpen",
                "mouthSmileLeft", "mouthSmileRight", "mouthFunnel",
                "mouthPucker", "noseSneerLeft", "noseSneerRight"
            ]

        selected = []
        if symmetric:
            # If symmetric, we need to select pairs. We'll pick left channels and add right.
            left_channels = [ch for ch in all_channels if ch.endswith("Left") and ch in LEFT_RIGHT_PAIRS]
            # Also include non-paired channels (e.g., jawOpen, browInnerUp)
            unpaired = [ch for ch in all_channels if ch not in LEFT_RIGHT_PAIRS and not ch.endswith("Right")]
            # We'll pick from left channels and unpaired.
            available = left_channels + unpaired
            # Ensure we don't exceed available
            num_pairs = min(active_channels // 2, len(left_channels))
            # Pick pairs
            chosen_left = random.sample(left_channels, num_pairs) if left_channels else []
            chosen_unpaired = random.sample(unpaired, min(active_channels - 2 * num_pairs, len(unpaired))) if unpaired else []
            selected_sources = chosen_left + chosen_unpaired
            # Build selected list including rights for pairs
            for ch in chosen_left:
                right = LEFT_RIGHT_PAIRS.get(ch)
                if right:
                    selected.append((ch, right))
            for ch in chosen_unpaired:
                selected.append((ch,))
        else:
            # Asymmetric: just pick random channels
            num = min(active_channels, len(all_channels))
            chosen = random.sample(all_channels, num)
            selected = [(ch,) for ch in chosen]

        # Generate values
        coeffs = {}
        for item in selected:
            if len(item) == 2:
                left, right = item
                val = random.uniform(0.1, intensity)
                coeffs[left] = val
                coeffs[right] = val
            else:
                ch = item[0]
                val = random.uniform(0.1, intensity)
                coeffs[ch] = val

        # Apply constraints: for conflicting pairs, ensure at most one is high.
        # We'll adjust values for conflicts.
        for (a, b) in cls.CONFLICT_PAIRS:
            if a in coeffs and b in coeffs:
                # If both > 0.5, reduce one
                if coeffs[a] > 0.5 and coeffs[b] > 0.5:
                    # Reduce the smaller one to 0
                    if coeffs[a] < coeffs[b]:
                        coeffs[a] = 0.0
                    else:
                        coeffs[b] = 0.0

        return Pose(name=name, coefficients=coeffs)


# ---- Part 9: Diagnostics ----------------------------------------------

class DiagnosticsCollector:
    """
    Collects diagnostic information about generated poses.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_generated = 0
        self.expressions_generated = 0
        self.blended_poses = 0
        self.mirrored_poses = 0
        self.random_poses = 0
        self.sequences_generated = 0
        self.errors = 0
        self.warnings = 0

    def record_generation(self, pose: Pose, type: str = "single"):
        self.total_generated += 1
        if type == "expression":
            self.expressions_generated += 1
        elif type == "blend":
            self.blended_poses += 1
        elif type == "mirror":
            self.mirrored_poses += 1
        elif type == "random":
            self.random_poses += 1
        elif type == "sequence":
            self.sequences_generated += 1

    def record_error(self):
        self.errors += 1

    def record_warning(self):
        self.warnings += 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_generated": self.total_generated,
            "expressions": self.expressions_generated,
            "blended": self.blended_poses,
            "mirrored": self.mirrored_poses,
            "random": self.random_poses,
            "sequences": self.sequences_generated,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ---- Part 10: Statistics ----------------------------------------------

class StatisticsEngine:
    """
    Computes statistics about generated poses.
    """
    @staticmethod
    def compute_pose_stats(pose: Pose) -> Dict[str, Any]:
        active = pose.get_active_channels()
        return {
            "name": pose.name,
            "channel_count": len(pose.coefficients),
            "active_channels": len(active),
            "sum": sum(pose.coefficients.values()),
            "mean": sum(pose.coefficients.values()) / max(1, len(pose.coefficients)),
            "is_mirrored": pose.is_mirrored,
            "normalized": pose.normalized,
        }

    @staticmethod
    def aggregate_stats(pose_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not pose_stats:
            return {}
        total = len(pose_stats)
        avg_active = sum(s["active_channels"] for s in pose_stats) / total
        avg_sum = sum(s["sum"] for s in pose_stats) / total
        mirrored_count = sum(1 for s in pose_stats if s["is_mirrored"])
        return {
            "total_poses": total,
            "average_active_channels": avg_active,
            "average_sum": avg_sum,
            "mirrored_poses": mirrored_count,
        }


# ---- Part 11: Public API -----------------------------------------------

class PoseGenerator:
    """
    The main pose generator class providing all functionality.

    Methods:
        from_coefficients: Create pose from coefficient dict.
        generate_expression: Generate a named expression.
        blend: Blend multiple poses.
        mirror: Mirror a pose.
        symmetric: Make a pose symmetric.
        random: Generate a random pose.
        sequence: Generate a sequence from two poses (interpolation).
        blink_sequence: Generate a blink sequence.
        smile_sequence: Generate a smile sequence.
        get_expression_list: List available expression names.
        get_diagnostics: Return diagnostic summary.
        get_statistics: Return statistics of generated poses.
        reset_diagnostics: Reset internal diagnostics.
        register_expression_template: Add a custom expression template.
    """

    def __init__(self, use_validator: bool = True, collect_stats: bool = True):
        """
        Args:
            use_validator: if True, validate generated poses.
            collect_stats: if True, collect statistics.
        """
        self._use_validator = use_validator
        self._collect_stats = collect_stats
        self._validator = ARKitValidator() if use_validator else None
        self._diagnostics = DiagnosticsCollector()
        self._statistics: List[Dict[str, Any]] = []
        self._expression_engine = ExpressionEngine()
        # Initialize default templates
        ExpressionEngine.initialize_default_templates()
        self._mirror_engine = PoseMirrorEngine()
        self._blend_engine = PoseBlendEngine()
        self._random_engine = RandomPoseGenerator()

    # --- Single Pose Generation ---
    def from_coefficients(self, coefficients: Dict[str, float], name: str = "Pose") -> Pose:
        """Create a pose from a coefficient dictionary."""
        pose = PoseGeneratorCore.from_coefficients(coefficients, name)
        self._validate_pose(pose)
        self._record_pose(pose, "single")
        return pose

    # --- Expression Generation ---
    def generate_expression(self, expression_name: str, intensity: float = 1.0) -> Pose:
        """Generate a pose from a named expression template."""
        pose = ExpressionEngine.generate(expression_name, intensity)
        self._validate_pose(pose)
        self._record_pose(pose, "expression")
        return pose

    def get_expression_list(self) -> List[str]:
        """Return list of available expression names."""
        return ExpressionEngine.list_templates()

    def register_expression_template(self, template: ExpressionTemplate) -> None:
        """Register a custom expression template."""
        ExpressionEngine.register_template(template)

    # --- Pose Blending ---
    def blend(self, poses: List[Pose], weights: List[float], name: str = "Blend") -> Pose:
        """Blend multiple poses with weights."""
        pose = self._blend_engine.blend(poses, weights, name)
        self._validate_pose(pose)
        self._record_pose(pose, "blend")
        return pose

    def blend_two(self, pose_a: Pose, pose_b: Pose, weight_a: float = 0.5, name: str = "Blend") -> Pose:
        """Convenience method to blend two poses."""
        return self.blend([pose_a, pose_b], [weight_a, 1.0 - weight_a], name)

    # --- Mirroring ---
    def mirror(self, pose: Pose, name: Optional[str] = None) -> Pose:
        """Mirror a pose (swap left/right)."""
        mirrored = self._mirror_engine.mirror_pose(pose, name)
        self._validate_pose(mirrored)
        self._record_pose(mirrored, "mirror")
        return mirrored

    def make_symmetric(self, pose: Pose, name: Optional[str] = None) -> Pose:
        """Make a pose symmetric by averaging left/right pairs."""
        sym = self._mirror_engine.ensure_symmetry(pose, name)
        self._validate_pose(sym)
        self._record_pose(sym, "single")  # not mirror, but single generation
        return sym

    # --- Random Pose ---
    def random_pose(
        self,
        intensity: float = 0.5,
        active_channels: int = 8,
        symmetric: bool = True,
        seed: Optional[int] = None,
        name: str = "Random"
    ) -> Pose:
        """Generate a random pose."""
        pose = self._random_engine.generate_random_pose(
            intensity, active_channels, symmetric, seed, name
        )
        self._validate_pose(pose)
        self._record_pose(pose, "random")
        return pose

    # --- Sequences ---
    def interpolate_sequence(self, pose_a: Pose, pose_b: Pose, steps: int, name: str = "Interpolate") -> PoseSequence:
        """Generate an interpolated sequence between two poses."""
        seq = SequenceGenerator.interpolate_linear(pose_a, pose_b, steps, name)
        self._diagnostics.record_generation(pose_a, "sequence")  # just count as sequence
        # Optionally validate each frame
        if self._use_validator:
            for frame in seq.frames:
                self._validate_pose(frame.pose)
        return seq

    def blink_sequence(self, duration: float = 1.0) -> PoseSequence:
        """Generate a blink sequence."""
        seq = SequenceGenerator.create_blink_sequence(duration)
        self._diagnostics.record_generation(Pose("Dummy"), "sequence")
        return seq

    def smile_sequence(self, duration: float = 1.5) -> PoseSequence:
        """Generate a smile sequence."""
        seq = SequenceGenerator.create_smile_sequence(duration)
        self._diagnostics.record_generation(Pose("Dummy"), "sequence")
        return seq

    def custom_sequence(self, poses: List[Pose], timings: List[float], name: str = "Custom") -> PoseSequence:
        """Generate a sequence from a list of poses and timings."""
        seq = SequenceGenerator.create_sequence_from_poses(poses, timings, name)
        self._diagnostics.record_generation(Pose("Dummy"), "sequence")
        return seq

    # --- Internal helpers ---
    def _validate_pose(self, pose: Pose) -> None:
        if self._use_validator and self._validator:
            report = self._validator.validate_coefficients(
                pose.coefficients,
                level=ValidationLevel.STANDARD if ValidationLevel else None,
                allow_extra_channels=True
            )
            if not report.is_valid:
                for err in report.errors:
                    logger.warning(f"Validation error in pose '{pose.name}': {err.message}")
                    self._diagnostics.record_error()
            for warn in report.warnings:
                logger.debug(f"Validation warning in pose '{pose.name}': {warn.message}")
                self._diagnostics.record_warning()

    def _record_pose(self, pose: Pose, type: str) -> None:
        self._diagnostics.record_generation(pose, type)
        if self._collect_stats:
            self._statistics.append(StatisticsEngine.compute_pose_stats(pose))

    # --- Diagnostics & Statistics ---
    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic summary."""
        return self._diagnostics.get_summary()

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate statistics of all generated poses."""
        if not self._statistics:
            return {"total_poses": 0}
        return StatisticsEngine.aggregate_stats(self._statistics)

    def reset_diagnostics(self):
        """Reset diagnostic counters."""
        self._diagnostics.reset()

    def reset_statistics(self):
        """Clear collected pose statistics."""
        self._statistics.clear()

    def reset_all(self):
        """Reset diagnostics and statistics."""
        self.reset_diagnostics()
        self.reset_statistics()


# ---- Public API --------------------------------------------------------

__all__ = [
    "PoseGenerator",
    "Pose",
    "PoseFrame",
    "PoseSequence",
    "ExpressionTemplate",
    "PoseBlend",
    "ARKitPoseGeneratorError",
    "ExpressionTemplateError",
    "PoseBlendError",
    "PoseDefinitionError",
]