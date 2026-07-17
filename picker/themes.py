"""
maya_faceit.picker.themes

Complete Visual Styling Engine for the Picker UI.

This module controls every aspect of appearance: colors, fonts, widget styles,
icons, animations, and accessibility. It allows users and studios to create,
switch, and customize themes dynamically.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set, Callable

# Qt imports
try:
    from PySide6 import QtCore, QtGui, QtWidgets # type: ignore
    from PySide6.QtCore import Qt, QSize # type: ignore
    from PySide6.QtGui import QColor, QFont, QPalette, QIcon, QPixmap # type: ignore
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets # type: ignore
        from PySide2.QtCore import Qt, QSize # type: ignore
        from PySide2.QtGui import QColor, QFont, QPalette, QIcon, QPixmap # type: ignore
    except ImportError:
        raise ImportError("No Qt binding found (PySide6 or PySide2).")

logger = logging.getLogger(__name__)

# ============================================================================
# Part 1: Foundation
# ============================================================================

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ============================================================================
# Exceptions
# ============================================================================

class ThemeError(Exception):
    """Base exception for theme errors."""
    pass


class ThemeNotFoundError(ThemeError):
    """Raised when a theme is not found."""
    pass


class ThemeValidationError(ThemeError):
    """Raised when theme validation fails."""
    pass


class ThemeLoadError(ThemeError):
    """Raised when theme loading fails."""
    pass


# ============================================================================
# Part 2: Constants & Enumerations
# ============================================================================

class ThemeType(Enum):
    """Types of themes."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"
    STUDIO = "studio"


class WidgetStyleType(Enum):
    """Types of widget styles."""
    BUTTON = "button"
    SLIDER = "slider"
    JOYSTICK = "joystick"
    LABEL = "label"
    BACKGROUND = "background"
    REGION = "region"
    ICON = "icon"
    CONTROLLER = "controller"
    SELECTION = "selection"


class ColorRole(Enum):
    """Roles for colors in a palette."""
    BACKGROUND = "background"
    FOREGROUND = "foreground"
    ACCENT = "accent"
    HOVER = "hover"
    SELECTED = "selected"
    DISABLED = "disabled"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    BORDER = "border"
    SHADOW = "shadow"
    GRID = "grid"
    TEXT = "text"
    TEXT_HOVER = "text_hover"
    TEXT_SELECTED = "text_selected"
    LINK = "link"


# ============================================================================
# Part 3: Theme Data Models
# ============================================================================

