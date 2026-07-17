# ui/themes/stylesheet.py

"""
ui/themes/stylesheet.py

Global application stylesheet.
"""

from .colors import ColorPalette

def build_stylesheet() -> str:
    """Build the stylesheet using current color palette."""
    colors = ColorPalette.all_colors()
    bg = colors["background"]
    bg_alt = colors["background_alt"]
    fg = colors["foreground"]
    fg_alt = colors["foreground_alt"]
    accent = colors["accent"]
    accent_hover = colors["accent_hover"]
    border = colors["border"]
    border_light = colors["border_light"]
    highlight = colors["highlight"]
    error = colors["error"]

    return f"""
    /* Global */
    QWidget {{
        background-color: {bg};
        color: {fg};
        font-family: "Segoe UI";
        font-size: 9pt;
    }}
    QMainWindow {{
        background-color: {bg};
    }}
    QTabWidget::pane {{
        border: 1px solid {border};
        background: {bg_alt};
    }}
    QTabBar::tab {{
        background: {bg_alt};
        color: {fg_alt};
        padding: 6px 12px;
        border: 1px solid {border};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background: {bg};
        color: {fg};
    }}
    QTabBar::tab:hover {{
        background: {highlight};
    }}
    QPushButton {{
        background: {bg_alt};
        color: {fg};
        border: 1px solid {border};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background: {highlight};
    }}
    QPushButton:pressed {{
        background: {border};
    }}
    QPushButton:checked {{
        background: {accent};
        color: white;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background: {bg};
        color: {fg};
        border: 1px solid {border};
        padding: 2px 4px;
        border-radius: 2px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {accent};
    }}
    QListWidget, QTreeWidget, QTableWidget {{
        background: {bg};
        color: {fg};
        border: 1px solid {border};
    }}
    QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
        background: {accent};
        color: white;
    }}
    QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {{
        background: {highlight};
    }}
    QHeaderView::section {{
        background: {bg_alt};
        color: {fg_alt};
        padding: 4px;
        border: 1px solid {border};
    }}
    QMenuBar {{
        background: {bg_alt};
        color: {fg};
    }}
    QMenuBar::item:selected {{
        background: {accent};
        color: white;
    }}
    QMenu {{
        background: {bg_alt};
        color: {fg};
        border: 1px solid {border};
    }}
    QMenu::item:selected {{
        background: {accent};
        color: white;
    }}
    QStatusBar {{
        background: {bg_alt};
        color: {fg_alt};
    }}
    QToolBar {{
        background: {bg_alt};
        border: none;
        spacing: 4px;
    }}
    QToolBar::separator {{
        background: {border};
        width: 1px;
        margin: 4px 2px;
    }}
    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {bg_alt};
        color: {fg};
        padding: 4px 8px;
        border: 1px solid {border};
        border-bottom: none;
    }}
    QGroupBox {{
        border: 1px solid {border};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: {fg_alt};
    }}
    QScrollBar:vertical {{
        background: {bg};
        width: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {bg_alt};
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {highlight};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QProgressBar {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 4px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {accent};
        border-radius: 4px;
    }}
    QCheckBox {{
        color: {fg};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {border};
        background: {bg};
    }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border: 1px solid {accent};
    }}
    QRadioButton {{
        color: {fg};
    }}
    QSpinBox, QDoubleSpinBox {{
        background: {bg};
        color: {fg};
        border: 1px solid {border};
        padding: 2px 4px;
        border-radius: 2px;
    }}
    QLabel {{
        color: {fg};
    }}
    """


class StyleSheet:
    """Stylesheet manager."""
    _instance = None
    _stylesheet = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get(cls) -> str:
        """Get the current stylesheet."""
        if cls._stylesheet is None:
            cls._stylesheet = build_stylesheet()
        return cls._stylesheet

    @classmethod
    def refresh(cls) -> None:
        """Rebuild the stylesheet (e.g., after theme change)."""
        cls._stylesheet = build_stylesheet()

    @classmethod
    def apply(cls, app) -> None:
        """Apply the stylesheet to a QApplication."""
        if app:
            app.setStyleSheet(cls.get())