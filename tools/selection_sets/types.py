# -*- coding: utf-8 -*-
"""
tools/selection_sets/types.py

Enums and dataclasses for selection sets.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


class SelectionSetType(Enum):
    """Type of selection set."""
    VERTEX = "vertex"
    EDGE = "edge"
    FACE = "face"
    OBJECT = "object"
    UV = "uv"
    MIXED = "mixed"


class SelectionSetState(Enum):
    """State of a selection set."""
    NORMAL = "normal"
    LOCKED = "locked"
    HIDDEN = "hidden"
    READ_ONLY = "read_only"


class SetMemberType(Enum):
    """Type of member in a set."""
    VERTEX = "vtx"
    EDGE = "e"
    FACE = "f"
    OBJECT = "obj"
    UV = "uv"


@dataclass
class SetInfo:
    """Information about a selection set."""
    name: str
    set_type: SelectionSetType = SelectionSetType.VERTEX
    state: SelectionSetState = SelectionSetState.NORMAL
    members: List[str] = field(default_factory=list)
    count: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: str = ""
    modified: str = ""