@dataclass
class ColorPalette:
    """
    A collection of colors used by the theme.
    """
    colors: Dict[ColorRole, str] = field(default_factory=dict)

    def get(self, role: ColorRole, default: str = "#000000") -> str:
        """Get a color by role, with default fallback."""
        return self.colors.get(role, default)

    def set(self, role: ColorRole, color: str) -> None:
        """Set a color for a role."""
        self.colors[role] = color

    def to_dict(self) -> Dict[str, str]:
        return {role.value: color for role, color in self.colors.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ColorPalette':
        palette = cls()
        for key, value in data.items():
            try:
                role = ColorRole(key)
                palette.colors[role] = value
            except ValueError:
                pass
        return palette


@dataclass
class Typography:
    """
    Typography settings for the theme.
    """
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: int = 400
    bold_font_weight: int = 700
    title_font_size: int = 14
    tooltip_font_size: int = 9
    monospace_family: str = "Consolas"
    line_height: float = 1.4
    letter_spacing: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "bold_font_weight": self.bold_font_weight,
            "title_font_size": self.title_font_size,
            "tooltip_font_size": self.tooltip_font_size,
            "monospace_family": self.monospace_family,
            "line_height": self.line_height,
            "letter_spacing": self.letter_spacing,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Typography':
        return cls(
            font_family=data.get("font_family", "Segoe UI"),
            font_size=data.get("font_size", 10),
            font_weight=data.get("font_weight", 400),
            bold_font_weight=data.get("bold_font_weight", 700),
            title_font_size=data.get("title_font_size", 14),
            tooltip_font_size=data.get("tooltip_font_size", 9),
            monospace_family=data.get("monospace_family", "Consolas"),
            line_height=data.get("line_height", 1.4),
            letter_spacing=data.get("letter_spacing", 0.0),
        )

    def get_qfont(self, size: Optional[int] = None, weight: Optional[int] = None) -> QFont:
        """Get a QFont object with the theme typography."""
        font = QFont(self.font_family)
        font.setPointSize(size or self.font_size)
        font.setWeight(weight or self.font_weight)
        return font


@dataclass
class WidgetStyle:
    """
    Style definition for a specific widget type.
    """
    fill_color: str = "#808080"
    fill_color_hover: str = "#A0A0A0"
    fill_color_pressed: str = "#6666AA"
    fill_color_selected: str = "#C8C832"
    fill_color_locked: str = "#555555"
    fill_color_disabled: str = "#333333"
    border_color: str = "#000000"
    border_color_hover: str = "#6666CC"
    border_color_selected: str = "#FFFF64"
    border_width: float = 1.0
    corner_radius: float = 4.0
    text_color: str = "#FFFFFF"
    text_color_hover: str = "#FFFFFF"
    text_color_selected: str = "#000000"
    opacity: float = 1.0
    opacity_hover: float = 1.0
    opacity_selected: float = 1.0
    opacity_disabled: float = 0.5
    shadow_enabled: bool = False
    shadow_color: str = "#00000032"
    shadow_offset: Tuple[float, float] = (2.0, 2.0)
    shadow_blur: float = 4.0
    glow_enabled: bool = False
    glow_color: str = "#6666FF"
    glow_radius: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fill_color": self.fill_color,
            "fill_color_hover": self.fill_color_hover,
            "fill_color_pressed": self.fill_color_pressed,
            "fill_color_selected": self.fill_color_selected,
            "fill_color_locked": self.fill_color_locked,
            "fill_color_disabled": self.fill_color_disabled,
            "border_color": self.border_color,
            "border_color_hover": self.border_color_hover,
            "border_color_selected": self.border_color_selected,
            "border_width": self.border_width,
            "corner_radius": self.corner_radius,
            "text_color": self.text_color,
            "text_color_hover": self.text_color_hover,
            "text_color_selected": self.text_color_selected,
            "opacity": self.opacity,
            "opacity_hover": self.opacity_hover,
            "opacity_selected": self.opacity_selected,
            "opacity_disabled": self.opacity_disabled,
            "shadow_enabled": self.shadow_enabled,
            "shadow_color": self.shadow_color,
            "shadow_offset": self.shadow_offset,
            "shadow_blur": self.shadow_blur,
            "glow_enabled": self.glow_enabled,
            "glow_color": self.glow_color,
            "glow_radius": self.glow_radius,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetStyle':
        return cls(
            fill_color=data.get("fill_color", "#808080"),
            fill_color_hover=data.get("fill_color_hover", "#A0A0A0"),
            fill_color_pressed=data.get("fill_color_pressed", "#6666AA"),
            fill_color_selected=data.get("fill_color_selected", "#C8C832"),
            fill_color_locked=data.get("fill_color_locked", "#555555"),
            fill_color_disabled=data.get("fill_color_disabled", "#333333"),
            border_color=data.get("border_color", "#000000"),
            border_color_hover=data.get("border_color_hover", "#6666CC"),
            border_color_selected=data.get("border_color_selected", "#FFFF64"),
            border_width=data.get("border_width", 1.0),
            corner_radius=data.get("corner_radius", 4.0),
            text_color=data.get("text_color", "#FFFFFF"),
            text_color_hover=data.get("text_color_hover", "#FFFFFF"),
            text_color_selected=data.get("text_color_selected", "#000000"),
            opacity=data.get("opacity", 1.0),
            opacity_hover=data.get("opacity_hover", 1.0),
            opacity_selected=data.get("opacity_selected", 1.0),
            opacity_disabled=data.get("opacity_disabled", 0.5),
            shadow_enabled=data.get("shadow_enabled", False),
            shadow_color=data.get("shadow_color", "#00000032"),
            shadow_offset=tuple(data.get("shadow_offset", [2.0, 2.0])),
            shadow_blur=data.get("shadow_blur", 4.0),
            glow_enabled=data.get("glow_enabled", False),
            glow_color=data.get("glow_color", "#6666FF"),
            glow_radius=data.get("glow_radius", 10.0),
        )


@dataclass
class IconSet:
    """
    Icon set for the theme.
    """
    icons: Dict[str, str] = field(default_factory=dict)  # icon_name -> path
    fallback_icon: str = ""

    def get(self, name: str) -> Optional[str]:
        """Get an icon path by name."""
        return self.icons.get(name)

    def set(self, name: str, path: str) -> None:
        """Set an icon path."""
        self.icons[name] = path

    def to_dict(self) -> Dict[str, str]:
        return self.icons

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'IconSet':
        return cls(icons=data)


@dataclass
class AnimationStyle:
    """
    Animation style settings.
    """
    fade_duration: int = 300
    hover_duration: int = 150
    selection_flash_duration: int = 500
    glow_duration: int = 400
    pulse_duration: int = 1000
    easing_curve: str = "in_out_quad"
    reduce_motion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fade_duration": self.fade_duration,
            "hover_duration": self.hover_duration,
            "selection_flash_duration": self.selection_flash_duration,
            "glow_duration": self.glow_duration,
            "pulse_duration": self.pulse_duration,
            "easing_curve": self.easing_curve,
            "reduce_motion": self.reduce_motion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimationStyle':
        return cls(
            fade_duration=data.get("fade_duration", 300),
            hover_duration=data.get("hover_duration", 150),
            selection_flash_duration=data.get("selection_flash_duration", 500),
            glow_duration=data.get("glow_duration", 400),
            pulse_duration=data.get("pulse_duration", 1000),
            easing_curve=data.get("easing_curve", "in_out_quad"),
            reduce_motion=data.get("reduce_motion", False),
        )


@dataclass
class AccessibilityOptions:
    """
    Accessibility settings.
    """
    high_contrast: bool = False
    large_fonts: bool = False
    font_scale: float = 1.0
    color_blind_palette: bool = False
    reduced_motion: bool = False
    keyboard_focus_highlight: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "high_contrast": self.high_contrast,
            "large_fonts": self.large_fonts,
            "font_scale": self.font_scale,
            "color_blind_palette": self.color_blind_palette,
            "reduced_motion": self.reduced_motion,
            "keyboard_focus_highlight": self.keyboard_focus_highlight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessibilityOptions':
        return cls(
            high_contrast=data.get("high_contrast", False),
            large_fonts=data.get("large_fonts", False),
            font_scale=data.get("font_scale", 1.0),
            color_blind_palette=data.get("color_blind_palette", False),
            reduced_motion=data.get("reduced_motion", False),
            keyboard_focus_highlight=data.get("keyboard_focus_highlight", True),
        )


@dataclass
class Theme:
    """
    A complete theme definition.
    """
    name: str
    version: str = "1.0"
    theme_type: ThemeType = ThemeType.CUSTOM
    palette: ColorPalette = field(default_factory=ColorPalette)
    typography: Typography = field(default_factory=Typography)
    widget_styles: Dict[WidgetStyleType, WidgetStyle] = field(default_factory=dict)
    icon_set: IconSet = field(default_factory=IconSet)
    animation: AnimationStyle = field(default_factory=AnimationStyle)
    accessibility: AccessibilityOptions = field(default_factory=AccessibilityOptions)
    author: str = "unknown"
    description: str = ""
    parent_theme: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_widget_style(self, style_type: WidgetStyleType) -> WidgetStyle:
        """Get a widget style, falling back to a default style if not found."""
        if style_type in self.widget_styles:
            return self.widget_styles[style_type]
        # Return a default style
        return WidgetStyle()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "theme_type": self.theme_type.value,
            "palette": self.palette.to_dict(),
            "typography": self.typography.to_dict(),
            "widget_styles": {k.value: v.to_dict() for k, v in self.widget_styles.items()},
            "icon_set": self.icon_set.to_dict(),
            "animation": self.animation.to_dict(),
            "accessibility": self.accessibility.to_dict(),
            "author": self.author,
            "description": self.description,
            "parent_theme": self.parent_theme,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        theme = cls(
            name=data["name"],
            version=data.get("version", "1.0"),
            theme_type=ThemeType(data.get("theme_type", "custom")),
            palette=ColorPalette.from_dict(data.get("palette", {})),
            typography=Typography.from_dict(data.get("typography", {})),
            icon_set=IconSet.from_dict(data.get("icon_set", {})),
            animation=AnimationStyle.from_dict(data.get("animation", {})),
            accessibility=AccessibilityOptions.from_dict(data.get("accessibility", {})),
            author=data.get("author", "unknown"),
            description=data.get("description", ""),
            parent_theme=data.get("parent_theme"),
            metadata=data.get("metadata", {}),
        )
        # Widget styles
        for key, style_data in data.get("widget_styles", {}).items():
            try:
                style_type = WidgetStyleType(key)
                theme.widget_styles[style_type] = WidgetStyle.from_dict(style_data)
            except ValueError:
                pass
        return theme

    def merge(self, other: 'Theme') -> 'Theme':
        """
        Merge another theme into this one (for inheritance).
        The other theme overrides this theme's properties.
        """
        merged = copy.deepcopy(self)
        merged.name = self.name
        merged.version = self.version
        merged.theme_type = self.theme_type
        # Merge palette
        for role, color in other.palette.colors.items():
            merged.palette.set(role, color)
        # Merge typography (only if different from default)
        for key, value in other.typography.to_dict().items():
            if value != Typography().to_dict().get(key):
                setattr(merged.typography, key, value)
        # Merge widget styles
        for style_type, style in other.widget_styles.items():
            merged.widget_styles[style_type] = copy.deepcopy(style)
        # Merge icon set
        for icon_name, icon_path in other.icon_set.icons.items():
            merged.icon_set.set(icon_name, icon_path)
        # Merge animation
        for key, value in other.animation.to_dict().items():
            if value != AnimationStyle().to_dict().get(key):
                setattr(merged.animation, key, value)
        # Merge accessibility
        for key, value in other.accessibility.to_dict().items():
            if value != AccessibilityOptions().to_dict().get(key):
                setattr(merged.accessibility, key, value)
        merged.parent_theme = other.name
        return merged


# ============================================================================
# Part 4: Theme Manager
# ============================================================================

class ThemeManager:
    """
    Central manager for themes.

    Handles loading, saving, applying, and switching themes.
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
        self._themes: Dict[str, Theme] = {}
        self._active_theme_name: Optional[str] = None
        self._fallback_theme: Optional[Theme] = None
        self._callbacks: List[Callable[[Theme], None]] = []

        # Initialize with built-in themes
        self._load_builtin_themes()

        # Set active theme
        self._active_theme_name = "Dark"
        self._ensure_active_theme()

    # ========================================================================
    # Theme Management
    # ========================================================================

    def register_theme(self, theme: Theme, overwrite: bool = False) -> None:
        """Register a theme."""
        if theme.name in self._themes and not overwrite:
            raise ThemeError(f"Theme '{theme.name}' already exists.")
        self._themes[theme.name] = theme

    def unregister_theme(self, name: str) -> None:
        """Unregister a theme."""
        if name in self._themes:
            del self._themes[name]
        if self._active_theme_name == name:
            self._active_theme_name = None

    def get_theme(self, name: str) -> Optional[Theme]:
        """Get a theme by name."""
        return self._themes.get(name)

    def get_active_theme(self) -> Optional[Theme]:
        """Get the currently active theme."""
        if self._active_theme_name:
            return self.get_theme(self._active_theme_name)
        return None

    def set_active_theme(self, name: str) -> None:
        """Set the active theme by name."""
        if name not in self._themes:
            raise ThemeNotFoundError(f"Theme '{name}' not found.")
        self._active_theme_name = name
        self._apply_theme()
        self._notify_callbacks()

    def get_theme_names(self) -> List[str]:
        """Get all theme names."""
        return list(self._themes.keys())

    def duplicate_theme(self, name: str, new_name: str) -> Theme:
        """Duplicate a theme."""
        if name not in self._themes:
            raise ThemeNotFoundError(f"Theme '{name}' not found.")
        if new_name in self._themes:
            raise ThemeError(f"Theme '{new_name}' already exists.")
        theme = self._themes[name]
        new_theme = copy.deepcopy(theme)
        new_theme.name = new_name
        self._themes[new_name] = new_theme
        return new_theme

    def delete_theme(self, name: str) -> None:
        """Delete a theme."""
        if name not in self._themes:
            raise ThemeNotFoundError(f"Theme '{name}' not found.")
        if name == "Dark":
            raise ThemeError("Cannot delete the default theme.")
        del self._themes[name]
        if self._active_theme_name == name:
            self._active_theme_name = "Dark"
            self._apply_theme()
            self._notify_callbacks()

    def reset_to_default(self) -> None:
        """Reset to the default theme."""
        self.set_active_theme("Dark")

    # ========================================================================
    # Loading Built-in Themes
    # ========================================================================

    def _load_builtin_themes(self) -> None:
        """Load built-in themes."""
        # Dark theme
        dark = Theme(
            name="Dark",
            theme_type=ThemeType.DARK,
            description="Default dark theme",
            palette=ColorPalette({
                ColorRole.BACKGROUND: "#2D2D2D",
                ColorRole.FOREGROUND: "#E0E0E0",
                ColorRole.ACCENT: "#4A90D9",
                ColorRole.HOVER: "#3D3D3D",
                ColorRole.SELECTED: "#4A90D9",
                ColorRole.DISABLED: "#555555",
                ColorRole.WARNING: "#F0A030",
                ColorRole.ERROR: "#D94A4A",
                ColorRole.SUCCESS: "#4CAF50",
                ColorRole.BORDER: "#444444",
                ColorRole.SHADOW: "#00000080",
                ColorRole.GRID: "#3A3A3A",
                ColorRole.TEXT: "#E0E0E0",
                ColorRole.TEXT_HOVER: "#FFFFFF",
                ColorRole.TEXT_SELECTED: "#FFFFFF",
                ColorRole.LINK: "#4A90D9",
            }),
            typography=Typography(font_family="Segoe UI", font_size=10),
            widget_styles={
                WidgetStyleType.BUTTON: WidgetStyle(
                    fill_color="#3D3D3D",
                    fill_color_hover="#4D4D4D",
                    fill_color_pressed="#2A2A2A",
                    fill_color_selected="#4A90D9",
                    fill_color_locked="#3D3D3D",
                    fill_color_disabled="#2D2D2D",
                    border_color="#555555",
                    border_color_hover="#6A6A6A",
                    border_color_selected="#4A90D9",
                    border_width=1.0,
                    corner_radius=4.0,
                    text_color="#E0E0E0",
                    text_color_hover="#FFFFFF",
                    text_color_selected="#FFFFFF",
                ),
                WidgetStyleType.SLIDER: WidgetStyle(
                    fill_color="#4A4A4A",
                    fill_color_hover="#5A5A5A",
                    fill_color_selected="#4A90D9",
                    corner_radius=2.0,
                ),
                WidgetStyleType.JOYSTICK: WidgetStyle(
                    fill_color="#3A3A3A",
                    fill_color_hover="#4A4A4A",
                    fill_color_selected="#4A90D9",
                ),
                WidgetStyleType.REGION: WidgetStyle(
                    fill_color="#4A4A6A",
                    fill_color_hover="#5A5A8A",
                    fill_color_selected="#6A6A9A",
                    border_color="#6666AA",
                    border_width=1.5,
                    corner_radius=0.0,
                    opacity=0.6,
                    opacity_hover=0.8,
                    opacity_selected=0.9,
                ),
            },
        )
        self.register_theme(dark, overwrite=True)

        # Light theme
        light = Theme(
            name="Light",
            theme_type=ThemeType.LIGHT,
            description="Light theme",
            palette=ColorPalette({
                ColorRole.BACKGROUND: "#F0F0F0",
                ColorRole.FOREGROUND: "#222222",
                ColorRole.ACCENT: "#4A90D9",
                ColorRole.HOVER: "#E0E0E0",
                ColorRole.SELECTED: "#4A90D9",
                ColorRole.DISABLED: "#C0C0C0",
                ColorRole.WARNING: "#F0A030",
                ColorRole.ERROR: "#D94A4A",
                ColorRole.SUCCESS: "#4CAF50",
                ColorRole.BORDER: "#CCCCCC",
                ColorRole.SHADOW: "#00000040",
                ColorRole.GRID: "#D0D0D0",
                ColorRole.TEXT: "#222222",
                ColorRole.TEXT_HOVER: "#000000",
                ColorRole.TEXT_SELECTED: "#FFFFFF",
                ColorRole.LINK: "#4A90D9",
            }),
            typography=Typography(font_family="Segoe UI", font_size=10, text_color="#222222"),
            widget_styles={
                WidgetStyleType.BUTTON: WidgetStyle(
                    fill_color="#E0E0E0",
                    fill_color_hover="#D0D0D0",
                    fill_color_pressed="#C0C0C0",
                    fill_color_selected="#4A90D9",
                    fill_color_locked="#E0E0E0",
                    fill_color_disabled="#F0F0F0",
                    border_color="#CCCCCC",
                    border_color_hover="#AAAAAA",
                    border_color_selected="#4A90D9",
                    border_width=1.0,
                    corner_radius=4.0,
                    text_color="#222222",
                    text_color_hover="#000000",
                    text_color_selected="#FFFFFF",
                ),
                WidgetStyleType.SLIDER: WidgetStyle(
                    fill_color="#D0D0D0",
                    fill_color_hover="#C0C0C0",
                    fill_color_selected="#4A90D9",
                    corner_radius=2.0,
                ),
                WidgetStyleType.JOYSTICK: WidgetStyle(
                    fill_color="#E0E0E0",
                    fill_color_hover="#D0D0D0",
                    fill_color_selected="#4A90D9",
                ),
                WidgetStyleType.REGION: WidgetStyle(
                    fill_color="#C0C0E0",
                    fill_color_hover="#D0D0F0",
                    fill_color_selected="#B0B0E0",
                    border_color="#6666AA",
                    border_width=1.5,
                    corner_radius=0.0,
                    opacity=0.6,
                    opacity_hover=0.8,
                    opacity_selected=0.9,
                ),
            },
        )
        self.register_theme(light, overwrite=True)

        # Studio Blue theme
        studio_blue = Theme(
            name="Studio Blue",
            theme_type=ThemeType.STUDIO,
            description="Studio blue theme",
            palette=ColorPalette({
                ColorRole.BACKGROUND: "#1A2332",
                ColorRole.FOREGROUND: "#E0E8F0",
                ColorRole.ACCENT: "#4A90D9",
                ColorRole.HOVER: "#2A3A50",
                ColorRole.SELECTED: "#4A90D9",
                ColorRole.DISABLED: "#4A5A6A",
                ColorRole.WARNING: "#F0A030",
                ColorRole.ERROR: "#D94A4A",
                ColorRole.SUCCESS: "#4CAF50",
                ColorRole.BORDER: "#2A3A50",
                ColorRole.SHADOW: "#00000080",
                ColorRole.GRID: "#2A3A50",
                ColorRole.TEXT: "#E0E8F0",
                ColorRole.TEXT_HOVER: "#FFFFFF",
                ColorRole.TEXT_SELECTED: "#FFFFFF",
                ColorRole.LINK: "#4A90D9",
            }),
            typography=Typography(font_family="Segoe UI", font_size=10),
            widget_styles={
                WidgetStyleType.BUTTON: WidgetStyle(
                    fill_color="#2A3A50",
                    fill_color_hover="#3A4A60",
                    fill_color_pressed="#1A2A3A",
                    fill_color_selected="#4A90D9",
                    fill_color_locked="#2A3A50",
                    fill_color_disabled="#1A2332",
                    border_color="#3A4A60",
                    border_color_hover="#4A5A70",
                    border_color_selected="#4A90D9",
                    border_width=1.0,
                    corner_radius=4.0,
                    text_color="#E0E8F0",
                    text_color_hover="#FFFFFF",
                    text_color_selected="#FFFFFF",
                ),
                WidgetStyleType.SLIDER: WidgetStyle(
                    fill_color="#3A4A60",
                    fill_color_hover="#4A5A70",
                    fill_color_selected="#4A90D9",
                    corner_radius=2.0,
                ),
                WidgetStyleType.JOYSTICK: WidgetStyle(
                    fill_color="#2A3A50",
                    fill_color_hover="#3A4A60",
                    fill_color_selected="#4A90D9",
                ),
                WidgetStyleType.REGION: WidgetStyle(
                    fill_color="#3A4A8A",
                    fill_color_hover="#4A5A9A",
                    fill_color_selected="#5A6AAA",
                    border_color="#4A5A9A",
                    border_width=1.5,
                    corner_radius=0.0,
                    opacity=0.6,
                    opacity_hover=0.8,
                    opacity_selected=0.9,
                ),
            },
        )
        self.register_theme(studio_blue, overwrite=True)

        # High Contrast theme
        high_contrast = Theme(
            name="High Contrast",
            theme_type=ThemeType.HIGH_CONTRAST,
            description="High contrast accessibility theme",
            palette=ColorPalette({
                ColorRole.BACKGROUND: "#000000",
                ColorRole.FOREGROUND: "#FFFFFF",
                ColorRole.ACCENT: "#FFFF00",
                ColorRole.HOVER: "#1A1A1A",
                ColorRole.SELECTED: "#FFFF00",
                ColorRole.DISABLED: "#666666",
                ColorRole.WARNING: "#FF8800",
                ColorRole.ERROR: "#FF0000",
                ColorRole.SUCCESS: "#00FF00",
                ColorRole.BORDER: "#FFFFFF",
                ColorRole.SHADOW: "#000000",
                ColorRole.GRID: "#333333",
                ColorRole.TEXT: "#FFFFFF",
                ColorRole.TEXT_HOVER: "#FFFFFF",
                ColorRole.TEXT_SELECTED: "#000000",
                ColorRole.LINK: "#FFFF00",
            }),
            typography=Typography(font_family="Arial", font_size=12, bold_font_weight=800),
            accessibility=AccessibilityOptions(high_contrast=True, large_fonts=True, font_scale=1.2),
            widget_styles={
                WidgetStyleType.BUTTON: WidgetStyle(
                    fill_color="#000000",
                    fill_color_hover="#1A1A1A",
                    fill_color_pressed="#333333",
                    fill_color_selected="#FFFF00",
                    fill_color_locked="#000000",
                    fill_color_disabled="#444444",
                    border_color="#FFFFFF",
                    border_color_hover="#FFFFFF",
                    border_color_selected="#000000",
                    border_width=2.0,
                    corner_radius=0.0,
                    text_color="#FFFFFF",
                    text_color_hover="#FFFFFF",
                    text_color_selected="#000000",
                    opacity=1.0,
                ),
                WidgetStyleType.SLIDER: WidgetStyle(
                    fill_color="#FFFFFF",
                    fill_color_hover="#FFFFFF",
                    fill_color_selected="#FFFF00",
                    corner_radius=0.0,
                    border_color="#FFFFFF",
                    border_width=1.0,
                ),
                WidgetStyleType.JOYSTICK: WidgetStyle(
                    fill_color="#000000",
                    fill_color_hover="#1A1A1A",
                    fill_color_selected="#FFFF00",
                    border_color="#FFFFFF",
                    border_width=2.0,
                ),
                WidgetStyleType.REGION: WidgetStyle(
                    fill_color="#1A1A3A",
                    fill_color_hover="#2A2A4A",
                    fill_color_selected="#3A3A5A",
                    border_color="#FFFF00",
                    border_width=2.0,
                    corner_radius=0.0,
                    opacity=0.8,
                    opacity_hover=1.0,
                    opacity_selected=1.0,
                ),
            },
        )
        self.register_theme(high_contrast, overwrite=True)

        # Minimal theme
        minimal = Theme(
            name="Minimal",
            theme_type=ThemeType.CUSTOM,
            description="Minimal clean theme",
            palette=ColorPalette({
                ColorRole.BACKGROUND: "#F8F8F8",
                ColorRole.FOREGROUND: "#333333",
                ColorRole.ACCENT: "#007ACC",
                ColorRole.HOVER: "#EEEEEE",
                ColorRole.SELECTED: "#007ACC",
                ColorRole.DISABLED: "#CCCCCC",
                ColorRole.WARNING: "#E6A800",
                ColorRole.ERROR: "#CC3333",
                ColorRole.SUCCESS: "#33AA33",
                ColorRole.BORDER: "#DDDDDD",
                ColorRole.SHADOW: "#00000020",
                ColorRole.GRID: "#E0E0E0",
                ColorRole.TEXT: "#333333",
                ColorRole.TEXT_HOVER: "#000000",
                ColorRole.TEXT_SELECTED: "#FFFFFF",
                ColorRole.LINK: "#007ACC",
            }),
            typography=Typography(font_family="Arial", font_size=9, font_weight=400),
            widget_styles={
                WidgetStyleType.BUTTON: WidgetStyle(
                    fill_color="#F0F0F0",
                    fill_color_hover="#E0E0E0",
                    fill_color_pressed="#D0D0D0",
                    fill_color_selected="#007ACC",
                    fill_color_locked="#F0F0F0",
                    fill_color_disabled="#F8F8F8",
                    border_color="#DDDDDD",
                    border_color_hover="#CCCCCC",
                    border_color_selected="#007ACC",
                    border_width=1.0,
                    corner_radius=2.0,
                    text_color="#333333",
                    text_color_hover="#000000",
                    text_color_selected="#FFFFFF",
                    shadow_enabled=False,
                    glow_enabled=False,
                ),
                WidgetStyleType.SLIDER: WidgetStyle(
                    fill_color="#DDDDDD",
                    fill_color_hover="#CCCCCC",
                    fill_color_selected="#007ACC",
                ),
                WidgetStyleType.JOYSTICK: WidgetStyle(
                    fill_color="#EEEEEE",
                    fill_color_hover="#DDDDDD",
                    fill_color_selected="#007ACC",
                ),
                WidgetStyleType.REGION: WidgetStyle(
                    fill_color="#E0E8F0",
                    fill_color_hover="#D0D8E0",
                    fill_color_selected="#C0C8D0",
                    border_color="#007ACC",
                    border_width=1.0,
                    corner_radius=0.0,
                    opacity=0.5,
                    opacity_hover=0.7,
                    opacity_selected=0.8,
                ),
            },
        )
        self.register_theme(minimal, overwrite=True)

        # Set default fallback
        self._fallback_theme = dark

    # ========================================================================
    # Applying Theme
    # ========================================================================

    def apply_theme(self, theme: Theme, target_widget: Optional[QtWidgets.QWidget] = None) -> None:
        """
        Apply a theme to a widget (or the entire application).
        """
        if target_widget is None:
            # Apply to all widgets? Not possible directly.
            # We'll apply to the main application palette.
            app = QtWidgets.QApplication.instance()
            if app:
                palette = self._create_palette(theme)
                app.setPalette(palette)
                # Apply stylesheet for additional styling
                stylesheet = self._create_stylesheet(theme)
                app.setStyleSheet(stylesheet)
        else:
            # Apply to a specific widget
            palette = self._create_palette(theme)
            target_widget.setPalette(palette)
            stylesheet = self._create_stylesheet(theme)
            target_widget.setStyleSheet(stylesheet)

    def _apply_theme(self) -> None:
        """Apply the active theme to the entire application."""
        theme = self.get_active_theme()
        if theme:
            self.apply_theme(theme)

    def _create_palette(self, theme: Theme) -> QPalette:
        """Create a QPalette from a theme."""
        palette = QPalette()
        # Map ColorRole to QPalette roles
        role_map = {
            ColorRole.BACKGROUND: QPalette.Window,
            ColorRole.FOREGROUND: QPalette.WindowText,
            ColorRole.TEXT: QPalette.Text,
            ColorRole.ACCENT: QPalette.Highlight,
            ColorRole.SELECTED: QPalette.Highlight,
            ColorRole.HOVER: QPalette.Light,
            ColorRole.DISABLED: QPalette.Dark,
            ColorRole.BORDER: QPalette.Mid,
        }
        for color_role, q_role in role_map.items():
            color_str = theme.palette.get(color_role)
            if color_str:
                color = QColor(color_str)
                palette.setColor(q_role, color)
        return palette

    def _create_stylesheet(self, theme: Theme) -> str:
        """Create a QSS stylesheet from a theme."""
        # Basic stylesheet for main window and widgets
        bg = theme.palette.get(ColorRole.BACKGROUND, "#2D2D2D")
        fg = theme.palette.get(ColorRole.FOREGROUND, "#E0E0E0")
        accent = theme.palette.get(ColorRole.ACCENT, "#4A90D9")
        border = theme.palette.get(ColorRole.BORDER, "#444444")
        text = theme.palette.get(ColorRole.TEXT, "#E0E0E0")
        hover = theme.palette.get(ColorRole.HOVER, "#3D3D3D")

        # Build CSS
        css = f"""
        QMainWindow {{
            background-color: {bg};
        }}
        QToolBar {{
            background-color: {bg};
            border: none;
        }}
        QMenuBar {{
            background-color: {bg};
            color: {text};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        QMenuBar::item:selected {{
            background-color: {hover};
        }}
        QMenu {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
        }}
        QMenu::item:selected {{
            background-color: {hover};
        }}
        QStatusBar {{
            background-color: {bg};
            color: {text};
        }}
        QPushButton {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {hover};
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background-color: {accent};
            color: white;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {bg};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {accent};
            width: 14px;
            height: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {accent};
        }}
        QComboBox {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QComboBox:hover {{
            border-color: {accent};
        }}
        QLineEdit {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            padding: 4px;
            border-radius: 4px;
        }}
        QLineEdit:focus {{
            border-color: {accent};
        }}
        QLabel {{
            color: {text};
        }}
        """
        return css

    # ========================================================================
    # Callbacks
    # ========================================================================

    def add_callback(self, callback: Callable[[Theme], None]) -> None:
        """Add a callback to be notified when the theme changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Theme], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self) -> None:
        """Notify all callbacks of theme change."""
        theme = self.get_active_theme()
        for cb in self._callbacks:
            try:
                cb(theme)
            except Exception as e:
                logger.error(f"Theme callback error: {e}")

    # ========================================================================
    # _ensure_active_theme
    # ========================================================================

    def _ensure_active_theme(self) -> None:
        """Ensure the active theme exists; if not, use fallback."""
        if self._active_theme_name and self._active_theme_name in self._themes:
            return
        self._active_theme_name = "Dark"
        if self._active_theme_name not in self._themes:
            # Use the first available theme
            if self._themes:
                self._active_theme_name = next(iter(self._themes.keys()))
            else:
                self._active_theme_name = None

    # ========================================================================
    # Import / Export
    # ========================================================================

    def export_theme(self, name: str, filepath: Union[str, Path]) -> None:
        """Export a theme to a JSON file."""
        theme = self.get_theme(name)
        if not theme:
            raise ThemeNotFoundError(f"Theme '{name}' not found.")
        path = Path(filepath)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(theme.to_dict(), f, indent=2)

    def import_theme(self, filepath: Union[str, Path]) -> Theme:
        """Import a theme from a JSON file."""
        path = Path(filepath)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        theme = Theme.from_dict(data)
        self.register_theme(theme)
        return theme

    def save_theme(self, name: str) -> None:
        """Save a theme to a file named after the theme."""
        # This is a stub; we'll just export with default location
        pass

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_theme(self, theme: Theme) -> Dict[str, Any]:
        """Validate a theme and return a report."""
        issues = {"errors": [], "warnings": []}
        # Check required fields
        if not theme.name:
            issues["errors"].append("Theme name is empty.")
        # Check palette
        if not theme.palette.colors:
            issues["warnings"].append("Theme palette is empty.")
        # Check fonts
        if not theme.typography.font_family:
            issues["warnings"].append("Typography font family is empty.")
        # Check widget styles
        for style_type, style in theme.widget_styles.items():
            if style.fill_color == "#808080":
                issues["warnings"].append(f"Widget style '{style_type.value}' uses default fill color.")
        # Check icons
        # (Could check if files exist, but we skip)
        return issues


