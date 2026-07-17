"""
ui/themes/dark_theme.py

Dark theme specific definitions (override colors).
"""

from .colors import ColorPalette

# Dark theme is the default; we just ensure it's set.
def apply_dark_theme():
    """Apply the dark theme (default)."""
    ColorPalette.set_theme("dark")

# For completeness, we also define a class that can be used.
class DarkTheme:
    @staticmethod
    def apply():
        apply_dark_theme()

    @staticmethod
    def name():
        return "Dark"