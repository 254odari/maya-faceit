"""
maya_faceit/services/events/event_bus.py

Simple event bus for decoupled communication between components.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Base event class."""
    name: str
    data: Any = None
    sender: Any = None
    priority: EventPriority = EventPriority.NORMAL


EventHandler = Callable[[Event], None]


class EventBus:
    """Central event bus for pub/sub communication."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._once_handlers: Dict[str, List[EventHandler]] = {}
        logger.debug("EventBus initialized")

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for a specific event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a handler."""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
            except ValueError:
                pass

    def once(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler that will be called at most once."""
        if event_name not in self._once_handlers:
            self._once_handlers[event_name] = []
        self._once_handlers[event_name].append(handler)

    def emit(self, event: Event) -> None:
        """Publish an event to all registered handlers."""
        logger.debug(f"Event emitted: {event.name} (priority {event.priority.value})")
        # Process once‑handlers first
        if event.name in self._once_handlers:
            for handler in self._once_handlers[event.name]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Once‑handler error: {e}")
            del self._once_handlers[event.name]

        # Process regular handlers
        if event.name in self._handlers:
            for handler in self._handlers[event.name]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Handler error for {event.name}: {e}")

    def clear(self) -> None:
        """Clear all handlers."""
        self._handlers.clear()
        self._once_handlers.clear()

    def get_handler_count(self, event_name: Optional[str] = None) -> int:
        if event_name:
            return len(self._handlers.get(event_name, []))
        return sum(len(h) for h in self._handlers.values())