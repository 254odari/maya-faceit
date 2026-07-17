# -*- coding: utf-8 -*-
"""
events/listeners.py

Listener decorators and registry for easy event handling.
"""

import logging
from typing import Dict, List, Callable, Optional, Any
from functools import wraps
from .dispatcher import dispatcher
from .event import Event

logger = logging.getLogger(__name__)


class ListenerRegistry:
    """
    Registry of event listeners for easy management.

    Keeps track of all registered listeners so they can be disconnected
    all at once, or per event.
    """

    def __init__(self) -> None:
        self._listeners: List[Dict[str, Any]] = []

    def add(self, event_name: str, handler: Callable, weak: bool = False, once: bool = False) -> None:
        """Add a listener to the registry."""
        entry = {
            'event': event_name,
            'handler': handler,
            'weak': weak,
            'once': once
        }
        self._listeners.append(entry)
        if once:
            dispatcher.once(event_name, handler)
        elif weak:
            dispatcher.register_weak(event_name, handler)
        else:
            dispatcher.register(event_name, handler)
        logger.debug("Registered listener for event '%s' (weak=%s, once=%s)", event_name, weak, once)

    def remove(self, event_name: str, handler: Callable) -> None:
        """Remove a specific listener."""
        self._listeners = [
            entry for entry in self._listeners
            if not (entry['event'] == event_name and entry['handler'] == handler)
        ]
        dispatcher.unregister(event_name, handler)

    def clear(self, event_name: Optional[str] = None) -> None:
        """Remove all registered listeners, optionally for a specific event."""
        if event_name is None:
            for entry in self._listeners:
                dispatcher.unregister(entry['event'], entry['handler'])
            self._listeners.clear()
            logger.debug("Cleared all listeners")
        else:
            to_remove = [entry for entry in self._listeners if entry['event'] == event_name]
            for entry in to_remove:
                dispatcher.unregister(entry['event'], entry['handler'])
                self._listeners.remove(entry)
            logger.debug("Cleared listeners for event '%s'", event_name)

    def get_listeners(self, event_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return a list of registered listeners, optionally filtered by event."""
        if event_name is None:
            return self._listeners.copy()
        return [entry for entry in self._listeners if entry['event'] == event_name]


# =============================================================================
# Global listener registry
# =============================================================================

listener_registry = ListenerRegistry()


# =============================================================================
# Decorators
# =============================================================================

def listen(event_name: str, weak: bool = False) -> Callable:
    """
    Decorator to register a function as an event listener.

    Args:
        event_name: Name of the event to listen for.
        weak: If True, use a weak reference to the handler.

    Example:
        @listen("scene_changed")
        def on_scene_changed(event):
            print(f"Scene changed: {event.data}")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        listener_registry.add(event_name, wrapper, weak=weak, once=False)
        return wrapper
    return decorator


def once(event_name: str, weak: bool = False) -> Callable:
    """
    Decorator to register a one-shot event listener.

    The handler will be called only once, then automatically removed.

    Args:
        event_name: Name of the event to listen for.
        weak: If True, use a weak reference to the handler.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(event):
            # Remove self before calling
            dispatcher.unregister(event_name, wrapper)
            return func(event)
        listener_registry.add(event_name, wrapper, weak=weak, once=True)
        return wrapper
    return decorator


# =============================================================================
# Convenience functions
# =============================================================================

def on(event_name: str, handler: Callable, weak: bool = False, once: bool = False) -> None:
    """
    Register a handler for an event.

    Args:
        event_name: Name of the event.
        handler: Callable that accepts an Event argument.
        weak: If True, use a weak reference.
        once: If True, the handler will be called only once.
    """
    listener_registry.add(event_name, handler, weak=weak, once=once)


def emit(event_name: str, data: Any = None, source: Any = None) -> None:
    """
    Emit an event.

    Args:
        event_name: Name of the event.
        data: Event payload.
        source: Source object that emitted the event.
    """
    dispatcher.emit(event_name, data, source)


def register_handler(event_name: str, handler: Callable, weak: bool = False) -> None:
    """Alias for on()."""
    on(event_name, handler, weak)


def unregister_handler(event_name: str, handler: Callable) -> None:
    """Unregister a handler."""
    listener_registry.remove(event_name, handler)


def clear_listeners(event_name: Optional[str] = None) -> None:
    """Clear all registered listeners, optionally for a specific event."""
    listener_registry.clear(event_name)