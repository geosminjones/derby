#!/usr/bin/env python3
"""
appearance_tab.py - Appearance settings tab for Derby GUI
"""

from typing import TYPE_CHECKING

import customtkinter as ctk

import themes
from themes import FONT_FAMILY

if TYPE_CHECKING:
    from gui import DerbyApp


class AppearanceTab:
    """Appearance tab for managing theme settings."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the appearance tab UI."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Theme section
        theme_section = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        theme_section.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(
            theme_section,
            text="Theme",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Radio buttons container
        self.theme_var = ctk.StringVar(value=themes.get_current_theme().name)
        radio_frame = ctk.CTkFrame(theme_section, fg_color="transparent")
        radio_frame.pack(fill=ctk.X, padx=10, pady=(0, 10))

        # Create radio button for each available theme
        for theme_name, display_name in themes.get_available_themes():
            radio = ctk.CTkRadioButton(
                radio_frame,
                text=display_name,
                variable=self.theme_var,
                value=theme_name,
                command=self._on_theme_change
            )
            radio.pack(anchor="w", pady=2)

    def _on_theme_change(self):
        """Handle theme selection change."""
        selected_theme = self.theme_var.get()

        # Trigger full UI rebuild via main app
        self.app.switch_theme(selected_theme)

    def refresh(self):
        """Refresh the appearance tab (update radio selection to current theme)."""
        self.theme_var.set(themes.get_current_theme().name)
