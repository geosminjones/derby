#!/usr/bin/env python3
"""
tab_projects.py - Projects management tab and dialogs for Derby GUI (PyQt6 version)
"""

import sqlite3
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import db
import jframes as themes
from jframes import FONT_FAMILY
from jframes import Table, TableRow, batch_update, MessageBox, get_dropdown_arrow_path

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


class ProjectsTab:
    """Projects tab for managing projects and background tasks."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self.tag_filter = "All"
        self._build_ui()

    def _build_ui(self):
        """Build the projects tab UI with split view."""
        colors = themes.get_colors()

        # Main layout for the parent frame
        main_layout = QVBoxLayout(self.parent)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = QFrame()
        top_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(top_frame, stretch=1)

        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 10, 10, 10)
        top_layout.setSpacing(5)

        # Projects header and filter row
        header_row = QFrame()
        header_row.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        projects_label = QLabel("Projects")
        projects_label.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        projects_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        header_layout.addWidget(projects_label)

        header_layout.addStretch()

        # Tag filter
        tag_label = QLabel("Filter by Tag:")
        tag_label.setFont(QFont(FONT_FAMILY, 11))
        tag_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        header_layout.addWidget(tag_label)

        self.tag_combo = QComboBox()
        self.tag_combo.setFixedSize(150, 28)
        self.tag_combo.setFont(QFont(FONT_FAMILY, 11))
        self.tag_combo.setStyleSheet(f"""
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
        self.tag_combo.currentTextChanged.connect(self._on_tag_changed)
        header_layout.addWidget(self.tag_combo)

        top_layout.addWidget(header_row)

        # Projects table
        self.projects_table = Table(
            top_frame,
            columns=["Name", "Priority", "Tags"],
            widths=[200, 120, 250],
            anchors=['w', 'w', 'w'],
            show_header=True,
            on_action=self._on_project_action
        )
        top_layout.addWidget(self.projects_table, stretch=1)

        # Button row for projects
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)

        add_btn = self._create_button("Add Project", colors)
        add_btn.clicked.connect(self.add_project)
        btn_layout.addWidget(add_btn)

        rename_btn = self._create_button("Rename", colors)
        rename_btn.clicked.connect(self.rename_project)
        btn_layout.addWidget(rename_btn)

        priority_btn = self._create_button("Edit Priority", colors)
        priority_btn.clicked.connect(self.edit_priority)
        btn_layout.addWidget(priority_btn)

        tags_btn = self._create_button("Edit Tags", colors)
        tags_btn.clicked.connect(self.edit_tags)
        btn_layout.addWidget(tags_btn)

        delete_btn = self._create_button("Delete", colors)
        delete_btn.clicked.connect(self.delete_project)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        top_layout.addWidget(btn_frame)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(bottom_frame, stretch=1)

        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(5)

        # Background tasks header
        bg_label = QLabel("Background Tasks")
        bg_label.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        bg_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        bottom_layout.addWidget(bg_label)

        # Background tasks table
        self.bg_table = Table(
            bottom_frame,
            columns=["Task Name"],
            widths=[400],
            anchors=['w'],
            show_header=True,
            on_action=self._on_bg_task_action
        )
        bottom_layout.addWidget(self.bg_table, stretch=1)

        # Button row for background tasks
        bg_btn_frame = QFrame()
        bg_btn_frame.setStyleSheet("background: transparent;")
        bg_btn_layout = QHBoxLayout(bg_btn_frame)
        bg_btn_layout.setContentsMargins(0, 0, 0, 0)
        bg_btn_layout.setSpacing(5)

        bg_add_btn = self._create_button("Add Task", colors)
        bg_add_btn.clicked.connect(self.add_background_task)
        bg_btn_layout.addWidget(bg_add_btn)

        bg_rename_btn = self._create_button("Rename", colors)
        bg_rename_btn.clicked.connect(self.rename_background_task)
        bg_btn_layout.addWidget(bg_rename_btn)

        bg_delete_btn = self._create_button("Delete", colors)
        bg_delete_btn.clicked.connect(self.delete_background_task)
        bg_btn_layout.addWidget(bg_delete_btn)

        refresh_btn = self._create_button("Refresh All", colors)
        refresh_btn.clicked.connect(self.refresh)
        bg_btn_layout.addWidget(refresh_btn)

        bg_btn_layout.addStretch()
        bottom_layout.addWidget(bg_btn_frame)

        # Track selected rows
        self._selected_project: str | None = None
        self._selected_bg_task: str | None = None
        self._selected_project_row: TableRow | None = None
        self._selected_bg_task_row: TableRow | None = None

    def _create_button(self, text: str, colors: dict) -> QPushButton:
        """Create a styled button."""
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setFont(QFont(FONT_FAMILY, 11))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        return btn

    def _on_project_action(self, row_id: str, action_id: str):
        """Handle project table row action."""
        # Deselect previous row
        if self._selected_project_row is not None:
            self._selected_project_row.set_selected(False)

        # Select new row
        new_row = self.projects_table.get_row(row_id)
        if new_row:
            new_row.set_selected(True)
            self._selected_project_row = new_row
        self._selected_project = row_id

    def _on_tag_changed(self, text: str):
        """Handle tag filter change."""
        self.tag_filter = text
        self.refresh()

    def _on_bg_task_action(self, row_id: str, action_id: str):
        """Handle background task table row action."""
        # Deselect previous row
        if self._selected_bg_task_row is not None:
            self._selected_bg_task_row.set_selected(False)

        # Select new row
        new_row = self.bg_table.get_row(row_id)
        if new_row:
            new_row.set_selected(True)
            self._selected_bg_task_row = new_row
        self._selected_bg_task = row_id

    def refresh(self):
        """Refresh both projects and background tasks lists."""
        colors = themes.get_colors()

        # Update tag filter options
        tags = db.list_tags()
        tag_names = ["All", "Untagged"] + [t.name for t in tags]

        self.tag_combo.blockSignals(True)
        current_tag = self.tag_combo.currentText()
        self.tag_combo.clear()
        self.tag_combo.addItems(tag_names)
        if current_tag in tag_names:
            self.tag_combo.setCurrentText(current_tag)
        else:
            self.tag_combo.setCurrentText("All")
        self.tag_combo.blockSignals(False)

        # Get data first
        tag = None if self.tag_filter == "All" else self.tag_filter
        projects = db.list_projects(is_background=False, tag=tag)
        bg_tasks = db.list_projects(is_background=True)

        # Use batch_update to defer painting
        # (parent widget covers all descendants, no need to nest)
        with batch_update(self.parent):
            # Reset row references before clearing
            self._selected_project_row = None
            self._selected_bg_task_row = None

            # Clear existing
            self.projects_table.clear()
            self.bg_table.clear()

            # Populate regular projects
            for project in projects:
                priority_label = f"{project.priority} ({PRIORITY_LABELS.get(project.priority, 'Unknown')})"
                tags_str = ", ".join(project.tags) if project.tags else ""

                self.projects_table.add_row(
                    row_id=project.name,
                    values=(project.name, priority_label, tags_str),
                    actions=[
                        {
                            "text": "Select",
                            "action_id": "select",
                            "fg_color": colors["bg_light"],
                            "hover_color": colors["separator"],
                            "text_color": colors["text_primary"],
                            "width": 60
                        }
                    ]
                )

            # Populate background tasks
            for task in bg_tasks:
                self.bg_table.add_row(
                    row_id=task.name,
                    values=(task.name,),
                    actions=[
                        {
                            "text": "Select",
                            "action_id": "select",
                            "fg_color": colors["bg_light"],
                            "hover_color": colors["separator"],
                            "text_color": colors["text_primary"],
                            "width": 60
                        }
                    ]
                )

            # Restore project selection if row still exists
            if self._selected_project:
                restored_row = self.projects_table.get_row(self._selected_project)
                if restored_row:
                    restored_row.set_selected(True)
                    self._selected_project_row = restored_row
                else:
                    self._selected_project = None

            # Restore background task selection if row still exists
            if self._selected_bg_task:
                restored_row = self.bg_table.get_row(self._selected_bg_task)
                if restored_row:
                    restored_row.set_selected(True)
                    self._selected_bg_task_row = restored_row
                else:
                    self._selected_bg_task = None

    def add_project(self):
        """Show dialog to add a new project."""
        AddProjectDialog(self.app, self.app)

    def add_background_task(self):
        """Show dialog to add a new background task."""
        AddBackgroundTaskDialog(self.app, self.app)

    def edit_priority(self):
        """Edit priority of selected project."""
        if not self._selected_project:
            MessageBox(self.app, "Warning", "Please select a project", "warning")
            return

        EditPriorityDialog(self.app, self.app, self._selected_project)

    def edit_tags(self):
        """Edit tags of selected project."""
        if not self._selected_project:
            MessageBox(self.app, "Warning", "Please select a project", "warning")
            return

        EditTagsDialog(self.app, self.app, self._selected_project)

    def rename_project(self):
        """Rename selected project."""
        if not self._selected_project:
            MessageBox(self.app, "Warning", "Please select a project", "warning")
            return

        RenameProjectDialog(self.app, self.app, self._selected_project)

    def rename_background_task(self):
        """Rename selected background task."""
        if not self._selected_bg_task:
            MessageBox(self.app, "Warning", "Please select a task", "warning")
            return

        RenameProjectDialog(self.app, self.app, self._selected_bg_task)

    def delete_project(self):
        """Delete selected project."""
        if not self._selected_project:
            MessageBox(self.app, "Warning", "Please select a project", "warning")
            return

        DeleteProjectDialog(self.app, self.app, self._selected_project)

    def delete_background_task(self):
        """Delete selected background task."""
        if not self._selected_bg_task:
            MessageBox(self.app, "Warning", "Please select a task", "warning")
            return

        DeleteProjectDialog(self.app, self.app, self._selected_bg_task, is_background=True)


