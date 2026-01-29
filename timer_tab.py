#!/usr/bin/env python3
"""
timer_tab.py - Timer tab and related dialogs for Derby GUI
"""

from datetime import datetime
from typing import TYPE_CHECKING

import customtkinter as ctk

import db
import themes
from themes import FONT_FAMILY
from models import parse_duration_string
from dialogs import CTkMessagebox
from ctk_table import CTkSessionList
from gui_utils import batch_update

if TYPE_CHECKING:
    from gui import DerbyApp


class TimerTab:
    """Timer tab for starting/stopping sessions."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self.project_var = ctk.StringVar()
        self.bg_task_var = ctk.StringVar()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the timer tab UI with split view for projects and background tasks."""
        colors = themes.get_colors()

        # Main container
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(main_frame, fg_color=colors["container_bg"], corner_radius=10)
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        # Start session section for regular projects
        start_frame = ctk.CTkFrame(top_frame, fg_color=colors["card_bg"], corner_radius=8)
        start_frame.pack(fill=ctk.X, padx=10, pady=10)

        start_inner = ctk.CTkFrame(start_frame, fg_color="transparent")
        start_inner.pack(fill=ctk.X, padx=12, pady=10)

        ctk.CTkLabel(
            start_inner,
            text="Start New Project Session",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=colors["text_primary"]
        ).pack(anchor="w")

        project_row = ctk.CTkFrame(start_inner, fg_color="transparent")
        project_row.pack(fill=ctk.X, pady=(8, 0))

        ctk.CTkLabel(
            project_row,
            text="Project:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=colors["text_secondary"]
        ).pack(side=ctk.LEFT)

        self.project_combo = ctk.CTkComboBox(
            project_row,
            variable=self.project_var,
            width=250,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.project_combo.pack(side=ctk.LEFT, padx=10)

        start_btn = ctk.CTkButton(
            project_row,
            text="Start Tracking",
            command=self.start_session,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        start_btn.pack(side=ctk.LEFT, padx=5)

        # Active regular sessions section header
        sessions_header = ctk.CTkFrame(top_frame, fg_color="transparent")
        sessions_header.pack(fill=ctk.X, padx=10, pady=(5, 0))

        ctk.CTkLabel(
            sessions_header,
            text="Active Project Sessions",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=colors["text_primary"]
        ).pack(anchor="w")

        # Active sessions list using CTkSessionList
        self.session_list = CTkSessionList(
            top_frame,
            on_stop=self._on_stop_session,
            on_toggle_pause=self._on_toggle_pause,
            empty_message="No active project sessions"
        )
        self.session_list.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(5, 10))

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ctk.CTkFrame(main_frame, fg_color=colors["container_bg"], corner_radius=10)
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        # Start session section for background tasks
        bg_start_frame = ctk.CTkFrame(bottom_frame, fg_color=colors["card_bg"], corner_radius=8)
        bg_start_frame.pack(fill=ctk.X, padx=10, pady=10)

        bg_start_inner = ctk.CTkFrame(bg_start_frame, fg_color="transparent")
        bg_start_inner.pack(fill=ctk.X, padx=12, pady=10)

        ctk.CTkLabel(
            bg_start_inner,
            text="Start Background Task",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=colors["text_primary"]
        ).pack(anchor="w")

        bg_row = ctk.CTkFrame(bg_start_inner, fg_color="transparent")
        bg_row.pack(fill=ctk.X, pady=(8, 0))

        ctk.CTkLabel(
            bg_row,
            text="Task:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=colors["text_secondary"]
        ).pack(side=ctk.LEFT)

        self.bg_task_combo = ctk.CTkComboBox(
            bg_row,
            variable=self.bg_task_var,
            width=250,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        self.bg_task_combo.pack(side=ctk.LEFT, padx=10)

        bg_start_btn = ctk.CTkButton(
            bg_row,
            text="Start Task",
            command=self.start_background_task,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12)
        )
        bg_start_btn.pack(side=ctk.LEFT, padx=5)

        # Active background tasks section header
        bg_sessions_header = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bg_sessions_header.pack(fill=ctk.X, padx=10, pady=(5, 0))

        ctk.CTkLabel(
            bg_sessions_header,
            text="Active Background Tasks",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=colors["text_primary"]
        ).pack(anchor="w")

        # Active background tasks list using CTkSessionList
        self.bg_session_list = CTkSessionList(
            bottom_frame,
            on_stop=self._on_stop_session,
            on_toggle_pause=self._on_toggle_pause,
            empty_message="No active background tasks"
        )
        self.bg_session_list.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(5, 10))

    def refresh(self):
        """Refresh project list and active sessions."""
        # Update project combo (regular projects only)
        projects = db.list_projects(is_background=False)
        project_names = [p.name for p in projects]
        self.project_combo.configure(values=project_names)

        # Update background task combo
        bg_tasks = db.list_projects(is_background=True)
        bg_task_names = [p.name for p in bg_tasks]
        self.bg_task_combo.configure(values=bg_task_names)

        # Update active sessions
        self._refresh_active_sessions()

    def _refresh_active_sessions(self):
        """Refresh both active sessions lists."""
        # Get all active sessions and project info first
        active = db.get_active_sessions()

        # Prepare session data with project info
        regular_sessions = []
        bg_sessions = []

        for session in active:
            project = db.get_project(session.project_name)
            is_bg = project.is_background if project else False

            started = session.start_time.strftime("%Y-%m-%d %I:%M:%S %p") if session.start_time else ""
            session_data = {
                'session_id': str(session.id),
                'project_name': session.project_name,
                'started': started,
                'duration': session.format_duration(),
                'is_paused': session.is_paused
            }

            if is_bg:
                bg_sessions.append(session_data)
            else:
                regular_sessions.append(session_data)

        # Use batch_update to defer painting during clear and repopulate
        with batch_update(self.session_list):
            with batch_update(self.bg_session_list):
                # Clear existing from both lists
                self.session_list.clear()
                self.bg_session_list.clear()

                # Add regular sessions
                for data in regular_sessions:
                    self.session_list.add_session(**data)

                # Add background sessions
                for data in bg_sessions:
                    self.bg_session_list.add_session(**data)

    def update_durations(self):
        """Update displayed durations and pause states for active sessions."""
        active = db.get_active_sessions()
        active_dict = {str(s.id): s for s in active}

        # Update regular sessions
        for session_id in self.session_list.get_children():
            if session_id in active_dict:
                session = active_dict[session_id]
                self.session_list.update_duration(session_id, session.format_duration())
                self.session_list.update_pause_state(session_id, session.is_paused)

        # Update background tasks
        for session_id in self.bg_session_list.get_children():
            if session_id in active_dict:
                session = active_dict[session_id]
                self.bg_session_list.update_duration(session_id, session.format_duration())
                self.bg_session_list.update_pause_state(session_id, session.is_paused)

    def start_session(self):
        """Start tracking the selected regular project."""
        project = self.project_var.get().strip()
        if not project:
            CTkMessagebox(self.app.root, "Warning", "Please enter a project name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(project)
        if active:
            CTkMessagebox(self.app.root, "Info", f"'{project}' is already being tracked", "info")
            return

        # Ensure project exists and is not a background task
        existing = db.get_project(project)
        if existing and existing.is_background:
            CTkMessagebox(self.app.root, "Warning", f"'{project}' is a background task, not a project", "warning")
            return

        db.start_session(project)
        self.project_var.set("")
        self.refresh()

    def start_background_task(self):
        """Start tracking a background task."""
        task = self.bg_task_var.get().strip()
        if not task:
            CTkMessagebox(self.app.root, "Warning", "Please enter a task name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(task)
        if active:
            CTkMessagebox(self.app.root, "Info", f"'{task}' is already being tracked", "info")
            return

        # Create as background task if new
        existing = db.get_project(task)
        if existing is None:
            db.create_project(task, is_background=True)
        elif not existing.is_background:
            CTkMessagebox(self.app.root, "Warning", f"'{task}' is a regular project, not a background task", "warning")
            return

        db.start_session(task)
        self.bg_task_var.set("")
        self.refresh()

    def _on_stop_session(self, session_id: str):
        """Handle stop button click from session card."""
        session_id_int = int(session_id)
        active = db.get_active_sessions()
        session = next((s for s in active if s.id == session_id_int), None)
        if session:
            db.stop_session(project_name=session.project_name)
            self.refresh()

    def _on_toggle_pause(self, session_id: str):
        """Handle pause/resume button click from session card."""
        session_id_int = int(session_id)
        active = db.get_active_sessions()
        session = next((s for s in active if s.id == session_id_int), None)
        if not session:
            return

        if session.is_paused:
            db.resume_session(session_id_int)
        else:
            db.pause_session(session_id_int)

        self.refresh()

    def stop_all(self):
        """Stop all active sessions (both projects and background tasks)."""
        self.app._stop_all()


class StopSessionDialog:
    """Dialog for stopping a session with optional notes."""

    def __init__(self, parent, app: 'DerbyApp', project_name: str):
        self.app = app
        self.project_name = project_name

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Stop: {project_name}")
        self.dialog.geometry("400x200")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text="Notes (optional):").pack(anchor="w", pady=(0, 5))

        self.notes_text = ctk.CTkTextbox(main_frame, height=80, width=350)
        self.notes_text.pack(pady=5)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Stop Session", command=self._do_stop).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_stop(self):
        """Stop the session."""
        notes = self.notes_text.get("1.0", ctk.END).strip()
        db.stop_session(project_name=self.project_name, notes=notes)
        self.dialog.destroy()
        self.app.timer_tab.refresh()


class LogSessionDialog:
    """Dialog for logging a manual session entry."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Log Manual Entry")
        self.dialog.geometry("450x350")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.project_var = ctk.StringVar()
        self.duration_var = ctk.StringVar()
        self.date_var = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        # Project
        ctk.CTkLabel(main_frame, text="Project:").pack(anchor="w", pady=(0, 2))
        projects = db.list_projects()
        project_names = [p.name for p in projects]
        project_combo = ctk.CTkComboBox(main_frame, variable=self.project_var, values=project_names, width=300)
        project_combo.pack(anchor="w", pady=(0, 10))

        # Duration
        duration_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        duration_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(duration_frame, text="Duration:").pack(side=ctk.LEFT)
        duration_entry = ctk.CTkEntry(duration_frame, textvariable=self.duration_var, width=120)
        duration_entry.pack(side=ctk.LEFT, padx=10)
        ctk.CTkLabel(duration_frame, text="(e.g., 1h30m, 45m, 2h)").pack(side=ctk.LEFT)

        # Date
        date_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        date_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(date_frame, text="Date:").pack(side=ctk.LEFT)
        date_entry = ctk.CTkEntry(date_frame, textvariable=self.date_var, width=120)
        date_entry.pack(side=ctk.LEFT, padx=10)
        ctk.CTkLabel(date_frame, text="(YYYY-MM-DD)").pack(side=ctk.LEFT)

        # Notes
        ctk.CTkLabel(main_frame, text="Notes:").pack(anchor="w", pady=(0, 2))
        self.notes_text = ctk.CTkTextbox(main_frame, height=80, width=380)
        self.notes_text.pack(pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="Log Session", command=self._do_log).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_log(self):
        """Log the session."""
        project = self.project_var.get().strip()
        duration_str = self.duration_var.get().strip()
        date_str = self.date_var.get().strip()
        notes = self.notes_text.get("1.0", ctk.END).strip()

        if not project:
            CTkMessagebox(self.dialog, "Warning", "Please enter a project name", "warning")
            return

        if not duration_str:
            CTkMessagebox(self.dialog, "Warning", "Please enter a duration", "warning")
            return

        try:
            duration = parse_duration_string(duration_str)
            if duration.total_seconds() == 0:
                raise ValueError("Duration must be greater than 0")
        except ValueError:
            CTkMessagebox(self.dialog, "Error", "Invalid duration format. Use formats like: 1h30m, 45m, 2h", "error")
            return

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=17, minute=0, second=0)
        except ValueError:
            CTkMessagebox(self.dialog, "Error", "Invalid date format. Use YYYY-MM-DD", "error")
            return

        db.log_session(project_name=project, duration=duration, notes=notes, date=date)
        self.dialog.destroy()
        CTkMessagebox(self.app.root, "Success", f"Logged {duration_str} for {project}", "info")
