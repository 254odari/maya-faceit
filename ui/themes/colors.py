# ui/themes/colors.py

"""
ui/themes/colors.py

Color palette definitions.
"""

from typing import Dict, Any

# Base colors for dark theme
DARK_COLORS = {
    "background": "#2b2b2b",
    "background_alt": "#3a3a3a",
    "foreground": "#dddddd",
    "foreground_alt": "#aaaaaa",
    "accent": "#4a90d9",
    "accent_hover": "#5a9fe9",
    "border": "#444444",
    "border_light": "#555555",
    "highlight": "#3a3a3a",
    "highlight_alt": "#4a4a4a",
    "error": "#8b3a3a",
    "warning": "#8b7a3a",
    "success": "#3a8b3a",
    "info": "#3a6a8b",
}

# Light theme colors
LIGHT_COLORS = {
    "background": "#f0f0f0",
    "background_alt": "#e0e0e0",
    "foreground": "#222222",
    "foreground_alt": "#555555",
    "accent": "#2a6ab0",
    "accent_hover": "#3a7ac0",
    "border": "#bbbbbb",
    "border_light": "#cccccc",
    "highlight": "#e0e0e0",
    "highlight_alt": "#d0d0d0",
    "error": "#cc4444",
    "warning": "#ccaa44",
    "success": "#44cc44",
    "info": "#4488cc",
}

class ColorPalette:
    """Color palette manager."""
    _instance = None
    _current_theme = "dark"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._colors = DARK_COLORS
        return cls._instance

    @classmethod
    def get(cls, key: str) -> str:
        """Get a color by key."""
        instance = cls()
        return instance._colors.get(key, "#ff00ff")  # fallback magenta

    @classmethod
    def set_theme(cls, theme: str) -> None:
        """Switch between 'dark' and 'light' themes."""
        instance = cls()
        if theme == "light":
            instance._colors = LIGHT_COLORS
        else:
            instance._colors = DARK_COLORS
        cls._current_theme = theme

    @classmethod
    def current_theme(cls) -> str:
        return cls._current_theme

    @classmethod
    def all_colors(cls) -> Dict[str, str]:
        instance = cls()
        return instance._colors.copy()