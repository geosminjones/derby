"""
themes.py - Theme definitions for Derby GUI

This module provides theme management for the Derby application.
Themes define colors for all UI components.
"""

from dataclasses import dataclass
from typing import Callable, Optional
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk


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

    # CustomTkinter mode
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
    separator="#3a3a5a",
    card_bg="#362040",
    container_bg="#281b2e",
    danger="#c0392b",
    danger_hover="#e74c3c",
    success="#27ae60",
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
    separator="#d0d0d0",
    card_bg="#ffffff",
    container_bg="#c8c8c8",
    danger="#c0392b",
    danger_hover="#e74c3c",
    success="#27ae60",
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
    separator="#252525",
    card_bg="#121212",
    container_bg="#0d0d0d",
    danger="#b03025",
    danger_hover="#d44035",
    success="#228b22",
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

    # Update CustomTkinter appearance mode
    ctk.set_appearance_mode(_current_theme.ctk_appearance_mode)

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


def apply_ttk_styles(style: ttk.Style):
    """
    Apply current theme to TTK styles.

    Call this after creating the root window and whenever theme changes.

    Args:
        style: The ttk.Style instance to configure
    """
    theme = _current_theme

    style.theme_use("clam")

    style.configure("Treeview",
        background=theme.bg_medium,
        foreground=theme.text_primary,
        fieldbackground=theme.bg_medium,
        bordercolor=theme.bg_dark,
        font=(FONT_FAMILY, 10),
        rowheight=25
    )

    style.configure("Treeview.Heading",
        background=theme.bg_light,
        foreground=theme.text_primary,
        font=(FONT_FAMILY, 10, "bold")
    )

    style.map("Treeview",
        background=[("selected", theme.bg_light)],
        foreground=[("selected", theme.text_primary)]
    )

    style.configure("Vertical.TScrollbar",
        background=theme.bg_medium,
        troughcolor=theme.bg_dark,
        arrowcolor=theme.text_primary
    )

    style.map("Vertical.TScrollbar",
        background=[("disabled", theme.bg_dark), ("!disabled", theme.bg_medium)],
        troughcolor=[("disabled", theme.bg_dark), ("!disabled", theme.bg_dark)]
    )


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


# =============================================================================
# INITIALIZATION
# =============================================================================

# Set initial CustomTkinter appearance mode
ctk.set_appearance_mode(_current_theme.ctk_appearance_mode)
ctk.set_default_color_theme("blue")
