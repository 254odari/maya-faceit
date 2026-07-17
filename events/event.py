# -*- coding: utf-8 -*-
"""
events/event.py

Event data container.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time


@dataclass
class Event:
    """
    An event with a name and optional data.

    Attributes:
        name: Event name.
        data: Event payload.
        source: Source object that emitted the event.
        timestamp: Unix timestamp when the event was created.
        stop_propagation: If True, prevents further propagation.
    """
    name: str
    data: Any = None
    source: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    stop_propagation: bool = False

    def stop(self) -> None:
        """Stop further propagation of this event."""
        self.stop_propagation = True

    @property
    def is_stopped(self) -> bool:
        """Return True if propagation has been stopped."""
        return self.stop_propagation

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to a dictionary (useful for serialization)."""
        return {
            "name": self.name,
            "data": self.data,
            "source": str(self.source) if self.source else None,
            "timestamp": self.timestamp,
            "stop_propagation": self.stop_propagation,
        }

    def __repr__(self) -> str:
        return f"Event(name={self.name!r}, data={self.data!r}, source={self.source!r})"


# Aliases for convenience
DataEvent = Event