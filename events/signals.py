# -*- coding: utf-8 -*-
"""
events/signals.py

Signal implementation (Qt-style signals).

Signals provide a type-safe way to connect callbacks to events.
"""

import logging
import weakref
from typing import List, Callable, Optional, Any, TypeVar, Generic

T = TypeVar('T')
logger = logging.getLogger(__name__)


class Signal(Generic[T]):
    """
    A signal that can be connected to callbacks and emitted.

    This is similar to Qt's Signal class but pure Python.

    Usage:
        class MyClass:
            changed = Signal(str)

        obj = MyClass()
        obj.changed.connect(lambda value: print(value))
        obj.changed.emit("Hello")
    """

    def __init__(self) -> None:
        self._slots: List[Callable[[T], None]] = []
        self._weak_slots: List[weakref.ref] = []
        self._once_slots: List[Callable[[T], None]] = []

    def connect(self, slot: Callable[[T], None]) -> None:
        """
        Connect a callable to this signal.

        Args:
            slot: Function to call when the signal is emitted.
        """
        if slot in self._slots:
            return
        for ref in self._weak_slots:
            if ref() is slot:
                return
        self._slots.append(slot)
        logger.debug("Connected slot to signal")

    def connect_weak(self, slot: Callable[[T], None]) -> None:
        """Connect a weak reference to the slot."""
        self._weak_slots.append(weakref.ref(slot))

    def once(self, slot: Callable[[T], None]) -> None:
        """Connect a slot that will be called only once."""
        self._once_slots.append(slot)

    def disconnect(self, slot: Optional[Callable[[T], None]] = None) -> None:
        """
        Disconnect a slot.

        Args:
            slot: If provided, disconnect only this slot. Otherwise, disconnect all.
        """
        if slot is None:
            self._slots.clear()
            self._weak_slots.clear()
            self._once_slots.clear()
            return
        if slot in self._slots:
            self._slots.remove(slot)
        self._weak_slots = [ref for ref in self._weak_slots if ref() != slot]
        if slot in self._once_slots:
            self._once_slots.remove(slot)

    def emit(self, *args, **kwargs) -> None:
        """Emit the signal to all connected slots."""
        # Process once‑slots first (auto‑remove)
        for slot in self._once_slots[:]:
            try:
                slot(*args, **kwargs)
            except Exception as e:
                logger.error("Error in once‑slot: %s", e)
            self._once_slots.remove(slot)

        # Call strong slots
        for slot in self._slots:
            try:
                slot(*args, **kwargs)
            except Exception as e:
                logger.error("Error in slot: %s", e)

        # Call weak slots
        stale = []
        for ref in self._weak_slots:
            slot = ref()
            if slot is None:
                stale.append(ref)
                continue
            try:
                slot(*args, **kwargs)
            except Exception:
                pass

        # Clean up stale weak refs
        for ref in stale:
            if ref in self._weak_slots:
                self._weak_slots.remove(ref)

    def __call__(self, *args, **kwargs) -> None:
        """Allow calling the signal directly to emit."""
        self.emit(*args, **kwargs)

    def __iadd__(self, slot: Callable[[T], None]) -> 'Signal[T]':
        """Support += syntax for connecting."""
        self.connect(slot)
        return self

    def __isub__(self, slot: Callable[[T], None]) -> 'Signal[T]':
        """Support -= syntax for disconnecting."""
        self.disconnect(slot)
        return self


def signal() -> Signal:
    """Create a new signal."""
    return Signal()