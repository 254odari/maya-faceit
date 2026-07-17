"""
maya_faceit.picker.hotkeys

Central Keyboard Shortcut System for the Picker.

Every keyboard binding should be registered, managed, and dispatched through
this module. This allows users and studios to customize shortcuts while keeping
the picker implementation clean.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, Union, Type

# Qt imports for key handling
try:
    from PySide6 import QtCore, QtGui # type: ignore
    from PySide6.QtCore import Qt # type: ignore
except ImportError:
    try:
        from PySide2 import QtCore, QtGui # type: ignore
        from PySide2.QtCore import Qt # type: ignore
    except ImportError:
        raise ImportError("No Qt binding found (PySide6 or PySide2).")

# Maya imports
try:
    import maya.cmds as cmds # type: ignore
except ImportError:
    cmds = None

# Local imports
from ..core.logger import log
from .commands import execute_command, CommandRegistry, CommandNotFoundError

logger = logging.getLogger(__name__)

# ============================================================================
# Part 1: Foundation
# ============================================================================

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ============================================================================
# Exceptions
# ============================================================================

class HotkeyError(Exception):
    """Base exception for hotkey errors."""
    pass


class HotkeyNotFoundError(HotkeyError):
    """Raised when a hotkey is not found."""
    pass


class HotkeyConflictError(HotkeyError):
    """Raised when a hotkey conflict is detected."""
    pass


class HotkeyProfileError(HotkeyError):
    """Raised when profile operations fail."""
    pass


class HotkeyValidationError(HotkeyError):
    """Raised when validation fails."""
    pass


# ============================================================================
# Part 2: Constants & Enumerations
# ============================================================================

class Modifier(Enum):
    """Modifier keys."""
    CTRL = "Ctrl"
    SHIFT = "Shift"
    ALT = "Alt"
    META = "Meta"
    NONE = "None"


class HotkeyContext(Enum):
    """Contexts for hotkey activation."""
    GLOBAL = "global"
    PICKER = "picker"
    EDITOR = "editor"
    ANIMATION = "animation"
    EXPRESSIONS = "expressions"
    BLENDSHAPES = "blendshapes"
    ARKIT = "arkit"
    VIEWPORT = "viewport"


class ShortcutState(Enum):
    """State of a shortcut."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    TEMPORARY = "temporary"
    USER_DEFINED = "user_defined"
    DEFAULT = "default"


# ============================================================================
# Part 3: Data Models
# ============================================================================

