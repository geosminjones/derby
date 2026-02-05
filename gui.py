#!/usr/bin/env python3
"""
gui.py - Graphical user interface for Derby

A PyQt6-based GUI that provides the same functionality as the CLI
but with a visual interface and live timer updates.

Run with: python gui.py
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QMenuBar, QMenu, QFileDialog,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction, QIcon

import db
import themes
from themes import FONT_FAMILY
from jframes import TabButton, TabSwitcher, batch_update, MessageBox, ConfirmDialog

# Import tab components
from timer_tab import TimerTab, LogSessionDialog
from history_tab import HistoryTab
from summary_tab import SummaryTab
from projects_tab import ProjectsTab
from appearance_tab import AppearanceTab


class DerbyApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Derby")
        self.setWindowIcon(QIcon("jockey.ico"))
        self.setGeometry(100, 100, 850, 550)
        self.setMinimumSize(700, 450)

        # Initialize database
        db.init_database()

        # Load saved theme
        themes.load_saved_theme()

        # Apply theme colors
        colors = themes.get_colors()
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        # Build UI components
        self._create_menu()
        self._create_main_ui()
        self._create_status_bar()

        # Start timer update loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timers)
        self.timer.start(1000)

    def _create_menu(self):
        """Create application menu bar."""
        colors = themes.get_colors()

        menubar = self.menuBar()
        menubar.clear()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
            }}
            QMenuBar::item:selected {{
                background-color: {colors['bg_light']};
            }}
            QMenu {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
            }}
            QMenu::item:selected {{
                background-color: {colors['bg_light']};
            }}
        """)

        # File menu
        file_menu = menubar.addMenu("File")

        export_action = QAction("Export to CSV...", self)
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Session menu
        session_menu = menubar.addMenu("Session")

        log_action = QAction("Log Manual Entry...", self)
        log_action.triggered.connect(self._show_log_dialog)
        session_menu.addAction(log_action)

        stop_all_action = QAction("Stop All", self)
        stop_all_action.triggered.connect(self._stop_all)
        session_menu.addAction(stop_all_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_main_ui(self):
        """Create the main UI with tab switcher and content area."""
        colors = themes.get_colors()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Main container
        self.main_container = QFrame()
        self.main_container.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_dark']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(self.main_container)

        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(5)

        # Header row with tab switcher and Stop All button
        header_frame = QFrame()
        header_frame.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Tab switcher
        self.tab_switcher = TabSwitcher(["Timer", "Summary", "History", "Projects", "Settings"])
        self.tab_switcher.set_on_tab_change(self._on_tab_change)
        header_layout.addWidget(self.tab_switcher)

        header_layout.addStretch()

        # Stop All button
        self.stop_all_btn = QPushButton("Stop All")
        self.stop_all_btn.setFixedSize(100, 32)
        self.stop_all_btn.setFont(QFont(FONT_FAMILY, 11))
        self.stop_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['danger']};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['danger_hover']};
            }}
        """)
        self.stop_all_btn.clicked.connect(self._stop_all)
        header_layout.addWidget(self.stop_all_btn)

        container_layout.addWidget(header_frame)

        # Content frame (stacked widget for tabs)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")
        container_layout.addWidget(self.content_stack)

        # Create tab frames
        self.tab_frames = {}
        for tab_name in ["Timer", "Summary", "History", "Projects", "Settings"]:
            frame = QFrame()
            frame.setStyleSheet("background: transparent;")
            self.tab_frames[tab_name] = frame
            self.content_stack.addWidget(frame)

        # Create tab content
        self.timer_tab = TimerTab(self.tab_frames["Timer"], self)
        self.history_tab = HistoryTab(self.tab_frames["History"], self)
        self.summary_tab = SummaryTab(self.tab_frames["Summary"], self)
        self.projects_tab = ProjectsTab(self.tab_frames["Projects"], self)
        self.settings_tab = AppearanceTab(self.tab_frames["Settings"], self)

        self.current_tab = "Timer"

    def _create_status_bar(self):
        """Create status bar at bottom of window."""
        colors = themes.get_colors()

        status_bar = self.statusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {colors['bg_dark']};
                color: {colors['text_secondary']};
            }}
        """)
        status_bar.setFont(QFont(FONT_FAMILY, 10))
        self.status_message = "Ready"
        status_bar.showMessage(self.status_message)

    def _update_timers(self):
        """Update all active session durations."""
        # Update timer tab
        self.timer_tab.update_durations()

        # Update status bar
        active = db.get_active_sessions()
        if not active:
            self.status_message = "Idle - No active sessions"
        elif len(active) == 1:
            s = active[0]
            paused_indicator = " [PAUSED]" if s.is_paused else ""
            self.status_message = f"Tracking: {s.project_name} ({s.format_duration()}){paused_indicator}"
        else:
            total = sum(s.duration_seconds for s in active)
            paused_count = sum(1 for s in active if s.is_paused)
            h = total // 3600
            m = (total % 3600) // 60
            sec = total % 60
            paused_indicator = f" [{paused_count} paused]" if paused_count > 0 else ""
            self.status_message = f"Tracking: {len(active)} sessions (Total: {h}h {m:02d}m {sec:02d}s){paused_indicator}"

        self.statusBar().showMessage(self.status_message)

    def _on_tab_change(self, tab_name: str):
        """Switch to a different tab and refresh its data."""
        # Switch to the selected tab
        tab_index = list(self.tab_frames.keys()).index(tab_name)
        self.content_stack.setCurrentIndex(tab_index)
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
        elif tab_name == "Settings":
            self.settings_tab.refresh()

    def _export_csv(self):
        """Export sessions to CSV file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            "timetrack_export.csv",
            "CSV files (*.csv);;All files (*.*)"
        )
        if filepath:
            db.export_sessions_csv(filepath)
            MessageBox(self, "Export Complete", f"Exported to:\n{filepath}", "info")

    def _stop_all(self):
        """Stop all active sessions."""
        active = db.get_active_sessions()
        if not active:
            MessageBox(self, "Info", "No active sessions to stop", "info")
            return

        dialog = ConfirmDialog(self, "Confirm", f"Stop {len(active)} active session(s)?")
        if dialog.get_result():
            db.stop_all_sessions()
            self.timer_tab.refresh()

    def _show_log_dialog(self):
        """Show dialog to log manual entry."""
        LogSessionDialog(self, self)

    def _show_about(self):
        """Show about dialog."""
        MessageBox(
            self,
            "About Derby",
            f"Derby v1.0\n\n"
            f"A simple, local-first time tracking application.\n\n"
            f"Data stored in: {db.get_database_path()}",
            "info"
        )

    # =========================================================================
    # Theme Switching Methods
    # =========================================================================

    def _capture_ui_state(self) -> dict:
        """Capture current UI state before rebuild for theme switching."""
        state = {
            'current_tab': self.current_tab,
            'geometry': self.geometry(),
            'timer': {
                'project_var': self.timer_tab.project_var,
                'bg_task_var': self.timer_tab.bg_task_var,
            },
            'history': {
                'project_filter': self.history_tab.project_filter,
                'period_filter': self.history_tab.period_filter,
                'limit_var': self.history_tab.limit_var,
            },
            'summary': {
                'period_var': self.summary_tab.period_var,
                'sort_var': self.summary_tab.sort_var,
                'group_var': self.summary_tab.group_var,
            },
        }
        return state

    def _restore_ui_state(self, state: dict):
        """Restore UI state after rebuild."""
        # Restore window geometry
        self.setGeometry(state['geometry'])

        # Restore timer tab state
        self.timer_tab.project_var = state['timer']['project_var']
        self.timer_tab.bg_task_var = state['timer']['bg_task_var']

        # Restore history tab state
        self.history_tab.project_filter = state['history']['project_filter']
        self.history_tab.period_filter = state['history']['period_filter']
        self.history_tab.limit_var = state['history']['limit_var']

        # Restore summary tab state
        self.summary_tab.period_var = state['summary']['period_var']
        self.summary_tab.sort_var = state['summary']['sort_var']
        self.summary_tab.group_var = state['summary']['group_var']

        # Switch to saved tab
        self.tab_switcher.set_current_tab(state['current_tab'])
        self._on_tab_change(state['current_tab'])

    def switch_theme(self, theme_name: str):
        """Switch theme and rebuild UI to apply changes.

        Args:
            theme_name: Theme identifier (e.g., 'dark', 'light', 'black')
        """
        # Capture current state
        state = self._capture_ui_state()

        # Apply new theme
        themes.set_theme(theme_name)
        themes.save_theme_preference()

        # Update styling
        colors = themes.get_colors()
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        # Rebuild UI
        self._rebuild_ui()

        # Restore state
        self._restore_ui_state(state)

    def _rebuild_ui(self):
        """Destroy and recreate all UI components for theme switching."""
        # Remove central widget
        old_central = self.centralWidget()
        if old_central:
            old_central.deleteLater()

        # Rebuild UI components
        self._create_menu()
        self._create_main_ui()
        self._create_status_bar()


def main():
    """Start the application."""
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont(FONT_FAMILY, 11)
    app.setFont(font)

    window = DerbyApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
