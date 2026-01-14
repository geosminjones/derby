#!/usr/bin/env python3
"""
gui.py - Graphical user interface for Derby

A tkinter-based GUI that provides the same functionality as the CLI
but with a visual interface and live timer updates.

Run with: python gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
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


class DerbyApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Derby")
        self.root.geometry("850x550")
        self.root.minsize(700, 450)

        # Initialize database
        db.init_database()

        # Status bar variable
        self.status_var = tk.StringVar(value="Ready")

        # Build UI components
        self._create_menu()
        self._create_notebook()
        self._create_status_bar()

        # Start timer update loop
        self._schedule_timer_update()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_menu(self):
        """Create application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export to CSV...", command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Session menu
        session_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Session", menu=session_menu)
        session_menu.add_command(label="Log Manual Entry...", command=self._show_log_dialog)
        session_menu.add_command(label="Stop All", command=self._stop_all)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_notebook(self):
        """Create tabbed interface."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.timer_tab = TimerTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        self.summary_tab = SummaryTab(self.notebook, self)
        self.projects_tab = ProjectsTab(self.notebook, self)

        self.notebook.add(self.timer_tab.frame, text="Timer")
        self.notebook.add(self.history_tab.frame, text="History")
        self.notebook.add(self.summary_tab.frame, text="Summary")
        self.notebook.add(self.projects_tab.frame, text="Projects")

        # Refresh data when tab changes
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _create_status_bar(self):
        """Create status bar at bottom of window."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        status_label.pack(fill=tk.X)

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
            self.status_var.set(f"Tracking: {s.project_name} ({s.format_duration()})")
        else:
            total = sum(s.duration_seconds for s in active)
            h = total // 3600
            m = (total % 3600) // 60
            sec = total % 60
            self.status_var.set(f"Tracking: {len(active)} sessions (Total: {h}h {m:02d}m {sec:02d}s)")

    def _on_tab_change(self, event):
        """Refresh data when switching tabs."""
        tab_id = self.notebook.index(self.notebook.select())
        if tab_id == 0:
            self.timer_tab.refresh()
        elif tab_id == 1:
            self.history_tab.refresh()
        elif tab_id == 2:
            self.summary_tab.refresh()
        elif tab_id == 3:
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
            messagebox.showinfo("Export Complete", f"Exported to:\n{filepath}")

    def _stop_all(self):
        """Stop all active sessions."""
        active = db.get_active_sessions()
        if not active:
            messagebox.showinfo("Info", "No active sessions to stop")
            return

        if messagebox.askyesno("Confirm", f"Stop {len(active)} active session(s)?"):
            db.stop_all_sessions()
            self.timer_tab.refresh()

    def _show_log_dialog(self):
        """Show dialog to log manual entry."""
        LogSessionDialog(self.root, self)

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About Derby",
            "Derby v1.0\n\n"
            "A simple, local-first time tracking application.\n\n"
            "Data stored in: ~/.timetrack/timetrack.db"
        )

    def _on_close(self):
        """Handle window close."""
        self.root.destroy()

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


