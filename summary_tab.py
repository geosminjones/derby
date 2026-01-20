#!/usr/bin/env python3
"""
summary_tab.py - Summary tab for time aggregations in Derby GUI
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import customtkinter as ctk

import db
import themes
from themes import FONT_FAMILY

if TYPE_CHECKING:
    from gui import DerbyApp, TreeviewFrame


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

        # Main content area
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects Summary
        # =====================================================================
        top_frame = ctk.CTkFrame(content_frame, fg_color=themes.get_colors()["container_bg"])
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
        bottom_frame = ctk.CTkFrame(content_frame, fg_color=themes.get_colors()["container_bg"])
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
        from gui import TreeviewFrame

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
        from gui import TreeviewFrame

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
        from gui import TreeviewFrame

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
        from gui import TreeviewFrame

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
        from gui import TreeviewFrame

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
        from gui import TreeviewFrame

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
        self.tree_frame.configure_tag("separator", background=themes.get_colors()["separator"])

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
        self.tree_frame.configure_tag("separator", background=themes.get_colors()["separator"])
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
        self.tree_frame.configure_tag("separator", background=themes.get_colors()["separator"])
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
