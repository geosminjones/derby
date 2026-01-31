#!/usr/bin/env python3
"""
appearance_tab.py - Settings tab for Derby GUI (includes appearance and data storage)
"""

import tkinter as tk
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

import db
import themes
from themes import FONT_FAMILY

if TYPE_CHECKING:
    from gui import DerbyApp


class ChangeDatabaseLocationDialog:
    """Dialog for changing the database storage location."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self.result = None
        self.new_folder = None

        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Change Database Location")
        self.dialog.geometry("500x280")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 280) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Apply theme colors
        colors = themes.get_colors()
        self.dialog.configure(bg=colors["bg_dark"])

        # Main frame
        main_frame = tk.Frame(self.dialog, bg=colors["bg_dark"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Select New Database Location",
            font=(FONT_FAMILY, 14, "bold"),
            bg=colors["bg_dark"],
            fg=colors["text_primary"]
        )
        title_label.pack(anchor="w", pady=(0, 15))

        # Current location info
        current_frame = tk.Frame(main_frame, bg=colors["bg_dark"])
        current_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            current_frame,
            text="Current location:",
            font=(FONT_FAMILY, 10),
            bg=colors["bg_dark"],
            fg=colors["text_secondary"]
        ).pack(anchor="w")

        tk.Label(
            current_frame,
            text=str(db.get_data_directory()),
            font=(FONT_FAMILY, 10),
            bg=colors["bg_dark"],
            fg=colors["text_primary"],
            wraplength=450
        ).pack(anchor="w")

        # New location selection
        new_frame = tk.Frame(main_frame, bg=colors["bg_dark"])
        new_frame.pack(fill=tk.X, pady=(10, 10))

        tk.Label(
            new_frame,
            text="New location:",
            font=(FONT_FAMILY, 10),
            bg=colors["bg_dark"],
            fg=colors["text_secondary"]
        ).pack(anchor="w")

        select_frame = tk.Frame(new_frame, bg=colors["bg_dark"])
        select_frame.pack(fill=tk.X, pady=(5, 0))

        self.folder_var = tk.StringVar(value="No folder selected")
        self.folder_label = tk.Label(
            select_frame,
            textvariable=self.folder_var,
            font=(FONT_FAMILY, 10),
            bg=colors["container_bg"],
            fg=colors["text_primary"],
            anchor="w",
            padx=10,
            pady=5
        )
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = tk.Button(
            select_frame,
            text="Browse...",
            font=(FONT_FAMILY, 10),
            command=self._browse_folder,
            bg=colors["bg_light"],
            fg=colors["text_primary"],
            activebackground=colors["separator"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            padx=15
        )
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Copy data option
        self.copy_var = tk.BooleanVar(value=True)
        copy_check = tk.Checkbutton(
            main_frame,
            text="Copy existing data to new location",
            variable=self.copy_var,
            font=(FONT_FAMILY, 10),
            bg=colors["bg_dark"],
            fg=colors["text_primary"],
            selectcolor=colors["container_bg"],
            activebackground=colors["bg_dark"],
            activeforeground=colors["text_primary"]
        )
        copy_check.pack(anchor="w", pady=(10, 15))

        # Warning message
        warning_label = tk.Label(
            main_frame,
            text="Note: The application will use the new location after confirming.",
            font=(FONT_FAMILY, 9),
            bg=colors["bg_dark"],
            fg=colors["text_secondary"],
            wraplength=450
        )
        warning_label.pack(anchor="w", pady=(0, 15))

        # Buttons
        btn_frame = tk.Frame(main_frame, bg=colors["bg_dark"])
        btn_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=(FONT_FAMILY, 10),
            command=self._cancel,
            bg=colors["bg_light"],
            fg=colors["text_primary"],
            activebackground=colors["separator"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.confirm_btn = tk.Button(
            btn_frame,
            text="Confirm",
            font=(FONT_FAMILY, 10),
            command=self._confirm,
            bg=colors["success"],
            fg=colors["text_primary"],
            activebackground=colors["success"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            width=12,
            state=tk.DISABLED
        )
        self.confirm_btn.pack(side=tk.RIGHT)

        self.dialog.wait_window()

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Database Folder",
            initialdir=str(db.get_data_directory())
        )
        if folder:
            self.new_folder = folder
            self.folder_var.set(folder)
            self.confirm_btn.configure(state=tk.NORMAL)

    def _confirm(self):
        """Confirm the folder change."""
        if self.new_folder:
            self.result = {
                'folder': self.new_folder,
                'copy_data': self.copy_var.get()
            }
        self.dialog.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.dialog.destroy()

    def get_result(self):
        """Get the dialog result."""
        return self.result


class BackupDatabaseDialog:
    """Simple dialog for backing up the database."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self.result = None

        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Backup Database")
        self.dialog.geometry("450x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Apply theme colors
        colors = themes.get_colors()
        self.dialog.configure(bg=colors["bg_dark"])

        # Main frame
        main_frame = tk.Frame(self.dialog, bg=colors["bg_dark"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Backup Database",
            font=(FONT_FAMILY, 14, "bold"),
            bg=colors["bg_dark"],
            fg=colors["text_primary"]
        )
        title_label.pack(anchor="w", pady=(0, 15))

        # Backup location selection
        tk.Label(
            main_frame,
            text="Select folder to save backup:",
            font=(FONT_FAMILY, 10),
            bg=colors["bg_dark"],
            fg=colors["text_secondary"]
        ).pack(anchor="w")

        select_frame = tk.Frame(main_frame, bg=colors["bg_dark"])
        select_frame.pack(fill=tk.X, pady=(5, 15))

        self.folder_var = tk.StringVar(value="No folder selected")
        self.folder_label = tk.Label(
            select_frame,
            textvariable=self.folder_var,
            font=(FONT_FAMILY, 10),
            bg=colors["container_bg"],
            fg=colors["text_primary"],
            anchor="w",
            padx=10,
            pady=5
        )
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = tk.Button(
            select_frame,
            text="Browse...",
            font=(FONT_FAMILY, 10),
            command=self._browse_folder,
            bg=colors["bg_light"],
            fg=colors["text_primary"],
            activebackground=colors["separator"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            padx=15
        )
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Info message
        info_label = tk.Label(
            main_frame,
            text=f"Backup will be saved as: {db.get_backup_filename()}",
            font=(FONT_FAMILY, 9),
            bg=colors["bg_dark"],
            fg=colors["text_secondary"]
        )
        info_label.pack(anchor="w", pady=(0, 15))

        # Buttons
        btn_frame = tk.Frame(main_frame, bg=colors["bg_dark"])
        btn_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=(FONT_FAMILY, 10),
            command=self._cancel,
            bg=colors["bg_light"],
            fg=colors["text_primary"],
            activebackground=colors["separator"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            width=12
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.backup_btn = tk.Button(
            btn_frame,
            text="Create Backup",
            font=(FONT_FAMILY, 10),
            command=self._backup,
            bg=colors["success"],
            fg=colors["text_primary"],
            activebackground=colors["success"],
            activeforeground=colors["text_primary"],
            relief=tk.FLAT,
            width=12,
            state=tk.DISABLED
        )
        self.backup_btn.pack(side=tk.RIGHT)

        self.backup_folder = None
        self.dialog.wait_window()

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Backup Folder"
        )
        if folder:
            self.backup_folder = folder
            self.folder_var.set(folder)
            self.backup_btn.configure(state=tk.NORMAL)

    def _backup(self):
        """Perform the backup."""
        if self.backup_folder:
            self.result = self.backup_folder
        self.dialog.destroy()

    def _cancel(self):
        """Cancel the dialog."""
        self.result = None
        self.dialog.destroy()

    def get_result(self):
        """Get the dialog result."""
        return self.result


class AppearanceTab:
    """Settings tab for managing theme and data storage settings."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the settings tab UI."""
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

        # Data Storage section
        storage_section = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        storage_section.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(
            storage_section,
            text="Data Storage",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Database location display
        location_frame = ctk.CTkFrame(storage_section, fg_color="transparent")
        location_frame.pack(fill=ctk.X, padx=10, pady=(0, 5))

        ctk.CTkLabel(
            location_frame,
            text="Database location:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=themes.get_colors()["text_secondary"]
        ).pack(anchor="w")

        # Location path and buttons row
        path_row = ctk.CTkFrame(storage_section, fg_color="transparent")
        path_row.pack(fill=ctk.X, padx=10, pady=(0, 10))

        # Path display
        self.db_path_var = ctk.StringVar(value=str(db.get_data_directory()))
        self.path_label = ctk.CTkLabel(
            path_row,
            textvariable=self.db_path_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=themes.get_colors()["bg_light"],
            corner_radius=5,
            anchor="w",
            padx=10,
            pady=5
        )
        self.path_label.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))

        # Buttons
        ctk.CTkButton(
            path_row,
            text="Select New Folder",
            command=self._on_select_new_folder,
            width=130
        ).pack(side=ctk.LEFT, padx=(0, 5))

        ctk.CTkButton(
            path_row,
            text="Backup Database",
            command=self._on_backup_database,
            width=130
        ).pack(side=ctk.LEFT)

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

    def _on_select_new_folder(self):
        """Handle select new folder button click."""
        dialog = ChangeDatabaseLocationDialog(self.app.root, self.app)
        result = dialog.get_result()

        if result:
            from dialogs import CTkMessagebox
            from pathlib import Path

            success = db.set_data_directory(
                Path(result['folder']),
                copy_existing=result['copy_data']
            )

            if success:
                self.db_path_var.set(str(db.get_data_directory()))
                CTkMessagebox(
                    self.app.root,
                    "Success",
                    f"Database location changed to:\n{result['folder']}",
                    "info"
                )
                # Refresh all tabs to reflect any data changes
                self.app.timer_tab.refresh()
            else:
                CTkMessagebox(
                    self.app.root,
                    "Error",
                    "Failed to change database location. Please check permissions and try again.",
                    "error"
                )

    def _on_backup_database(self):
        """Handle backup database button click."""
        dialog = BackupDatabaseDialog(self.app.root, self.app)
        result = dialog.get_result()

        if result:
            from dialogs import CTkMessagebox
            from pathlib import Path

            success = db.backup_database(Path(result))

            if success:
                CTkMessagebox(
                    self.app.root,
                    "Success",
                    f"Database backed up successfully to:\n{result}",
                    "info"
                )
            else:
                CTkMessagebox(
                    self.app.root,
                    "Error",
                    "Failed to create backup. Please check permissions and try again.",
                    "error"
                )

    def refresh(self):
        """Refresh the settings tab (update radio selection to current theme)."""
        self.theme_var.set(themes.get_current_theme().name)
        self.row_dividers_var.set(db.get_setting("show_row_dividers", "1") == "1")
        self.group_separators_var.set(db.get_setting("show_group_separators", "1") == "1")
        self.db_path_var.set(str(db.get_data_directory()))