class TimerTab:
    """Timer tab for starting/stopping sessions."""

    def __init__(self, parent, app: DerbyApp):
        self.frame = ttk.Frame(parent)
        self.app = app
        self.project_var = tk.StringVar()
        self.bg_task_var = tk.StringVar()
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the timer tab UI with split view for projects and background tasks."""
        # Use PanedWindow for resizable split
        paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ttk.Frame(paned)
        paned.add(top_frame, weight=1)

        # Start session section for regular projects
        start_frame = ttk.LabelFrame(top_frame, text="Start New Project Session", padding=10)
        start_frame.pack(fill=tk.X, padx=5, pady=5)

        project_row = ttk.Frame(start_frame)
        project_row.pack(fill=tk.X, pady=5)

        ttk.Label(project_row, text="Project:").pack(side=tk.LEFT)

        self.project_combo = ttk.Combobox(
            project_row,
            textvariable=self.project_var,
            width=35
        )
        self.project_combo.pack(side=tk.LEFT, padx=10)
        self.project_combo.bind('<Return>', lambda e: self.start_session())

        start_btn = ttk.Button(project_row, text="Start Tracking", command=self.start_session)
        start_btn.pack(side=tk.LEFT, padx=5)

        # Active regular sessions section
        active_frame = ttk.LabelFrame(top_frame, text="Active Project Sessions", padding=5)
        active_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview for active regular sessions
        columns = ("project", "started", "duration")
        self.tree = ttk.Treeview(active_frame, columns=columns, show="headings", height=4)

        self.tree.heading("project", text="Project")
        self.tree.heading("started", text="Started")
        self.tree.heading("duration", text="Duration")

        self.tree.column("project", width=200)
        self.tree.column("started", width=150)
        self.tree.column("duration", width=100)

        scrollbar = ttk.Scrollbar(active_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button row for regular projects
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=2)

        stop_btn = ttk.Button(btn_frame, text="Stop Selected", command=self.stop_selected)
        stop_btn.pack(side=tk.LEFT, padx=5)

        stop_all_btn = ttk.Button(btn_frame, text="Stop All Projects", command=self.stop_all_projects)
        stop_all_btn.pack(side=tk.LEFT, padx=5)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ttk.Frame(paned)
        paned.add(bottom_frame, weight=1)

        # Start session section for background tasks
        bg_start_frame = ttk.LabelFrame(bottom_frame, text="Start Background Task", padding=10)
        bg_start_frame.pack(fill=tk.X, padx=5, pady=5)

        bg_row = ttk.Frame(bg_start_frame)
        bg_row.pack(fill=tk.X, pady=5)

        ttk.Label(bg_row, text="Task:").pack(side=tk.LEFT)

        self.bg_task_combo = ttk.Combobox(
            bg_row,
            textvariable=self.bg_task_var,
            width=35
        )
        self.bg_task_combo.pack(side=tk.LEFT, padx=10)
        self.bg_task_combo.bind('<Return>', lambda e: self.start_background_task())

        bg_start_btn = ttk.Button(bg_row, text="Start Task", command=self.start_background_task)
        bg_start_btn.pack(side=tk.LEFT, padx=5)

        # Active background tasks section
        bg_active_frame = ttk.LabelFrame(bottom_frame, text="Active Background Tasks", padding=5)
        bg_active_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview for active background tasks
        self.bg_tree = ttk.Treeview(bg_active_frame, columns=columns, show="headings", height=4)

        self.bg_tree.heading("project", text="Task")
        self.bg_tree.heading("started", text="Started")
        self.bg_tree.heading("duration", text="Duration")

        self.bg_tree.column("project", width=200)
        self.bg_tree.column("started", width=150)
        self.bg_tree.column("duration", width=100)

        bg_scrollbar = ttk.Scrollbar(bg_active_frame, orient=tk.VERTICAL, command=self.bg_tree.yview)
        self.bg_tree.configure(yscrollcommand=bg_scrollbar.set)

        self.bg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button row for background tasks
        bg_btn_frame = ttk.Frame(bottom_frame)
        bg_btn_frame.pack(fill=tk.X, padx=5, pady=2)

        bg_stop_btn = ttk.Button(bg_btn_frame, text="Stop Selected", command=self.stop_selected_bg)
        bg_stop_btn.pack(side=tk.LEFT, padx=5)

        bg_stop_all_btn = ttk.Button(bg_btn_frame, text="Stop All Tasks", command=self.stop_all_background)
        bg_stop_all_btn.pack(side=tk.LEFT, padx=5)

    def refresh(self):
        """Refresh project list and active sessions."""
        # Update project combo (regular projects only)
        projects = db.list_projects(is_background=False)
        project_names = [p.name for p in projects]
        self.project_combo['values'] = project_names

        # Update background task combo
        bg_tasks = db.list_projects(is_background=True)
        bg_task_names = [p.name for p in bg_tasks]
        self.bg_task_combo['values'] = bg_task_names

        # Update active sessions
        self._refresh_active_sessions()

    def _refresh_active_sessions(self):
        """Refresh both active sessions treeviews."""
        # Clear existing from both trees
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.bg_tree.get_children():
            self.bg_tree.delete(item)

        # Get all active sessions
        active = db.get_active_sessions()

        # Separate into regular and background
        for session in active:
            project = db.get_project(session.project_name)
            is_bg = project.is_background if project else False

            started = session.start_time.strftime("%Y-%m-%d %I:%M:%S %p") if session.start_time else ""

            if is_bg:
                self.bg_tree.insert("", tk.END, iid=str(session.id), values=(
                    session.project_name,
                    started,
                    session.format_duration()
                ))
            else:
                self.tree.insert("", tk.END, iid=str(session.id), values=(
                    session.project_name,
                    started,
                    session.format_duration()
                ))

    def update_durations(self):
        """Update displayed durations for active sessions."""
        active = db.get_active_sessions()
        active_dict = {str(s.id): s for s in active}

        # Update regular sessions tree
        for item in self.tree.get_children():
            if item in active_dict:
                session = active_dict[item]
                self.tree.set(item, "duration", session.format_duration())

        # Update background tasks tree
        for item in self.bg_tree.get_children():
            if item in active_dict:
                session = active_dict[item]
                self.bg_tree.set(item, "duration", session.format_duration())

    def start_session(self):
        """Start tracking the selected regular project."""
        project = self.project_var.get().strip()
        if not project:
            messagebox.showwarning("Warning", "Please enter a project name")
            return

        # Check if already active
        active = db.get_active_session_by_project(project)
        if active:
            messagebox.showinfo("Info", f"'{project}' is already being tracked")
            return

        # Ensure project exists and is not a background task
        existing = db.get_project(project)
        if existing and existing.is_background:
            messagebox.showwarning("Warning", f"'{project}' is a background task, not a project")
            return

        db.start_session(project)
        self.project_var.set("")
        self.refresh()

    def start_background_task(self):
        """Start tracking a background task."""
        task = self.bg_task_var.get().strip()
        if not task:
            messagebox.showwarning("Warning", "Please enter a task name")
            return

        # Check if already active
        active = db.get_active_session_by_project(task)
        if active:
            messagebox.showinfo("Info", f"'{task}' is already being tracked")
            return

        # Create as background task if new
        existing = db.get_project(task)
        if existing is None:
            db.create_project(task, is_background=True)
        elif not existing.is_background:
            messagebox.showwarning("Warning", f"'{task}' is a regular project, not a background task")
            return

        db.start_session(task)
        self.bg_task_var.set("")
        self.refresh()

    def stop_selected(self):
        """Stop the selected regular project session."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session to stop")
            return

        item = selection[0]
        project_name = self.tree.set(item, "project")

        # Show notes dialog
        StopSessionDialog(self.app.root, self.app, project_name)

    def stop_selected_bg(self):
        """Stop the selected background task session."""
        selection = self.bg_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a task to stop")
            return

        item = selection[0]
        task_name = self.bg_tree.set(item, "project")

        # Show notes dialog
        StopSessionDialog(self.app.root, self.app, task_name)

    def stop_all_projects(self):
        """Stop all active regular project sessions."""
        active = db.get_active_sessions()
        project_sessions = []
        for s in active:
            project = db.get_project(s.project_name)
            if project and not project.is_background:
                project_sessions.append(s)

        if not project_sessions:
            messagebox.showinfo("Info", "No active project sessions to stop")
            return

        if messagebox.askyesno("Confirm", f"Stop {len(project_sessions)} active project session(s)?"):
            for s in project_sessions:
                db.stop_session(project_name=s.project_name)
            self.refresh()

    def stop_all_background(self):
        """Stop all active background task sessions."""
        active = db.get_active_sessions()
        bg_sessions = []
        for s in active:
            project = db.get_project(s.project_name)
            if project and project.is_background:
                bg_sessions.append(s)

        if not bg_sessions:
            messagebox.showinfo("Info", "No active background tasks to stop")
            return

        if messagebox.askyesno("Confirm", f"Stop {len(bg_sessions)} active background task(s)?"):
            for s in bg_sessions:
                db.stop_session(project_name=s.project_name)
            self.refresh()

    def stop_all(self):
        """Stop all active sessions (both projects and background tasks)."""
        self.app._stop_all()


