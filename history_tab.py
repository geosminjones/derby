#!/usr/bin/env python3
"""
history_tab.py - History tab for viewing past sessions in Derby GUI
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import customtkinter as ctk

import db
import themes
from dialogs import CTkMessagebox, CTkConfirmDialog

if TYPE_CHECKING:
    from gui import DerbyApp, TreeviewFrame


class HistoryTab:
    """History tab for viewing past sessions."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self.project_filter = ctk.StringVar(value="All")
        self.period_filter = ctk.StringVar(value="All")
        self.limit_var = ctk.StringVar(value="50")
        self._build_ui()

    def _build_ui(self):
        """Build the history tab UI."""
        # Runtime import to avoid circular dependency
        from gui import TreeviewFrame

        # Filter section
        filter_frame = ctk.CTkFrame(self.frame, fg_color=themes.get_colors()["card_bg"])
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
