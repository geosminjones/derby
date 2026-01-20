#!/usr/bin/env python3
"""
gui.py - Graphical user interface for Derby

A CustomTkinter-based GUI that provides the same functionality as the CLI
but with a visual interface and live timer updates.

Run with: python gui.py
"""

import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

import db
import themes
from themes import FONT_FAMILY

# Import tab components
from timer_tab import TimerTab, LogSessionDialog
from history_tab import HistoryTab
from summary_tab import SummaryTab
from projects_tab import ProjectsTab
from appearance_tab import AppearanceTab
from dialogs import CTkMessagebox, CTkConfirmDialog


class DerbyApp:
    """Main application window."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Derby")
        self.root.geometry("850x550")
        self.root.minsize(700, 450)

        # Initialize database
        db.init_database()

        # Load saved theme and apply TTK styles
        themes.load_saved_theme()
        self.ttk_style = tk.ttk.Style()
        themes.apply_ttk_styles(self.ttk_style)

        # Apply theme colors to root
        colors = themes.get_colors()
        self.root.configure(fg_color=colors["bg_dark"])

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
            "bg": themes.get_colors()["bg_dark"],
            "fg": themes.get_colors()["text_primary"],
            "activebackground": themes.get_colors()["bg_light"],
            "activeforeground": themes.get_colors()["text_primary"],
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
        self.main_container = ctk.CTkFrame(self.root, fg_color=themes.get_colors()["bg_dark"])
        self.main_container.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Header row with tab switcher and Stop All button
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill=ctk.X, padx=10, pady=(10, 5))

        # Tab switcher (segmented button) on the left
        self.tab_var = ctk.StringVar(value="Timer")
        self.tab_switcher = ctk.CTkSegmentedButton(
            header_frame,
            values=["Timer", "History", "Summary", "Projects", "Appearance"],
            variable=self.tab_var,
            command=self._on_tab_change,
            fg_color=themes.get_colors()["container_bg"],
            selected_color=themes.get_colors()["bg_light"],
            selected_hover_color=themes.get_colors()["bg_light"],
            unselected_color=themes.get_colors()["container_bg"],
            unselected_hover_color=themes.get_colors()["separator"],
            text_color=themes.get_colors()["text_primary"],
            text_color_disabled=themes.get_colors()["text_secondary"]
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
        for tab_name in ["Timer", "History", "Summary", "Projects", "Appearance"]:
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
        self.appearance_tab = AppearanceTab(self.tab_frames["Appearance"], self)

    def _create_status_bar(self):
        """Create status bar at bottom of window."""
        status_frame = ctk.CTkFrame(self.root, height=30, fg_color=themes.get_colors()["bg_dark"])
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
        elif tab_name == "Appearance":
            self.appearance_tab.refresh()

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

    # =========================================================================
    # Theme Switching Methods
    # =========================================================================

    def _capture_ui_state(self) -> dict:
        """Capture current UI state before rebuild for theme switching."""
        state = {
            'current_tab': self.current_tab,
            'geometry': self.root.geometry(),
            'timer': {
                'project_var': self.timer_tab.project_var.get(),
                'bg_task_var': self.timer_tab.bg_task_var.get(),
            },
            'history': {
                'project_filter': self.history_tab.project_filter.get(),
                'period_filter': self.history_tab.period_filter.get(),
                'limit_var': self.history_tab.limit_var.get(),
            },
            'summary': {
                'period_var': self.summary_tab.period_var.get(),
                'sort_var': self.summary_tab.sort_var.get(),
                'group_var': self.summary_tab.group_var.get(),
            },
        }
        return state

    def _restore_ui_state(self, state: dict):
        """Restore UI state after rebuild."""
        # Restore window geometry
        self.root.geometry(state['geometry'])

        # Restore timer tab state
        self.timer_tab.project_var.set(state['timer']['project_var'])
        self.timer_tab.bg_task_var.set(state['timer']['bg_task_var'])

        # Restore history tab state
        self.history_tab.project_filter.set(state['history']['project_filter'])
        self.history_tab.period_filter.set(state['history']['period_filter'])
        self.history_tab.limit_var.set(state['history']['limit_var'])

        # Restore summary tab state
        self.summary_tab.period_var.set(state['summary']['period_var'])
        self.summary_tab.sort_var.set(state['summary']['sort_var'])
        self.summary_tab.group_var.set(state['summary']['group_var'])

        # Switch to saved tab (this triggers refresh)
        self.tab_var.set(state['current_tab'])
        self._on_tab_change(state['current_tab'])

    def _rebuild_ui(self):
        """Destroy and recreate all UI components for theme switching."""
        # Destroy all child widgets (menu, containers, status bar)
        for widget in self.root.winfo_children():
            widget.destroy()

        # Reapply TTK styles with new theme
        self.ttk_style = tk.ttk.Style()
        themes.apply_ttk_styles(self.ttk_style)

        # Reset status variable
        self.status_var = ctk.StringVar(value="Ready")

        # Rebuild UI components
        self._create_menu()
        self._create_tabview()
        self._create_status_bar()

    def switch_theme(self, theme_name: str):
        """Switch theme and rebuild UI to apply changes.

        Args:
            theme_name: Theme identifier (e.g., 'dark', 'light', 'black')
        """
        # Capture current state
        state = self._capture_ui_state()

        # Apply new theme (updates themes module state + CustomTkinter appearance mode)
        themes.set_theme(theme_name)
        themes.save_theme_preference()

        # Update root window background
        self.root.configure(fg_color=themes.get_colors()["bg_dark"])

        # Rebuild UI
        self._rebuild_ui()

        # Restore state
        self._restore_ui_state(state)


class TreeviewFrame(ctk.CTkFrame):
    """A frame containing a treeview with scrollbar (using tkinter Treeview)."""

    def __init__(self, parent, columns, headings, widths, height=8, show_scrollbar=True, anchors=None):
        super().__init__(parent, fg_color=themes.get_colors()["bg_dark"])

        # Create treeview container
        tree_container = ctk.CTkFrame(self, fg_color="transparent")
        tree_container.pack(fill=ctk.BOTH, expand=True)

        # Create treeview (using tkinter since CustomTkinter doesn't have treeview)
        # TTK styles are configured centrally via themes.apply_ttk_styles()
        self.tree = tk.ttk.Treeview(tree_container, columns=columns, show="headings", height=height)

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


if __name__ == "__main__":
    app = DerbyApp()
    app.run()