class HistoryTab:
    """History tab for viewing past sessions."""

    def __init__(self, parent, app: DerbyApp):
        self.frame = ttk.Frame(parent)
        self.app = app
        self.project_filter = tk.StringVar(value="All")
        self.period_filter = tk.StringVar(value="All")
        self.limit_var = tk.IntVar(value=50)
        self._build_ui()

    def _build_ui(self):
        """Build the history tab UI."""
        # Filter section
        filter_frame = ttk.Frame(self.frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(filter_frame, text="Project:").pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.project_filter,
            width=20,
            state="readonly"
        )
        self.project_combo.pack(side=tk.LEFT, padx=(5, 15))
        self.project_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Period:").pack(side=tk.LEFT)
        period_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.period_filter,
            values=["All", "Today", "This Week"],
            width=12,
            state="readonly"
        )
        period_combo.pack(side=tk.LEFT, padx=(5, 15))
        period_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Limit:").pack(side=tk.LEFT)
        limit_spin = ttk.Spinbox(
            filter_frame,
            textvariable=self.limit_var,
            from_=10,
            to=500,
            width=6
        )
        limit_spin.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(filter_frame, text="Refresh", command=self.refresh)
        refresh_btn.pack(side=tk.LEFT, padx=10)

        # Sessions treeview
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("id", "date", "project", "duration", "notes")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)

        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("project", text="Project")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("notes", text="Notes")

        self.tree.column("id", width=50)
        self.tree.column("date", width=100)
        self.tree.column("project", width=150)
        self.tree.column("duration", width=100)
        self.tree.column("notes", width=300)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button row
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        delete_btn = ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected)
        delete_btn.pack(side=tk.LEFT, padx=5)

        export_btn = ttk.Button(btn_frame, text="Export to CSV...", command=self.app._export_csv)
        export_btn.pack(side=tk.LEFT, padx=5)

    def refresh(self):
        """Refresh sessions list."""
        # Update project filter options
        projects = db.list_projects()
        project_names = ["All"] + [p.name for p in projects]
        self.project_combo['values'] = project_names

        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)

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

        # Query sessions
        sessions = db.get_sessions(
            project_name=project,
            start_date=start_date,
            end_date=end_date,
            limit=self.limit_var.get()
        )

        # Populate tree
        for session in sessions:
            date_str = session.start_time.strftime("%Y-%m-%d") if session.start_time else ""
            notes_preview = session.notes[:50] + "..." if len(session.notes) > 50 else session.notes
            self.tree.insert("", tk.END, iid=str(session.id), values=(
                session.id,
                date_str,
                session.project_name,
                session.format_duration(),
                notes_preview
            ))

    def delete_selected(self):
        """Delete the selected session."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a session to delete")
            return

        item = selection[0]
        session_id = int(self.tree.set(item, "id"))
        project = self.tree.set(item, "project")

        if messagebox.askyesno("Confirm Delete", f"Delete session #{session_id} ({project})?"):
            db.delete_session(session_id)
            self.refresh()


class SummaryTab:
    """Summary tab for time aggregations with split view for projects and background tasks."""

    # Day abbreviations for column headers
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def __init__(self, parent, app: DerbyApp):
        self.frame = ttk.Frame(parent)
        self.app = app
        self.period_var = tk.StringVar(value="today")
        self.current_view = "standard"  # "standard" or "weekly"
        self._build_ui()

    def _build_ui(self):
        """Build the summary tab UI with split view."""
        # Period selection
        period_frame = ttk.Frame(self.frame)
        period_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(period_frame, text="Period:").pack(side=tk.LEFT)

        for text, value in [("Today", "today"), ("This Week", "week"), ("All Time", "all")]:
            rb = ttk.Radiobutton(
                period_frame,
                text=text,
                variable=self.period_var,
                value=value,
                command=self.refresh
            )
            rb.pack(side=tk.LEFT, padx=10)

        # Use PanedWindow for resizable split
        paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects Summary
        # =====================================================================
        top_frame = ttk.LabelFrame(paned, text="Projects", padding=5)
        paned.add(top_frame, weight=1)

        self.tree_frame = ttk.Frame(top_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        # Create standard view treeview for projects
        self._create_standard_treeview()

        # Project total label
        self.project_total_var = tk.StringVar(value="Projects Total: 0h 00m")
        project_total_label = ttk.Label(top_frame, textvariable=self.project_total_var, font=("TkDefaultFont", 10, "bold"))
        project_total_label.pack(pady=3)

        # =====================================================================
        # BOTTOM HALF: Background Tasks Summary
        # =====================================================================
        bottom_frame = ttk.LabelFrame(paned, text="Background Tasks", padding=5)
        paned.add(bottom_frame, weight=1)

        self.bg_tree_frame = ttk.Frame(bottom_frame)
        self.bg_tree_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview for background tasks (simpler - no priority column)
        self._create_bg_standard_treeview()

        # Background tasks total label
        self.bg_total_var = tk.StringVar(value="Tasks Total: 0h 00m")
        bg_total_label = ttk.Label(bottom_frame, textvariable=self.bg_total_var, font=("TkDefaultFont", 10, "bold"))
        bg_total_label.pack(pady=3)

        # Combined total at bottom
        self.total_var = tk.StringVar(value="Combined Total: 0h 00m")
        total_label = ttk.Label(self.frame, textvariable=self.total_var, font=("TkDefaultFont", 11, "bold"))
        total_label.pack(pady=5)

    def _create_standard_treeview(self):
        """Create the standard (non-weekly) treeview for projects."""
        columns = ("project", "priority", "time", "hours")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=5)

        self.tree.heading("project", text="Project")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("time", text="Time")
        self.tree.heading("hours", text="Hours")

        self.tree.column("project", width=200)
        self.tree.column("priority", width=100)
        self.tree.column("time", width=100)
        self.tree.column("hours", width=80)

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.current_view = "standard"

    def _create_bg_standard_treeview(self):
        """Create the standard treeview for background tasks (no priority)."""
        columns = ("task", "time", "hours")
        self.bg_tree = ttk.Treeview(self.bg_tree_frame, columns=columns, show="headings", height=5)

        self.bg_tree.heading("task", text="Task")
        self.bg_tree.heading("time", text="Time")
        self.bg_tree.heading("hours", text="Hours")

        self.bg_tree.column("task", width=250)
        self.bg_tree.column("time", width=120)
        self.bg_tree.column("hours", width=100)

        self.bg_scrollbar = ttk.Scrollbar(self.bg_tree_frame, orient=tk.VERTICAL, command=self.bg_tree.yview)
        self.bg_tree.configure(yscrollcommand=self.bg_scrollbar.set)

        self.bg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bg_current_view = "standard"

    def _create_weekly_treeview(self, week_start: datetime):
        """Create the weekly view treeview with day columns for projects."""
        # Build column headers with dates (single line: "Mon 1/6")
        day_columns = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            col_id = f"day{i}"
            day_columns.append((col_id, f"{self.DAY_NAMES[i]} {day_date.day}"))

        columns = ["project"] + [c[0] for c in day_columns] + ["total"]
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=5)

        # Configure headings
        self.tree.heading("project", text="Project")
        self.tree.column("project", width=120, minwidth=80)

        for col_id, header in day_columns:
            self.tree.heading(col_id, text=header)
            self.tree.column(col_id, width=55, anchor=tk.CENTER, minwidth=45)

        self.tree.heading("total", text="Total")
        self.tree.column("total", width=60, anchor=tk.CENTER, minwidth=50)

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.current_view = "weekly"

    def _create_bg_weekly_treeview(self, week_start: datetime):
        """Create the weekly view treeview for background tasks."""
        day_columns = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            col_id = f"day{i}"
            day_columns.append((col_id, f"{self.DAY_NAMES[i]} {day_date.day}"))

        columns = ["task"] + [c[0] for c in day_columns] + ["total"]
        self.bg_tree = ttk.Treeview(self.bg_tree_frame, columns=columns, show="headings", height=5)

        self.bg_tree.heading("task", text="Task")
        self.bg_tree.column("task", width=120, minwidth=80)

        for col_id, header in day_columns:
            self.bg_tree.heading(col_id, text=header)
            self.bg_tree.column(col_id, width=55, anchor=tk.CENTER, minwidth=45)

        self.bg_tree.heading("total", text="Total")
        self.bg_tree.column("total", width=60, anchor=tk.CENTER, minwidth=50)

        self.bg_scrollbar = ttk.Scrollbar(self.bg_tree_frame, orient=tk.VERTICAL, command=self.bg_tree.yview)
        self.bg_tree.configure(yscrollcommand=self.bg_scrollbar.set)

        self.bg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.bg_current_view = "weekly"

    def _destroy_treeview(self):
        """Destroy the current project treeview and scrollbar."""
        if hasattr(self, 'tree'):
            self.tree.destroy()
        if hasattr(self, 'scrollbar'):
            self.scrollbar.destroy()

    def _destroy_bg_treeview(self):
        """Destroy the current background task treeview and scrollbar."""
        if hasattr(self, 'bg_tree'):
            self.bg_tree.destroy()
        if hasattr(self, 'bg_scrollbar'):
            self.bg_scrollbar.destroy()

    def _format_time_short(self, seconds: int) -> str:
        """Format seconds as short time string (e.g., '1:30' for 1h 30m, '0:45' for 45m)."""
        if seconds == 0:
            return "-"
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}:{mins:02d}"

    def refresh(self):
        """Refresh summary data."""
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

        # Switch view type if needed
        if period == "week":
            if self.current_view != "weekly":
                self._destroy_treeview()
                self._create_weekly_treeview(start_date)
            if not hasattr(self, 'bg_current_view') or self.bg_current_view != "weekly":
                self._destroy_bg_treeview()
                self._create_bg_weekly_treeview(start_date)
            self._refresh_weekly(start_date, end_date)
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
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.bg_tree.get_children():
            self.bg_tree.delete(item)

        # Configure separator tag (thin divider line)
        self.tree.tag_configure("separator", background="#CCCCCC")

        # Get project summary (regular projects only)
        project_summary = db.get_summary_with_priority(start_date=start_date, end_date=end_date, is_background=False)

        # Populate project tree with separators between priority groups
        project_total_seconds = 0
        last_priority = None
        for project_name, data in project_summary.items():
            seconds = data["seconds"]
            priority = data["priority"]
            project_total_seconds += seconds

            # Add separator row between priority groups
            if last_priority is not None and priority != last_priority:
                self.tree.insert("", tk.END, values=("", "", "", ""), tags=("separator",))
            last_priority = priority

            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = seconds % 60
            time_str = f"{hours}:{mins:02d}:{secs:02d}"
            hours_decimal = round(seconds / 3600, 2)

            priority_label = f"{priority} ({PRIORITY_LABELS.get(priority, 'Unknown')})"

            self.tree.insert("", tk.END, values=(
                project_name,
                priority_label,
                time_str,
                hours_decimal
            ))

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

            self.bg_tree.insert("", tk.END, values=(
                task_name,
                time_str,
                hours_decimal
            ))

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
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.bg_tree.get_children():
            self.bg_tree.delete(item)

        # Configure separator and total row tags
        self.tree.tag_configure("separator", background="#CCCCCC")
        self.tree.tag_configure("total_row", font=("TkDefaultFont", 9, "bold"))

        # Build date strings for each day of the week
        day_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        # Get per-day summary for projects
        project_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=False)

        project_total_seconds = 0
        project_daily_totals = [0] * 7
        last_priority = None

        for project_name, data in project_summary.items():
            project_total_seconds += data["total"]
            priority = data["priority"]

            # Add separator row between priority groups
            if last_priority is not None and priority != last_priority:
                self.tree.insert("", tk.END, values=("", "", "", "", "", "", "", "", ""), tags=("separator",))
            last_priority = priority

            day_values = []
            for i, date_str in enumerate(day_dates):
                seconds = data["days"].get(date_str, 0)
                project_daily_totals[i] += seconds
                day_values.append(self._format_time_short(seconds))

            total_str = self._format_time_short(data["total"])

            self.tree.insert("", tk.END, values=(
                project_name,
                *day_values,
                total_str
            ))

        # Add project totals row
        project_daily_total_values = [self._format_time_short(s) for s in project_daily_totals]
        project_total_str = self._format_time_short(project_total_seconds)

        self.tree.insert("", tk.END, values=(
            "TOTAL",
            *project_daily_total_values,
            project_total_str
        ), tags=("total_row",))

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

            self.bg_tree.insert("", tk.END, values=(
                task_name,
                *day_values,
                total_str
            ))

        # Add background task totals row
        bg_daily_total_values = [self._format_time_short(s) for s in bg_daily_totals]
        bg_total_str = self._format_time_short(bg_total_seconds)

        self.bg_tree.insert("", tk.END, values=(
            "TOTAL",
            *bg_daily_total_values,
            bg_total_str
        ), tags=("total_row",))
        self.bg_tree.tag_configure("total_row", font=("TkDefaultFont", 9, "bold"))

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
        self.frame = ttk.Frame(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the projects tab UI with split view."""
        # Use PanedWindow for resizable split
        paned = ttk.PanedWindow(self.frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ttk.LabelFrame(paned, text="Projects", padding=5)
        paned.add(top_frame, weight=1)

        tree_frame = ttk.Frame(top_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "priority", "tags")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=6)

        self.tree.heading("name", text="Name")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("tags", text="Tags")

        self.tree.column("name", width=200)
        self.tree.column("priority", width=120)
        self.tree.column("tags", width=250)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button row for projects
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        add_btn = ttk.Button(btn_frame, text="Add Project", command=self.add_project)
        add_btn.pack(side=tk.LEFT, padx=5)

        rename_btn = ttk.Button(btn_frame, text="Rename", command=self.rename_project)
        rename_btn.pack(side=tk.LEFT, padx=5)

        priority_btn = ttk.Button(btn_frame, text="Edit Priority", command=self.edit_priority)
        priority_btn.pack(side=tk.LEFT, padx=5)

        tags_btn = ttk.Button(btn_frame, text="Edit Tags", command=self.edit_tags)
        tags_btn.pack(side=tk.LEFT, padx=5)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ttk.LabelFrame(paned, text="Background Tasks", padding=5)
        paned.add(bottom_frame, weight=1)

        bg_tree_frame = ttk.Frame(bottom_frame)
        bg_tree_frame.pack(fill=tk.BOTH, expand=True)

        bg_columns = ("name",)
        self.bg_tree = ttk.Treeview(bg_tree_frame, columns=bg_columns, show="headings", height=6)

        self.bg_tree.heading("name", text="Task Name")
        self.bg_tree.column("name", width=400)

        bg_scrollbar = ttk.Scrollbar(bg_tree_frame, orient=tk.VERTICAL, command=self.bg_tree.yview)
        self.bg_tree.configure(yscrollcommand=bg_scrollbar.set)

        self.bg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button row for background tasks
        bg_btn_frame = ttk.Frame(bottom_frame)
        bg_btn_frame.pack(fill=tk.X, pady=5)

        bg_add_btn = ttk.Button(bg_btn_frame, text="Add Task", command=self.add_background_task)
        bg_add_btn.pack(side=tk.LEFT, padx=5)

        bg_rename_btn = ttk.Button(bg_btn_frame, text="Rename", command=self.rename_background_task)
        bg_rename_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(bg_btn_frame, text="Refresh All", command=self.refresh)
        refresh_btn.pack(side=tk.LEFT, padx=5)

    def refresh(self):
        """Refresh both projects and background tasks lists."""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.bg_tree.get_children():
            self.bg_tree.delete(item)

        # Get regular projects
        projects = db.list_projects(is_background=False)

        for project in projects:
            priority_label = f"{project.priority} ({PRIORITY_LABELS.get(project.priority, 'Unknown')})"
            tags_str = ", ".join(project.tags) if project.tags else ""

            self.tree.insert("", tk.END, iid=project.name, values=(
                project.name,
                priority_label,
                tags_str
            ))

        # Get background tasks
        bg_tasks = db.list_projects(is_background=True)

        for task in bg_tasks:
            self.bg_tree.insert("", tk.END, iid=task.name, values=(
                task.name,
            ))

    def add_project(self):
        """Show dialog to add a new project."""
        AddProjectDialog(self.app.root, self.app)

    def add_background_task(self):
        """Show dialog to add a new background task."""
        AddBackgroundTaskDialog(self.app.root, self.app)

    def edit_priority(self):
        """Edit priority of selected project."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a project")
            return

        project_name = selection[0]
        EditPriorityDialog(self.app.root, self.app, project_name)

    def edit_tags(self):
        """Edit tags of selected project."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a project")
            return

        project_name = selection[0]
        EditTagsDialog(self.app.root, self.app, project_name)

    def rename_project(self):
        """Rename selected project."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a project")
            return

        project_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, project_name)

    def rename_background_task(self):
        """Rename selected background task."""
        selection = self.bg_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a task")
            return

        task_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, task_name)


class StopSessionDialog:
    """Dialog for stopping a session with optional notes."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Stop: {project_name}")
        self.dialog.geometry("400x200")
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
        ttk.Label(self.dialog, text="Notes (optional):").pack(pady=(15, 5))

        self.notes_text = tk.Text(self.dialog, height=4, width=45)
        self.notes_text.pack(pady=5, padx=15)

        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Stop Session", command=self._do_stop).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_stop(self):
        """Stop the session."""
        notes = self.notes_text.get("1.0", tk.END).strip()
        db.stop_session(project_name=self.project_name, notes=notes)
        self.dialog.destroy()
        self.app.timer_tab.refresh()