# ============================================================================
# Part 15: Public API
# ============================================================================

# Singleton instance
_theme_manager = ThemeManager()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return _theme_manager


def get_active_theme() -> Optional[Theme]:
    """Get the currently active theme."""
    return _theme_manager.get_active_theme()


def set_active_theme(name: str) -> None:
    """Set the active theme by name."""
    _theme_manager.set_active_theme(name)


def register_theme(theme: Theme, overwrite: bool = False) -> None:
    """Register a theme."""
    _theme_manager.register_theme(theme, overwrite)


def get_theme(name: str) -> Optional[Theme]:
    """Get a theme by name."""
    return _theme_manager.get_theme(name)


def list_themes() -> List[str]:
    """List all registered theme names."""
    return _theme_manager.get_theme_names()


def duplicate_theme(name: str, new_name: str) -> Theme:
    """Duplicate a theme."""
    return _theme_manager.duplicate_theme(name, new_name)


def delete_theme(name: str) -> None:
    """Delete a theme."""
    _theme_manager.delete_theme(name)


def export_theme(name: str, filepath: Union[str, Path]) -> None:
    """Export a theme to a JSON file."""
    _theme_manager.export_theme(name, filepath)


def import_theme(filepath: Union[str, Path]) -> Theme:
    """Import a theme from a JSON file."""
    return _theme_manager.import_theme(filepath)


