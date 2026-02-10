#!/usr/bin/env python3
"""
tab_timer.py - Timer tab and related dialogs for Derby GUI (PyQt6 version)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTextEdit, QDialog, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import db
import jframes as themes
from jframes import FONT_FAMILY
from models import parse_duration_string
from jframes import SessionList, StoppedSessionList, batch_update, get_dropdown_arrow_path, MessageBox, get_scrollbar_qss

if TYPE_CHECKING:
    from gui import DerbyApp
    from models import Project


# Priority labels - copied here to avoid circular import
PRIORITY_LABELS = {
    1: "Critical",
    2: "High",
    3: "Normal",
    4: "Low",
    5: "Very Low"
}


class ProjectSelectorPopup(QDialog):
    """Popup window displaying projects organized by priority in columns."""

    def __init__(self, parent: QWidget, anchor_widget: QWidget, projects_by_priority: dict,
                 on_select: Optional[Callable[[str], None]] = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        colors = themes.get_colors()

        self.on_select = on_select
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        # Position below anchor widget
        pos = anchor_widget.mapToGlobal(anchor_widget.rect().bottomLeft())
        self.move(pos.x(), pos.y() + 2)

        self._build_ui(projects_by_priority)

    def _build_ui(self, projects_by_priority: dict):
        """Build the multi-column popup UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Main container with border effect
        main_frame = QFrame()
        main_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_dark']};
                border: 1px solid {colors['separator']};
                border-radius: 8px;
            }}
        """)
        layout.addWidget(main_frame)

        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Create 5 columns for priorities 1-5
        columns_frame = QFrame()
        columns_frame.setStyleSheet("background: transparent; border: none;")
        columns_layout = QHBoxLayout(columns_frame)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(4)

        column_width = 115
        max_height = 250

        for priority in range(1, 6):
            # Column container
            col_frame = QFrame()
            col_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors['bg_medium']};
                    border-radius: 6px;
                    border: none;
                }}
            """)
            col_frame.setFixedWidth(column_width + 10)

            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(3, 3, 3, 3)
            col_layout.setSpacing(2)

            # Header
            header_text = f"P{priority}"
            if priority in PRIORITY_LABELS:
                label = PRIORITY_LABELS[priority]
                if label == "Very Low":
                    label = "V.Low"
                header_text = f"P{priority} ({label})"

            header = QLabel(header_text)
            header.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setFixedHeight(24)
            header.setStyleSheet(f"""
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border-radius: 4px;
            """)
            col_layout.addWidget(header)

            # Scrollable area for projects
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setMaximumHeight(max_height)
            scrollbar_qss = get_scrollbar_qss(
                vertical=True,
                horizontal=False,
                transparent_track=True,
                width=8
            )
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                {scrollbar_qss}
            """)

            scroll_content = QWidget()
            scroll_content.setStyleSheet("background: transparent;")
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(2)
            scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            projects = projects_by_priority.get(priority, [])

            if not projects:
                empty_label = QLabel("(none)")
                empty_label.setFont(QFont(FONT_FAMILY, 10))
                empty_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scroll_layout.addWidget(empty_label)
            else:
                for project_name in projects:
                    btn = QPushButton(project_name)
                    btn.setFont(QFont(FONT_FAMILY, 11))
                    btn.setFixedHeight(26)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {colors['card_bg']};
                            color: {colors['text_primary']};
                            border: none;
                            border-radius: 4px;
                            text-align: left;
                            padding-left: 6px;
                        }}
                        QPushButton:hover {{
                            background-color: {colors['bg_light']};
                        }}
                    """)
                    btn.clicked.connect(lambda checked, name=project_name: self._select_project(name))
                    scroll_layout.addWidget(btn)

            scroll_area.setWidget(scroll_content)
            col_layout.addWidget(scroll_area)

            columns_layout.addWidget(col_frame)

        main_layout.addWidget(columns_frame)

    def _select_project(self, project_name: str):
        """Handle project selection."""
        if self.on_select:
            self.on_select(project_name)
        self.accept()