class LogSessionDialog:
    """Dialog for logging a manual session entry."""

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Log Manual Entry")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 300) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.project_var = tk.StringVar()
        self.duration_var = tk.StringVar()
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Project
        ttk.Label(main_frame, text="Project:").grid(row=0, column=0, sticky=tk.W, pady=5)
        projects = db.list_projects()
        project_names = [p.name for p in projects]
        project_combo = ttk.Combobox(main_frame, textvariable=self.project_var, values=project_names, width=30)
        project_combo.grid(row=0, column=1, sticky=tk.W, pady=5)

        # Duration
        ttk.Label(main_frame, text="Duration:").grid(row=1, column=0, sticky=tk.W, pady=5)
        duration_entry = ttk.Entry(main_frame, textvariable=self.duration_var, width=20)
        duration_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(e.g., 1h30m, 45m, 2h)").grid(row=1, column=2, sticky=tk.W, padx=5)

        # Date
        ttk.Label(main_frame, text="Date:").grid(row=2, column=0, sticky=tk.W, pady=5)
        date_entry = ttk.Entry(main_frame, textvariable=self.date_var, width=20)
        date_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(YYYY-MM-DD)").grid(row=2, column=2, sticky=tk.W, padx=5)

        # Notes
        ttk.Label(main_frame, text="Notes:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.notes_text = tk.Text(main_frame, height=4, width=35)
        self.notes_text.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)

        ttk.Button(btn_frame, text="Log Session", command=self._do_log).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_log(self):
        """Log the session."""
        project = self.project_var.get().strip()
        duration_str = self.duration_var.get().strip()
        date_str = self.date_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not project:
            messagebox.showwarning("Warning", "Please enter a project name", parent=self.dialog)
            return

        if not duration_str:
            messagebox.showwarning("Warning", "Please enter a duration", parent=self.dialog)
            return

        try:
            duration = parse_duration_string(duration_str)
            if duration.total_seconds() == 0:
                raise ValueError("Duration must be greater than 0")
        except Exception:
            messagebox.showerror("Error", "Invalid duration format. Use formats like: 1h30m, 45m, 2h", parent=self.dialog)
            return

        try:
            # Parse date and set time to 5 PM as end time
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=17, minute=0, second=0)
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD", parent=self.dialog)
            return

        db.log_session(project_name=project, duration=duration, notes=notes, date=date)
        self.dialog.destroy()
        messagebox.showinfo("Success", f"Logged {duration_str} for {project}")


