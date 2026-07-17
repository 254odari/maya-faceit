#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ARKit Streaming – Real‑time processing of ARKit coefficient streams.

This module provides a complete streaming pipeline for receiving, buffering,
processing, and dispatching ARKit frames from various sources (OSC, file,
mock). It supports thread‑safe producer/consumer patterns, frame timing,
playback controls, and diagnostics.
"""

from __future__ import annotations

import time
import threading
import logging
import json
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic
from pathlib import Path

# Placeholder imports matching the original layout architecture
# Replace or adjust paths based on your final package naming structure
try:
    from .mapper import ARKitMapper
    from .converter import ARKitConverter, MergeMode
    from .exceptions import StreamingError, ConversionError
    from .io import JSONHandler
except ImportError:
    # Fallback declarations for isolated testing
    class MergeMode(Enum):
        ADD = 1
    class StreamingError(Exception): pass
    class JSONHandler:
        @staticmethod
        def read(path: Path) -> Any:
            with open(path, "r") as f: return json.load(f)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

class StreamState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class FrameStatus(Enum):
    OK = "ok"
    DROPPED = "dropped"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(slots=True)
class Frame:
    """A single frame of ARKit coefficients with metadata."""
    coefficients: Dict[str, float]
    timestamp: float
    frame_number: int
    source: str = "unknown"
    status: FrameStatus = FrameStatus.OK
    processing_time: float = 0.0
    note: str = ""

    def __post_init__(self):
        self.timestamp = self.timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coefficients": self.coefficients,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
            "source": self.source,
            "status": self.status.value,
            "processing_time": self.processing_time,
            "note": self.note,
        }


@dataclass(slots=True)
class StreamingConfig:
    max_buffer_size: int = 1024          
    target_frame_rate: int = 60           
    timeout_seconds: float = 5.0          
    drop_threshold: float = 0.5           
    enable_stats: bool = True
    logger_level: str = "INFO"
    auto_convert: bool = True              
    merge_mode: MergeMode = MergeMode.ADD


@dataclass(slots=True)
class StreamingStats:
    """Runtime statistics for tracking performance drop frequencies."""
    start_time: float = 0.0
    last_frame_time: float = 0.0
    frames_received: int = 0
    frames_processed: int = 0
    frames_dropped: int = 0
    frames_skipped: int = 0
    errors: int = 0
    average_fps: float = 0.0
    min_fps: float = 1000.0
    max_fps: float = 0.0
    total_time: float = 0.0

    def update(self, frame: Frame) -> None:
        self.frames_received += 1
        if frame.status == FrameStatus.OK:
            self.frames_processed += 1
        elif frame.status == FrameStatus.DROPPED:
            self.frames_dropped += 1
        elif frame.status == FrameStatus.SKIPPED:
            self.frames_skipped += 1

        now = time.time()
        if self.last_frame_time > 0:
            dt = now - self.last_frame_time
            if dt > 0:
                fps = 1.0 / dt
                self.min_fps = min(self.min_fps, fps)
                self.max_fps = max(self.max_fps, fps)
        self.last_frame_time = now

        if self.start_time == 0:
            self.start_time = now
        self.total_time = now - self.start_time
        if self.total_time > 0:
            self.average_fps = self.frames_received / self.total_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frames_received": self.frames_received,
            "frames_processed": self.frames_processed,
            "frames_dropped": self.frames_dropped,
            "frames_skipped": self.frames_skipped,
            "errors": self.errors,
            "average_fps": round(self.average_fps, 2),
            "min_fps": round(self.min_fps, 2) if self.min_fps < 1000 else None,
            "max_fps": round(self.max_fps, 2) if self.max_fps > 0 else None,
            "total_time": round(self.total_time, 2),
        }

# -----------------------------------------------------------------------------
# Buffer Implementations
# -----------------------------------------------------------------------------

T = TypeVar('T')

class RingBuffer(Generic[T]):
    """Thread‑safe circular ring buffer with fixed maximum allocations."""
    def __init__(self, capacity: int):
        self._buffer: List[Optional[T]] = [None] * capacity
        self._capacity = capacity
        self._head = 0
        self._tail = 0
        self._count = 0
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> bool:
        if self._count == self._capacity and block:
            with self._not_full:
                if timeout is None:
                    self._not_full.wait()
                elif not self._not_full.wait(timeout):
                    return False
        with self._lock:
            if self._count == self._capacity:
                self._tail = (self._tail + 1) % self._capacity
            else:
                self._count += 1
            self._buffer[self._head] = item
            self._head = (self._head + 1) % self._capacity
            self._not_empty.notify()
            return True

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[T]:
        if self._count == 0 and block:
            with self._not_empty:
                if timeout is None:
                    self._not_empty.wait()
                elif not self._not_empty.wait(timeout):
                    return None
        with self._lock:
            if self._count == 0:
                return None
            item = self._buffer[self._tail]
            self._buffer[self._tail] = None
            self._tail = (self._tail + 1) % self._capacity
            self._count -= 1
            self._not_full.notify()
            return item

    def clear(self) -> None:
        with self._lock:
            self._buffer = [None] * self._capacity
            self._head = 0
            self._tail = 0
            self._count = 0
            self._not_full.notify_all()

    def size(self) -> int:
        with self._lock:
            return self._count


class TimedBuffer(RingBuffer[Frame]):
    def __init__(self, capacity: int):
        super().__init__(capacity)
        self._timestamps: List[float] = [0.0] * capacity

    def put(self, frame: Frame, block: bool = True, timeout: Optional[float] = None) -> bool:
        result = super().put(frame, block=block, timeout=timeout)
        with self._lock:
            idx = (self._head - 1) % self._capacity
            self._timestamps[idx] = frame.timestamp
        return result

    def get_by_timestamp(self, timestamp: float, tolerance: float = 0.01) -> Optional[Frame]:
        with self._lock:
            if self._count == 0:
                return None
            best_idx = -1
            best_diff = tolerance + 1.0
            for i in range(self._count):
                idx = (self._tail + i) % self._capacity
                diff = abs(self._timestamps[idx] - timestamp)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = idx
            if best_idx >= 0 and best_diff <= tolerance:
                return self._buffer[best_idx]
        return None

# -----------------------------------------------------------------------------
# Streaming Sources
# -----------------------------------------------------------------------------

class StreamSource(ABC):
    def __init__(self):
        self._running = False
        self._frame_count = 0

    @abstractmethod
    def open(self) -> None: pass

    @abstractmethod
    def read(self, timeout: float = 1.0) -> Optional[Dict[str, float]]: pass

    @abstractmethod
    def close(self) -> None: pass

    def start(self) -> None: self._running = True
    def stop(self) -> None: self._running = False
    def is_running(self) -> bool: return self._running


class OSCSource(StreamSource):
    """OSC source supporting JSON network payloads or direct fallback maps."""
    def __init__(self, address: str = "127.0.0.1", port: int = 9001, buffer_size: int = 1024):
        super().__init__()
        self.address = address
        self.port = port
        self.buffer_size = buffer_size
        self._socket: Optional[socket.socket] = None

    def open(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(0.1)
        self._socket.bind((self.address, self.port))
        logger.info(f"OSC source listening on {self.address}:{self.port}")

    def read(self, timeout: float = 1.0) -> Optional[Dict[str, float]]:
        if self._socket is None:
            return None
        try:
            data, _ = self._socket.recvfrom(self.buffer_size)
            try:
                payload = json.loads(data.decode('utf-8'))
                coeffs = payload.get('blendshapes', payload)
                self._frame_count += 1
                return coeffs
            except json.JSONDecodeError:
                # Add third-party binary OSC decoding libraries here if needed
                return None
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"OSC read error: {e}")
            return None

    def close(self) -> None:
        if self._socket:
            self._socket.close()
            self._socket = None
        logger.info("OSC source closed.")


class FileSource(StreamSource):
    """File source executing real-time playback simulation throttles."""
    def __init__(self, filepath: Union[str, Path], loop: bool = False, playback_speed: float = 1.0):
        super().__init__()
        self.filepath = Path(filepath)
        self.loop = loop
        self.playback_speed = playback_speed
        self._frames: List[Dict[str, Any]] = []
        self._index = 0
        self._last_frame_time = 0.0

    def open(self) -> None:
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        data = JSONHandler.read(self.filepath)
        frames = data.get('frames', data) if isinstance(data, dict) else data
        if isinstance(frames, list):
            self._frames = frames
        else:
            raise ValueError("Invalid file format: expected list of frames")
        self._index = 0
        self._last_frame_time = time.time()
        logger.info(f"Loaded {len(self._frames)} frames from {self.filepath}")

    def read(self, timeout: float = 1.0) -> Optional[Dict[str, float]]:
        if self._index >= len(self._frames):
            if self.loop:
                self._index = 0
            else:
                return None

        frame_data = self._frames[self._index]
        
        # Fixed: Real-time clock synchronization loop throttling
        if 'timestamp' in frame_data and self._index > 0:
            prev_frame = self._frames[self._index - 1]
            time_delta = frame_data['timestamp'] - prev_frame.get('timestamp', frame_data['timestamp'])
            scaled_sleep = max(0.0, time_delta / max(0.01, self.playback_speed))
            time.sleep(scaled_sleep)

        self._index += 1
        self._frame_count += 1
        return frame_data.get('coefficients', frame_data)

    def close(self) -> None:
        self._frames = []
        self._index = 0
        logger.info("File source closed.")


class MockSource(StreamSource):
    def __init__(self, frame_rate: int = 60, channels: Optional[List[str]] = None):
        super().__init__()
        self.frame_rate = frame_rate
        self.channels = channels or ["jawOpen", "mouthSmileLeft", "mouthSmileRight", "eyeBlinkLeft", "eyeBlinkRight"]
        self._frame_interval = 1.0 / frame_rate
        self._last_read = 0.0

    def open(self) -> None:
        self._last_read = time.time()
        logger.info("Mock source opened.")

    def read(self, timeout: float = 1.0) -> Optional[Dict[str, float]]:
        now = time.time()
        elapsed = now - self._last_read
        if elapsed < self._frame_interval:
            time.sleep(max(0.001, self._frame_interval - elapsed))
            
        self._last_read = time.time()
        import random
        coeffs = {ch: random.uniform(0.0, 1.0) for ch in self.channels}
        self._frame_count += 1
        return coeffs

    def close(self) -> None:
        logger.info("Mock source closed.")

# -----------------------------------------------------------------------------
# Pipeline Stages
# -----------------------------------------------------------------------------

class PipelineStage(ABC):
    @abstractmethod
    def process(self, frame: Frame) -> Frame: pass


class FrameDecoder(PipelineStage):
    def process(self, data: Any) -> Frame:
        if isinstance(data, Frame):
            return data
        if isinstance(data, dict):
            return Frame(data, timestamp=time.time(), frame_number=0)
        raise ValueError(f"Unsupported data type: {type(data)}")


class ConverterStage(PipelineStage):
    def __init__(self, converter: ARKitConverter):
        self.converter = converter

    def process(self, frame: Frame) -> Frame:
        if not frame.coefficients:
            return frame
        start = time.time()
        try:
            result = self.converter.convert_frame(frame.coefficients)
            frame.coefficients = result  
            frame.processing_time = time.time() - start
            frame.status = FrameStatus.OK
        except Exception as e:
            frame.status = FrameStatus.ERROR
            frame.note = str(e)
        return frame


class Dispatcher:
    def __init__(self):
        self._callbacks: List[Callable[[Frame], None]] = []
        self._lock = threading.Lock()

    def register(self, callback: Callable[[Frame], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def unregister(self, callback: Callable[[Frame], None]) -> bool:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                return True
            return False

    def dispatch(self, frame: Frame) -> None:
        with self._lock:
            callbacks = self._callbacks[:]
        for cb in callbacks:
            try:
                cb(frame)
            except Exception as e:
                logger.error(f"Callback error: {e}")

# -----------------------------------------------------------------------------
# Producer/Consumer Threads
# -----------------------------------------------------------------------------

class ProducerThread(threading.Thread):
    def __init__(self, source: StreamSource, buffer: RingBuffer[Frame], decoder: PipelineStage,
                 stats: StreamingStats, stop_event: threading.Event, timeout: float = 1.0):
        super().__init__(daemon=True)
        self.source = source
        self.buffer = buffer
        self.decoder = decoder
        self.stats = stats
        self.stop_event = stop_event
        self.timeout = timeout
        self.name = "ProducerThread"

    def run(self) -> None:
        self.source.start()
        frame_number = 0
        while not self.stop_event.is_set():
            try:
                data = self.source.read(self.timeout)
                if data is None:
                    continue
                try:
                    frame = self.decoder.process(data)
                    frame.frame_number = frame_number
                    frame.source = self.source.__class__.__name__
                    frame_number += 1
                    if not self.buffer.put(frame, block=False):
                        frame.status = FrameStatus.DROPPED
                        self.stats.update(frame)
                except Exception as e:
                    logger.error(f"Frame processing error: {e}")
                    self.stats.errors += 1
            except Exception as e:
                logger.error(f"Producer error: {e}")
                self.stats.errors += 1
        self.source.stop()
        self.source.close()
        logger.info("Producer stopped.")


class ConsumerThread(threading.Thread):
    """Consumer loop checking pause states to synchronize pipelines."""
    def __init__(self, buffer: RingBuffer[Frame], dispatcher: Dispatcher, stats: StreamingStats,
                 stop_event: threading.Event, playback_controls: PlaybackControls,
                 timeout: float = 1.0, pipeline_steps: List[PipelineStage] = None):
        super().__init__(daemon=True)
        self.buffer = buffer
        self.dispatcher = dispatcher
        self.stats = stats
        self.stop_event = stop_event
        self.playback_controls = playback_controls
        self.timeout = timeout
        self.pipeline_steps = pipeline_steps or []
        self.name = "ConsumerThread"

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                # Fixed: System-wide pipeline pause interceptor
                if self.playback_controls.is_paused():
                    time.sleep(0.05)
                    continue

                frame = self.buffer.get(block=True, timeout=self.timeout)
                if frame is None:
                    continue
                
                for stage in self.pipeline_steps:
                    try:
                        frame = stage.process(frame)
                    except Exception as e:
                        frame.status = FrameStatus.ERROR
                        frame.note = str(e)
                
                self.stats.update(frame)
                self.dispatcher.dispatch(frame)
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                self.stats.errors += 1
        logger.info("Consumer stopped.")

# -----------------------------------------------------------------------------
# Playback Controls
# -----------------------------------------------------------------------------

class PlaybackControls:
    def __init__(self, buffer: RingBuffer[Frame]):
        self.buffer = buffer
        self._paused = False
        self._lock = threading.Lock()

    def pause(self) -> None:
        with self._lock: self._paused = True

    def resume(self) -> None:
        with self._lock: self._paused = False

    def is_paused(self) -> bool:
        with self._lock: return self._paused

    def seek(self, timestamp: float) -> bool:
        if isinstance(self.buffer, TimedBuffer):
            frame = self.buffer.get_by_timestamp(timestamp)
            if frame:
                self.buffer.clear()
                self.buffer.put(frame)
                return True
        return False

    def clear(self) -> None:
        self.buffer.clear()

# -----------------------------------------------------------------------------
# Streaming Manager (Public API Layout)
# -----------------------------------------------------------------------------

class StreamingManager:
    def __init__(self, config: Optional[StreamingConfig] = None, mapper: Optional[ARKitMapper] = None):
        self.config = config or StreamingConfig()
        self.mapper = mapper
        self.converter: Optional[ARKitConverter] = None
        
        if mapper:
            self.converter = ARKitConverter(
                mapper.get_mappings(),
                merge_rules=None,
                auto_compile=True
            )

        self._buffer: RingBuffer[Frame] = TimedBuffer(self.config.max_buffer_size)
        self._dispatcher = Dispatcher()
        self._stop_event = threading.Event()
        self._stats = StreamingStats()
        self._source: Optional[StreamSource] = None
        self._producer: Optional[ProducerThread] = None
        self._consumer: Optional[ConsumerThread] = None
        self._playback = PlaybackControls(self._buffer)
        self._state = StreamState.IDLE
        self._lock = threading.Lock()

        self._decoder = FrameDecoder()
        self._pipeline_stages: List[PipelineStage] = [self._decoder]
        if self.converter:
            self._pipeline_stages.append(ConverterStage(self.converter))

    def connect(self, source: StreamSource) -> None:
        with self._lock:
            if self._state in (StreamState.RUNNING, StreamState.PAUSED):
                raise StreamingError("Cannot change source while streaming.")
            if self._source:
                self._source.close()
            self._source = source
            source.open()
            self._state = StreamState.IDLE

    def add_callback(self, callback: Callable[[Frame], None]) -> None:
        self._dispatcher.register(callback)

    def remove_callback(self, callback: Callable[[Frame], None]) -> bool:
        return self._dispatcher.unregister(callback)

    def start(self) -> None:
        with self._lock:
            if self._state == StreamState.RUNNING:
                return
            if self._source is None:
                raise StreamingError("No source connected. Call connect() first.")
            self._stop_event.clear()
            self._playback.resume() # Reset pause flags on startup
            
            self._producer = ProducerThread(
                self._source, self._buffer, self._decoder, self._stats,
                self._stop_event, self.config.timeout_seconds
            )
            self._consumer = ConsumerThread(
                self._buffer, self._dispatcher, self._stats, self._stop_event,
                self._playback, self.config.timeout_seconds, self._pipeline_stages
            )
            self._producer.start()
            self._consumer.start()
            self._state = StreamState.RUNNING
            logger.info("Streaming started.")

    def pause(self) -> None:
        with self._lock:
            self._playback.pause()
            self._state = StreamState.PAUSED

    def resume(self) -> None:
        with self._lock:
            self._playback.resume()
            self._state = StreamState.RUNNING

    def stop(self) -> None:
        with self._lock:
            if self._state in (StreamState.STOPPED, StreamState.IDLE):
                return
            self._stop_event.set()
            if self._producer and self._producer.is_alive():
                self._producer.join(timeout=2.0)
            if self._consumer and self._consumer.is_alive():
                self._consumer.join(timeout=2.0)
            self._producer = None
            self._consumer = None
            self._buffer.clear()
            self._state = StreamState.STOPPED
            logger.info("Streaming stopped.")

    def get_stats(self) -> StreamingStats: return self._stats
    def get_state(self) -> StreamState: return self._state
    def is_running(self) -> bool: return self._state == StreamState.RUNNING
    def is_paused(self) -> bool: return self._state == StreamState.PAUSED

    def __enter__(self) -> "StreamingManager": return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        if self._source:
            self._source.close()
            self._source = None


def format_stats(stats: StreamingStats, verbose: bool = False) -> str:
    lines = [
        "--- Streaming Statistics ---",
        f"Frames received:   {stats.frames_received}",
        f"Frames processed:  {stats.frames_processed}",
        f"Frames dropped:    {stats.frames_dropped}",
        f"Frames skipped:    {stats.frames_skipped}",
        f"Errors:            {stats.errors}",
        f"Average FPS:       {stats.average_fps:.2f}",
        f"Total time:        {stats.total_time:.2f}s",
    ]
    if verbose:
        lines.append(f"Min FPS:           {stats.min_fps:.2f}")
        lines.append(f"Max FPS:           {stats.max_fps:.2f}")
    return "\n".join(lines)


__all__ = [
    "StreamState", "FrameStatus", "Frame", "StreamingConfig", "StreamingStats",
    "RingBuffer", "TimedBuffer", "StreamSource", "OSCSource", "FileSource",
    "MockSource", "PipelineStage", "FrameDecoder", "ConverterStage", "Dispatcher",
    "ProducerThread", "ConsumerThread", "PlaybackControls", "StreamingManager",
    "format_stats", "logger"
]