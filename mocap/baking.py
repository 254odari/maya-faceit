"""
mocap/baking.py

Bake captured data to blendshapes or animation.

Converts mocap data to keyframes or baked blendshape weights in the Maya scene.
Supports baking to existing blendshape nodes, creating new blendshape targets,
and baking to animation curves.

Features:
- Bake coefficients to blendshape node keyframes
- Batch bake multiple frames
- Support for start frame and step size
- Clear existing keys before baking (optional)
- Bake to specific targets only (optional)
- Create new blendshape node if needed
- Progress callbacks for long bakes

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union

# Maya imports
try:
    import maya.cmds as cmds
    HAS_MAYA = True
except ImportError:
    HAS_MAYA = False
    # Dummy for testing
    class DummyCmds:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyCmds()

# Import recording data
try:
    from .recorder import RecordingData, MocapRecorder
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    class RecordingData:
        frames: List[Dict[str, float]] = []
        timestamps: List[float] = []
        frame_rate: int = 60
        duration: float = 0.0
    class MocapRecorder: pass

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class BakingError(Exception):
    """Base exception for baking operations."""
    pass


# ---- Data Models ----

@dataclass
class BakeSettings:
    """
    Settings for baking.
    """
    start_frame: int = 1                    # Starting frame in Maya
    step: int = 1                           # Frame step (bake every N frames)
    blendshape_node: Optional[str] = None   # Existing blendshape node to bake to
    target_channels: Optional[List[str]] = None  # Specific targets to bake (None = all)
    clear_existing: bool = True             # Clear existing keys before baking
    create_node_if_missing: bool = True     # Create blendshape node if not found
    bake_all_targets: bool = True           # If False, only bake channels present in data
    progress_callback: Optional[Callable[[float, str], None]] = None


@dataclass
class BakeResult:
    """
    Result of baking.
    """
    success: bool
    keyframes_created: int = 0
    targets_baked: int = 0
    blendshape_node: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    elapsed_time: float = 0.0


# ---- Mocap Baker ----

class MocapBaker:
    """
    Bake mocap data to blendshapes or keyframes.

    Converts recorded data to Maya animation.

    Usage:
        baker = MocapBaker()
        result = baker.bake(data, blendshape_node="face_BS", start_frame=1)
        if result.success:
            print(f"Baked {result.keyframes_created} keyframes")
    """

    def __init__(self, settings: Optional[BakeSettings] = None):
        """
        Initialize the baker.

        Args:
            settings: Optional settings.
        """
        if not HAS_MAYA:
            raise BakingError("Maya is not available for baking")

        self.settings = settings or BakeSettings()
        logger.debug("MocapBaker initialized")

    # ---- Main Baking Methods ----

    def bake(
        self,
        data: Union[RecordingData, List[Dict[str, float]]],
        blendshape_node: Optional[str] = None,
        start_frame: Optional[int] = None,
        settings: Optional[BakeSettings] = None,
    ) -> BakeResult:
        """
        Bake data to a blendshape node.

        Args:
            data: RecordingData or list of coefficient frames.
            blendshape_node: Target blendshape node.
            start_frame: Starting frame (overrides settings).
            settings: Override settings for this bake.

        Returns:
            BakeResult.
        """
        start_time = time.time()

        # Apply settings
        if settings is None:
            settings = self.settings
        else:
            self.settings = settings

        if blendshape_node is not None:
            settings.blendshape_node = blendshape_node

        if start_frame is not None:
            settings.start_frame = start_frame

        result = BakeResult(success=True, blendshape_node=settings.blendshape_node or "")

        # Extract frames
        if isinstance(data, RecordingData):
            frames = data.frames
            if not frames:
                result.success = False
                result.errors.append("No frames in recording data")
                result.elapsed_time = time.time() - start_time
                return result
        elif isinstance(data, list):
            frames = data
            if not frames:
                result.success = False
                result.errors.append("No frames provided")
                result.elapsed_time = time.time() - start_time
                return result
        else:
            result.success = False
            result.errors.append(f"Unsupported data type: {type(data)}")
            result.elapsed_time = time.time() - start_time
            return result

        # Get or create blendshape node
        node = self._get_or_create_node(settings.blendshape_node)
        if node is None:
            result.success = False
            result.errors.append("Could not find or create blendshape node")
            result.elapsed_time = time.time() - start_time
            return result

        result.blendshape_node = node

        # Bake the frames
        try:
            bake_result = self._bake_frames(frames, node, settings)
            result.keyframes_created = bake_result["keyframes"]
            result.targets_baked = bake_result["targets"]
            result.warnings.extend(bake_result["warnings"])
        except Exception as e:
            result.success = False
            result.errors.append(str(e))

        result.elapsed_time = time.time() - start_time
        return result

    def bake_to_scene(
        self,
        recording: RecordingData,
        blendshape_node: Optional[str] = None,
        start_frame: Optional[int] = None,
    ) -> BakeResult:
        """
        Bake recorded data to the Maya scene.

        Args:
            recording: RecordingData from MocapRecorder.
            blendshape_node: Target blendshade node.
            start_frame: Starting frame.

        Returns:
            BakeResult.
        """
        if start_frame is None:
            start_frame = int(cmds.playbackOptions(q=True, min=True))
        return self.bake(recording, blendshape_node, start_frame)

    # ---- Internal Methods ----

    def _get_or_create_node(self, node_name: Optional[str]) -> Optional[str]:
        """
        Get or create a blendshape node.

        Args:
            node_name: Name of the blendshape node.

        Returns:
            Node name or None if failed.
        """
        # If node exists, return it
        if node_name and cmds.objExists(node_name):
            if cmds.nodeType(node_name) == "blendShape":
                return node_name
            else:
                logger.warning(f"'{node_name}' exists but is not a blendShape node")

        # If node doesn't exist, try to create
        if self.settings.create_node_if_missing:
            # Need a base mesh to create a blendshape node
            # Try to find a mesh in the scene
            meshes = cmds.ls(type="mesh") or []
            if not meshes:
                logger.warning("No mesh found to create blendshape node")
                return None

            base_mesh = meshes[0]
            # Get the transform
            transform = cmds.listRelatives(base_mesh, parent=True)
            if transform:
                base_mesh = transform[0]

            # Create blendshape node
            if node_name:
                new_node = cmds.blendShape(base_mesh, name=node_name)[0]
            else:
                new_node = cmds.blendShape(base_mesh)[0]

            logger.info(f"Created blendshape node: {new_node}")
            return new_node

        return None

    def _bake_frames(
        self,
        frames: List[Dict[str, float]],
        node: str,
        settings: BakeSettings,
    ) -> Dict[str, Any]:
        """
        Bake frames to a blendshape node.

        Args:
            frames: List of coefficient frames.
            node: Blendshape node.
            settings: Bake settings.

        Returns:
            Dict with 'keyframes', 'targets', 'warnings'.
        """
        # Get targets on the blendshape node
        node_targets = cmds.listAttr(node, m=True, string="weight") or []
        if not node_targets:
            logger.warning(f"No targets found on blendshape node '{node}'")

        # Determine which targets to bake
        if settings.target_channels:
            bake_targets = [t for t in settings.target_channels if t in node_targets]
            if not bake_targets:
                logger.warning("None of the specified targets exist on the blendshape node")
                bake_targets = []
        elif settings.bake_all_targets:
            bake_targets = node_targets
        else:
            # Only bake targets that exist in the data
            data_targets = set()
            for f in frames:
                data_targets.update(f.keys())
            bake_targets = [t for t in node_targets if t in data_targets]

        if not bake_targets:
            return {"keyframes": 0, "targets": 0, "warnings": ["No targets to bake"]}

        # Clear existing keys if requested
        if settings.clear_existing:
            for target in bake_targets:
                attr = f"{node}.{target}"
                if cmds.objExists(attr):
                    cmds.cutKey(attr, clear=True)

        # Bake each frame
        keyframes_created = 0
        frame = settings.start_frame
        warnings = []

        total_frames = len(frames)
        for i, coeffs in enumerate(frames):
            # Update progress
            if settings.progress_callback:
                progress = i / total_frames
                settings.progress_callback(progress, f"Baking frame {i+1}/{total_frames}")

            # Set keys for each target
            for target in bake_targets:
                value = coeffs.get(target, 0.0)
                # Clamp to [0, 1] for safety
                if value < 0.0:
                    value = 0.0
                elif value > 1.0:
                    value = 1.0
                    warnings.append(f"Value {coeffs.get(target, 0.0):.3f} for '{target}' clamped to 1.0")

                attr = f"{node}.{target}"
                try:
                    cmds.setKeyframe(attr, t=frame, v=value)
                    keyframes_created += 1
                except Exception as e:
                    warnings.append(f"Failed to set key for '{target}': {e}")

            frame += settings.step

        return {
            "keyframes": keyframes_created,
            "targets": len(bake_targets),
            "warnings": warnings,
        }

    # ---- Convenience Methods ----

    def bake_from_file(
        self,
        filepath: str,
        blendshape_node: str,
        start_frame: int = 1,
    ) -> BakeResult:
        """
        Bake data from a recording file.

        Args:
            filepath: Path to recording JSON file.
            blendshape_node: Target blendshape node.
            start_frame: Starting frame.

        Returns:
            BakeResult.
        """
        recorder = MocapRecorder()
        data = recorder.load_from_file(filepath)
        return self.bake(data, blendshape_node, start_frame)

    def bake_current_session(
        self,
        recorder: MocapRecorder,
        blendshape_node: str,
        start_frame: Optional[int] = None,
    ) -> BakeResult:
        """
        Bake data from the current recording session.

        Args:
            recorder: MocapRecorder with recorded data.
            blendshape_node: Target blendshape node.
            start_frame: Starting frame.

        Returns:
            BakeResult.
        """
        data = recorder.get_data()
        return self.bake(data, blendshape_node, start_frame)


# ---- Convenience Functions ----

def bake_recording(
    recording_file: str,
    blendshape_node: str,
    start_frame: int = 1,
    step: int = 1,
    clear_existing: bool = True,
) -> BakeResult:
    """
    Convenience function to bake a recording file.

    Args:
        recording_file: Path to recording JSON file.
        blendshape_node: Target blendshape node.
        start_frame: Starting frame.
        step: Frame step.
        clear_existing: Clear existing keys.

    Returns:
        BakeResult.
    """
    settings = BakeSettings(
        start_frame=start_frame,
        step=step,
        blendshape_node=blendshape_node,
        clear_existing=clear_existing,
    )
    baker = MocapBaker(settings)
    return baker.bake_from_file(recording_file, blendshape_node, start_frame)


# ---- Public API ----

__all__ = [
    "MocapBaker",
    "BakeSettings",
    "BakeResult",
    "BakingError",
    "bake_recording",
]