#!/usr/bin/env python3
"""
gui.py - Graphical user interface for Derby

A CustomTkinter-based GUI that provides the same functionality as the CLI
but with a visual interface and live timer updates.

Run with: python gui.py
"""

import sqlite3
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional

import db
from models import Session, Project, parse_duration_string


# Priority labels for display
PRIORITY_LABELS = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
    5: "Very Low"
}

# Theme colors - Navy blue dark theme
COLORS = {
    "bg_dark": "#1a1a2e",       # Main background
    "bg_medium": "#130b17",     # Secondary/card background
    "bg_light": "#362040",      # Lighter accent background
    "text_primary": "#ffffff",  # Primary text
    "text_secondary": "#a0a0a0",  # Secondary/muted text
    "separator": "#3a3a5a",     # Treeview separator rows
    "card_bg": "#362040",       # Section card background (intermediate purple)
    "container_bg": "#281b2e",  # Container frame background (dark purple)
}

# Font configuration
FONT_FAMILY = "Inter"

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DerbyApp:
    """Main application window."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Derby")
        self.root.geometry("850x550")
        self.root.minsize(700, 450)
        self.root.configure(fg_color=COLORS["bg_dark"])

        # Initialize database
        db.init_database()

        # Status bar variable
        self.status_var = ctk.StringVar(value="Ready")

        # Build UI components
        self._create_menu()
        self._create_tabview()
        self._create_status_bar()

        # Start timer update loop
        self._schedule_timer_update()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_menu(self):
        """Create application menu bar using tkinter Menu (CustomTkinter doesn't have native menu)."""
        menu_style = {
            "bg": COLORS["bg_dark"],
            "fg": COLORS["text_primary"],
            "activebackground": COLORS["bg_light"],
            "activeforeground": COLORS["text_primary"],
            "font": (FONT_FAMILY, 10)
        }
        menubar = tk.Menu(self.root, **menu_style)
        self.root.configure(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export to CSV...", command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Session menu
        session_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        menubar.add_cascade(label="Session", menu=session_menu)
        session_menu.add_command(label="Log Manual Entry...", command=self._show_log_dialog)
        session_menu.add_command(label="Stop All", command=self._stop_all)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, **menu_style)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_tabview(self):
        """Create tabbed interface with tab switcher inside the main container."""
        # Main container frame (the gray box)
        self.main_container = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"])
        self.main_container.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Header row with tab switcher and Stop All button
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill=ctk.X, padx=10, pady=(10, 5))

        # Tab switcher (segmented button) on the left
        self.tab_var = ctk.StringVar(value="Timer")
        self.tab_switcher = ctk.CTkSegmentedButton(
            header_frame,
            values=["Timer", "History", "Summary", "Projects"],
            variable=self.tab_var,
            command=self._on_tab_change,
            fg_color=COLORS["container_bg"],
            selected_color=COLORS["bg_light"],
            unselected_color=COLORS["container_bg"]
        )
        self.tab_switcher.pack(side=ctk.LEFT)

        # Stop All button on the right
        self.stop_all_btn = ctk.CTkButton(header_frame, text="Stop All", command=self._stop_all, width=100)
        self.stop_all_btn.pack(side=ctk.RIGHT)

        # Content frame for tab contents
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill=ctk.BOTH, expand=True)

        # Create individual tab frames (all hidden initially except Timer)
        self.tab_frames = {}
        for tab_name in ["Timer", "History", "Summary", "Projects"]:
            frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            self.tab_frames[tab_name] = frame

        # Show Timer tab by default
        self.tab_frames["Timer"].pack(fill=ctk.BOTH, expand=True)
        self.current_tab = "Timer"

        # Create tab content
        self.timer_tab = TimerTab(self.tab_frames["Timer"], self)
        self.history_tab = HistoryTab(self.tab_frames["History"], self)
        self.summary_tab = SummaryTab(self.tab_frames["Summary"], self)
        self.projects_tab = ProjectsTab(self.tab_frames["Projects"], self)

    def _create_status_bar(self):
        """Create status bar at bottom of window."""
        status_frame = ctk.CTkFrame(self.root, height=30, fg_color=COLORS["bg_dark"])
        status_frame.pack(fill=ctk.X, side=ctk.BOTTOM)
        status_frame.pack_propagate(False)

        status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            anchor="w"
        )
        status_label.pack(fill=ctk.X, padx=10, pady=5)

    def _schedule_timer_update(self):
        """Schedule periodic timer updates."""
        self._update_timers()
        self.root.after(1000, self._schedule_timer_update)

    def _update_timers(self):
        """Update all active session durations."""
        # Update timer tab
        self.timer_tab.update_durations()

        # Update status bar
        active = db.get_active_sessions()
        if not active:
            self.status_var.set("Idle - No active sessions")
        elif len(active) == 1:
            s = active[0]
            paused_indicator = " [PAUSED]" if s.is_paused else ""
            self.status_var.set(f"Tracking: {s.project_name} ({s.format_duration()}){paused_indicator}")
        else:
            total = sum(s.duration_seconds for s in active)
            paused_count = sum(1 for s in active if s.is_paused)
            h = total // 3600
            m = (total % 3600) // 60
            sec = total % 60
            paused_indicator = f" [{paused_count} paused]" if paused_count > 0 else ""
            self.status_var.set(f"Tracking: {len(active)} sessions (Total: {h}h {m:02d}m {sec:02d}s){paused_indicator}")

    def _on_tab_change(self, tab_name: str = None):
        """Switch to a different tab and refresh its data."""
        if tab_name is None:
            tab_name = self.tab_var.get()

        # Hide current tab
        if hasattr(self, 'current_tab') and self.current_tab in self.tab_frames:
            self.tab_frames[self.current_tab].pack_forget()

        # Show new tab
        self.tab_frames[tab_name].pack(fill=ctk.BOTH, expand=True)
        self.current_tab = tab_name

        # Refresh the tab data
        if tab_name == "Timer":
            self.timer_tab.refresh()
        elif tab_name == "History":
            self.history_tab.refresh()
        elif tab_name == "Summary":
            self.summary_tab.refresh()
        elif tab_name == "Projects":
            self.projects_tab.refresh()

    def _export_csv(self):
        """Export sessions to CSV file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="timetrack_export.csv"
        )
        if filepath:
            db.export_sessions_csv(filepath)
            CTkMessagebox(self.root, "Export Complete", f"Exported to:\n{filepath}", "info")

    def _stop_all(self):
        """Stop all active sessions."""
        active = db.get_active_sessions()
        if not active:
            CTkMessagebox(self.root, "Info", "No active sessions to stop", "info")
            return

        if CTkConfirmDialog(self.root, "Confirm", f"Stop {len(active)} active session(s)?").get_result():
            db.stop_all_sessions()
            self.timer_tab.refresh()

    def _show_log_dialog(self):
        """Show dialog to log manual entry."""
        LogSessionDialog(self.root, self)

    def _show_about(self):
        """Show about dialog."""
        CTkMessagebox(
            self.root,
            "About Derby",
            "Derby v1.0\n\n"
            "A simple, local-first time tracking application.\n\n"
            "Data stored in: ~/.timetrack/timetrack.db",
            "info"
        )

    def _on_close(self):
        """Handle window close."""
        self.root.destroy()

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


class TreeviewFrame(ctk.CTkFrame):
    """A frame containing a treeview with scrollbar (using tkinter Treeview)."""

    def __init__(self, parent, columns, headings, widths, height=8, show_scrollbar=True, anchors=None):
        super().__init__(parent, fg_color=COLORS["bg_dark"])

        # Create treeview container
        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill=ctk.BOTH, expand=True)

        # Create treeview (using tkinter since CustomTkinter doesn't have treeview)
        self.tree = tk.ttk.Treeview(tree_container, columns=columns, show="headings", height=height)

        # Configure style for dark theme
        style = tk.ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
            background=COLORS["bg_medium"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_medium"],
            bordercolor=COLORS["bg_dark"],
            font=(FONT_FAMILY, 10),
            rowheight=25
        )
        style.configure("Treeview.Heading",
            background=COLORS["bg_light"],
            foreground=COLORS["text_primary"],
            font=(FONT_FAMILY, 10, "bold")
        )
        style.map("Treeview",
            background=[("selected", COLORS["bg_light"])],
            foreground=[("selected", COLORS["text_primary"])]
        )
        style.configure("Vertical.TScrollbar",
            background=COLORS["bg_medium"],
            troughcolor=COLORS["bg_dark"],
            arrowcolor=COLORS["text_primary"]
        )
        style.map("Vertical.TScrollbar",
            background=[("disabled", COLORS["bg_dark"]), ("!disabled", COLORS["bg_medium"])],
            troughcolor=[("disabled", COLORS["bg_dark"]), ("!disabled", COLORS["bg_dark"])]
        )

        # Default anchors to 'w' (left) if not provided
        if anchors is None:
            anchors = ['w'] * len(columns)

        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            self.tree.heading(col, text=heading, anchor='center')
            self.tree.column(col, width=width, anchor=anchor)

        if show_scrollbar:
            scrollbar = tk.ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar.set)
            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.tree.pack(fill=tk.BOTH, expand=True)

    def clear(self):
        """Clear all items from the treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

    def insert(self, values, iid=None, tags=None):
        """Insert a row into the treeview."""
        if tags:
            return self.tree.insert("", tk.END, iid=iid, values=values, tags=tags)
        return self.tree.insert("", tk.END, iid=iid, values=values)

    def get_selection(self):
        """Get the current selection."""
        return self.tree.selection()

    def set(self, item, column, value):
        """Set a value in a cell."""
        self.tree.set(item, column, value)

    def get_children(self):
        """Get all children."""
        return self.tree.get_children()

    def configure_tag(self, tag_name, **options):
        """Configure a tag."""
        self.tree.tag_configure(tag_name, **options)


