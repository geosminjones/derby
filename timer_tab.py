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

if TYPE_CHECKING:
    from gui import DerbyApp, TreeviewFrame


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
        # Runtime import to avoid circular dependency
        from gui import TreeviewFrame

        # Main container
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        # Start session section for regular projects
        start_frame = ctk.CTkFrame(top_frame, fg_color=themes.get_colors()["card_bg"])
        start_frame.pack(fill=ctk.X, padx=10, pady=10)

        ctk.CTkLabel(start_frame, text="Start New Project Session", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w")

        project_row = ctk.CTkFrame(start_frame, fg_color="transparent")
        project_row.pack(fill=ctk.X, pady=5)

        ctk.CTkLabel(project_row, text="Project:").pack(side=ctk.LEFT)

        self.project_combo = ctk.CTkComboBox(
            project_row,
            variable=self.project_var,
            width=250
        )
        self.project_combo.pack(side=ctk.LEFT, padx=10)

        start_btn = ctk.CTkButton(project_row, text="Start Tracking", command=self.start_session)
        start_btn.pack(side=ctk.LEFT, padx=5)

        # Active regular sessions section
        ctk.CTkLabel(top_frame, text="Active Project Sessions", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10)

        self.tree_frame = TreeviewFrame(
            top_frame,
            columns=("project", "started", "duration", "actions"),
            headings=["Project", "Started", "Duration", "Actions"],
            widths=[160, 140, 90, 120],
            height=4,
            anchors=['w', 'w', 'w', 'center']
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=5)
        self.tree = self.tree_frame.tree

        # Bind click event for action buttons
        self.tree.bind("<Button-1>", self._on_tree_click)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        # Start session section for background tasks
        bg_start_frame = ctk.CTkFrame(bottom_frame, fg_color=themes.get_colors()["card_bg"])
        bg_start_frame.pack(fill=ctk.X, padx=10, pady=10)

        ctk.CTkLabel(bg_start_frame, text="Start Background Task", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w")

        bg_row = ctk.CTkFrame(bg_start_frame, fg_color="transparent")
        bg_row.pack(fill=ctk.X, pady=5)

        ctk.CTkLabel(bg_row, text="Task:").pack(side=ctk.LEFT)

        self.bg_task_combo = ctk.CTkComboBox(
            bg_row,
            variable=self.bg_task_var,
            width=250
        )
        self.bg_task_combo.pack(side=ctk.LEFT, padx=10)

        bg_start_btn = ctk.CTkButton(bg_row, text="Start Task", command=self.start_background_task)
        bg_start_btn.pack(side=ctk.LEFT, padx=5)

        # Active background tasks section
        ctk.CTkLabel(bottom_frame, text="Active Background Tasks", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10)

        self.bg_tree_frame = TreeviewFrame(
            bottom_frame,
            columns=("project", "started", "duration", "actions"),
            headings=["Task", "Started", "Duration", "Actions"],
            widths=[160, 140, 90, 120],
            height=4,
            anchors=['w', 'w', 'w', 'center']
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=5)
        self.bg_tree = self.bg_tree_frame.tree

        # Bind click event for action buttons
        self.bg_tree.bind("<Button-1>", self._on_bg_tree_click)

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
        """Refresh both active sessions treeviews."""
        # Clear existing from both trees
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Get all active sessions
        active = db.get_active_sessions()

        # Separate into regular and background
        for session in active:
            project = db.get_project(session.project_name)
            is_bg = project.is_background if project else False

            started = session.start_time.strftime("%Y-%m-%d %I:%M:%S %p") if session.start_time else ""

            # Build action text based on pause state
            # Using text labels for clearer clickable areas
            if session.is_paused:
                action_text = "[Stop] [Play]"  # Stop and Play available when paused
            else:
                action_text = "[Stop] [Pause]"  # Stop and Pause available when playing

            if is_bg:
                self.bg_tree_frame.insert(
                    values=(session.project_name, started, session.format_duration(), action_text),
                    iid=str(session.id)
                )
            else:
                self.tree_frame.insert(
                    values=(session.project_name, started, session.format_duration(), action_text),
                    iid=str(session.id)
                )

    def update_durations(self):
        """Update displayed durations and action buttons for active sessions."""
        active = db.get_active_sessions()
        active_dict = {str(s.id): s for s in active}

        # Update regular sessions tree
        for item in self.tree_frame.get_children():
            if item in active_dict:
                session = active_dict[item]
                self.tree_frame.set(item, "duration", session.format_duration())
                # Update action buttons based on pause state
                if session.is_paused:
                    self.tree_frame.set(item, "actions", "[Stop] [Play]")
                else:
                    self.tree_frame.set(item, "actions", "[Stop] [Pause]")

        # Update background tasks tree
        for item in self.bg_tree_frame.get_children():
            if item in active_dict:
                session = active_dict[item]
                self.bg_tree_frame.set(item, "duration", session.format_duration())
                # Update action buttons based on pause state
                if session.is_paused:
                    self.bg_tree_frame.set(item, "actions", "[Stop] [Play]")
                else:
                    self.bg_tree_frame.set(item, "actions", "[Stop] [Pause]")

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

    def _on_tree_click(self, event):
        """Handle clicks on the regular projects treeview for action buttons."""
        self._handle_action_click(event, self.tree, is_background=False)

    def _on_bg_tree_click(self, event):
        """Handle clicks on the background tasks treeview for action buttons."""
        self._handle_action_click(event, self.bg_tree, is_background=True)

    def _handle_action_click(self, event, tree, is_background: bool):
        """Handle action button clicks in treeview."""
        # Identify the row and column clicked
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = tree.identify_column(event.x)
        item = tree.identify_row(event.y)

        if not item:
            return

        # Check if Actions column was clicked (column #4)
        if column != "#4":
            return

        # Get session ID from the item
        session_id = int(item)

        # Get the action text to determine current state
        # Format: "[Stop] [Play]" or "[Stop] [Pause]"
        action_text = tree.set(item, "actions")

        # Get column bbox to calculate relative position
        bbox = tree.bbox(item, column)
        if not bbox:
            # If bbox is not available, default to pause/play toggle
            self._toggle_pause_action(session_id)
            return

        # bbox returns (x, y, width, height)
        cell_x, _, cell_width, _ = bbox
        relative_x = event.x - cell_x

        # The action text is "[Stop] [Play]" or "[Stop] [Pause]"
        # [Stop] takes roughly first half, [Play]/[Pause] takes second half
        if relative_x < cell_width * 0.5:
            # Stop action (left side)
            self._stop_session_action(session_id)
        else:
            # Pause or Play action (right side)
            self._toggle_pause_action(session_id)

    def _stop_session_action(self, session_id: int):
        """Stop the session with the given ID."""
        # Get the session to find project name
        active = db.get_active_sessions()
        session = next((s for s in active if s.id == session_id), None)
        if session:
            db.stop_session(project_name=session.project_name)
            self.refresh()

    def _toggle_pause_action(self, session_id: int):
        """Toggle pause state for the session."""
        # Get current session state
        active = db.get_active_sessions()
        session = next((s for s in active if s.id == session_id), None)
        if not session:
            return

        if session.is_paused:
            db.resume_session(session_id)
        else:
            db.pause_session(session_id)

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