@dataclass
class Hotkey:
    """
    A keyboard shortcut binding.
    """
    name: str
    key: str                      # e.g., "S", "F", "Space"
    modifiers: List[str]          # e.g., ["Ctrl", "Shift"]
    command: str                  # Name of the command to execute
    context: HotkeyContext = HotkeyContext.GLOBAL
    state: ShortcutState = ShortcutState.DEFAULT
    description: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def shortcut_string(self) -> str:
        """Return a human-readable shortcut string."""
        parts = []
        if self.modifiers:
            # Sort modifiers in a consistent order
            mod_order = ["Ctrl", "Shift", "Alt", "Meta"]
            mods = sorted(self.modifiers, key=lambda m: mod_order.index(m) if m in mod_order else 999)
            parts.extend(mods)
        parts.append(self.key)
        return "+".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "key": self.key,
            "modifiers": self.modifiers,
            "command": self.command,
            "context": self.context.value,
            "state": self.state.value,
            "description": self.description,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hotkey':
        return cls(
            name=data["name"],
            key=data["key"],
            modifiers=data["modifiers"],
            command=data["command"],
            context=HotkeyContext(data.get("context", "global")),
            state=ShortcutState(data.get("state", "default")),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class HotkeyBinding:
    """
    A runtime binding between a shortcut and a command.
    """
    shortcut: str                # e.g., "Ctrl+S"
    command: str                 # command name
    context: HotkeyContext
    state: ShortcutState


@dataclass
class HotkeyProfile:
    """
    A named collection of hotkeys.
    """
    name: str
    hotkeys: List[Hotkey] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "hotkeys": [h.to_dict() for h in self.hotkeys],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HotkeyProfile':
        profile = cls(
            name=data["name"],
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
        for hdata in data.get("hotkeys", []):
            profile.hotkeys.append(Hotkey.from_dict(hdata))
        return profile


@dataclass
class HotkeyConflict:
    """Information about a hotkey conflict."""
    shortcut: str
    commands: List[str]
    contexts: List[HotkeyContext]
    states: List[ShortcutState]


@dataclass
class HotkeyStatistics:
    """Statistics for the hotkey system."""
    total_hotkeys: int = 0
    active_hotkeys: int = 0
    disabled_hotkeys: int = 0
    user_defined: int = 0
    default: int = 0
    conflicts: int = 0
    profile_name: str = ""


# ============================================================================
# Part 4: Hotkey Registry
# ============================================================================

class HotkeyRegistry:
    """
    Central registry for all keyboard shortcuts.

    Manages hotkey registration, lookup, execution, and profiles.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._hotkeys: Dict[str, Hotkey] = {}              # name -> hotkey
        self._shortcut_map: Dict[str, List[str]] = {}      # shortcut -> list of hotkey names
        self._context_map: Dict[HotkeyContext, List[str]] = {}  # context -> list of hotkey names
        self._active_context: HotkeyContext = HotkeyContext.GLOBAL
        self._profiles: Dict[str, HotkeyProfile] = {}
        self._active_profile: Optional[str] = None
        self._statistics = HotkeyStatistics()
        self._disabled_shortcuts: Set[str] = set()

        # Default profile
        self._init_default_profile()
        self._load_profile("Default")

    # ========================================================================
    # Registration
    # ========================================================================

    def register(self, hotkey: Hotkey) -> None:
        """
        Register a hotkey.

        Args:
            hotkey: The Hotkey object to register.

        Raises:
            HotkeyConflictError: If a conflict is detected.
        """
        # Check for conflicts
        shortcut = hotkey.shortcut_string()
        if shortcut in self._shortcut_map:
            existing_names = self._shortcut_map[shortcut]
            # If the same name exists, we're updating; else conflict.
            if hotkey.name not in existing_names:
                # Conflict
                conflicting_hotkeys = [self._hotkeys[name] for name in existing_names]
                raise HotkeyConflictError(
                    f"Shortcut '{shortcut}' already used by: {', '.join(existing_names)}"
                )

        # Register
        self._hotkeys[hotkey.name] = hotkey
        if shortcut not in self._shortcut_map:
            self._shortcut_map[shortcut] = []
        if hotkey.name not in self._shortcut_map[shortcut]:
            self._shortcut_map[shortcut].append(hotkey.name)

        # Context mapping
        context = hotkey.context
        if context not in self._context_map:
            self._context_map[context] = []
        if hotkey.name not in self._context_map[context]:
            self._context_map[context].append(hotkey.name)

    def unregister(self, name: str) -> None:
        """Unregister a hotkey by name."""
        if name not in self._hotkeys:
            raise HotkeyNotFoundError(f"Hotkey '{name}' not found.")
        hotkey = self._hotkeys.pop(name)
        shortcut = hotkey.shortcut_string()
        if shortcut in self._shortcut_map:
            if name in self._shortcut_map[shortcut]:
                self._shortcut_map[shortcut].remove(name)
            if not self._shortcut_map[shortcut]:
                del self._shortcut_map[shortcut]
        # Remove from context map
        context = hotkey.context
        if context in self._context_map and name in self._context_map[context]:
            self._context_map[context].remove(name)
            if not self._context_map[context]:
                del self._context_map[context]

    def enable(self, name: str) -> None:
        """Enable a hotkey."""
        if name not in self._hotkeys:
            raise HotkeyNotFoundError(f"Hotkey '{name}' not found.")
        self._hotkeys[name].enabled = True
        self._disabled_shortcuts.discard(name)

    def disable(self, name: str) -> None:
        """Disable a hotkey."""
        if name not in self._hotkeys:
            raise HotkeyNotFoundError(f"Hotkey '{name}' not found.")
        self._hotkeys[name].enabled = False
        self._disabled_shortcuts.add(name)

    def find(self, name: str) -> Optional[Hotkey]:
        """Find a hotkey by name."""
        return self._hotkeys.get(name)

    def find_by_shortcut(self, shortcut: str, context: Optional[HotkeyContext] = None) -> List[Hotkey]:
        """Find all hotkeys matching a shortcut string."""
        if shortcut not in self._shortcut_map:
            return []
        names = self._shortcut_map[shortcut]
        if context is None:
            context = self._active_context
        result = []
        for name in names:
            hotkey = self._hotkeys.get(name)
            if hotkey and hotkey.enabled and (hotkey.context == context or hotkey.context == HotkeyContext.GLOBAL):
                result.append(hotkey)
        # Return in priority order: context-specific first, then global
        result.sort(key=lambda h: 0 if h.context == context else 1)
        return result

    def execute(self, shortcut: str, context: Optional[HotkeyContext] = None) -> bool:
        """
        Execute the command bound to a shortcut.

        Args:
            shortcut: Shortcut string (e.g., "Ctrl+S").
            context: Context to use; if None, uses active context.

        Returns:
            True if a command was executed, False otherwise.
        """
        if context is None:
            context = self._active_context
        hotkeys = self.find_by_shortcut(shortcut, context)
        if not hotkeys:
            return False
        # Execute the first matching hotkey (usually the most specific)
        hotkey = hotkeys[0]
        try:
            execute_command(hotkey.command)
            return True
        except CommandNotFoundError as e:
            logger.warning(f"Command '{hotkey.command}' not found for hotkey '{hotkey.name}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error executing hotkey command '{hotkey.command}': {e}")
            return False

    def list_hotkeys(self, context: Optional[HotkeyContext] = None) -> List[Hotkey]:
        """List all registered hotkeys, optionally filtered by context."""
        if context is None:
            return list(self._hotkeys.values())
        names = self._context_map.get(context, [])
        return [self._hotkeys[name] for name in names if name in self._hotkeys]

    def reset_defaults(self) -> None:
        """Reset all hotkeys to their default states."""
        for hotkey in self._hotkeys.values():
            hotkey.state = ShortcutState.DEFAULT
            hotkey.enabled = True
        self._disabled_shortcuts.clear()

    # ========================================================================
    # Context System
    # ========================================================================

    def set_active_context(self, context: HotkeyContext) -> None:
        """Set the active context."""
        self._active_context = context

    def get_active_context(self) -> HotkeyContext:
        return self._active_context

    def get_context_hotkeys(self, context: HotkeyContext) -> List[Hotkey]:
        """Get all hotkeys for a specific context."""
        return self.list_hotkeys(context)

    # ========================================================================
    # Profiles
    # ========================================================================

    def load_profile(self, name: str) -> None:
        """Load a profile by name."""
        if name not in self._profiles:
            raise HotkeyProfileError(f"Profile '{name}' not found.")
        profile = self._profiles[name]
        # Clear existing hotkeys
        self._hotkeys.clear()
        self._shortcut_map.clear()
        self._context_map.clear()
        self._disabled_shortcuts.clear()
        # Register hotkeys from profile
        for hotkey in profile.hotkeys:
            try:
                self.register(hotkey)
            except HotkeyConflictError:
                # This should not happen if the profile was created properly
                logger.warning(f"Skipping duplicate hotkey in profile: {hotkey.name}")
        self._active_profile = name

    def save_profile(self, name: str) -> None:
        """Save the current hotkey configuration as a profile."""
        if name not in self._profiles:
            raise HotkeyProfileError(f"Profile '{name}' not found.")
        profile = self._profiles[name]
        profile.hotkeys = list(self._hotkeys.values())

    def create_profile(self, name: str, description: str = "") -> HotkeyProfile:
        """Create a new empty profile."""
        if name in self._profiles:
            raise HotkeyProfileError(f"Profile '{name}' already exists.")
        profile = HotkeyProfile(name=name, description=description)
        self._profiles[name] = profile
        return profile

    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        if name not in self._profiles:
            raise HotkeyProfileError(f"Profile '{name}' not found.")
        if name == "Default":
            raise HotkeyProfileError("Cannot delete the Default profile.")
        del self._profiles[name]
        if self._active_profile == name:
            self._active_profile = None

    def duplicate_profile(self, name: str, new_name: str) -> HotkeyProfile:
        """Duplicate a profile."""
        if name not in self._profiles:
            raise HotkeyProfileError(f"Profile '{name}' not found.")
        if new_name in self._profiles:
            raise HotkeyProfileError(f"Profile '{new_name}' already exists.")
        original = self._profiles[name]
        new_profile = HotkeyProfile(
            name=new_name,
            description=f"Copy of {name}",
            hotkeys=[h for h in original.hotkeys],
            metadata=original.metadata.copy(),
        )
        self._profiles[new_name] = new_profile
        return new_profile

    def list_profiles(self) -> List[str]:
        """List all profile names."""
        return list(self._profiles.keys())

    def get_active_profile(self) -> Optional[str]:
        return self._active_profile

    # ========================================================================
    # Conflicts
    # ========================================================================

    def detect_conflicts(self) -> List[HotkeyConflict]:
        """Detect all hotkey conflicts."""
        conflicts = []
        for shortcut, names in self._shortcut_map.items():
            if len(names) > 1:
                hotkeys = [self._hotkeys[name] for name in names if name in self._hotkeys]
                commands = [h.command for h in hotkeys]
                contexts = [h.context for h in hotkeys]
                states = [h.state for h in hotkeys]
                conflicts.append(HotkeyConflict(
                    shortcut=shortcut,
                    commands=commands,
                    contexts=contexts,
                    states=states,
                ))
        return conflicts

    def resolve_conflicts(self, policy: str = "keep_first") -> None:
        """
        Resolve conflicts by keeping the first or last hotkey.

        Args:
            policy: 'keep_first' or 'keep_last'.
        """
        conflicts = self.detect_conflicts()
        for conflict in conflicts:
            shortcut = conflict.shortcut
            names = self._shortcut_map[shortcut]
            if policy == "keep_first":
                keep_name = names[0]
            else:
                keep_name = names[-1]
            for name in names:
                if name != keep_name:
                    self.unregister(name)

    # ========================================================================
    # Import / Export
    # ========================================================================

    def export_profiles(self, filepath: str, profile_names: Optional[List[str]] = None) -> None:
        """Export profiles to a JSON file."""
        if profile_names is None:
            profile_names = list(self._profiles.keys())
        data = {}
        for name in profile_names:
            if name not in self._profiles:
                continue
            data[name] = self._profiles[name].to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def import_profiles(self, filepath: str, overwrite: bool = False) -> int:
        """Import profiles from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for name, prof_data in data.items():
            if name in self._profiles and not overwrite:
                continue
            profile = HotkeyProfile.from_dict(prof_data)
            self._profiles[name] = profile
            count += 1
        return count

    # ========================================================================
    # Utilities
    # ========================================================================

    def get_statistics(self) -> HotkeyStatistics:
        """Get statistics for the current hotkey setup."""
        stats = HotkeyStatistics()
        stats.total_hotkeys = len(self._hotkeys)
        stats.active_hotkeys = sum(1 for h in self._hotkeys.values() if h.enabled)
        stats.disabled_hotkeys = stats.total_hotkeys - stats.active_hotkeys
        stats.user_defined = sum(1 for h in self._hotkeys.values() if h.state == ShortcutState.USER_DEFINED)
        stats.default = sum(1 for h in self._hotkeys.values() if h.state == ShortcutState.DEFAULT)
        stats.conflicts = len(self.detect_conflicts())
        stats.profile_name = self._active_profile or ""
        return stats

    def get_shortcut_for_command(self, command: str, context: Optional[HotkeyContext] = None) -> Optional[str]:
        """Find the shortcut for a given command."""
        if context is None:
            context = self._active_context
        for hotkey in self._hotkeys.values():
            if hotkey.command == command and hotkey.enabled and (hotkey.context == context or hotkey.context == HotkeyContext.GLOBAL):
                return hotkey.shortcut_string()
        return None

    # ========================================================================
    # Default Profile
    # ========================================================================

    def _init_default_profile(self) -> None:
        """Initialize the default profile with built-in hotkeys."""
        defaults = [
            # Selection
            ("F", [], "frame_selection", HotkeyContext.PICKER, "Frame Selection"),
            ("A", ["Ctrl"], "select_all", HotkeyContext.PICKER, "Select All Controls"),
            ("Esc", [], "clear_selection", HotkeyContext.PICKER, "Clear Selection"),
            ("Delete", [], "reset", HotkeyContext.PICKER, "Reset Selected Controls"),
            ("M", ["Ctrl"], "mirror", HotkeyContext.PICKER, "Mirror Selected"),
            # Animation
            ("S", [], "set_key", HotkeyContext.ANIMATION, "Set Key"),
            ("S", ["Shift"], "set_keys_all", HotkeyContext.ANIMATION, "Set Keys on Entire Face"),
            ("Z", ["Ctrl"], "undo", HotkeyContext.GLOBAL, "Undo"),
            ("Z", ["Ctrl", "Shift"], "redo", HotkeyContext.GLOBAL, "Redo"),
            ("C", ["Ctrl"], "copy_pose", HotkeyContext.ANIMATION, "Copy Pose"),
            ("V", ["Ctrl"], "paste_pose", HotkeyContext.ANIMATION, "Paste Pose"),
            ("D", ["Ctrl"], "duplicate_expression", HotkeyContext.EXPRESSIONS, "Duplicate Expression"),
            # Expressions
            ("R", ["Ctrl"], "reset_face", HotkeyContext.EXPRESSIONS, "Reset Face"),
            ("Space", [], "preview_expression", HotkeyContext.EXPRESSIONS, "Toggle Preview"),
            # Layout
            ("Tab", [], "next_page", HotkeyContext.PICKER, "Cycle Picker Pages"),
            ("G", [], "toggle_guides", HotkeyContext.EDITOR, "Toggle Guides"),
            ("L", [], "lock_widgets", HotkeyContext.EDITOR, "Lock/Unlock Widgets"),
            ("H", [], "hide_region", HotkeyContext.PICKER, "Hide Selected Region"),
            ("H", ["Shift"], "show_all_regions", HotkeyContext.PICKER, "Show All Regions"),
            ("F", ["Ctrl"], "search_controllers", HotkeyContext.PICKER, "Search Controllers"),
            ("L", ["Ctrl"], "load_layout", HotkeyContext.PICKER, "Load Picker Layout"),
            ("S", ["Ctrl", "Shift"], "save_layout", HotkeyContext.PICKER, "Save Picker Layout"),
            # ARKit
            ("K", [], "arkit_capture", HotkeyContext.ARKIT, "ARKit Capture"),
            ("K", ["Shift"], "arkit_playback", HotkeyContext.ARKIT, "ARKit Playback"),
        ]

        default_profile = HotkeyProfile(name="Default", description="Default hotkey profile")
        for key, modifiers, command, context, description in defaults:
            hotkey = Hotkey(
                name=f"{command}_{context.value}",
                key=key,
                modifiers=modifiers,
                command=command,
                context=context,
                state=ShortcutState.DEFAULT,
                description=description,
            )
            default_profile.hotkeys.append(hotkey)
            self._profiles["Default"] = default_profile

    # ========================================================================
    # Maya Integration (placeholder)
    # ========================================================================

    def sync_with_maya(self) -> None:
        """
        Sync picker hotkeys with Maya's hotkey system (optional).
        This is a placeholder for future integration.
        """
        pass


# ============================================================================
# Part 5: Public API
# ============================================================================

# Create global instance
_hotkey_registry = HotkeyRegistry()


def register_hotkey(hotkey: Hotkey) -> None:
    """Register a hotkey."""
    _hotkey_registry.register(hotkey)


def unregister_hotkey(name: str) -> None:
    """Unregister a hotkey."""
    _hotkey_registry.unregister(name)


def execute_shortcut(shortcut: str, context: Optional[HotkeyContext] = None) -> bool:
    """Execute the command for a shortcut."""
    return _hotkey_registry.execute(shortcut, context)


def get_hotkey(name: str) -> Optional[Hotkey]:
    """Get a hotkey by name."""
    return _hotkey_registry.find(name)


def list_hotkeys(context: Optional[HotkeyContext] = None) -> List[Hotkey]:
    """List all hotkeys."""
    return _hotkey_registry.list_hotkeys(context)


def load_profile(name: str) -> None:
    """Load a hotkey profile."""
    _hotkey_registry.load_profile(name)


def save_profile(name: str) -> None:
    """Save the current configuration to a profile."""
    _hotkey_registry.save_profile(name)


def create_profile(name: str, description: str = "") -> HotkeyProfile:
    """Create a new hotkey profile."""
    return _hotkey_registry.create_profile(name, description)


def delete_profile(name: str) -> None:
    """Delete a profile."""
    _hotkey_registry.delete_profile(name)


def duplicate_profile(name: str, new_name: str) -> HotkeyProfile:
    """Duplicate a profile."""
    return _hotkey_registry.duplicate_profile(name, new_name)


def list_profiles() -> List[str]:
    """List all profiles."""
    return _hotkey_registry.list_profiles()


def export_profiles(filepath: str, profile_names: Optional[List[str]] = None) -> None:
    """Export profiles to a JSON file."""
    _hotkey_registry.export_profiles(filepath, profile_names)


def import_profiles(filepath: str, overwrite: bool = False) -> int:
    """Import profiles from a JSON file."""
    return _hotkey_registry.import_profiles(filepath, overwrite)


def detect_conflicts() -> List[HotkeyConflict]:
    """Detect hotkey conflicts."""
    return _hotkey_registry.detect_conflicts()


def resolve_conflicts(policy: str = "keep_first") -> None:
    """Resolve conflicts."""
    _hotkey_registry.resolve_conflicts(policy)


def get_statistics() -> HotkeyStatistics:
    """Get hotkey statistics."""
    return _hotkey_registry.get_statistics()


def set_context(context: HotkeyContext) -> None:
    """Set the active context."""
    _hotkey_registry.set_active_context(context)


def get_context() -> HotkeyContext:
    """Get the active context."""
    return _hotkey_registry.get_active_context()


def get_shortcut_for_command(command: str) -> Optional[str]:
    """Get the shortcut for a command in the current context."""
    return _hotkey_registry.get_shortcut_for_command(command)


# ============================================================================
# Part 6: Utilities (Key Normalization, Modifier Parsing)
# ============================================================================

class HotkeyUtils:
    """Utility functions for hotkeys."""

    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize a key string."""
        # Handle special keys
        key_map = {
            "Ctrl": "Ctrl",
            "Shift": "Shift",
            "Alt": "Alt",
            "Meta": "Meta",
            "Space": "Space",
            "Esc": "Esc",
            "Delete": "Delete",
            "Tab": "Tab",
            "Enter": "Enter",
            "Return": "Return",
            "Up": "Up",
            "Down": "Down",
            "Left": "Left",
            "Right": "Right",
            "Home": "Home",
            "End": "End",
            "PageUp": "PageUp",
            "PageDown": "PageDown",
            "Insert": "Insert",
            "Print": "Print",
            "Pause": "Pause",
            "NumLock": "NumLock",
            "ScrollLock": "ScrollLock",
        }
        if key in key_map:
            return key_map[key]
        # Single letters: convert to uppercase
        if len(key) == 1 and key.isalpha():
            return key.upper()
        return key

    @staticmethod
    def parse_shortcut(shortcut: str) -> Tuple[List[str], str]:
        """Parse a shortcut string into modifiers and key."""
        parts = shortcut.split('+')
        modifiers = []
        key = parts[-1]
        for p in parts[:-1]:
            norm = HotkeyUtils.normalize_key(p)
            if norm in ["Ctrl", "Shift", "Alt", "Meta"]:
                modifiers.append(norm)
            else:
                # Treat as part of key (unlikely)
                key = p
        return modifiers, HotkeyUtils.normalize_key(key)

    @staticmethod
    def format_shortcut(modifiers: List[str], key: str) -> str:
        """Format a shortcut string."""
        # Sort modifiers
        mod_order = ["Ctrl", "Shift", "Alt", "Meta"]
        mods = sorted(modifiers, key=lambda m: mod_order.index(m) if m in mod_order else 999)
        parts = mods + [key]
        return "+".join(parts)

    @staticmethod
    def is_standard_key(key: str) -> bool:
        """Check if the key is a standard printable key."""
        # Allow letters, numbers, space, punctuation
        return re.match(r'^[a-zA-Z0-9 .,!?;:\'"()\-_=+\[\]{}|\\/<>`~]$', key) is not None

    @staticmethod
    def key_to_qt_key(key: str) -> int:
        """Convert a key string to a Qt.Key value."""
        key_map = {
            "Space": Qt.Key_Space,
            "Esc": Qt.Key_Escape,
            "Delete": Qt.Key_Delete,
            "Tab": Qt.Key_Tab,
            "Enter": Qt.Key_Enter,
            "Return": Qt.Key_Return,
            "Up": Qt.Key_Up,
            "Down": Qt.Key_Down,
            "Left": Qt.Key_Left,
            "Right": Qt.Key_Right,
            "Home": Qt.Key_Home,
            "End": Qt.Key_End,
            "PageUp": Qt.Key_PageUp,
            "PageDown": Qt.Key_PageDown,
            "Insert": Qt.Key_Insert,
            "Print": Qt.Key_Print,
            "Pause": Qt.Key_Pause,
            "NumLock": Qt.Key_NumLock,
            "ScrollLock": Qt.Key_ScrollLock,
        }
        if key in key_map:
            return key_map[key]
        if len(key) == 1:
            return ord(key.upper())
        return 0

    @staticmethod
    def qt_key_to_key(qt_key: int) -> str:
        """Convert a Qt.Key value to a key string."""
        # This is complex; we'll use a reverse lookup
        # For simplicity, we'll map common ones
        key_map = {
            Qt.Key_Space: "Space",
            Qt.Key_Escape: "Esc",
            Qt.Key_Delete: "Delete",
            Qt.Key_Tab: "Tab",
            Qt.Key_Enter: "Enter",
            Qt.Key_Return: "Return",
            Qt.Key_Up: "Up",
            Qt.Key_Down: "Down",
            Qt.Key_Left: "Left",
            Qt.Key_Right: "Right",
            Qt.Key_Home: "Home",
            Qt.Key_End: "End",
            Qt.Key_PageUp: "PageUp",
            Qt.Key_PageDown: "PageDown",
            Qt.Key_Insert: "Insert",
            Qt.Key_Print: "Print",
            Qt.Key_Pause: "Pause",
            Qt.Key_NumLock: "NumLock",
            Qt.Key_ScrollLock: "ScrollLock",
        }
        if qt_key in key_map:
            return key_map[qt_key]
        if 0x41 <= qt_key <= 0x5A:  # A-Z
            return chr(qt_key)
        if 0x30 <= qt_key <= 0x39:  # 0-9
            return chr(qt_key)
        return ""

    @staticmethod
    def qt_modifiers_to_string(modifiers: Qt.KeyboardModifier) -> List[str]:
        """Convert Qt modifiers to a list of strings."""
        result = []
        if modifiers & Qt.ControlModifier:
            result.append("Ctrl")
        if modifiers & Qt.ShiftModifier:
            result.append("Shift")
        if modifiers & Qt.AltModifier:
            result.append("Alt")
        if modifiers & Qt.MetaModifier:
            result.append("Meta")
        return result


# ============================================================================
# Part 7: Validation
# ============================================================================

class HotkeyValidator:
    """Validates hotkeys and profiles."""

    @staticmethod
    def validate_hotkey(hotkey: Hotkey) -> bool:
        """Validate a hotkey."""
        # Check key
        if not hotkey.key:
            return False
        # Check modifiers
        valid_mods = ["Ctrl", "Shift", "Alt", "Meta"]
        for mod in hotkey.modifiers:
            if mod not in valid_mods:
                return False
        # Check command exists
        from .commands import get_registry
        if not get_registry().exists(hotkey.command):
            return False
        return True

    @staticmethod
    def validate_profile(profile: HotkeyProfile) -> bool:
        """Validate a profile."""
        for hotkey in profile.hotkeys:
            if not HotkeyValidator.validate_hotkey(hotkey):
                return False
        return True


# ============================================================================
# Public API Exports
# ============================================================================

__all__ = [
    # Enums
    "Modifier",
    "HotkeyContext",
    "ShortcutState",
    # Data Models
    "Hotkey",
    "HotkeyBinding",
    "HotkeyProfile",
    "HotkeyConflict",
    "HotkeyStatistics",
    # Registry
    "HotkeyRegistry",
    # Public API
    "register_hotkey",
    "unregister_hotkey",
    "execute_shortcut",
    "get_hotkey",
    "list_hotkeys",
    "load_profile",
    "save_profile",
    "create_profile",
    "delete_profile",
    "duplicate_profile",
    "list_profiles",
    "export_profiles",
    "import_profiles",
    "detect_conflicts",
    "resolve_conflicts",
    "get_statistics",
    "set_context",
    "get_context",
    "get_shortcut_for_command",
    # Utilities
    "HotkeyUtils",
    "HotkeyValidator",
    # Exceptions
    "HotkeyError",
    "HotkeyNotFoundError",
    "HotkeyConflictError",
    "HotkeyProfileError",
    "HotkeyValidationError",
]