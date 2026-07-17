"""
mocap package - Facial motion capture processing for Maya FaceIT.

This package provides tools for recording, calibrating, filtering, retargeting,
and streaming facial motion capture data from various sources (iPhone Live Link,
MediaPipe, FaceCap, etc.) to blendshape rigs in Maya.

Modules:
- baking: Bake recorded data to blendshape keyframes.
- calibration: Calibrate facial capture data (neutral, range, symmetry).
- facecap: Process FaceCap (iPhone) data format.
- filters: Various filters for noise reduction, jitter removal, smoothing.
- iphone: iPhone TrueDepth camera capture (Live Link, FaceCap).
- livelink: Live Link Face receiver for Apple ARKit.
- mediapipe: MediaPipe face landmark detection and tracking.
- playback: Playback recorded motion data.
- recorder: Record facial motion data.
- retarget: Retarget captured data to face rigs.
- smoothing: Smoothing filters for tracking data.
- streaming: Real-time streaming to Maya.
"""

from .baking import (
    MocapBaker,
    BakeSettings,
    BakeResult,
    BakingError,
    bake_recording,
)

from .calibration import (
    MocapCalibration,
    CalibrationProfile,
    CalibrationResult,
    CalibrationError,
    create_calibration_profile,
)

from .facecap import (
    FaceCapProcessor,
    FaceCapSettings,
    FaceCapData,
    FaceCapError,
    facecap_to_arkit,
    facecap_to_faceit,
)

from .filters import (
    FilterBase,
    FilterSettings,
    FilterError,
    NoiseReductionFilter,
    JitterFilter,
    MedianFilter,
    LowPassFilter,
    ClampFilter,
    NormalizeFilter,
    ScaleFilter,
    BiasFilter,
    FilterChain,
    create_noise_reduction_filter,
    create_jitter_filter,
    create_median_filter,
    create_low_pass_filter,
    create_standard_chain,
)

from .iphone import (
    iPhoneCapture,
    iPhoneSettings,
    iPhoneFrame,
    iPhoneError,
    create_iphone_capture,
)

from .livelink import (
    LiveLinkReceiver,
    LiveLinkSettings,
    LiveLinkData,
    LiveLinkError,
)

from .mediapipe import (
    MediaPipeTracker,
    MediaPipeSettings,
    MediaPipeResult,
    MediaPipeError,
    blendshapes_to_arkit,
    blendshapes_to_faceit,
)

from .playback import (
    MocapPlayback,
    PlaybackSettings,
    PlaybackState,
    PlaybackError,
    create_playback_from_file,
)

from .recorder import (
    MocapRecorder,
    RecordingSettings,
    RecordingData,
    RecorderError,
    save_recording,
    load_recording,
)

from .retarget import (
    RetargetEngine,
    RetargetSettings,
    RetargetResult,
    RetargetError,
)

from .smoothing import (
    SmoothingFilter,
    SmoothingSettings,
    SmoothingError,
    create_moving_average_filter,
    create_exponential_filter,
    create_gaussian_filter,
)

from .streaming import (
    MocapStreamer,
    StreamSettings,
    StreamStatistics,
    StreamError,
    create_livelink_streamer,
    create_mediapipe_streamer,
    create_iphone_streamer,
)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

__all__ = [
    # baking
    "MocapBaker",
    "BakeSettings",
    "BakeResult",
    "BakingError",
    "bake_recording",
    # calibration
    "MocapCalibration",
    "CalibrationProfile",
    "CalibrationResult",
    "CalibrationError",
    "create_calibration_profile",
    # facecap
    "FaceCapProcessor",
    "FaceCapSettings",
    "FaceCapData",
    "FaceCapError",
    "facecap_to_arkit",
    "facecap_to_faceit",
    # filters
    "FilterBase",
    "FilterSettings",
    "FilterError",
    "NoiseReductionFilter",
    "JitterFilter",
    "MedianFilter",
    "LowPassFilter",
    "ClampFilter",
    "NormalizeFilter",
    "ScaleFilter",
    "BiasFilter",
    "FilterChain",
    "create_noise_reduction_filter",
    "create_jitter_filter",
    "create_median_filter",
    "create_low_pass_filter",
    "create_standard_chain",
    # iphone
    "iPhoneCapture",
    "iPhoneSettings",
    "iPhoneFrame",
    "iPhoneError",
    "create_iphone_capture",
    # livelink
    "LiveLinkReceiver",
    "LiveLinkSettings",
    "LiveLinkData",
    "LiveLinkError",
    # mediapipe
    "MediaPipeTracker",
    "MediaPipeSettings",
    "MediaPipeResult",
    "MediaPipeError",
    "blendshapes_to_arkit",
    "blendshapes_to_faceit",
    # playback
    "MocapPlayback",
    "PlaybackSettings",
    "PlaybackState",
    "PlaybackError",
    "create_playback_from_file",
    # recorder
    "MocapRecorder",
    "RecordingSettings",
    "RecordingData",
    "RecorderError",
    "save_recording",
    "load_recording",
    # retarget
    "RetargetEngine",
    "RetargetSettings",
    "RetargetResult",
    "RetargetError",
    # smoothing
    "SmoothingFilter",
    "SmoothingSettings",
    "SmoothingError",
    "create_moving_average_filter",
    "create_exponential_filter",
    "create_gaussian_filter",
    # streaming
    "MocapStreamer",
    "StreamSettings",
    "StreamStatistics",
    "StreamError",
    "create_livelink_streamer",
    "create_mediapipe_streamer",
    "create_iphone_streamer",
]