class AddProjectDialog:
    """Dialog for adding a new project."""

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Project")
        self.dialog.geometry("350x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = tk.StringVar()
        self.priority_var = tk.IntVar(value=3)
        self.tags_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=25)
        name_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        name_entry.focus()

        # Priority
        ttk.Label(main_frame, text="Priority:").grid(row=1, column=0, sticky=tk.W, pady=5)
        priority_spin = ttk.Spinbox(main_frame, textvariable=self.priority_var, from_=1, to=5, width=10)
        priority_spin.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Tags
        ttk.Label(main_frame, text="Tags:").grid(row=2, column=0, sticky=tk.W, pady=5)
        tags_entry = ttk.Entry(main_frame, textvariable=self.tags_var, width=25)
        tags_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="(comma-separated)").grid(row=2, column=2, sticky=tk.W, padx=5)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=20)

        ttk.Button(btn_frame, text="Add", command=self._do_add).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_add(self):
        """Add the project."""
        name = self.name_var.get().strip()
        priority = self.priority_var.get()
        tags_str = self.tags_var.get().strip()

        if not name:
            messagebox.showwarning("Warning", "Please enter a project name", parent=self.dialog)
            return

        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        try:
            db.create_project(name, priority=priority, tags=tags)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)


class AddBackgroundTaskDialog:
    """Dialog for adding a new background task."""

    def __init__(self, parent, app: DerbyApp):
        self.app = app

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Background Task")
        self.dialog.geometry("300x120")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 300) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 120) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(main_frame, text="Task Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=25)
        name_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        name_entry.focus()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Add", command=self._do_add).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_add(self):
        """Add the background task."""
        name = self.name_var.get().strip()

        if not name:
            messagebox.showwarning("Warning", "Please enter a task name", parent=self.dialog)
            return

        try:
            db.create_project(name, is_background=True)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)


