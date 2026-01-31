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
    from models import Project


class TimerTab:
    """Timer tab for starting/stopping sessions."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self.project_var = ctk.StringVar()
        self.bg_task_var = ctk.StringVar()

        # Caches for optimization
        self._projects_cache: dict[str, 'Project'] | None = None
        self._last_session_ids: set[str] = set()
        self._last_session_state: dict[str, tuple[str, bool]] = {}  # id -> (duration, is_paused)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the timer tab UI with split view for projects and background tasks."""
        colors = themes.get_colors()

        # Main container (stored for batch_update during refreshes)
        self.main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(self.main_frame, fg_color=colors["container_bg"], corner_radius=10)
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
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color=colors["container_bg"], corner_radius=10)
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

    # -------------------------------------------------------------------------
    # Cache management
    # -------------------------------------------------------------------------

    def _get_projects_map(self) -> dict[str, 'Project']:
        """Get cached project map, refreshing if invalidated."""
        if self._projects_cache is None:
            all_projects = db.list_projects()
            self._projects_cache = {p.name: p for p in all_projects}
        return self._projects_cache

    def _invalidate_caches(self):
        """Invalidate all caches - call when data may have changed externally."""
        self._projects_cache = None
        self._last_session_ids.clear()
        self._last_session_state.clear()

    # -------------------------------------------------------------------------
    # Refresh methods (split for targeted updates)
    # -------------------------------------------------------------------------

    def refresh(self):
        """Full refresh - project lists and active sessions."""
        self._invalidate_caches()
        self.refresh_combos()
        self.refresh_sessions()

    def refresh_combos(self):
        """Refresh only the combo box values (when projects change)."""
        project_map = self._get_projects_map()

        # Extract and sort project names by type
        project_names = sorted(
            [p.name for p in project_map.values() if not p.is_background],
            key=str.lower
        )
        bg_task_names = sorted(
            [p.name for p in project_map.values() if p.is_background],
            key=str.lower
        )

        self.project_combo.configure(values=project_names)
        self.bg_task_combo.configure(values=bg_task_names)

    def refresh_sessions(self):
        """Refresh only the active sessions lists."""
        self._refresh_active_sessions()
        # Clear timer state cache so update_durations rebuilds properly
        self._last_session_ids.clear()
        self._last_session_state.clear()

    def _refresh_active_sessions(self):
        """Refresh both active sessions lists using cached project data."""
        active = db.get_active_sessions()

        # Use cached project map for O(1) lookups instead of N queries
        project_map = self._get_projects_map()

        regular_sessions = []
        bg_sessions = []

        for session in active:
            project = project_map.get(session.project_name)
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

        # Use batch_update to freeze entire main frame during clear and repopulate
        with batch_update(self.main_frame):
            with batch_update(self.session_list):
                with batch_update(self.bg_session_list):
                    self.session_list.clear()
                    self.bg_session_list.clear()

                    for data in regular_sessions:
                        self.session_list.add_session(**data)

                    for data in bg_sessions:
                        self.bg_session_list.add_session(**data)

    # -------------------------------------------------------------------------
    # Timer update (called every 1 second)
    # -------------------------------------------------------------------------

    def update_durations(self):
        """Update displayed durations and pause states for active sessions."""
        active = db.get_active_sessions()
        current_ids = {str(s.id) for s in active}

        # Detect if session list changed (start/stop occurred externally)
        if current_ids != self._last_session_ids:
            # Session added or removed - do a targeted refresh
            self._refresh_active_sessions()
            self._last_session_ids = current_ids
            self._last_session_state.clear()
            # Rebuild state cache for the new sessions
            for session in active:
                session_id = str(session.id)
                self._last_session_state[session_id] = (
                    session.format_duration(),
                    session.is_paused
                )
            return

        # Session list unchanged - do incremental updates
        for session in active:
            session_id = str(session.id)
            duration = session.format_duration()
            is_paused = session.is_paused

            # Only update UI if state actually changed
            cached = self._last_session_state.get(session_id)
            if cached != (duration, is_paused):
                # Update in both lists (session is only in one, but checks are fast)
                self.session_list.update_duration(session_id, duration)
                self.session_list.update_pause_state(session_id, is_paused)
                self.bg_session_list.update_duration(session_id, duration)
                self.bg_session_list.update_pause_state(session_id, is_paused)
                self._last_session_state[session_id] = (duration, is_paused)

    def start_session(self):
        """Start tracking the selected regular project."""
        project_name = self.project_var.get().strip()
        if not project_name:
            CTkMessagebox(self.app.root, "Warning", "Please enter a project name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(project_name)
        if active:
            CTkMessagebox(self.app.root, "Info", f"'{project_name}' is already being tracked", "info")
            return

        # Use cached project map to check project type
        project_map = self._get_projects_map()
        existing = project_map.get(project_name)
        if existing and existing.is_background:
            CTkMessagebox(self.app.root, "Warning", f"'{project_name}' is a background task, not a project", "warning")
            return

        # Track if this is a new project (for cache invalidation)
        is_new_project = existing is None

        db.start_session(project_name)
        self.project_var.set("")

        if is_new_project:
            # New project created - full refresh to update combos
            self.refresh()
        else:
            # Existing project - only refresh sessions
            self.refresh_sessions()

    def start_background_task(self):
        """Start tracking a background task."""
        task_name = self.bg_task_var.get().strip()
        if not task_name:
            CTkMessagebox(self.app.root, "Warning", "Please enter a task name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(task_name)
        if active:
            CTkMessagebox(self.app.root, "Info", f"'{task_name}' is already being tracked", "info")
            return

        # Use cached project map to check project type
        project_map = self._get_projects_map()
        existing = project_map.get(task_name)

        if existing is None:
            # New background task - create it
            db.create_project(task_name, is_background=True)
            is_new_task = True
        elif not existing.is_background:
            CTkMessagebox(self.app.root, "Warning", f"'{task_name}' is a regular project, not a background task", "warning")
            return
        else:
            is_new_task = False

        db.start_session(task_name)
        self.bg_task_var.set("")

        if is_new_task:
            # New task created - full refresh to update combos
            self.refresh()
        else:
            # Existing task - only refresh sessions
            self.refresh_sessions()

    def _on_stop_session(self, session_id: str):
        """Handle stop button click from session card."""
        session = db.get_session_by_id(int(session_id))
        if session and session.end_time is None:
            db.stop_session(project_name=session.project_name)
            self.refresh_sessions()  # Only sessions changed, not projects

    def _on_toggle_pause(self, session_id: str):
        """Handle pause/resume button click from session card."""
        session_id_int = int(session_id)
        session = db.get_session_by_id(session_id_int)
        if not session or session.end_time is not None:
            return

        if session.is_paused:
            db.resume_session(session_id_int)
        else:
            db.pause_session(session_id_int)

        self.refresh_sessions()  # Only sessions changed, not projects

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
