# -*- coding: utf-8 -*-
"""
maya_faceit.events

Central event system for Maya FaceIT.

Provides a publisher-subscriber pattern for loose coupling between modules.

Usage:
    from maya_faceit.events import Signal, dispatcher, listen

    # Define a signal
    class MyEvents:
        something_happened = Signal(str)

    # Connect to a signal
    MyEvents.something_happened.connect(my_callback)

    # Emit the signal
    MyEvents.something_happened.emit("Hello!")

    # Or use the dispatcher directly
    dispatcher.register("my_event", my_callback)
    dispatcher.emit("my_event", data="Hello!")
"""

from .dispatcher import EventDispatcher, dispatcher
from .event import Event
from .signals import Signal, signal
from .listeners import (
    ListenerRegistry,
    listener_registry,
    on,
    listen,
    once,
    emit,
    register_handler,
    unregister_handler,
    clear_listeners,
)

__all__ = [
    "EventDispatcher",
    "dispatcher",
    "Event",
    "Signal",
    "signal",
    "ListenerRegistry",
    "listener_registry",
    "on",
    "listen",
    "once",
    "emit",
    "register_handler",
    "unregister_handler",
    "clear_listeners",
]