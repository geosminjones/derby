"""
themes.py - Theme definitions for Derby GUI

This module provides theme management for the Derby application.
Themes define colors for all UI components.
"""

from dataclasses import dataclass
from typing import Callable


# Font configuration
FONT_FAMILY = "Inter"


@dataclass
class Theme:
    """Represents a complete UI theme."""

    name: str              # Internal identifier (e.g., "dark")
    display_name: str      # User-facing name (e.g., "Dark Mode")

    # Core background colors
    bg_dark: str           # Main window background
    bg_medium: str         # Secondary/treeview background
    bg_light: str          # Lighter accent/selection background

    # Text colors
    text_primary: str      # Main text color
    text_secondary: str    # Muted/hint text color

    # Component colors
    separator: str         # Treeview separator rows
    card_bg: str           # Section card background
    container_bg: str      # Container frame background

    # Semantic colors (buttons, alerts)
    danger: str            # Delete/destructive actions
    danger_hover: str      # Hover state for danger buttons
    success: str           # Success indicators

    # Session card colors
    session_active_bg: str    # Active session card background (light green)
    session_paused_bg: str    # Paused session card background (light yellow)
    session_stopped_bg: str   # Stopped session card background (slightly lighter than bg)

    # Row selection color
    row_selected: str         # Selected row background (blue tint)

    # Scrollbar colors
    scrollbar_track: str          # Track background for opaque contexts
    scrollbar_thumb: str          # Default thumb color
    scrollbar_thumb_hover: str    # Hover state for thumb

    # Appearance mode (for compatibility)
    ctk_appearance_mode: str  # "Dark" or "Light"

    def to_dict(self) -> dict[str, str]:
        """Return color values as dictionary for backward compatibility."""
        return {
            "bg_dark": self.bg_dark,
            "bg_medium": self.bg_medium,
            "bg_light": self.bg_light,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "separator": self.separator,
            "card_bg": self.card_bg,
            "container_bg": self.container_bg,
            "danger": self.danger,
            "danger_hover": self.danger_hover,
            "success": self.success,
            "session_active_bg": self.session_active_bg,
            "session_paused_bg": self.session_paused_bg,
            "session_stopped_bg": self.session_stopped_bg,
            "row_selected": self.row_selected,
            "scrollbar_track": self.scrollbar_track,
            "scrollbar_thumb": self.scrollbar_thumb,
            "scrollbar_thumb_hover": self.scrollbar_thumb_hover,
        }


# =============================================================================
# THEME DEFINITIONS
# =============================================================================

DARK_THEME = Theme(
    name="dark",
    display_name="Dark Mode",
    bg_dark="#1a1a2e",
    bg_medium="#130b17",
    bg_light="#362040",
    text_primary="#ffffff",
    text_secondary="#a0a0a0",
    separator="#606060",
    card_bg="#362040",
    container_bg="#281b2e",
    danger="#c0392b",
    danger_hover="#e74c3c",
    success="#27ae60",
    session_active_bg="#1e3a2f",
    session_paused_bg="#3a3520",
    session_stopped_bg="#2a2a3e",
    row_selected="#1a2540",
    scrollbar_track="#1a1a2e",
    scrollbar_thumb="#4a3a54",
    scrollbar_thumb_hover="#606060",
    ctk_appearance_mode="Dark"
)

LIGHT_THEME = Theme(
    name="light",
    display_name="Light Mode",
    bg_dark="#f5f5f5",
    bg_medium="#ffffff",
    bg_light="#e8e8e8",
    text_primary="#1a1a1a",
    text_secondary="#666666",
    separator="#606060",
    card_bg="#ffffff",
    container_bg="#c8c8c8",
    danger="#c0392b",
    danger_hover="#e74c3c",
    success="#27ae60",
    session_active_bg="#d4edda",
    session_paused_bg="#fff3cd",
    session_stopped_bg="#e8e8e8",
    row_selected="#cce5ff",
    scrollbar_track="#e0e0e0",
    scrollbar_thumb="#c0c0c0",
    scrollbar_thumb_hover="#a0a0a0",
    ctk_appearance_mode="Light"
)