class ProjectSelector(QFrame):
    """Custom project selector with entry field and multi-column dropdown."""

    def __init__(self, parent: QWidget, width: int = 250, height: int = 32):
        super().__init__(parent)
        colors = themes.get_colors()

        self.setStyleSheet("background: transparent;")

        self._value = ""
        self.projects_by_priority: dict = {1: [], 2: [], 3: [], 4: [], 5: []}
        self.popup: Optional[ProjectSelectorPopup] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # Entry field for typing
        self.entry = QLineEdit()
        self.entry.setFixedSize(width - 35, height)
        self.entry.setFont(QFont(FONT_FAMILY, 12))
        self.entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 0 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {colors['bg_light']};
            }}
        """)
        self.entry.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.entry)

        # Dropdown button
        self.dropdown_btn = QPushButton("\u25BC")  # Down arrow
        self.dropdown_btn.setFixedSize(30, height)
        self.dropdown_btn.setFont(QFont(FONT_FAMILY, 10))
        self.dropdown_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dropdown_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        self.dropdown_btn.clicked.connect(self._toggle_popup)
        layout.addWidget(self.dropdown_btn)

    def _on_text_changed(self, text: str):
        """Handle text changes in the entry field."""
        self._value = text

    def set_projects(self, projects_by_priority: dict):
        """Update the projects dictionary."""
        self.projects_by_priority = projects_by_priority

    def get(self) -> str:
        """Get the current entry value."""
        return self.entry.text()

    def set(self, value: str):
        """Set the entry value."""
        self._value = value
        self.entry.setText(value)

    def _toggle_popup(self):
        """Toggle the dropdown popup."""
        if self.popup is not None and self.popup.isVisible():
            self.popup.close()
            self.popup = None
            return

        self.popup = ProjectSelectorPopup(
            self.window(),
            self,
            self.projects_by_priority,
            on_select=self._on_project_selected
        )
        self.popup.show()

    def _on_project_selected(self, project_name: str):
        """Handle project selection from popup."""
        self._value = project_name
        self.entry.setText(project_name)
        self.popup = None


class TimerTab:
    """Timer tab for starting/stopping sessions."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self.project_var = ""
        self.bg_task_var = ""

        # Caches for optimization
        self._projects_cache: dict[str, 'Project'] | None = None
        self._last_session_ids: set[str] = set()
        self._last_session_state: dict[str, tuple[str, bool]] = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the timer tab UI with split view for projects and background tasks."""
        colors = themes.get_colors()

        # Main layout for the parent frame
        main_layout = QVBoxLayout(self.parent)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Main container
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("background: transparent;")
        main_layout.addWidget(self.main_frame)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(10)

        # Create splitter for resizable split between projects and background tasks
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {colors['separator']};
                height: 4px;
            }}
        """)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = QFrame()
        top_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 10px;
            }}
        """)

        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(5)

        # Start session section for regular projects
        start_frame = QFrame()
        start_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['card_bg']};
                border-radius: 8px;
            }}
        """)
        top_layout.addWidget(start_frame)

        start_layout = QVBoxLayout(start_frame)
        start_layout.setContentsMargins(12, 10, 12, 10)
        start_layout.setSpacing(8)

        # Header
        header_label = QLabel("Start New Project Session")
        header_label.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        start_layout.addWidget(header_label)

        # Project row
        project_row = QFrame()
        project_row.setStyleSheet("background: transparent;")
        project_row_layout = QHBoxLayout(project_row)
        project_row_layout.setContentsMargins(0, 0, 0, 0)
        project_row_layout.setSpacing(10)

        project_label = QLabel("Project:")
        project_label.setFont(QFont(FONT_FAMILY, 12))
        project_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        project_row_layout.addWidget(project_label)

        self.project_selector = ProjectSelector(project_row, width=250, height=32)
        project_row_layout.addWidget(self.project_selector)

        start_btn = QPushButton("Start Tracking")
        start_btn.setFixedHeight(32)
        start_btn.setFont(QFont(FONT_FAMILY, 12))
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
            }}
        """)
        start_btn.clicked.connect(self.start_session)
        project_row_layout.addWidget(start_btn)

        project_row_layout.addStretch()
        start_layout.addWidget(project_row, alignment=Qt.AlignmentFlag.AlignLeft)

        # Active regular sessions section header
        sessions_header = QLabel("Active Project Sessions")
        sessions_header.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
        sessions_header.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        top_layout.addWidget(sessions_header)

        # Active sessions list
        self.session_list = SessionList(
            top_frame,
            on_stop=self._on_stop_session,
            on_toggle_pause=self._on_toggle_pause,
            on_play_stopped=self._on_play_stopped_session,
            empty_message="No active project sessions",
            max_stopped_cards=3
        )
        top_layout.addWidget(self.session_list, stretch=1)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 10px;
            }}
        """)

        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(5)

        # Start session section for background tasks
        bg_start_frame = QFrame()
        bg_start_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['card_bg']};
                border-radius: 8px;
            }}
        """)
        bottom_layout.addWidget(bg_start_frame)

        bg_start_layout = QVBoxLayout(bg_start_frame)
        bg_start_layout.setContentsMargins(12, 10, 12, 10)
        bg_start_layout.setSpacing(8)

        # Header
        bg_header_label = QLabel("Start Background Task")
        bg_header_label.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
        bg_header_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        bg_start_layout.addWidget(bg_header_label)

        # Task row
        bg_row = QFrame()
        bg_row.setStyleSheet("background: transparent;")
        bg_row_layout = QHBoxLayout(bg_row)
        bg_row_layout.setContentsMargins(0, 0, 0, 0)
        bg_row_layout.setSpacing(10)

        task_label = QLabel("Task:")
        task_label.setFont(QFont(FONT_FAMILY, 12))
        task_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        bg_row_layout.addWidget(task_label)

        self.bg_task_combo = QComboBox()
        self.bg_task_combo.setFixedSize(250, 32)
        self.bg_task_combo.setFont(QFont(FONT_FAMILY, 12))
        self.bg_task_combo.setEditable(True)
        self.bg_task_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 0 8px;
            }}
            QComboBox:focus {{
                border: 1px solid {colors['bg_light']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: url("{get_dropdown_arrow_path(colors['text_primary'])}");
                width: 12px;
                height: 8px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
                selection-background-color: {colors['bg_light']};
            }}
        """)
        bg_row_layout.addWidget(self.bg_task_combo)

        bg_start_btn = QPushButton("Start Task")
        bg_start_btn.setFixedHeight(32)
        bg_start_btn.setFont(QFont(FONT_FAMILY, 12))
        bg_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bg_start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
            }}
        """)
        bg_start_btn.clicked.connect(self.start_background_task)
        bg_row_layout.addWidget(bg_start_btn)

        bg_row_layout.addStretch()
        bg_start_layout.addWidget(bg_row)

        # Active background tasks section header
        bg_sessions_header = QLabel("Active Background Tasks")
        bg_sessions_header.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
        bg_sessions_header.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        bottom_layout.addWidget(bg_sessions_header)

        # Active background tasks list
        self.bg_session_list = SessionList(
            bottom_frame,
            on_stop=self._on_stop_session,
            on_toggle_pause=self._on_toggle_pause,
            on_play_stopped=self._on_play_stopped_session,
            empty_message="No active background tasks",
            max_stopped_cards=3
        )
        bottom_layout.addWidget(self.bg_session_list, stretch=1)

        # Add frames to splitter and splitter to layout
        self.splitter.addWidget(top_frame)
        self.splitter.addWidget(bottom_frame)
        self.splitter.setStretchFactor(0, 2)  # Projects: 2 parts
        self.splitter.setStretchFactor(1, 1)  # Background: 1 part
        frame_layout.addWidget(self.splitter, stretch=1)

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

        # Group regular projects by priority
        projects_by_priority = {1: [], 2: [], 3: [], 4: [], 5: []}
        for p in project_map.values():
            if not p.is_background:
                projects_by_priority[p.priority].append(p.name)

        # Sort each priority group alphabetically
        for priority in projects_by_priority:
            projects_by_priority[priority].sort(key=str.lower)

        self.project_selector.set_projects(projects_by_priority)

        # Background tasks
        bg_task_names = sorted(
            [p.name for p in project_map.values() if p.is_background],
            key=str.lower
        )
        self.bg_task_combo.clear()
        self.bg_task_combo.addItems(bg_task_names)

    def refresh_sessions(self):
        """Refresh only the active sessions lists."""
        self._refresh_active_sessions()
        # Clear timer state cache so update_durations rebuilds properly
        self._last_session_ids.clear()
        self._last_session_state.clear()

    def _refresh_active_sessions(self):
        """Refresh both active sessions lists using cached project data."""
        active = db.get_active_sessions()

        # Use cached project map for O(1) lookups
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

        # Use batch_update to freeze during clear and repopulate
        # (parent widget covers all descendants, no need to nest)
        with batch_update(self.main_frame):
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

        # Detect if session list changed
        if current_ids != self._last_session_ids:
            self._refresh_active_sessions()
            self._last_session_ids = current_ids
            self._last_session_state.clear()
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

            cached = self._last_session_state.get(session_id)
            if cached != (duration, is_paused):
                self.session_list.update_duration(session_id, duration)
                self.session_list.update_pause_state(session_id, is_paused)
                self.bg_session_list.update_duration(session_id, duration)
                self.bg_session_list.update_pause_state(session_id, is_paused)
                self._last_session_state[session_id] = (duration, is_paused)

    def start_session(self):
        """Start tracking the selected regular project."""
        project_name = self.project_selector.get().strip()
        if not project_name:
            MessageBox(self.app, "Warning", "Please enter a project name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(project_name)
        if active:
            MessageBox(self.app, "Info", f"'{project_name}' is already being tracked", "info")
            return

        # Use cached project map
        project_map = self._get_projects_map()
        existing = project_map.get(project_name)
        if existing and existing.is_background:
            MessageBox(self.app, "Warning", f"'{project_name}' is a background task, not a project", "warning")
            return

        is_new_project = existing is None

        db.start_session(project_name)
        self.project_selector.set("")
        self.project_var = ""

        if is_new_project:
            self.refresh()
        else:
            self.refresh_sessions()

    def start_background_task(self):
        """Start tracking a background task."""
        task_name = self.bg_task_combo.currentText().strip()
        if not task_name:
            MessageBox(self.app, "Warning", "Please enter a task name", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(task_name)
        if active:
            MessageBox(self.app, "Info", f"'{task_name}' is already being tracked", "info")
            return

        project_map = self._get_projects_map()
        existing = project_map.get(task_name)

        if existing is None:
            db.create_project(task_name, is_background=True)
            is_new_task = True
        elif not existing.is_background:
            MessageBox(self.app, "Warning", f"'{task_name}' is a regular project, not a background task", "warning")
            return
        else:
            is_new_task = False

        db.start_session(task_name)
        self.bg_task_combo.setCurrentText("")
        self.bg_task_var = ""

        if is_new_task:
            self.refresh()
        else:
            self.refresh_sessions()

    def _on_stop_session(self, session_id: str):
        """Handle stop button click from session card."""
        session = db.get_session_by_id(int(session_id))
        if session and session.end_time is None:
            # Capture info before stopping
            project_name = session.project_name
            duration_str = session.format_duration()

            # Determine if background task
            project_map = self._get_projects_map()
            project = project_map.get(project_name)
            is_bg = project.is_background if project else False

            # Stop the session
            db.stop_session(project_name=project_name)

            # Add to stopped sessions list
            stop_date_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            if is_bg:
                if self.bg_session_list.stopped_list:
                    self.bg_session_list.stopped_list.add_stopped_session(
                        project_name=project_name,
                        stop_date=stop_date_str,
                        duration=duration_str
                    )
            else:
                if self.session_list.stopped_list:
                    self.session_list.stopped_list.add_stopped_session(
                        project_name=project_name,
                        stop_date=stop_date_str,
                        duration=duration_str
                    )

            self.refresh_sessions()

    def _on_play_stopped_session(self, project_name: str):
        """Handle play button click on stopped session card - start new session."""
        # Remove the stopped card from both lists
        if self.session_list.stopped_list:
            self.session_list.stopped_list.remove_card(project_name)
        if self.bg_session_list.stopped_list:
            self.bg_session_list.stopped_list.remove_card(project_name)

        # Check if project still exists
        project_map = self._get_projects_map()
        project = project_map.get(project_name)

        if project is None:
            MessageBox(self.app, "Warning", f"Project '{project_name}' no longer exists", "warning")
            return

        # Check if already active
        active = db.get_active_session_by_project(project_name)
        if active:
            MessageBox(self.app, "Info", f"'{project_name}' is already being tracked", "info")
            return

        # Start new session
        db.start_session(project_name)
        self.refresh_sessions()

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

        self.refresh_sessions()

    def stop_all(self):
        """Stop all active sessions."""
        self.app._stop_all()


class StopSessionDialog(QDialog):
    """Dialog for stopping a session with optional notes."""

    def __init__(self, parent: QWidget, app: 'DerbyApp', project_name: str):
        super().__init__(parent)
        colors = themes.get_colors()

        self.app = app
        self.project_name = project_name

        self.setWindowTitle(f"Stop: {project_name}")
        self.setFixedSize(400, 200)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 400) // 2
            y = parent_geo.y() + (parent_geo.height() - 200) // 2
            self.move(x, y)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        # Notes label
        notes_label = QLabel("Notes (optional):")
        notes_label.setFont(QFont(FONT_FAMILY, 11))
        notes_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(notes_label)

        # Notes text area
        self.notes_text = QTextEdit()
        self.notes_text.setFixedHeight(80)
        self.notes_text.setFont(QFont(FONT_FAMILY, 11))
        self.notes_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.notes_text)

        layout.addStretch()

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        stop_btn = QPushButton("Stop Session")
        stop_btn.setFixedSize(120, 32)
        stop_btn.setFont(QFont(FONT_FAMILY, 11))
        stop_btn.setStyleSheet(f"""
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
        stop_btn.clicked.connect(self._do_stop)
        btn_layout.addWidget(stop_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setFont(QFont(FONT_FAMILY, 11))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _do_stop(self):
        """Stop the session."""
        notes = self.notes_text.toPlainText().strip()
        db.stop_session(project_name=self.project_name, notes=notes)
        self.accept()
        self.app.tab_timer.refresh()


class LogSessionDialog(QDialog):
    """Dialog for logging a manual session entry."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        super().__init__(parent)
        colors = themes.get_colors()

        self.app = app

        self.setWindowTitle("Log Manual Entry")
        self.setFixedSize(450, 350)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 450) // 2
            y = parent_geo.y() + (parent_geo.height() - 350) // 2
            self.move(x, y)

        self._build_ui()
        self.exec()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Project
        project_label = QLabel("Project:")
        project_label.setFont(QFont(FONT_FAMILY, 11))
        project_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(project_label)

        projects = db.list_projects()
        project_names = [p.name for p in projects]

        self.project_combo = QComboBox()
        self.project_combo.setFixedSize(300, 32)
        self.project_combo.setFont(QFont(FONT_FAMILY, 11))
        self.project_combo.setEditable(True)
        self.project_combo.addItems(project_names)
        self.project_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 0 8px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: url("{get_dropdown_arrow_path(colors['text_primary'])}");
                width: 12px;
                height: 8px;
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
                selection-background-color: {colors['bg_light']};
            }}
        """)
        layout.addWidget(self.project_combo)

        # Duration row
        duration_frame = QFrame()
        duration_frame.setStyleSheet("background: transparent;")
        duration_layout = QHBoxLayout(duration_frame)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(10)

        duration_label = QLabel("Duration:")
        duration_label.setFont(QFont(FONT_FAMILY, 11))
        duration_label.setStyleSheet(f"color: {colors['text_primary']};")
        duration_layout.addWidget(duration_label)

        self.duration_entry = QLineEdit()
        self.duration_entry.setFixedSize(120, 32)
        self.duration_entry.setFont(QFont(FONT_FAMILY, 11))
        self.duration_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 0 8px;
            }}
        """)
        duration_layout.addWidget(self.duration_entry)

        hint_label = QLabel("(e.g., 1h30m, 45m, 2h)")
        hint_label.setFont(QFont(FONT_FAMILY, 10))
        hint_label.setStyleSheet(f"color: {colors['text_secondary']};")
        duration_layout.addWidget(hint_label)

        duration_layout.addStretch()
        layout.addWidget(duration_frame)

        # Date row
        date_frame = QFrame()
        date_frame.setStyleSheet("background: transparent;")
        date_layout = QHBoxLayout(date_frame)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(10)

        date_label = QLabel("Date:")
        date_label.setFont(QFont(FONT_FAMILY, 11))
        date_label.setStyleSheet(f"color: {colors['text_primary']};")
        date_layout.addWidget(date_label)

        self.date_entry = QLineEdit()
        self.date_entry.setFixedSize(120, 32)
        self.date_entry.setFont(QFont(FONT_FAMILY, 11))
        self.date_entry.setText(datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 0 8px;
            }}
        """)
        date_layout.addWidget(self.date_entry)

        date_hint = QLabel("(YYYY-MM-DD)")
        date_hint.setFont(QFont(FONT_FAMILY, 10))
        date_hint.setStyleSheet(f"color: {colors['text_secondary']};")
        date_layout.addWidget(date_hint)

        date_layout.addStretch()
        layout.addWidget(date_frame)

        # Notes
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont(FONT_FAMILY, 11))
        notes_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setFixedHeight(80)
        self.notes_text.setFont(QFont(FONT_FAMILY, 11))
        self.notes_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colors['bg_medium']};
                color: {colors['text_primary']};
                border: 1px solid {colors['separator']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.notes_text)

        layout.addStretch()

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        log_btn = QPushButton("Log Session")
        log_btn.setFixedSize(100, 32)
        log_btn.setFont(QFont(FONT_FAMILY, 11))
        log_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
            }}
        """)
        log_btn.clicked.connect(self._do_log)
        btn_layout.addWidget(log_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setFont(QFont(FONT_FAMILY, 11))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _do_log(self):
        """Log the session."""
        project = self.project_combo.currentText().strip()
        duration_str = self.duration_entry.text().strip()
        date_str = self.date_entry.text().strip()
        notes = self.notes_text.toPlainText().strip()

        if not project:
            MessageBox(self, "Warning", "Please enter a project name", "warning")
            return

        if not duration_str:
            MessageBox(self, "Warning", "Please enter a duration", "warning")
            return

        try:
            duration = parse_duration_string(duration_str)
            if duration.total_seconds() == 0:
                raise ValueError("Duration must be greater than 0")
        except ValueError:
            MessageBox(self, "Error", "Invalid duration format. Use formats like: 1h30m, 45m, 2h", "error")
            return

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=17, minute=0, second=0)
        except ValueError:
            MessageBox(self, "Error", "Invalid date format. Use YYYY-MM-DD", "error")
            return

        db.log_session(project_name=project, duration=duration, notes=notes, date=date)
        self.accept()
        MessageBox(self.app, "Success", f"Logged {duration_str} for {project}", "info")
