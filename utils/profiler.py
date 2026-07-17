# -*- coding: utf-8 -*-
"""
maya_faceit.utils.profiler
~~~~~~~~~~~~~~~~~~~~~~~~~~

Profiling utilities.
"""

import time
import functools
from typing import Dict, Any


class Profiler:
    """Simple profiler for measuring execution times of functions."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
        return cls._instance

    def __init__(self):
        self._data = getattr(self, '_data', {})

    def start(self, name: str):
        """Start timing a named block."""
        self._data[name] = {'start': time.time(), 'end': None, 'duration': 0.0}

    def stop(self, name: str):
        """Stop timing a named block."""
        if name in self._data:
            self._data[name]['end'] = time.time()
            self._data[name]['duration'] = self._data[name]['end'] - self._data[name]['start']

    def get_duration(self, name: str) -> float:
        """Get the duration of a named block in seconds."""
        if name in self._data:
            return self._data[name]['duration']
        return 0.0

    def get_all(self) -> Dict[str, float]:
        """Get all durations."""
        return {name: data['duration'] for name, data in self._data.items()}

    def reset(self):
        """Clear all profiling data."""
        self._data.clear()

    def report(self):
        """Print a report."""
        print("\n=== Profiler Report ===")
        total = 0
        for name, data in self._data.items():
            duration = data['duration']
            total += duration
            print(f"{name}: {duration:.4f}s")
        print(f"Total: {total:.4f}s")


def profile(func):
    """Decorator to profile a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = Profiler()
        profiler.start(func.__name__)
        result = func(*args, **kwargs)
        profiler.stop(func.__name__)
        return result
    return wrapper