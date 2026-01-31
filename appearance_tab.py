#!/usr/bin/env python3
"""
appearance_tab.py - Appearance settings tab for Derby GUI
"""

from typing import TYPE_CHECKING

import customtkinter as ctk

import db
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

        # Table display section
        display_section = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        display_section.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(
            display_section,
            text="Table Display",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Row dividers toggle
        self.row_dividers_var = ctk.BooleanVar(
            value=db.get_setting("show_row_dividers", "1") == "1"
        )
        ctk.CTkSwitch(
            display_section,
            text="Show row dividers",
            variable=self.row_dividers_var,
            command=self._on_row_dividers_change
        ).pack(anchor="w", padx=10, pady=2)

        # Group separators toggle
        self.group_separators_var = ctk.BooleanVar(
            value=db.get_setting("show_group_separators", "1") == "1"
        )
        ctk.CTkSwitch(
            display_section,
            text="Show group separators",
            variable=self.group_separators_var,
            command=self._on_group_separators_change
        ).pack(anchor="w", padx=10, pady=(2, 10))

    def _on_theme_change(self):
        """Handle theme selection change."""
        selected_theme = self.theme_var.get()

        # Trigger full UI rebuild via main app
        self.app.switch_theme(selected_theme)

    def _on_row_dividers_change(self):
        """Handle row dividers toggle change."""
        db.set_setting("show_row_dividers", "1" if self.row_dividers_var.get() else "0")
        if hasattr(self.app, 'summary_tab') and self.app.summary_tab._tables_initialized:
            self.app.summary_tab.refresh()

    def _on_group_separators_change(self):
        """Handle group separators toggle change."""
        db.set_setting("show_group_separators", "1" if self.group_separators_var.get() else "0")
        if hasattr(self.app, 'summary_tab') and self.app.summary_tab._tables_initialized:
            self.app.summary_tab.refresh()

    def refresh(self):
        """Refresh the appearance tab (update radio selection to current theme)."""
        self.theme_var.set(themes.get_current_theme().name)
        self.row_dividers_var.set(db.get_setting("show_row_dividers", "1") == "1")
        self.group_separators_var.set(db.get_setting("show_group_separators", "1") == "1")
