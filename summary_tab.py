#!/usr/bin/env python3
"""
summary_tab.py - Summary tab for time aggregations in Derby GUI
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import customtkinter as ctk
from tkinter import ttk

import db
import themes
from ctk_table import CTkTable
from themes import FONT_FAMILY
from gui_utils import batch_update

if TYPE_CHECKING:
    from gui import DerbyApp


# Priority labels for display
PRIORITY_LABELS = {
    1: "Critical",
    2: "High",
    3: "Medium",
    4: "Low",
    5: "Very Low"
}


class SummaryTab:
    """Summary tab for time aggregations with split view for projects and background tasks."""

    # Day abbreviations for column headers
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self.period_var = ctk.StringVar(value="today")
        self.sort_var = ctk.StringVar(value="priority")
        self.group_var = ctk.BooleanVar(value=False)
        self.current_view = "standard"  # "standard", "weekly", or "monthly"
        self.bg_current_view = "standard"  # Track bg table view separately
        self._tables_initialized = False  # Track if tables have been created
        self._build_ui()

    def _build_ui(self):
        """Build the summary tab UI with split view."""
        # Runtime import to avoid circular dependency
        from gui import TreeviewFrame

        # Period selection
        period_frame = ctk.CTkFrame(self.frame, fg_color=themes.get_colors()["card_bg"])
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
        sort_frame = ctk.CTkFrame(self.frame, fg_color=themes.get_colors()["card_bg"])
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

        # Main content area - use ttk.PanedWindow for resizable split
        colors = themes.get_colors()

        # Configure ttk style for the paned window sash
        style = ttk.Style()
        style.configure("Summary.TPanedwindow", background=colors["bg_dark"])

        self.paned = ttk.PanedWindow(self.frame, orient="vertical", style="Summary.TPanedwindow")
        self.paned.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP PANE: Regular Projects Summary
        # =====================================================================
        top_frame = ctk.CTkFrame(self.paned, fg_color=colors["container_bg"])

        ctk.CTkLabel(top_frame, text="Projects", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.table_container = ctk.CTkFrame(top_frame, fg_color="transparent")
        self.table_container.pack(fill=ctk.BOTH, expand=True, padx=10)

        # Tables will be created lazily on first refresh
        self.table = None
        self.table_weekly = None
        self.table_monthly = None

        # Project total label
        self.project_total_var = ctk.StringVar(value="Projects Total: 0h 00m")
        project_total_label = ctk.CTkLabel(top_frame, textvariable=self.project_total_var, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"))
        project_total_label.pack(pady=3)

        # =====================================================================
        # BOTTOM PANE: Background Tasks Summary
        # =====================================================================
        bottom_frame = ctk.CTkFrame(self.paned, fg_color=colors["container_bg"])

        ctk.CTkLabel(bottom_frame, text="Background Tasks", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.bg_table_container = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        self.bg_table_container.pack(fill=ctk.BOTH, expand=True, padx=10)

        # Background task tables will be created lazily on first refresh
        self.bg_table = None
        self.bg_table_weekly = None
        self.bg_table_monthly = None

        # Background tasks total label
        self.bg_total_var = ctk.StringVar(value="Tasks Total: 0h 00m")
        bg_total_label = ctk.CTkLabel(bottom_frame, textvariable=self.bg_total_var, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"))
        bg_total_label.pack(pady=3)

        # Add frames to paned window with weight for initial sizing
        self.paned.add(top_frame, weight=2)
        self.paned.add(bottom_frame, weight=1)

        # Combined total at bottom
        self.total_var = ctk.StringVar(value="Combined Total: 0h 00m")
        total_label = ctk.CTkLabel(self.frame, textvariable=self.total_var, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        total_label.pack(pady=5)

    def _initialize_tables(self):
        """Create all three table variants for both projects and background tasks."""
        if self._tables_initialized:
            return

        # =====================================================================
        # PROJECT TABLES
        # =====================================================================

        # Standard view table (for today/all time)
        show_row_dividers = db.get_setting("show_row_dividers", "1") == "1"
        self.table_standard = CTkTable(
            self.table_container,
            columns=["Project", "Priority", "Tags", "Time", "Hours"],
            widths=[160, 50, 260, 90, 70],
            anchors=['w', 'w', 'w', 'w', 'w'],
            show_header=True,
            show_dividers=show_row_dividers
        )

        # Weekly view table (placeholder columns, will be updated dynamically)
        self.table_weekly = CTkTable(
            self.table_container,
            columns=["Project", "Priority", "Tags", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"],
            widths=[100, 50, 200, 50, 50, 50, 50, 50, 50, 50, 55],
            anchors=['w'] + ['w'] * 10,
            show_header=True,
            show_dividers=show_row_dividers
        )

        # Monthly view table (placeholder columns, will be updated dynamically)
        self.table_monthly = CTkTable(
            self.table_container,
            columns=["Project", "Priority", "Tags", "1-5", "6-10", "11-15", "16-20", "21-25", "26-31", "Total"],
            widths=[100, 50, 200, 50, 50, 50, 50, 50, 50, 55],
            anchors=['w'] + ['w'] * 9,
            show_header=True,
            show_dividers=show_row_dividers
        )

        # =====================================================================
        # BACKGROUND TASK TABLES
        # =====================================================================

        # Standard view table
        self.bg_table_standard = CTkTable(
            self.bg_table_container,
            columns=["Task", "Time", "Hours"],
            widths=[250, 120, 100],
            anchors=['w', 'w', 'w'],
            show_header=True,
            show_dividers=show_row_dividers
        )

        # Weekly view table
        self.bg_table_weekly = CTkTable(
            self.bg_table_container,
            columns=["Task", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Total"],
            widths=[120, 55, 55, 55, 55, 55, 55, 55, 60],
            anchors=['w'] + ['w'] * 8,
            show_header=True,
            show_dividers=show_row_dividers
        )

        # Monthly view table
        self.bg_table_monthly = CTkTable(
            self.bg_table_container,
            columns=["Task", "1-5", "6-10", "11-15", "16-20", "21-25", "26-31", "Total"],
            widths=[120, 55, 55, 55, 55, 55, 55, 60],
            anchors=['w'] + ['w'] * 7,
            show_header=True,
            show_dividers=show_row_dividers
        )

        # Set default active tables
        self.table = self.table_standard
        self.bg_table = self.bg_table_standard

        # Show only standard tables initially
        self._show_table_view("standard")
        self._show_bg_table_view("standard")

        self._tables_initialized = True

    def _update_table_divider_settings(self):
        """Update show_dividers setting on all tables based on current setting."""
        show_row_dividers = db.get_setting("show_row_dividers", "1") == "1"
        if self._tables_initialized:
            self.table_standard.show_dividers = show_row_dividers
            self.table_weekly.show_dividers = show_row_dividers
            self.table_monthly.show_dividers = show_row_dividers
            self.bg_table_standard.show_dividers = show_row_dividers
            self.bg_table_weekly.show_dividers = show_row_dividers
            self.bg_table_monthly.show_dividers = show_row_dividers

    def _show_table_view(self, view: str):
        """Show the specified project table and hide others."""
        # Unpack all tables (use getattr to handle case where tables aren't created yet)
        if getattr(self, 'table_standard', None):
            self.table_standard.pack_forget()
        if getattr(self, 'table_weekly', None):
            self.table_weekly.pack_forget()
        if getattr(self, 'table_monthly', None):
            self.table_monthly.pack_forget()

        # Pack the requested table
        if view == "standard":
            self.table = self.table_standard
        elif view == "weekly":
            self.table = self.table_weekly
        elif view == "monthly":
            self.table = self.table_monthly

        if self.table:
            self.table.pack(fill=ctk.BOTH, expand=True)
        self.current_view = view

    def _show_bg_table_view(self, view: str):
        """Show the specified background task table and hide others."""
        # Unpack all tables (use getattr to handle case where tables aren't created yet)
        if getattr(self, 'bg_table_standard', None):
            self.bg_table_standard.pack_forget()
        if getattr(self, 'bg_table_weekly', None):
            self.bg_table_weekly.pack_forget()
        if getattr(self, 'bg_table_monthly', None):
            self.bg_table_monthly.pack_forget()

        # Pack the requested table
        if view == "standard":
            self.bg_table = self.bg_table_standard
        elif view == "weekly":
            self.bg_table = self.bg_table_weekly
        elif view == "monthly":
            self.bg_table = self.bg_table_monthly

        if self.bg_table:
            self.bg_table.pack(fill=ctk.BOTH, expand=True)
        self.bg_current_view = view

    def _update_weekly_columns(self, week_start: datetime):
        """Update the weekly table column headers with actual dates."""
        day_headings = ["Project", "Priority", "Tags"]
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_headings.append(f"{self.DAY_NAMES[i]} {day_date.day}")
        day_headings.append("Total")

        # Update project table headers
        for i, heading in enumerate(day_headings):
            self.table_weekly.update_header(i, heading)

        # Update bg task table headers (no Priority/Tags columns)
        bg_headings = ["Task"]
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            bg_headings.append(f"{self.DAY_NAMES[i]} {day_date.day}")
        bg_headings.append("Total")
        for i, heading in enumerate(bg_headings):
            self.bg_table_weekly.update_header(i, heading)

    def _update_monthly_columns(self, month_start: datetime):
        """Update the monthly table column headers with actual date ranges."""
        import calendar

        year = month_start.year
        month = month_start.month
        days_in_month = calendar.monthrange(year, month)[1]

        period_headings = ["Project", "Priority", "Tags"]
        period_starts = [1, 6, 11, 16, 21, 26]

        for i, start_day in enumerate(period_starts):
            if i < 5:
                end_day = start_day + 4
                header = f"{start_day}-{end_day}"
            else:
                header = f"{start_day}-{days_in_month}"
            period_headings.append(header)
        period_headings.append("Total")

        # Update project table headers
        for i, heading in enumerate(period_headings):
            self.table_monthly.update_header(i, heading)

        # Update bg task table headers (no Priority/Tags columns)
        bg_headings = ["Task"]
        for i, start_day in enumerate(period_starts):
            if i < 5:
                end_day = start_day + 4
                header = f"{start_day}-{end_day}"
            else:
                header = f"{start_day}-{days_in_month}"
            bg_headings.append(header)
        bg_headings.append("Total")
        for i, heading in enumerate(bg_headings):
            self.bg_table_monthly.update_header(i, heading)

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

        # Initialize tables on first refresh (lazy initialization)
        if not self._tables_initialized:
            self._initialize_tables()

        # Update divider settings on all tables (in case setting changed)
        self._update_table_divider_settings()

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

        # Switch view type if needed (show/hide tables instead of destroy/create)
        if period == "week":
            if self.current_view != "weekly":
                self._show_table_view("weekly")
            if self.bg_current_view != "weekly":
                self._show_bg_table_view("weekly")
            self._refresh_weekly(start_date, end_date)
        elif period in ("month", "last_month"):
            if self.current_view != "monthly":
                self._show_table_view("monthly")
            if self.bg_current_view != "monthly":
                self._show_bg_table_view("monthly")
            self._refresh_monthly(start_date, end_date)
        else:
            if self.current_view != "standard":
                self._show_table_view("standard")
            if self.bg_current_view != "standard":
                self._show_bg_table_view("standard")
            self._refresh_standard(start_date, end_date)

    def _refresh_standard(self, start_date, end_date):
        """Refresh with standard (non-weekly) view."""
        sort_by = self.sort_var.get()
        group_by = self.group_var.get()

        # Use batch_update to defer painting for both tables
        with batch_update(self.table_container):
            with batch_update(self.bg_table_container):
                self._refresh_standard_inner(start_date, end_date, sort_by, group_by)

    def _refresh_standard_inner(self, start_date, end_date, sort_by, group_by):
        """Inner refresh logic for standard view (called within batch_update)."""
        # Update column headers and widths based on sort mode and group mode
        # Use update_columns to rebuild header with correct widths
        if group_by:
            # When grouping, collapse the unused Priority/Tags columns (indices 1-2)
            # First column shows group label, then minimal space, then Time/Hours
            first_col = "Tag" if sort_by == "tag" else "Priority"
            self.table_standard.update_columns(
                columns=[first_col, "", "", "Time", "Hours"],
                widths=[100, 0, 0, 90, 70],
                anchors=['w', 'w', 'w', 'w', 'w']
            )
        else:
            self.table_standard.update_columns(
                columns=["Project", "Priority", "Tags", "Time", "Hours"],
                widths=[160, 50, 260, 90, 70],
                anchors=['w', 'w', 'w', 'w', 'w']
            )

        # Clear background table
        self.bg_table.clear()

        # Build a map of project_name -> tags for quick lookup
        all_projects = db.list_projects(is_background=False)
        project_tags_map = {p.name: p.tags for p in all_projects}
        project_priority_map = {p.name: p.priority for p in all_projects}

        project_total_seconds = 0
        row_counter = 0

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

                    priority_label = str(priority)

                    self.table.add_row(f"priority_{priority}", (priority_label, "", "", time_str, hours_decimal))
            else:
                # Populate project table with separators between priority groups
                last_priority = None
                for project_name, data in project_summary.items():
                    seconds = data["seconds"]
                    priority = data["priority"]
                    project_total_seconds += seconds

                    # Add separator between priority groups
                    if last_priority is not None and priority != last_priority:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
                    last_priority = priority

                    hours = seconds // 3600
                    mins = (seconds % 3600) // 60
                    secs = seconds % 60
                    time_str = f"{hours}:{mins:02d}:{secs:02d}"
                    hours_decimal = round(seconds / 3600, 2)

                    priority_label = str(priority)
                    tags_str = ", ".join(project_tags_map.get(project_name, []))

                    self.table.add_row(f"project_{row_counter}", (project_name, priority_label, tags_str, time_str, hours_decimal))
                    row_counter += 1
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

                    self.table.add_row(f"tag_{tag_name}", (tag_name, "", "", time_str, hours_decimal))
            else:
                seen_projects = set()

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
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
                        priority = project_priority_map.get(project_name, 3)
                        priority_label = str(priority)
                        # When sorting by tag, show only the current tag being grouped by
                        tags_str = tag_name

                        self.table.add_row(f"project_{row_counter}", (display_name, priority_label, tags_str, time_str, hours_decimal))
                        row_counter += 1

        # Get background task summary
        bg_summary = db.get_summary_with_priority(start_date=start_date, end_date=end_date, is_background=True)

        # Populate background task table
        bg_total_seconds = 0
        bg_row_counter = 0
        for task_name, data in bg_summary.items():
            seconds = data["seconds"]
            bg_total_seconds += seconds

            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            secs = seconds % 60
            time_str = f"{hours}:{mins:02d}:{secs:02d}"
            hours_decimal = round(seconds / 3600, 2)

            self.bg_table.add_row(f"task_{bg_row_counter}", (task_name, time_str, hours_decimal))
            bg_row_counter += 1

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

        # Use batch_update to defer painting for both tables
        with batch_update(self.table_container):
            with batch_update(self.bg_table_container):
                self._refresh_weekly_inner(start_date, end_date, sort_by, group_by)

    def _refresh_weekly_inner(self, start_date: datetime, end_date: datetime, sort_by, group_by):
        """Inner refresh logic for weekly view (called within batch_update)."""
        # Build day headings (will be updated with actual dates below)
        day_headings_base = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Update column header and widths based on group mode
        if group_by:
            # When grouping, collapse the unused Priority/Tags columns (indices 1-2)
            first_col = "Tag" if sort_by == "tag" else "Priority"
            self.table_weekly.update_columns(
                columns=[first_col, "", ""] + day_headings_base + ["Total"],
                widths=[80, 0, 0, 50, 50, 50, 50, 50, 50, 50, 55],
                anchors=['w'] + ['w'] * 10
            )
        else:
            self.table_weekly.update_columns(
                columns=["Project", "Priority", "Tags"] + day_headings_base + ["Total"],
                widths=[100, 50, 200, 50, 50, 50, 50, 50, 50, 50, 55],
                anchors=['w'] + ['w'] * 10
            )

        # Update column headers with actual dates (after update_columns)
        self._update_weekly_columns(start_date)

        # Clear background table
        self.bg_table.clear()

        # Build a map of project_name -> tags for quick lookup
        all_projects = db.list_projects(is_background=False)
        project_tags_map = {p.name: p.tags for p in all_projects}
        project_priority_map = {p.name: p.priority for p in all_projects}

        # Build date strings for each day of the week
        day_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        project_total_seconds = 0
        project_daily_totals = [0] * 7
        row_counter = 0

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
                    priority_label = str(priority)

                    self.table.add_row(f"priority_{priority}", (priority_label, "", "", *day_values, total_str))
            else:
                last_priority = None

                for project_name, data in project_summary.items():
                    project_total_seconds += data["total"]
                    priority = data["priority"]

                    if last_priority is not None and priority != last_priority:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
                    last_priority = priority

                    day_values = []
                    for i, date_str in enumerate(day_dates):
                        seconds = data["days"].get(date_str, 0)
                        project_daily_totals[i] += seconds
                        day_values.append(self._format_time_short(seconds))

                    total_str = self._format_time_short(data["total"])
                    priority_label = str(priority)
                    tags_str = ", ".join(project_tags_map.get(project_name, []))

                    self.table.add_row(f"project_{row_counter}", (project_name, priority_label, tags_str, *day_values, total_str))
                    row_counter += 1
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

                    self.table.add_row(f"tag_{tag_name}", (tag_name, "", "", *day_values, total_str))
            else:
                seen_projects = set()
                project_daily_counted = {}

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
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
                        priority = project_priority_map.get(project_name, 3)
                        priority_label = str(priority)
                        # When sorting by tag, show only the current tag being grouped by
                        tags_str = tag_name

                        self.table.add_row(f"project_{row_counter}", (display_name, priority_label, tags_str, *day_values, total_str))
                        row_counter += 1

        # Add project totals row
        project_daily_total_values = [self._format_time_short(s) for s in project_daily_totals]
        project_total_str = self._format_time_short(project_total_seconds)

        self.table.add_row("total_row", ("TOTAL", "", "", *project_daily_total_values, project_total_str), is_total=True)

        # Get per-day summary for background tasks
        bg_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=True)

        bg_total_seconds = 0
        bg_daily_totals = [0] * 7
        bg_row_counter = 0

        for task_name, data in bg_summary.items():
            bg_total_seconds += data["total"]

            day_values = []
            for i, date_str in enumerate(day_dates):
                seconds = data["days"].get(date_str, 0)
                bg_daily_totals[i] += seconds
                day_values.append(self._format_time_short(seconds))

            total_str = self._format_time_short(data["total"])

            self.bg_table.add_row(f"task_{bg_row_counter}", (task_name, *day_values, total_str))
            bg_row_counter += 1

        # Add background task totals row
        bg_daily_total_values = [self._format_time_short(s) for s in bg_daily_totals]
        bg_total_str = self._format_time_short(bg_total_seconds)

        self.bg_table.add_row("bg_total_row", ("TOTAL", *bg_daily_total_values, bg_total_str), is_total=True)

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

        # Use batch_update to defer painting for both tables
        with batch_update(self.table_container):
            with batch_update(self.bg_table_container):
                self._refresh_monthly_inner(start_date, end_date, sort_by, group_by)

    def _refresh_monthly_inner(self, start_date: datetime, end_date: datetime, sort_by, group_by):
        """Inner refresh logic for monthly view (called within batch_update)."""
        import calendar

        # Build period headings (will be updated with actual date ranges below)
        period_headings_base = ["1-5", "6-10", "11-15", "16-20", "21-25", "26-31"]

        # Update column header and widths based on group mode
        if group_by:
            # When grouping, collapse the unused Priority/Tags columns (indices 1-2)
            first_col = "Tag" if sort_by == "tag" else "Priority"
            self.table_monthly.update_columns(
                columns=[first_col, "", ""] + period_headings_base + ["Total"],
                widths=[80, 0, 0, 50, 50, 50, 50, 50, 50, 55],
                anchors=['w'] + ['w'] * 9
            )
        else:
            self.table_monthly.update_columns(
                columns=["Project", "Priority", "Tags"] + period_headings_base + ["Total"],
                widths=[100, 50, 200, 50, 50, 50, 50, 50, 50, 55],
                anchors=['w'] + ['w'] * 9
            )

        # Update column headers with actual date ranges (after update_columns)
        self._update_monthly_columns(start_date)

        # Clear background table
        self.bg_table.clear()

        # Build a map of project_name -> tags for quick lookup
        all_projects = db.list_projects(is_background=False)
        project_tags_map = {p.name: p.tags for p in all_projects}
        project_priority_map = {p.name: p.priority for p in all_projects}

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
        row_counter = 0

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
                    priority_label = str(priority)

                    self.table.add_row(f"priority_{priority}", (priority_label, "", "", *period_values, total_str))
            else:
                last_priority = None

                for project_name, data in project_summary.items():
                    project_total_seconds += data["total"]
                    priority = data["priority"]

                    if last_priority is not None and priority != last_priority:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
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
                    priority_label = str(priority)
                    tags_str = ", ".join(project_tags_map.get(project_name, []))

                    self.table.add_row(f"project_{row_counter}", (project_name, priority_label, tags_str, *period_values, total_str))
                    row_counter += 1
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

                    self.table.add_row(f"tag_{tag_name}", (tag_name, "", "", *period_values, total_str))
            else:
                seen_projects = set()
                project_period_counted = {}

                last_tag = None
                for tag_name, tag_data in tag_summary.items():
                    if last_tag is not None:
                        if db.get_setting("show_group_separators", "1") == "1":
                            self.table.add_divider()
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
                        priority = project_priority_map.get(project_name, 3)
                        priority_label = str(priority)
                        # When sorting by tag, show only the current tag being grouped by
                        tags_str = tag_name

                        self.table.add_row(f"project_{row_counter}", (display_name, priority_label, tags_str, *period_values, total_str))
                        row_counter += 1

        # Add project totals row
        project_period_total_values = [self._format_time_short(s) for s in project_period_totals]
        project_total_str = self._format_time_short(project_total_seconds)

        self.table.add_row("total_row", ("TOTAL", "", "", *project_period_total_values, project_total_str), is_total=True)

        # Get per-day summary for background tasks
        bg_summary = db.get_summary_by_day(start_date=start_date, end_date=end_date, is_background=True)

        bg_total_seconds = 0
        bg_period_totals = [0] * 6
        bg_row_counter = 0

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

            self.bg_table.add_row(f"task_{bg_row_counter}", (task_name, *period_values, total_str))
            bg_row_counter += 1

        # Add background task totals row
        bg_period_total_values = [self._format_time_short(s) for s in bg_period_totals]
        bg_total_str = self._format_time_short(bg_total_seconds)

        self.bg_table.add_row("bg_total_row", ("TOTAL", *bg_period_total_values, bg_total_str), is_total=True)

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