BLACK_THEME = Theme(
    name="black",
    display_name="Black Mode",
    bg_dark="#000000",
    bg_medium="#0a0a0a",
    bg_light="#1a1a1a",
    text_primary="#e0e0e0",
    text_secondary="#808080",
    separator="#606060",
    card_bg="#121212",
    container_bg="#0d0d0d",
    danger="#b03025",
    danger_hover="#d44035",
    success="#228b22",
    session_active_bg="#1a2e1a",
    session_paused_bg="#2e2a1a",
    session_stopped_bg="#151515",
    row_selected="#0d1a2a",
    scrollbar_track="#0d0d0d",
    scrollbar_thumb="#2a2a2a",
    scrollbar_thumb_hover="#404040",
    ctk_appearance_mode="Dark"
)

# Theme registry
THEMES: dict[str, Theme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "black": BLACK_THEME,
}


# =============================================================================
# MODULE STATE
# =============================================================================

_current_theme: Theme = DARK_THEME
_theme_change_callbacks: list[Callable[[], None]] = []


# =============================================================================
# PUBLIC API
# =============================================================================

def get_current_theme() -> Theme:
    """Get the currently active theme."""
    return _current_theme


def get_colors() -> dict[str, str]:
    """
    Get current theme colors as dictionary.

    This provides backward compatibility with the existing COLORS usage.
    """
    return _current_theme.to_dict()


def get_available_themes() -> list[tuple[str, str]]:
    """
    Get list of available themes.

    Returns:
        List of (name, display_name) tuples
    """
    return [(t.name, t.display_name) for t in THEMES.values()]


def set_theme(theme_name: str) -> Theme:
    """
    Set the active theme by name.

    Args:
        theme_name: Internal name of theme (e.g., "dark")

    Returns:
        The newly active Theme

    Raises:
        ValueError: If theme_name is not found
    """
    global _current_theme

    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")

    _current_theme = THEMES[theme_name]

    # Notify all registered callbacks
    _notify_theme_change()

    return _current_theme


def register_theme_callback(callback: Callable[[], None]):
    """
    Register a callback to be called when theme changes.

    Args:
        callback: A callable that takes no arguments
    """
    if callback not in _theme_change_callbacks:
        _theme_change_callbacks.append(callback)


def unregister_theme_callback(callback: Callable[[], None]):
    """
    Unregister a theme change callback.

    Args:
        callback: The callback to remove
    """
    if callback in _theme_change_callbacks:
        _theme_change_callbacks.remove(callback)


def load_saved_theme() -> Theme:
    """
    Load theme from database settings.

    Call this after db.init_database() to restore user's theme preference.

    Returns:
        The loaded (or default) Theme
    """
    import db
    saved_theme = db.get_setting("theme", "dark")

    try:
        return set_theme(saved_theme)
    except ValueError:
        # Fall back to dark theme if saved theme is invalid
        return set_theme("dark")


def save_theme_preference():
    """Save current theme to database."""
    import db
    db.set_setting("theme", _current_theme.name)


# =============================================================================
# PRIVATE FUNCTIONS
# =============================================================================

def _notify_theme_change():
    """Call all registered theme change callbacks."""
    for callback in _theme_change_callbacks:
        try:
            callback()
        except Exception as e:
            # Log but don't crash if a callback fails
            print(f"Theme callback error: {e}")


def get_scrollbar_qss(
    vertical: bool = True,
    horizontal: bool = False,
    transparent_track: bool = False,
    width: int = 12
) -> str:
    """
    Generate consistent QSS for scrollbar styling.

    Args:
        vertical: Include vertical scrollbar styling
        horizontal: Include horizontal scrollbar styling
        transparent_track: Use transparent track (True) or opaque theme color (False)
        width: Scrollbar width in pixels

    Returns:
        QSS string for scrollbar styling
    """
    colors = get_colors()
    track_color = "transparent" if transparent_track else colors["scrollbar_track"]
    thumb_color = colors["scrollbar_thumb"]
    thumb_hover = colors["scrollbar_thumb_hover"]
    border_radius = max(3, width // 3)

    qss_parts = []

    if vertical:
        qss_parts.append(f"""
            QScrollBar:vertical {{
                background-color: {track_color};
                width: {width}px;
                border-radius: {border_radius}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {thumb_color};
                border-radius: {border_radius}px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {thumb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    if horizontal:
        qss_parts.append(f"""
            QScrollBar:horizontal {{
                background-color: {track_color};
                height: {width}px;
                border-radius: {border_radius}px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {thumb_color};
                border-radius: {border_radius}px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {thumb_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """)

    return "".join(qss_parts)
