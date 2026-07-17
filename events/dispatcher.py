# -*- coding: utf-8 -*-
"""
events/dispatcher.py

Event dispatcher for named events.
"""

import logging
import weakref
from typing import Dict, List, Callable, Optional, Any, Set

from .event import Event

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Event dispatcher for named events.

    This is a global event bus that allows modules to communicate
    without direct coupling.

    Usage:
        dispatcher = EventDispatcher()
        dispatcher.register("selection_changed", my_callback)
        dispatcher.emit("selection_changed", data=selection)
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}
        self._weak_handlers: Dict[str, List[weakref.ref]] = {}
        self._once_handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def register(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """
        Register a handler for an event.

        Args:
            event_name: Name of the event to listen for.
            handler: Callable that accepts an Event argument.
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)
            logger.debug("Registered handler for event '%s'", event_name)

    def register_weak(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Register a weak reference to a handler."""
        if event_name not in self._weak_handlers:
            self._weak_handlers[event_name] = []
        self._weak_handlers[event_name].append(weakref.ref(handler))
        logger.debug("Registered weak handler for event '%s'", event_name)

    def once(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Register a handler that will be called at most once."""
        if event_name not in self._once_handlers:
            self._once_handlers[event_name] = []
        self._once_handlers[event_name].append(handler)
        logger.debug("Registered once-handler for event '%s'", event_name)

    def unregister(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Unregister a handler."""
        removed = False
        if event_name in self._handlers:
            if handler in self._handlers[event_name]:
                self._handlers[event_name].remove(handler)
                removed = True
        if event_name in self._weak_handlers:
            self._weak_handlers[event_name] = [
                ref for ref in self._weak_handlers[event_name] if ref() != handler
            ]
            removed = True
        if removed:
            logger.debug("Unregistered handler for event '%s'", event_name)

    def emit(self, event_name: str, data: Any = None, source: Any = None) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event_name: Name of the event.
            data: Event payload.
            source: Source object that emitted the event.
        """
        event = Event(name=event_name, data=data, source=source)
        logger.debug("Emitting event '%s'", event_name)

        # Process once‑handlers first (they auto‑remove)
        if event_name in self._once_handlers:
            for handler in self._once_handlers[event_name]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error("Error in once‑handler for '%s': %s", event_name, e)
                if event.is_stopped:
                    break
            # Remove all once‑handlers after execution
            del self._once_handlers[event_name]

        # Process strong handlers
        for handler in self._handlers.get(event_name, []):
            if event.is_stopped:
                break
            try:
                handler(event)
            except Exception as e:
                logger.error("Error in handler for '%s': %s", event_name, e)

        # Process weak handlers
        stale: List[weakref.ref] = []
        for ref in self._weak_handlers.get(event_name, []):
            if event.is_stopped:
                break
            handler = ref()
            if handler is None:
                stale.append(ref)
                continue
            try:
                handler(event)
            except Exception as e:
                logger.error("Error in weak handler for '%s': %s", event_name, e)

        # Clean up stale weak refs
        if stale:
            self._weak_handlers[event_name] = [
                ref for ref in self._weak_handlers.get(event_name, [])
                if ref not in stale
            ]

    def clear(self, event_name: Optional[str] = None) -> None:
        """
        Clear all handlers for an event, or all events.

        Args:
            event_name: If provided, clear only handlers for this event.
        """
        if event_name is None:
            self._handlers.clear()
            self._weak_handlers.clear()
            self._once_handlers.clear()
            logger.debug("Cleared all handlers")
        else:
            self._handlers.pop(event_name, None)
            self._weak_handlers.pop(event_name, None)
            self._once_handlers.pop(event_name, None)
            logger.debug("Cleared handlers for event '%s'", event_name)

    def get_handler_count(self, event_name: Optional[str] = None) -> int:
        """Return the number of handlers for an event, or total."""
        if event_name is not None:
            return (len(self._handlers.get(event_name, [])) +
                    len(self._weak_handlers.get(event_name, [])) +
                    len(self._once_handlers.get(event_name, [])))
        total = 0
        for name in set(self._handlers) | set(self._weak_handlers) | set(self._once_handlers):
            total += (len(self._handlers.get(name, [])) +
                      len(self._weak_handlers.get(name, [])) +
                      len(self._once_handlers.get(name, [])))
        return total


# =============================================================================
# Global dispatcher
# =============================================================================

dispatcher = EventDispatcher()