class AddProjectDialog(QDialog):
    """Dialog for adding a new project."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        super().__init__(parent)
        self.app = app
        colors = themes.get_colors()

        self.setWindowTitle("Add Project")
        self.setFixedSize(400, 250)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui()

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 400) // 2
            y = parent_geo.y() + (parent_geo.height() - 250) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Name
        name_label = QLabel("Name:")
        name_label.setFont(QFont(FONT_FAMILY, 11))
        name_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(name_label)

        self.name_entry = QLineEdit()
        self.name_entry.setFixedSize(300, 32)
        self.name_entry.setFont(QFont(FONT_FAMILY, 11))
        self.name_entry.setStyleSheet(f"""
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
        layout.addWidget(self.name_entry)

        # Priority row
        priority_frame = QFrame()
        priority_frame.setStyleSheet("background: transparent;")
        priority_layout = QHBoxLayout(priority_frame)
        priority_layout.setContentsMargins(0, 0, 0, 0)
        priority_layout.setSpacing(10)

        priority_label = QLabel("Priority (1-5):")
        priority_label.setFont(QFont(FONT_FAMILY, 11))
        priority_label.setStyleSheet(f"color: {colors['text_primary']};")
        priority_layout.addWidget(priority_label)

        self.priority_entry = QLineEdit()
        self.priority_entry.setFixedSize(60, 32)
        self.priority_entry.setFont(QFont(FONT_FAMILY, 11))
        self.priority_entry.setText("3")
        self.priority_entry.setStyleSheet(f"""
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
        priority_layout.addWidget(self.priority_entry)

        priority_layout.addStretch()
        layout.addWidget(priority_frame)

        # Tags row
        tags_frame = QFrame()
        tags_frame.setStyleSheet("background: transparent;")
        tags_layout = QHBoxLayout(tags_frame)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(10)

        tags_label = QLabel("Tags:")
        tags_label.setFont(QFont(FONT_FAMILY, 11))
        tags_label.setStyleSheet(f"color: {colors['text_primary']};")
        tags_layout.addWidget(tags_label)

        self.tags_entry = QLineEdit()
        self.tags_entry.setFixedSize(200, 32)
        self.tags_entry.setFont(QFont(FONT_FAMILY, 11))
        self.tags_entry.setStyleSheet(f"""
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
        tags_layout.addWidget(self.tags_entry)

        comma_label = QLabel("(comma-separated)")
        comma_label.setFont(QFont(FONT_FAMILY, 10))
        comma_label.setStyleSheet(f"color: {colors['text_secondary']};")
        tags_layout.addWidget(comma_label)

        tags_layout.addStretch()
        layout.addWidget(tags_frame)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        add_btn = QPushButton("Add")
        add_btn.setFixedSize(100, 32)
        add_btn.setFont(QFont(FONT_FAMILY, 11))
        add_btn.setStyleSheet(f"""
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
        add_btn.clicked.connect(self._do_add)
        btn_layout.addWidget(add_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

        self.name_entry.setFocus()

    def _do_add(self):
        """Add the project."""
        name = self.name_entry.text().strip()
        tags_str = self.tags_entry.text().strip()

        if not name:
            MessageBox(self, "Warning", "Please enter a project name", "warning")
            return

        try:
            priority = int(self.priority_entry.text())
        except ValueError:
            MessageBox(self, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            MessageBox(self, "Warning", "Priority must be between 1 and 5", "warning")
            return

        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        try:
            db.create_project(name, priority=priority, tags=tags)
            self.accept()
            self.app.tab_projects.refresh()
            self.app.tab_timer.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            MessageBox(self, "Error", str(e), "error")


class AddBackgroundTaskDialog(QDialog):
    """Dialog for adding a new background task."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        super().__init__(parent)
        self.app = app
        colors = themes.get_colors()

        self.setWindowTitle("Add Background Task")
        self.setFixedSize(350, 150)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui()

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 350) // 2
            y = parent_geo.y() + (parent_geo.height() - 150) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Name
        name_label = QLabel("Task Name:")
        name_label.setFont(QFont(FONT_FAMILY, 11))
        name_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(name_label)

        self.name_entry = QLineEdit()
        self.name_entry.setFixedSize(250, 32)
        self.name_entry.setFont(QFont(FONT_FAMILY, 11))
        self.name_entry.setStyleSheet(f"""
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
        layout.addWidget(self.name_entry)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        add_btn = QPushButton("Add")
        add_btn.setFixedSize(100, 32)
        add_btn.setFont(QFont(FONT_FAMILY, 11))
        add_btn.setStyleSheet(f"""
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
        add_btn.clicked.connect(self._do_add)
        btn_layout.addWidget(add_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

        self.name_entry.setFocus()

    def _do_add(self):
        """Add the background task."""
        name = self.name_entry.text().strip()

        if not name:
            MessageBox(self, "Warning", "Please enter a task name", "warning")
            return

        try:
            db.create_project(name, is_background=True)
            self.accept()
            self.app.tab_projects.refresh()
            self.app.tab_timer.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            MessageBox(self, "Error", str(e), "error")


class EditPriorityDialog(QDialog):
    """Dialog for editing a project's priority."""

    def __init__(self, parent: QWidget, app: 'DerbyApp', project_name: str):
        super().__init__(parent)
        self.app = app
        self.project_name = project_name
        colors = themes.get_colors()

        # Get current priority
        project = db.get_project(project_name)
        current_priority = project.priority if project else 3

        self.setWindowTitle(f"Edit Priority: {project_name}")
        self.setFixedSize(350, 180)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui(current_priority)

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 350) // 2
            y = parent_geo.y() + (parent_geo.height() - 180) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self, current_priority: int):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Project name label
        project_label = QLabel(f"Project: {self.project_name}")
        project_label.setFont(QFont(FONT_FAMILY, 11))
        project_label.setStyleSheet(f"color: {colors['text_primary']};")
        project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(project_label)

        # Priority row
        priority_frame = QFrame()
        priority_frame.setStyleSheet("background: transparent;")
        priority_layout = QHBoxLayout(priority_frame)
        priority_layout.setContentsMargins(0, 0, 0, 0)
        priority_layout.setSpacing(10)

        priority_layout.addStretch()

        priority_label = QLabel("Priority (1-5):")
        priority_label.setFont(QFont(FONT_FAMILY, 11))
        priority_label.setStyleSheet(f"color: {colors['text_primary']};")
        priority_layout.addWidget(priority_label)

        self.priority_entry = QLineEdit()
        self.priority_entry.setFixedSize(60, 32)
        self.priority_entry.setFont(QFont(FONT_FAMILY, 11))
        self.priority_entry.setText(str(current_priority))
        self.priority_entry.setStyleSheet(f"""
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
        priority_layout.addWidget(self.priority_entry)

        priority_layout.addStretch()
        layout.addWidget(priority_frame)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(100, 32)
        save_btn.setFont(QFont(FONT_FAMILY, 11))
        save_btn.setStyleSheet(f"""
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
        save_btn.clicked.connect(self._do_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

    def _do_save(self):
        """Save the priority."""
        try:
            priority = int(self.priority_entry.text())
        except ValueError:
            MessageBox(self, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            MessageBox(self, "Warning", "Priority must be between 1 and 5", "warning")
            return

        try:
            db.update_project_priority(self.project_name, priority)
            self.accept()
            self.app.tab_projects.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            MessageBox(self, "Error", str(e), "error")


class EditTagsDialog(QDialog):
    """Dialog for editing a project's tags."""

    def __init__(self, parent: QWidget, app: 'DerbyApp', project_name: str):
        super().__init__(parent)
        self.app = app
        self.project_name = project_name
        colors = themes.get_colors()

        # Get project and current tags
        self.project = db.get_project(project_name)
        current_tags = self.project.tags if self.project else []

        self.setWindowTitle(f"Edit Tags: {project_name}")
        self.setFixedSize(450, 200)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui(current_tags)

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 450) // 2
            y = parent_geo.y() + (parent_geo.height() - 200) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self, current_tags: list):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Project name label
        project_label = QLabel(f"Project: {self.project_name}")
        project_label.setFont(QFont(FONT_FAMILY, 11))
        project_label.setStyleSheet(f"color: {colors['text_primary']};")
        project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(project_label)

        # Tags row
        tags_frame = QFrame()
        tags_frame.setStyleSheet("background: transparent;")
        tags_layout = QHBoxLayout(tags_frame)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(10)

        tags_label = QLabel("Tags:")
        tags_label.setFont(QFont(FONT_FAMILY, 11))
        tags_label.setStyleSheet(f"color: {colors['text_primary']};")
        tags_layout.addWidget(tags_label)

        self.tags_entry = QLineEdit()
        self.tags_entry.setFixedSize(300, 32)
        self.tags_entry.setFont(QFont(FONT_FAMILY, 11))
        self.tags_entry.setText(", ".join(current_tags))
        self.tags_entry.setStyleSheet(f"""
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
        tags_layout.addWidget(self.tags_entry)

        tags_layout.addStretch()
        layout.addWidget(tags_frame)

        # Hint label
        hint_label = QLabel("(comma-separated)")
        hint_label.setFont(QFont(FONT_FAMILY, 10))
        hint_label.setStyleSheet(f"color: {colors['text_secondary']};")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setFixedSize(100, 32)
        save_btn.setFont(QFont(FONT_FAMILY, 11))
        save_btn.setStyleSheet(f"""
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
        save_btn.clicked.connect(self._do_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

        self.tags_entry.setFocus()

    def _do_save(self):
        """Save the tags."""
        if not self.project:
            MessageBox(self, "Error", "Project not found", "error")
            return

        # Parse new tags
        tags_str = self.tags_entry.text().strip()
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

            self.accept()
            self.app.tab_projects.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            MessageBox(self, "Error", str(e), "error")


class RenameProjectDialog(QDialog):
    """Dialog for renaming a project."""

    def __init__(self, parent: QWidget, app: 'DerbyApp', project_name: str):
        super().__init__(parent)
        self.app = app
        self.old_name = project_name
        colors = themes.get_colors()

        self.setWindowTitle("Rename Project")
        self.setFixedSize(450, 200)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui()

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 450) // 2
            y = parent_geo.y() + (parent_geo.height() - 200) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Current name label
        current_label = QLabel(f"Current name: {self.old_name}")
        current_label.setFont(QFont(FONT_FAMILY, 11))
        current_label.setStyleSheet(f"color: {colors['text_primary']};")
        current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(current_label)

        # New name row
        name_frame = QFrame()
        name_frame.setStyleSheet("background: transparent;")
        name_layout = QHBoxLayout(name_frame)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(10)

        name_label = QLabel("New name:")
        name_label.setFont(QFont(FONT_FAMILY, 11))
        name_label.setStyleSheet(f"color: {colors['text_primary']};")
        name_layout.addWidget(name_label)

        self.name_entry = QLineEdit()
        self.name_entry.setFixedSize(280, 32)
        self.name_entry.setFont(QFont(FONT_FAMILY, 11))
        self.name_entry.setText(self.old_name)
        self.name_entry.setStyleSheet(f"""
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
        name_layout.addWidget(self.name_entry)

        name_layout.addStretch()
        layout.addWidget(name_frame)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        rename_btn = QPushButton("Rename")
        rename_btn.setFixedSize(100, 32)
        rename_btn.setFont(QFont(FONT_FAMILY, 11))
        rename_btn.setStyleSheet(f"""
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
        rename_btn.clicked.connect(self._do_rename)
        btn_layout.addWidget(rename_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

        self.name_entry.setFocus()
        self.name_entry.selectAll()

    def _do_rename(self):
        """Rename the project."""
        new_name = self.name_entry.text().strip()

        if not new_name:
            MessageBox(self, "Warning", "Please enter a project name", "warning")
            return

        if new_name == self.old_name:
            self.accept()
            return

        try:
            result = db.rename_project(self.old_name, new_name)
            if result is None:
                MessageBox(self, "Error", "Project not found", "error")
                return

            self.accept()
            self.app.tab_projects.refresh()
            self.app.tab_timer.refresh()
            self.app.tab_history.refresh()
        except sqlite3.IntegrityError:
            MessageBox(self, "Error", f"A project named '{new_name}' already exists", "error")
        except (ValueError, sqlite3.OperationalError) as e:
            MessageBox(self, "Error", str(e), "error")


class DeleteProjectDialog(QDialog):
    """Dialog for deleting a project with option to delete associated sessions."""

    def __init__(self, parent: QWidget, app: 'DerbyApp', project_name: str, is_background: bool = False):
        super().__init__(parent)
        self.app = app
        self.project_name = project_name
        self.is_background = is_background
        colors = themes.get_colors()

        title = "Delete Task" if is_background else "Delete Project"
        self.setWindowTitle(title)
        self.setFixedSize(450, 220)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui()

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 450) // 2
            y = parent_geo.y() + (parent_geo.height() - 220) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self):
        """Build dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Confirmation message
        item_type = "task" if self.is_background else "project"
        message_label = QLabel(f'Are you sure you want to delete the {item_type}:\n"{self.project_name}"?')
        message_label.setFont(QFont(FONT_FAMILY, 11))
        message_label.setStyleSheet(f"color: {colors['text_primary']};")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Checkbox for deleting sessions
        self.delete_sessions_checkbox = QCheckBox("Also delete all associated sessions (time entries)")
        self.delete_sessions_checkbox.setFont(QFont(FONT_FAMILY, 11))
        self.delete_sessions_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {colors['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {colors['separator']};
                border-radius: 4px;
                background-color: {colors['bg_medium']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['bg_light']};
            }}
        """)
        layout.addWidget(self.delete_sessions_checkbox)

        # Warning hint
        hint_label = QLabel("(If unchecked, sessions will be kept but become orphaned)")
        hint_label.setFont(QFont(FONT_FAMILY, 10))
        hint_label.setStyleSheet(f"color: {colors['text_secondary']};")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        btn_layout.addStretch()

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(100, 32)
        delete_btn.setFont(QFont(FONT_FAMILY, 11))
        delete_btn.setStyleSheet(f"""
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
        delete_btn.clicked.connect(self._do_delete)
        btn_layout.addWidget(delete_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
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
        layout.addWidget(btn_frame)

    def _do_delete(self):
        """Delete the project."""
        delete_sessions = self.delete_sessions_checkbox.isChecked()

        result = db.delete_project(self.project_name, delete_sessions=delete_sessions)
        if not result:
            MessageBox(self, "Error", "Project not found", "error")
            return

        self.accept()
        self.app.tab_projects.refresh()
        self.app.tab_timer.refresh()
        self.app.tab_history.refresh()