class TimerTab:
    """Timer tab for starting/stopping sessions."""

    def __init__(self, parent, app: DerbyApp):
        self.frame = parent
        self.app = app
        self.project_var = ctk.StringVar()
        self.bg_task_var = ctk.StringVar()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the timer tab UI with split view for projects and background tasks."""
        # Main container
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["container_bg"])
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        # Start session section for regular projects
        start_frame = ctk.CTkFrame(top_frame, fg_color=COLORS["card_bg"])
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
        bottom_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["container_bg"])
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        # Start session section for background tasks
        bg_start_frame = ctk.CTkFrame(bottom_frame, fg_color=COLORS["card_bg"])
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


class HistoryTab:
    """History tab for viewing past sessions."""

    def __init__(self, parent, app: DerbyApp):
        self.frame = parent
        self.app = app
        self.project_filter = ctk.StringVar(value="All")
        self.period_filter = ctk.StringVar(value="All")
        self.limit_var = ctk.StringVar(value="50")
        self._build_ui()

    def _build_ui(self):
        """Build the history tab UI."""
        # Filter section
        filter_frame = ctk.CTkFrame(self.frame, fg_color=COLORS["card_bg"])
        filter_frame.pack(fill=ctk.X, padx=10, pady=10)

        # First row of filters
        filter_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_row.pack(fill=ctk.X, pady=5)

        ctk.CTkLabel(filter_row, text="Project:").pack(side=ctk.LEFT)
        self.project_combo = ctk.CTkComboBox(
            filter_row,
            variable=self.project_filter,
            width=150,
            command=lambda _: self.refresh()
        )
        self.project_combo.pack(side=ctk.LEFT, padx=(5, 15))

        ctk.CTkLabel(filter_row, text="Period:").pack(side=ctk.LEFT)
        period_combo = ctk.CTkComboBox(
            filter_row,
            variable=self.period_filter,
            values=["All", "Today", "This Week"],
            width=120,
            command=lambda _: self.refresh()
        )
        period_combo.pack(side=ctk.LEFT, padx=(5, 15))

        ctk.CTkLabel(filter_row, text="Limit:").pack(side=ctk.LEFT)
        limit_entry = ctk.CTkEntry(
            filter_row,
            textvariable=self.limit_var,
            width=60
        )
        limit_entry.pack(side=ctk.LEFT, padx=5)

        refresh_btn = ctk.CTkButton(filter_row, text="Refresh", command=self.refresh)
        refresh_btn.pack(side=ctk.LEFT, padx=10)

        # Sessions treeview
        self.tree_frame = TreeviewFrame(
            self.frame,
            columns=("id", "date", "project", "duration", "notes"),
            headings=["ID", "Date", "Project", "Duration", "Notes"],
            widths=[50, 100, 150, 100, 300],
            height=12
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=5)
        self.tree = self.tree_frame.tree

        # Button row
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=10, pady=10)

        delete_btn = ctk.CTkButton(btn_frame, text="Delete Selected", command=self.delete_selected)
        delete_btn.pack(side=ctk.LEFT, padx=5)

        export_btn = ctk.CTkButton(btn_frame, text="Export to CSV...", command=self.app._export_csv)
        export_btn.pack(side=ctk.LEFT, padx=5)

    def refresh(self):
        """Refresh sessions list."""
        # Update project filter options
        projects = db.list_projects()
        project_names = ["All"] + [p.name for p in projects]
        self.project_combo.configure(values=project_names)

        # Clear existing
        self.tree_frame.clear()

        # Calculate date filters
        start_date = None
        end_date = None
        period = self.period_filter.get()

        if period == "Today":
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period == "This Week":
            now = datetime.now()
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=now.weekday())
            end_date = start_date + timedelta(days=7)

        # Get project filter
        project = None
        if self.project_filter.get() != "All":
            project = self.project_filter.get()

        # Get limit
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 50

        # Query sessions
        sessions = db.get_sessions(
            project_name=project,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        # Populate tree
        for session in sessions:
            date_str = session.start_time.strftime("%Y-%m-%d") if session.start_time else ""
            notes_preview = session.notes[:50] + "..." if len(session.notes) > 50 else session.notes
            self.tree_frame.insert(
                values=(session.id, date_str, session.project_name, session.format_duration(), notes_preview),
                iid=str(session.id)
            )

    def delete_selected(self):
        """Delete the selected session."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a session to delete", "warning")
            return

        item = selection[0]
        session_id = int(self.tree.set(item, "id"))
        project = self.tree.set(item, "project")

        if CTkConfirmDialog(self.app.root, "Confirm Delete", f"Delete session #{session_id} ({project})?").get_result():
            db.delete_session(session_id)
            self.refresh()


