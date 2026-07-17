"""
singleton.py

Global runtime singleton and registry.
"""

import weakref
from threading import Lock
from typing import Dict, List, Optional

from .manager import RuntimeManager


# Global state
_RUNTIME_SINGLETON: Optional[RuntimeManager] = None
_RUNTIME_LOCK = Lock()
_RUNTIME_REGISTRY = weakref.WeakValueDictionary()


# ============================================================
# Singleton Access
# ============================================================

def get_runtime(converter=None, config=None) -> RuntimeManager:
    """Return the global RuntimeManager."""
    global _RUNTIME_SINGLETON
    with _RUNTIME_LOCK:
        if _RUNTIME_SINGLETON is None:
            _RUNTIME_SINGLETON = RuntimeManager(converter=converter, config=config)
        return _RUNTIME_SINGLETON


def set_runtime(runtime: RuntimeManager) -> RuntimeManager:
    """Replace the global runtime."""
    global _RUNTIME_SINGLETON
    with _RUNTIME_LOCK:
        _RUNTIME_SINGLETON = runtime
    return runtime


def reset_runtime() -> RuntimeManager:
    """Reset and recreate the global runtime."""
    global _RUNTIME_SINGLETON
    with _RUNTIME_LOCK:
        if _RUNTIME_SINGLETON is not None:
            try:
                _RUNTIME_SINGLETON.dispose()
            finally:
                _RUNTIME_SINGLETON = None
        _RUNTIME_SINGLETON = RuntimeManager()
    return _RUNTIME_SINGLETON


def shutdown_runtime() -> None:
    """Shutdown the global runtime."""
    global _RUNTIME_SINGLETON
    with _RUNTIME_LOCK:
        if _RUNTIME_SINGLETON is not None:
            try:
                _RUNTIME_SINGLETON.shutdown()
            finally:
                _RUNTIME_SINGLETON = None


def runtime_exists() -> bool:
    """Check if a global runtime exists."""
    return _RUNTIME_SINGLETON is not None


# ============================================================
# Registry
# ============================================================

def register_runtime(runtime: RuntimeManager) -> None:
    """Register a runtime in the global registry."""
    if runtime.session is not None:
        _RUNTIME_REGISTRY[runtime.session.session_id] = runtime


def unregister_runtime(runtime: RuntimeManager) -> None:
    """Remove a runtime from the registry."""
    if runtime.session is not None:
        _RUNTIME_REGISTRY.pop(runtime.session.session_id, None)


def get_all_runtimes() -> Dict[str, RuntimeManager]:
    """Return all active runtime managers."""
    return dict(_RUNTIME_REGISTRY)


def active_runtimes() -> List[RuntimeManager]:
    """Return all registered runtime managers."""
    return list(_RUNTIME_REGISTRY.values())


def shutdown_all_runtimes() -> None:
    """Shutdown every runtime."""
    for runtime in list(_RUNTIME_REGISTRY.values()):
        try:
            runtime.shutdown()
        except Exception:
            pass


def dispose_all_runtimes() -> None:
    """Dispose every runtime."""
    for runtime in list(_RUNTIME_REGISTRY.values()):
        try:
            runtime.dispose()
        except Exception:
            pass
    _RUNTIME_REGISTRY.clear()


def runtime_count() -> int:
    """Number of active runtimes."""
    return len(_RUNTIME_REGISTRY)