class EditPriorityDialog:
    """Dialog for editing a project's priority."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        # Get current priority
        project = db.get_project(project_name)
        current_priority = project.priority if project else 3

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Priority: {project_name}")
        self.dialog.geometry("300x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 300) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.priority_var = tk.IntVar(value=current_priority)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Project: {self.project_name}").pack(pady=5)

        priority_frame = ttk.Frame(main_frame)
        priority_frame.pack(pady=10)

        ttk.Label(priority_frame, text="Priority:").pack(side=tk.LEFT)
        priority_spin = ttk.Spinbox(priority_frame, textvariable=self.priority_var, from_=1, to=5, width=10)
        priority_spin.pack(side=tk.LEFT, padx=10)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Save", command=self._do_save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_save(self):
        """Save the priority."""
        priority = self.priority_var.get()
        try:
            db.update_project_priority(self.project_name, priority)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)


class EditTagsDialog:
    """Dialog for editing a project's tags."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.project_name = project_name

        # Get project and current tags
        self.project = db.get_project(project_name)
        current_tags = self.project.tags if self.project else []

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Tags: {project_name}")
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.tags_var = tk.StringVar(value=", ".join(current_tags))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Project: {self.project_name}").pack(pady=5)

        tags_frame = ttk.Frame(main_frame)
        tags_frame.pack(fill=tk.X, pady=10)

        ttk.Label(tags_frame, text="Tags:").pack(side=tk.LEFT)
        tags_entry = ttk.Entry(tags_frame, textvariable=self.tags_var, width=35)
        tags_entry.pack(side=tk.LEFT, padx=10)
        tags_entry.focus()

        ttk.Label(main_frame, text="(comma-separated)", foreground="gray").pack()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Save", command=self._do_save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_save(self):
        """Save the tags."""
        if not self.project:
            messagebox.showerror("Error", "Project not found", parent=self.dialog)
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
                # Get the original case from input if possible
                original_tag = next((t.strip() for t in tags_str.split(",") if t.strip().lower() == tag), tag)
                db.add_tag_to_project(self.project.id, original_tag)

            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)


class RenameProjectDialog:
    """Dialog for renaming a project."""

    def __init__(self, parent, app: DerbyApp, project_name: str):
        self.app = app
        self.old_name = project_name

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Rename Project")
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = tk.StringVar(value=project_name)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Current name: {self.old_name}").pack(pady=5)

        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=10)

        ttk.Label(name_frame, text="New name:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=10)
        name_entry.focus()
        name_entry.select_range(0, tk.END)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Rename", command=self._do_rename).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=10)

    def _do_rename(self):
        """Rename the project."""
        new_name = self.name_var.get().strip()

        if not new_name:
            messagebox.showwarning("Warning", "Please enter a project name", parent=self.dialog)
            return

        if new_name == self.old_name:
            self.dialog.destroy()
            return

        try:
            result = db.rename_project(self.old_name, new_name)
            if result is None:
                messagebox.showerror("Error", "Project not found", parent=self.dialog)
                return

            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
            self.app.history_tab.refresh()
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                messagebox.showerror("Error", f"A project named '{new_name}' already exists", parent=self.dialog)
            else:
                messagebox.showerror("Error", str(e), parent=self.dialog)


if __name__ == "__main__":
    app = DerbyApp()
    app.run()