class SummaryTab:
    """Summary tab for time aggregations with split view for projects and background tasks."""

    # Day abbreviations for column headers
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def __init__(self, parent, app: DerbyApp):
        self.frame = parent
        self.app = app
        self.period_var = ctk.StringVar(value="today")
        self.sort_var = ctk.StringVar(value="priority")
        self.group_var = ctk.BooleanVar(value=False)
        self.current_view = "standard"  # "standard", "weekly", or "monthly"
        self._build_ui()

    def _build_ui(self):
        """Build the summary tab UI with split view."""
        # Period selection
        period_frame = ctk.CTkFrame(self.frame, fg_color=COLORS["card_bg"])
        period_frame.pack(fill=ctk.X, padx=10, pady=5)

        ctk.CTkLabel(period_frame, text="Period:").pack(side=ctk.LEFT, padx=5)

        for text, value in [("Today", "today"), ("This Week", "week"), ("This Month", "month"), ("Last Month", "last_month"), ("All Time", "all")]:
            rb = ctk.CTkRadioButton(
                period_frame,
                text=text,
                variable=self.period_var,
                value=value,
                command=self.refresh
            )
            rb.pack(side=ctk.LEFT, padx=10)

        # Sort selection
        sort_frame = ctk.CTkFrame(self.frame, fg_color=COLORS["card_bg"])
        sort_frame.pack(fill=ctk.X, padx=10, pady=5)

        ctk.CTkLabel(sort_frame, text="Sort:").pack(side=ctk.LEFT, padx=5)

        for text, value in [("Priority", "priority"), ("Tag", "tag")]:
            rb = ctk.CTkRadioButton(
                sort_frame,
                text=text,
                variable=self.sort_var,
                value=value,
                command=self.refresh
            )
            rb.pack(side=ctk.LEFT, padx=10)

        # Group checkbox on right side
        group_check = ctk.CTkCheckBox(
            sort_frame,
            text="Group?",
            variable=self.group_var,
            command=self.refresh
        )
        group_check.pack(side=ctk.RIGHT, padx=10)

        # Main content area
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects Summary
        # =====================================================================
        top_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["container_bg"])
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        ctk.CTkLabel(top_frame, text="Projects", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.tree_container = ctk.CTkFrame(top_frame, fg_color="transparent")
        self.tree_container.pack(fill=ctk.BOTH, expand=True, padx=10)

        # Create standard view treeview for projects
        self._create_standard_treeview()

        # Project total label
        self.project_total_var = ctk.StringVar(value="Projects Total: 0h 00m")
        project_total_label = ctk.CTkLabel(top_frame, textvariable=self.project_total_var, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"))
        project_total_label.pack(pady=3)

        # =====================================================================
        # BOTTOM HALF: Background Tasks Summary
        # =====================================================================
        bottom_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["container_bg"])
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        ctk.CTkLabel(bottom_frame, text="Background Tasks", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.bg_tree_container = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        self.bg_tree_container.pack(fill=ctk.BOTH, expand=True, padx=10)

        # Create treeview for background tasks (simpler - no priority column)
        self._create_bg_standard_treeview()

        # Background tasks total label
        self.bg_total_var = ctk.StringVar(value="Tasks Total: 0h 00m")
        bg_total_label = ctk.CTkLabel(bottom_frame, textvariable=self.bg_total_var, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"))
        bg_total_label.pack(pady=3)

        # Combined total at bottom
        self.total_var = ctk.StringVar(value="Combined Total: 0h 00m")
        total_label = ctk.CTkLabel(self.frame, textvariable=self.total_var, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        total_label.pack(pady=5)

    def _create_standard_treeview(self):
        """Create the standard (non-weekly) treeview for projects."""
        self.tree_frame = TreeviewFrame(
            self.tree_container,
            columns=("project", "priority", "time", "hours"),
            headings=["Project", "Priority", "Time", "Hours"],
            widths=[200, 100, 100, 80],
            height=5
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.tree = self.tree_frame.tree
        self.current_view = "standard"

    def _create_bg_standard_treeview(self):
        """Create the standard treeview for background tasks (no priority)."""
        self.bg_tree_frame = TreeviewFrame(
            self.bg_tree_container,
            columns=("task", "time", "hours"),
            headings=["Task", "Time", "Hours"],
            widths=[250, 120, 100],
            height=5
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.bg_tree = self.bg_tree_frame.tree
        self.bg_current_view = "standard"

    def _create_weekly_treeview(self, week_start: datetime):
        """Create the weekly view treeview with day columns for projects."""
        # Build column headers with dates (single line: "Mon 1/6")
        day_columns = []
        day_headings = ["Project"]
        day_widths = [120]

        for i in range(7):
            day_date = week_start + timedelta(days=i)
            col_id = f"day{i}"
            day_columns.append(col_id)
            day_headings.append(f"{self.DAY_NAMES[i]} {day_date.day}")
            day_widths.append(55)

        columns = ["project"] + day_columns + ["total"]
        day_headings.append("Total")
        day_widths.append(60)

        self.tree_frame = TreeviewFrame(
            self.tree_container,
            columns=columns,
            headings=day_headings,
            widths=day_widths,
            height=5
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.tree = self.tree_frame.tree
        self.current_view = "weekly"

    def _create_bg_weekly_treeview(self, week_start: datetime):
        """Create the weekly view treeview for background tasks."""
        day_columns = []
        day_headings = ["Task"]
        day_widths = [120]

        for i in range(7):
            day_date = week_start + timedelta(days=i)
            col_id = f"day{i}"
            day_columns.append(col_id)
            day_headings.append(f"{self.DAY_NAMES[i]} {day_date.day}")
            day_widths.append(55)

        columns = ["task"] + day_columns + ["total"]
        day_headings.append("Total")
        day_widths.append(60)

        self.bg_tree_frame = TreeviewFrame(
            self.bg_tree_container,
            columns=columns,
            headings=day_headings,
            widths=day_widths,
            height=5
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.bg_tree = self.bg_tree_frame.tree
        self.bg_current_view = "weekly"

    def _create_monthly_treeview(self, month_start: datetime):
        """Create the monthly view treeview with 5-day period columns for projects."""
        import calendar

        # Calculate the number of days in the month
        year = month_start.year
        month = month_start.month
        days_in_month = calendar.monthrange(year, month)[1]

        # Build column headers for 5-day periods
        period_columns = []
        period_headings = ["Project"]
        period_widths = [120]
        period_starts = [1, 6, 11, 16, 21, 26]

        for i, start_day in enumerate(period_starts):
            col_id = f"period{i}"
            period_columns.append(col_id)
            if i < 5:
                end_day = start_day + 4
                header = f"{start_day}-{end_day}"
            else:
                header = f"{start_day}-{days_in_month}"
            period_headings.append(header)
            period_widths.append(55)

        columns = ["project"] + period_columns + ["total"]
        period_headings.append("Total")
        period_widths.append(60)

        self.tree_frame = TreeviewFrame(
            self.tree_container,
            columns=columns,
            headings=period_headings,
            widths=period_widths,
            height=5
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.tree = self.tree_frame.tree
        self.current_view = "monthly"

    def _create_bg_monthly_treeview(self, month_start: datetime):
        """Create the monthly view treeview for background tasks."""
        import calendar

        year = month_start.year
        month = month_start.month
        days_in_month = calendar.monthrange(year, month)[1]

        period_columns = []
        period_headings = ["Task"]
        period_widths = [120]
        period_starts = [1, 6, 11, 16, 21, 26]

        for i, start_day in enumerate(period_starts):
            col_id = f"period{i}"
            period_columns.append(col_id)
            if i < 5:
                end_day = start_day + 4
                header = f"{start_day}-{end_day}"
            else:
                header = f"{start_day}-{days_in_month}"
            period_headings.append(header)
            period_widths.append(55)

        columns = ["task"] + period_columns + ["total"]
        period_headings.append("Total")
        period_widths.append(60)

        self.bg_tree_frame = TreeviewFrame(
            self.bg_tree_container,
            columns=columns,
            headings=period_headings,
            widths=period_widths,
            height=5
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True)
        self.bg_tree = self.bg_tree_frame.tree
        self.bg_current_view = "monthly"

    def _destroy_treeview(self):
        """Destroy the current project treeview."""
        if hasattr(self, 'tree_frame'):
            self.tree_frame.destroy()

    def _destroy_bg_treeview(self):
        """Destroy the current background task treeview."""
        if hasattr(self, 'bg_tree_frame'):
            self.bg_tree_frame.destroy()

    def _format_time_short(self, seconds: int) -> str:
        """Format seconds as short time string (e.g., '1:30' for 1h 30m, '0:45' for 45m)."""
        if seconds == 0:
            return "-"
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}:{mins:02d}"

    def refresh(self):
        """Refresh summary data."""
        import calendar
        period = self.period_var.get()

        # Calculate date range
        start_date = None
        end_date = None

        if period == "today":
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period == "week":
            now = datetime.now()
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = start_date - timedelta(days=now.weekday())
            end_date = start_date + timedelta(days=7)
        elif period == "month":
            now = datetime.now()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            end_date = start_date + timedelta(days=days_in_month)
        elif period == "last_month":
            now = datetime.now()
            first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_of_prev_month = first_of_this_month - timedelta(days=1)
            start_date = last_day_of_prev_month.replace(day=1)
            days_in_month = calendar.monthrange(start_date.year, start_date.month)[1]
            end_date = start_date + timedelta(days=days_in_month)

        # Switch view type if needed
        if period == "week":
            if self.current_view != "weekly":
                self._destroy_treeview()
                self._create_weekly_treeview(start_date)
            if not hasattr(self, 'bg_current_view') or self.bg_current_view != "weekly":
                self._destroy_bg_treeview()
                self._create_bg_weekly_treeview(start_date)
            self._refresh_weekly(start_date, end_date)
        elif period in ("month", "last_month"):
            self._destroy_treeview()
            self._create_monthly_treeview(start_date)
            self._destroy_bg_treeview()
            self._create_bg_monthly_treeview(start_date)
            self._refresh_monthly(start_date, end_date)
        else:
            if self.current_view != "standard":
                self._destroy_treeview()
                self._create_standard_treeview()
            if not hasattr(self, 'bg_current_view') or self.bg_current_view != "standard":
                self._destroy_bg_treeview()
                self._create_bg_standard_treeview()
            self._refresh_standard(start_date, end_date)

    def _refresh_standard(self, start_date, end_date):
        """Refresh with standard (non-weekly) view."""
        sort_by = self.sort_var.get()
        group_by = self.group_var.get()

        # Clear existing
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Configure separator tag (thin divider line)
        self.tree_frame.configure_tag("separator", background=COLORS["separator"])

        # Update column headers based on sort mode and group mode
        if group_by:
            if sort_by == "tag":
                self.tree.heading("project", text="Tag")
            else:
                self.tree.heading("project", text="Priority")
            self.tree.heading("priority", text="")
        else:
            self.tree.heading("project", text="Project")
            if sort_by == "tag":
                self.tree.heading("priority", text="Tag")
            else:
                self.tree.heading("priority", text="Priority")

        project_total_seconds = 0

        if sort_by == "priority":
            # Get project summary (regular projects only)
            project_summary = db.get_summary_with_priority(start_date=start_date, end_date=end_date, is_background=False)

            if group_by:
                # Aggregate by priority level
                priority_totals: dict[int, int] = {}
                for project_name, data in project_summary.items():
                    seconds = data["seconds"]
                    priority = data["priority"]
                    project_total_seconds += seconds
                    priority_totals[priority] = priority_totals.get(priority, 0) + seconds

                # Display one row per priority level
                for priority in sorted(priority_totals.keys()):
                    seconds = priority_totals[priority]
                    hours = seconds // 3600
                    mins = (seconds % 3600) // 60
                    secs = seconds % 60
                    time_str = f"{hours}:{mins:02d}:{secs:02d}"
                    hours_decimal = round(seconds / 3600, 2)

                    priority_label = f"{priority} ({PRIORITY_LABELS.get(priority, 'Unknown')})"

                    self.tree_frame.insert(values=(priority_label, "", time_str, hours_decimal))
            else:
                # Populate project tree with separators between priority groups
                last_priority = None
                for project_name, data in project_summary.items():
                    seconds = data["seconds"]
                    priority = data["priority"]
                    project_total_seconds += seconds

                    # Add separator row between priority groups
                    if last_priority is not None and priority != last_priority:
                        self.tree_frame.insert(values=("", "", "", ""), tags=("separator",))
                    last_priority = priority

                    hours = seconds // 3600
                    mins = (seconds % 3600) // 60
                    secs = seconds % 60
                    time_str = f"{hours}:{mins:02d}:{secs:02d}"
                    hours_decimal = round(seconds / 3600, 2)

                    priority_label = f"{priority} ({PRIORITY_LABELS.get(priority, 'Unknown')})"

                    self.tree_frame.insert(values=(project_name, priority_label, time_str, hours_decimal))
        else:
            # Tag-based sorting
            if start_date is None:
                start_date = datetime(1970, 1, 1)
            if end_date is None:
                end_date = datetime(2100, 1, 1)

            tag_summary = db.get_summary_by_tag(start_date=start_date, end_date=end_date)

            if group_by:
                # Display one row per tag
                seen_projects = set()
                for tag_name, tag_data in tag_summary.items():
                    tag_seconds = 0
                    for project_name, pdata in tag_data["projects"].items():
                        if project_name not in seen_projects:
                            project_total_seconds += pdata["total"]
                            seen_projects.add(project_name)
                        tag_seconds += pdata["total"]

                    hours = tag_seconds // 3600
                    mins = (tag_seconds % 3600) // 60
                    secs = tag_seconds % 60
                    time_str = f"{hours}:{mins:02d}:{secs:02d}"
                    hours_decimal = round(tag_seconds / 3600, 2)

                    self.tree_frame.insert(values=(tag_name, "", time_str, hours_decimal))
            else:
                seen_projects = set()

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        self.tree_frame.insert(values=("", "", "", ""), tags=("separator",))
                    last_tag = tag_name

                    for project_name, pdata in tag_data["projects"].items():
                        seconds = pdata["total"]

                        if project_name not in seen_projects:
                            project_total_seconds += seconds
                            seen_projects.add(project_name)

                        hours = seconds // 3600
                        mins = (seconds % 3600) // 60
                        secs = seconds % 60
                        time_str = f"{hours}:{mins:02d}:{secs:02d}"
                        hours_decimal = round(seconds / 3600, 2)

                        display_name = project_name + " *" if pdata["has_multiple_tags"] else project_name

                        self.tree_frame.insert(values=(display_name, tag_name, time_str, hours_decimal))

        # Get background task summary
        bg_summary = db.get_summary_with_priority(start_date=start_date, end_date=end_date, is_background=True)

        # Populate background task tree
        bg_total_seconds = 0
        for task_name, data in bg_summary.items():
            seconds = data["seconds"]
            bg_total_seconds += seconds

            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = seconds % 60
            time_str = f"{hours}:{mins:02d}:{secs:02d}"
            hours_decimal = round(seconds / 3600, 2)

            self.bg_tree_frame.insert(values=(task_name, time_str, hours_decimal))

        # Update totals
        proj_h = project_total_seconds // 3600
        proj_m = (project_total_seconds % 3600) // 60
        self.project_total_var.set(f"Projects Total: {proj_h}h {proj_m:02d}m ({round(project_total_seconds/3600, 2)} hours)")

        bg_h = bg_total_seconds // 3600
        bg_m = (bg_total_seconds % 3600) // 60
        self.bg_total_var.set(f"Tasks Total: {bg_h}h {bg_m:02d}m ({round(bg_total_seconds/3600, 2)} hours)")

        combined = project_total_seconds + bg_total_seconds
        comb_h = combined // 3600
        comb_m = (combined % 3600) // 60
        self.total_var.set(f"Combined Total: {comb_h}h {comb_m:02d}m ({round(combined/3600, 2)} hours)")

    def _refresh_weekly(self, start_date: datetime, end_date: datetime):
        """Refresh with weekly day-by-day view."""
        sort_by = self.sort_var.get()
        group_by = self.group_var.get()

        # Clear existing
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Configure separator and total row tags
        self.tree_frame.configure_tag("separator", background=COLORS["separator"])
        self.tree_frame.configure_tag("total_row", font=(FONT_FAMILY, 10, "bold"))

        # Update column header based on group mode
        if group_by:
            if sort_by == "tag":
                self.tree.heading("project", text="Tag")
            else:
                self.tree.heading("project", text="Priority")
        else:
            self.tree.heading("project", text="Project")

        # Build date strings for each day of the week
        day_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        project_total_seconds = 0
        project_daily_totals = [0] * 7

        if sort_by == "priority":
            # Get per-day summary for projects
            project_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=False)

            if group_by:
                # Aggregate by priority level
                priority_daily_totals: dict[int, list[int]] = {}
                priority_totals: dict[int, int] = {}

                for project_name, data in project_summary.items():
                    priority = data["priority"]
                    project_total_seconds += data["total"]

                    if priority not in priority_daily_totals:
                        priority_daily_totals[priority] = [0] * 7
                        priority_totals[priority] = 0

                    priority_totals[priority] += data["total"]
                    for i, date_str in enumerate(day_dates):
                        seconds = data["days"].get(date_str, 0)
                        priority_daily_totals[priority][i] += seconds
                        project_daily_totals[i] += seconds

                # Display one row per priority level
                for priority in sorted(priority_daily_totals.keys()):
                    day_values = [self._format_time_short(s) for s in priority_daily_totals[priority]]
                    total_str = self._format_time_short(priority_totals[priority])
                    priority_label = f"{priority} ({PRIORITY_LABELS.get(priority, 'Unknown')})"

                    self.tree_frame.insert(values=(priority_label, *day_values, total_str))
            else:
                last_priority = None

                for project_name, data in project_summary.items():
                    project_total_seconds += data["total"]
                    priority = data["priority"]

                    if last_priority is not None and priority != last_priority:
                        self.tree_frame.insert(values=("", "", "", "", "", "", "", "", ""), tags=("separator",))
                    last_priority = priority

                    day_values = []
                    for i, date_str in enumerate(day_dates):
                        seconds = data["days"].get(date_str, 0)
                        project_daily_totals[i] += seconds
                        day_values.append(self._format_time_short(seconds))

                    total_str = self._format_time_short(data["total"])

                    self.tree_frame.insert(values=(project_name, *day_values, total_str))
        else:
            # Tag-based sorting
            tag_summary = db.get_summary_by_tag(start_date=start_date, end_date=end_date)

            if group_by:
                seen_projects = set()
                project_daily_counted = {}

                for tag_name, tag_data in tag_summary.items():
                    tag_daily_totals = [0] * 7
                    tag_total = 0

                    for project_name, pdata in tag_data["projects"].items():
                        tag_total += pdata["total"]
                        for i, date_str in enumerate(day_dates):
                            seconds = pdata["days"].get(date_str, 0)
                            tag_daily_totals[i] += seconds

                            if project_name not in project_daily_counted:
                                project_daily_counted[project_name] = [False] * 7
                            if not project_daily_counted[project_name][i]:
                                project_daily_totals[i] += seconds
                                project_daily_counted[project_name][i] = True

                        if project_name not in seen_projects:
                            project_total_seconds += pdata["total"]
                            seen_projects.add(project_name)

                    day_values = [self._format_time_short(s) for s in tag_daily_totals]
                    total_str = self._format_time_short(tag_total)

                    self.tree_frame.insert(values=(tag_name, *day_values, total_str))
            else:
                seen_projects = set()
                project_daily_counted = {}

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        self.tree_frame.insert(values=("", "", "", "", "", "", "", "", ""), tags=("separator",))
                    last_tag = tag_name

                    for project_name, pdata in tag_data["projects"].items():
                        day_values = []
                        for i, date_str in enumerate(day_dates):
                            seconds = pdata["days"].get(date_str, 0)
                            if project_name not in project_daily_counted:
                                project_daily_counted[project_name] = [False] * 7
                            if not project_daily_counted[project_name][i]:
                                project_daily_totals[i] += seconds
                                project_daily_counted[project_name][i] = True
                            day_values.append(self._format_time_short(seconds))

                        if project_name not in seen_projects:
                            project_total_seconds += pdata["total"]
                            seen_projects.add(project_name)

                        total_str = self._format_time_short(pdata["total"])

                        display_name = project_name + " *" if pdata["has_multiple_tags"] else project_name

                        self.tree_frame.insert(values=(display_name, *day_values, total_str))

        # Add project totals row
        project_daily_total_values = [self._format_time_short(s) for s in project_daily_totals]
        project_total_str = self._format_time_short(project_total_seconds)

        self.tree_frame.insert(values=("TOTAL", *project_daily_total_values, project_total_str), tags=("total_row",))

        # Get per-day summary for background tasks
        bg_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=True)

        bg_total_seconds = 0
        bg_daily_totals = [0] * 7

        for task_name, data in bg_summary.items():
            bg_total_seconds += data["total"]

            day_values = []
            for i, date_str in enumerate(day_dates):
                seconds = data["days"].get(date_str, 0)
                bg_daily_totals[i] += seconds
                day_values.append(self._format_time_short(seconds))

            total_str = self._format_time_short(data["total"])

            self.bg_tree_frame.insert(values=(task_name, *day_values, total_str))

        # Add background task totals row
        bg_daily_total_values = [self._format_time_short(s) for s in bg_daily_totals]
        bg_total_str = self._format_time_short(bg_total_seconds)

        self.bg_tree_frame.insert(values=("TOTAL", *bg_daily_total_values, bg_total_str), tags=("total_row",))
        self.bg_tree_frame.configure_tag("total_row", font=(FONT_FAMILY, 10, "bold"))

        # Update totals
        proj_h = project_total_seconds // 3600
        proj_m = (project_total_seconds % 3600) // 60
        self.project_total_var.set(f"Projects Total: {proj_h}h {proj_m:02d}m ({round(project_total_seconds/3600, 2)} hours)")

        bg_h = bg_total_seconds // 3600
        bg_m = (bg_total_seconds % 3600) // 60
        self.bg_total_var.set(f"Tasks Total: {bg_h}h {bg_m:02d}m ({round(bg_total_seconds/3600, 2)} hours)")

        combined = project_total_seconds + bg_total_seconds
        comb_h = combined // 3600
        comb_m = (combined % 3600) // 60
        self.total_var.set(f"Combined Total: {comb_h}h {comb_m:02d}m ({round(combined/3600, 2)} hours)")

    def _refresh_monthly(self, start_date: datetime, end_date: datetime):
        """Refresh with monthly 5-day period view."""
        import calendar
        sort_by = self.sort_var.get()
        group_by = self.group_var.get()

        # Clear existing
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Configure separator and total row tags
        self.tree_frame.configure_tag("separator", background=COLORS["separator"])
        self.tree_frame.configure_tag("total_row", font=(FONT_FAMILY, 10, "bold"))

        # Update column header based on group mode
        if group_by:
            if sort_by == "tag":
                self.tree.heading("project", text="Tag")
            else:
                self.tree.heading("project", text="Priority")
        else:
            self.tree.heading("project", text="Project")

        # Calculate period boundaries
        year = start_date.year
        month = start_date.month
        days_in_month = calendar.monthrange(year, month)[1]

        period_starts = [1, 6, 11, 16, 21, 26]
        period_ranges = []
        for i, start_day in enumerate(period_starts):
            if i < 5:
                end_day = start_day + 4
            else:
                end_day = days_in_month
            period_ranges.append((start_day, end_day))

        project_total_seconds = 0
        project_period_totals = [0] * 6

        if sort_by == "priority":
            project_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=False)

            if group_by:
                priority_period_totals: dict[int, list[int]] = {}
                priority_totals: dict[int, int] = {}

                for project_name, data in project_summary.items():
                    priority = data["priority"]
                    project_total_seconds += data["total"]

                    if priority not in priority_period_totals:
                        priority_period_totals[priority] = [0] * 6
                        priority_totals[priority] = 0

                    priority_totals[priority] += data["total"]

                    for period_idx, (ps, pe) in enumerate(period_ranges):
                        period_seconds = 0
                        for day in range(ps, pe + 1):
                            date_str = f"{year}-{month:02d}-{day:02d}"
                            period_seconds += data["days"].get(date_str, 0)
                        priority_period_totals[priority][period_idx] += period_seconds
                        project_period_totals[period_idx] += period_seconds

                for priority in sorted(priority_period_totals.keys()):
                    period_values = [self._format_time_short(s) for s in priority_period_totals[priority]]
                    total_str = self._format_time_short(priority_totals[priority])
                    priority_label = f"{priority} ({PRIORITY_LABELS.get(priority, 'Unknown')})"

                    self.tree_frame.insert(values=(priority_label, *period_values, total_str))
            else:
                last_priority = None

                for project_name, data in project_summary.items():
                    project_total_seconds += data["total"]
                    priority = data["priority"]

                    if last_priority is not None and priority != last_priority:
                        self.tree_frame.insert(values=("", "", "", "", "", "", "", ""), tags=("separator",))
                    last_priority = priority

                    period_values = []
                    for period_idx, (ps, pe) in enumerate(period_ranges):
                        period_seconds = 0
                        for day in range(ps, pe + 1):
                            date_str = f"{year}-{month:02d}-{day:02d}"
                            period_seconds += data["days"].get(date_str, 0)
                        project_period_totals[period_idx] += period_seconds
                        period_values.append(self._format_time_short(period_seconds))

                    total_str = self._format_time_short(data["total"])

                    self.tree_frame.insert(values=(project_name, *period_values, total_str))
        else:
            tag_summary = db.get_summary_by_tag(start_date=start_date, end_date=end_date)

            if group_by:
                seen_projects = set()
                project_period_counted = {}

                for tag_name, tag_data in tag_summary.items():
                    tag_period_totals = [0] * 6
                    tag_total = 0

                    for project_name, pdata in tag_data["projects"].items():
                        tag_total += pdata["total"]

                        for period_idx, (ps, pe) in enumerate(period_ranges):
                            period_seconds = 0
                            for day in range(ps, pe + 1):
                                date_str = f"{year}-{month:02d}-{day:02d}"
                                period_seconds += pdata["days"].get(date_str, 0)
                            tag_period_totals[period_idx] += period_seconds

                            if project_name not in project_period_counted:
                                project_period_counted[project_name] = [False] * 6
                            if not project_period_counted[project_name][period_idx]:
                                project_period_totals[period_idx] += period_seconds
                                project_period_counted[project_name][period_idx] = True

                        if project_name not in seen_projects:
                            project_total_seconds += pdata["total"]
                            seen_projects.add(project_name)

                    period_values = [self._format_time_short(s) for s in tag_period_totals]
                    total_str = self._format_time_short(tag_total)

                    self.tree_frame.insert(values=(tag_name, *period_values, total_str))
            else:
                seen_projects = set()
                project_period_counted = {}

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        self.tree_frame.insert(values=("", "", "", "", "", "", "", ""), tags=("separator",))
                    last_tag = tag_name

                    for project_name, pdata in tag_data["projects"].items():
                        period_values = []
                        for period_idx, (ps, pe) in enumerate(period_ranges):
                            period_seconds = 0
                            for day in range(ps, pe + 1):
                                date_str = f"{year}-{month:02d}-{day:02d}"
                                period_seconds += pdata["days"].get(date_str, 0)

                            if project_name not in project_period_counted:
                                project_period_counted[project_name] = [False] * 6
                            if not project_period_counted[project_name][period_idx]:
                                project_period_totals[period_idx] += period_seconds
                                project_period_counted[project_name][period_idx] = True

                            period_values.append(self._format_time_short(period_seconds))

                        if project_name not in seen_projects:
                            project_total_seconds += pdata["total"]
                            seen_projects.add(project_name)

                        total_str = self._format_time_short(pdata["total"])

                        display_name = project_name + " *" if pdata["has_multiple_tags"] else project_name

                        self.tree_frame.insert(values=(display_name, *period_values, total_str))

        # Add project totals row
        project_period_total_values = [self._format_time_short(s) for s in project_period_totals]
        project_total_str = self._format_time_short(project_total_seconds)

        self.tree_frame.insert(values=("TOTAL", *project_period_total_values, project_total_str), tags=("total_row",))

        # Get per-day summary for background tasks
        bg_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=True)

        bg_total_seconds = 0
        bg_period_totals = [0] * 6

        for task_name, data in bg_summary.items():
            bg_total_seconds += data["total"]

            period_values = []
            for period_idx, (ps, pe) in enumerate(period_ranges):
                period_seconds = 0
                for day in range(ps, pe + 1):
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    period_seconds += data["days"].get(date_str, 0)
                bg_period_totals[period_idx] += period_seconds
                period_values.append(self._format_time_short(period_seconds))

            total_str = self._format_time_short(data["total"])

            self.bg_tree_frame.insert(values=(task_name, *period_values, total_str))

        # Add background task totals row
        bg_period_total_values = [self._format_time_short(s) for s in bg_period_totals]
        bg_total_str = self._format_time_short(bg_total_seconds)

        self.bg_tree_frame.insert(values=("TOTAL", *bg_period_total_values, bg_total_str), tags=("total_row",))
        self.bg_tree_frame.configure_tag("total_row", font=(FONT_FAMILY, 10, "bold"))

        # Update totals
        proj_h = project_total_seconds // 3600
        proj_m = (project_total_seconds % 3600) // 60
        self.project_total_var.set(f"Projects Total: {proj_h}h {proj_m:02d}m ({round(project_total_seconds/3600, 2)} hours)")

        bg_h = bg_total_seconds // 3600
        bg_m = (bg_total_seconds % 3600) // 60
        self.bg_total_var.set(f"Tasks Total: {bg_h}h {bg_m:02d}m ({round(bg_total_seconds/3600, 2)} hours)")

        combined = project_total_seconds + bg_total_seconds
        comb_h = combined // 3600
        comb_m = (combined % 3600) // 60
        self.total_var.set(f"Combined Total: {comb_h}h {comb_m:02d}m ({round(combined/3600, 2)} hours)")


class ProjectsTab:
    """Projects tab for managing projects and background tasks."""

    def __init__(self, parent, app: DerbyApp):
        self.frame = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the projects tab UI with split view."""
        # Main container
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["container_bg"])
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        ctk.CTkLabel(top_frame, text="Projects", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.tree_frame = TreeviewFrame(
            top_frame,
            columns=("name", "priority", "tags"),
            headings=["Name", "Priority", "Tags"],
            widths=[200, 120, 250],
            height=6
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10)
        self.tree = self.tree_frame.tree

        # Button row for projects
        btn_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=10, pady=5)

        add_btn = ctk.CTkButton(btn_frame, text="Add Project", command=self.add_project)
        add_btn.pack(side=ctk.LEFT, padx=5)

        rename_btn = ctk.CTkButton(btn_frame, text="Rename", command=self.rename_project)
        rename_btn.pack(side=ctk.LEFT, padx=5)

        priority_btn = ctk.CTkButton(btn_frame, text="Edit Priority", command=self.edit_priority)
        priority_btn.pack(side=ctk.LEFT, padx=5)

        tags_btn = ctk.CTkButton(btn_frame, text="Edit Tags", command=self.edit_tags)
        tags_btn.pack(side=ctk.LEFT, padx=5)

        delete_btn = ctk.CTkButton(btn_frame, text="Delete", command=self.delete_project)
        delete_btn.pack(side=ctk.LEFT, padx=5)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["container_bg"])
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        ctk.CTkLabel(bottom_frame, text="Background Tasks", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.bg_tree_frame = TreeviewFrame(
            bottom_frame,
            columns=("name",),
            headings=["Task Name"],
            widths=[400],
            height=6
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10)
        self.bg_tree = self.bg_tree_frame.tree

        # Button row for background tasks
        bg_btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bg_btn_frame.pack(fill=ctk.X, padx=10, pady=5)

        bg_add_btn = ctk.CTkButton(bg_btn_frame, text="Add Task", command=self.add_background_task)
        bg_add_btn.pack(side=ctk.LEFT, padx=5)

        bg_rename_btn = ctk.CTkButton(bg_btn_frame, text="Rename", command=self.rename_background_task)
        bg_rename_btn.pack(side=ctk.LEFT, padx=5)

        bg_delete_btn = ctk.CTkButton(bg_btn_frame, text="Delete", command=self.delete_background_task)
        bg_delete_btn.pack(side=ctk.LEFT, padx=5)

        refresh_btn = ctk.CTkButton(bg_btn_frame, text="Refresh All", command=self.refresh)
        refresh_btn.pack(side=ctk.LEFT, padx=5)

    def refresh(self):
        """Refresh both projects and background tasks lists."""
        # Clear existing
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Get regular projects
        projects = db.list_projects(is_background=False)

        for project in projects:
            priority_label = f"{project.priority} ({PRIORITY_LABELS.get(project.priority, 'Unknown')})"
            tags_str = ", ".join(project.tags) if project.tags else ""

            self.tree_frame.insert(
                values=(project.name, priority_label, tags_str),
                iid=project.name
            )

        # Get background tasks
        bg_tasks = db.list_projects(is_background=True)

        for task in bg_tasks:
            self.bg_tree_frame.insert(values=(task.name,), iid=task.name)

    def add_project(self):
        """Show dialog to add a new project."""
        AddProjectDialog(self.app.root, self.app)

    def add_background_task(self):
        """Show dialog to add a new background task."""
        AddBackgroundTaskDialog(self.app.root, self.app)

    def edit_priority(self):
        """Edit priority of selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        EditPriorityDialog(self.app.root, self.app, project_name)

    def edit_tags(self):
        """Edit tags of selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        EditTagsDialog(self.app.root, self.app, project_name)

    def rename_project(self):
        """Rename selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, project_name)

    def rename_background_task(self):
        """Rename selected background task."""
        selection = self.bg_tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a task", "warning")
            return

        task_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, task_name)

    def delete_project(self):
        """Delete selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        DeleteProjectDialog(self.app.root, self.app, project_name)

    def delete_background_task(self):
        """Delete selected background task."""
        selection = self.bg_tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a task", "warning")
            return

        task_name = selection[0]
        DeleteProjectDialog(self.app.root, self.app, task_name, is_background=True)


# =============================================================================
# Dialog Helper Classes
# =============================================================================

class CTkMessagebox:
    """Simple message box dialog using CustomTkinter."""

    def __init__(self, parent, title: str, message: str, msg_type: str = "info"):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Content
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=message, wraplength=300).pack(pady=20)

        ctk.CTkButton(main_frame, text="OK", command=self.dialog.destroy, width=100).pack()

        self.dialog.wait_window()


class CTkConfirmDialog:
    """Confirmation dialog using CustomTkinter."""

    def __init__(self, parent, title: str, message: str):
        self.result = False
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Content
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=message, wraplength=300).pack(pady=20)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(btn_frame, text="Yes", command=self._yes, width=80).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="No", command=self._no, width=80).pack(side=ctk.LEFT, padx=10)

        self.dialog.wait_window()

    def _yes(self):
        self.result = True
        self.dialog.destroy()

    def _no(self):
        self.result = False
        self.dialog.destroy()

    def get_result(self):
        return self.result


class StopSessionDialog:
    """Dialog for stopping a session with optional notes."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Stop: {project_name}")
        self.dialog.geometry("400x200")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
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

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Log Manual Entry")
        self.dialog.geometry("450x350")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
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


class AddProjectDialog:
    """Dialog for adding a new project."""

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Add Project")
        self.dialog.geometry("400x250")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar()
        self.priority_var = ctk.StringVar(value="3")
        self.tags_var = ctk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        # Name
        ctk.CTkLabel(main_frame, text="Name:").pack(anchor="w", pady=(0, 2))
        name_entry = ctk.CTkEntry(main_frame, textvariable=self.name_var, width=300)
        name_entry.pack(anchor="w", pady=(0, 10))
        name_entry.focus()

        # Priority
        priority_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        priority_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(priority_frame, text="Priority (1-5):").pack(side=ctk.LEFT)
        priority_entry = ctk.CTkEntry(priority_frame, textvariable=self.priority_var, width=60)
        priority_entry.pack(side=ctk.LEFT, padx=10)

        # Tags
        tags_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tags_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(tags_frame, text="Tags:").pack(side=ctk.LEFT)
        tags_entry = ctk.CTkEntry(tags_frame, textvariable=self.tags_var, width=200)
        tags_entry.pack(side=ctk.LEFT, padx=10)
        ctk.CTkLabel(tags_frame, text="(comma-separated)").pack(side=ctk.LEFT)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Add", command=self._do_add).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_add(self):
        """Add the project."""
        name = self.name_var.get().strip()
        tags_str = self.tags_var.get().strip()

        if not name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a project name", "warning")
            return

        try:
            priority = int(self.priority_var.get())
        except ValueError:
            CTkMessagebox(self.dialog, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            CTkMessagebox(self.dialog, "Warning", "Priority must be between 1 and 5", "warning")
            return

        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        try:
            db.create_project(name, priority=priority, tags=tags)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class AddBackgroundTaskDialog:
    """Dialog for adding a new background task."""

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Add Background Task")
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        # Name
        ctk.CTkLabel(main_frame, text="Task Name:").pack(anchor="w", pady=(0, 2))
        name_entry = ctk.CTkEntry(main_frame, textvariable=self.name_var, width=250)
        name_entry.pack(anchor="w", pady=(0, 10))
        name_entry.focus()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Add", command=self._do_add).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_add(self):
        """Add the background task."""
        name = self.name_var.get().strip()

        if not name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a task name", "warning")
            return

        try:
            db.create_project(name, is_background=True)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class EditPriorityDialog:
    """Dialog for editing a project's priority."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        # Get current priority
        project = db.get_project(project_name)
        current_priority = project.priority if project else 3

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Edit Priority: {project_name}")
        self.dialog.geometry("350x180")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.priority_var = ctk.StringVar(value=str(current_priority))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Project: {self.project_name}").pack(pady=10)

        priority_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        priority_frame.pack(pady=10)

        ctk.CTkLabel(priority_frame, text="Priority (1-5):").pack(side=ctk.LEFT)
        priority_entry = ctk.CTkEntry(priority_frame, textvariable=self.priority_var, width=60)
        priority_entry.pack(side=ctk.LEFT, padx=10)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Save", command=self._do_save).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_save(self):
        """Save the priority."""
        try:
            priority = int(self.priority_var.get())
        except ValueError:
            CTkMessagebox(self.dialog, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            CTkMessagebox(self.dialog, "Warning", "Priority must be between 1 and 5", "warning")
            return

        try:
            db.update_project_priority(self.project_name, priority)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class EditTagsDialog:
    """Dialog for editing a project's tags."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        # Get project and current tags
        self.project = db.get_project(project_name)
        current_tags = self.project.tags if self.project else []

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Edit Tags: {project_name}")
        self.dialog.geometry("450x200")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.tags_var = ctk.StringVar(value=", ".join(current_tags))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Project: {self.project_name}").pack(pady=10)

        tags_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tags_frame.pack(fill=ctk.X, pady=10)

        ctk.CTkLabel(tags_frame, text="Tags:").pack(side=ctk.LEFT)
        tags_entry = ctk.CTkEntry(tags_frame, textvariable=self.tags_var, width=300)
        tags_entry.pack(side=ctk.LEFT, padx=10)
        tags_entry.focus()

        ctk.CTkLabel(main_frame, text="(comma-separated)", text_color=COLORS["text_secondary"]).pack()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Save", command=self._do_save).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_save(self):
        """Save the tags."""
        if not self.project:
            CTkMessagebox(self.dialog, "Error", "Project not found", "error")
            return

        # Parse new tags
        tags_str = self.tags_var.get().strip()
        new_tags = set(t.strip().lower() for t in tags_str.split(",") if t.strip())
        current_tags = set(t.lower() for t in self.project.tags)

        # Find tags to add and remove
        tags_to_add = new_tags - current_tags
        tags_to_remove = current_tags - new_tags

        try:
            # Remove old tags
            for tag in tags_to_remove:
                db.remove_tag_from_project(self.project.id, tag)

            # Add new tags
            for tag in tags_to_add:
                original_tag = next((t.strip() for t in tags_str.split(",") if t.strip().lower() == tag), tag)
                db.add_tag_to_project(self.project.id, original_tag)

            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class RenameProjectDialog:
    """Dialog for renaming a project."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.old_name = project_name

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Rename Project")
        self.dialog.geometry("450x200")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar(value=project_name)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Current name: {self.old_name}").pack(pady=10)

        name_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        name_frame.pack(fill=ctk.X, pady=10)

        ctk.CTkLabel(name_frame, text="New name:").pack(side=ctk.LEFT)
        name_entry = ctk.CTkEntry(name_frame, textvariable=self.name_var, width=280)
        name_entry.pack(side=ctk.LEFT, padx=10)
        name_entry.focus()
        name_entry.select_range(0, ctk.END)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Rename", command=self._do_rename).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_rename(self):
        """Rename the project."""
        new_name = self.name_var.get().strip()

        if not new_name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a project name", "warning")
            return

        if new_name == self.old_name:
            self.dialog.destroy()
            return

        try:
            result = db.rename_project(self.old_name, new_name)
            if result is None:
                CTkMessagebox(self.dialog, "Error", "Project not found", "error")
                return

            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
            self.app.history_tab.refresh()
        except sqlite3.IntegrityError:
            CTkMessagebox(self.dialog, "Error", f"A project named '{new_name}' already exists", "error")
        except (ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class DeleteProjectDialog:
    """Dialog for deleting a project with option to delete associated sessions."""

    def __init__(self, parent, app: DerbyApp, project_name: str, is_background: bool = False):
        self.app = app
        self.project_name = project_name
        self.is_background = is_background

        self.dialog = ctk.CTkToplevel(parent)
        title = "Delete Task" if is_background else "Delete Project"
        self.dialog.title(title)
        self.dialog.geometry("450x220")
        self.dialog.configure(fg_color=COLORS["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.delete_sessions_var = ctk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        item_type = "task" if self.is_background else "project"
        ctk.CTkLabel(
            main_frame,
            text=f"Are you sure you want to delete the {item_type}:\n\"{self.project_name}\"?",
            wraplength=400
        ).pack(pady=10)

        # Option to delete sessions
        delete_sessions_check = ctk.CTkCheckBox(
            main_frame,
            text="Also delete all associated sessions (time entries)",
            variable=self.delete_sessions_var
        )
        delete_sessions_check.pack(pady=10)

        ctk.CTkLabel(
            main_frame,
            text="(If unchecked, sessions will be kept but become orphaned)",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=11)
        ).pack()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Delete", command=self._do_delete, fg_color="#c0392b", hover_color="#e74c3c").pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_delete(self):
        """Delete the project."""
        delete_sessions = self.delete_sessions_var.get()

        result = db.delete_project(self.project_name, delete_sessions=delete_sessions)
        if not result:
            CTkMessagebox(self.dialog, "Error", "Project not found", "error")
            return

        self.dialog.destroy()
        self.app.projects_tab.refresh()
        self.app.timer_tab.refresh()
        self.app.history_tab.refresh()


if __name__ == "__main__":
    app = DerbyApp()
    app.run()