def apply_theme(theme: Theme, widget: Optional[QtWidgets.QWidget] = None) -> None:
    """Apply a theme to a widget or the entire application."""
    _theme_manager.apply_theme(theme, widget)


def add_theme_callback(callback: Callable[[Theme], None]) -> None:
    """Add a callback for theme changes."""
    _theme_manager.add_callback(callback)


def remove_theme_callback(callback: Callable[[Theme], None]) -> None:
    """Remove a theme callback."""
    _theme_manager.remove_callback(callback)


# ============================================================================
# Part 14: Utilities (color conversion, merging, DPI scaling)
# ============================================================================

class ThemeUtils:
    """Utility functions for themes."""

    @staticmethod
    def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        """Convert a hex color string to RGB."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join([c*2 for c in hex_str])
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex string."""
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def lighten_color(hex_str: str, amount: float) -> str:
        """Lighten a color by a percentage."""
        r, g, b = ThemeUtils.hex_to_rgb(hex_str)
        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return ThemeUtils.rgb_to_hex(r, g, b)

    @staticmethod
    def darken_color(hex_str: str, amount: float) -> str:
        """Darken a color by a percentage."""
        r, g, b = ThemeUtils.hex_to_rgb(hex_str)
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return ThemeUtils.rgb_to_hex(r, g, b)

    @staticmethod
    def scale_font(font_size: int, scale: float) -> int:
        """Scale a font size by a factor."""
        return int(font_size * scale)

    @staticmethod
    def dpi_scaled_size(size: int, dpi_scale: float = 1.0) -> int:
        """Scale a size based on DPI."""
        return int(size * dpi_scale)


# ============================================================================
# Public API Exports
# ============================================================================

__all__ = [
    # Manager
    "ThemeManager",
    "get_theme_manager",
    "get_active_theme",
    "set_active_theme",
    "register_theme",
    "get_theme",
    "list_themes",
    "duplicate_theme",
    "delete_theme",
    "export_theme",
    "import_theme",
    "apply_theme",
    "add_theme_callback",
    "remove_theme_callback",
    # Data Models
    "Theme",
    "ColorPalette",
    "Typography",
    "WidgetStyle",
    "IconSet",
    "AnimationStyle",
    "AccessibilityOptions",
    # Enums
    "ThemeType",
    "WidgetStyleType",
    "ColorRole",
    # Utilities
    "ThemeUtils",
    # Exceptions
    "ThemeError",
    "ThemeNotFoundError",
    "ThemeValidationError",
    "ThemeLoadError",
]