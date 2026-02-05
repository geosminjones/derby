#!/usr/bin/env python3
"""
history_tab.py - History tab for viewing past sessions in Derby GUI (PyQt6 version)
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import db
import themes
from themes import FONT_FAMILY
from jframes import Table, TableRow, batch_update, get_dropdown_arrow_path, MessageBox, ConfirmDialog

if TYPE_CHECKING:
    from gui import DerbyApp


class HistoryTab:
    """History tab for viewing past sessions."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self.project_filter = "All"
        self.period_filter = "All"
        self.limit_var = "50"
        self._build_ui()

    def _build_ui(self):
        """Build the history tab UI."""
        colors = themes.get_colors()

        # Main layout for the parent frame
        main_layout = QVBoxLayout(self.parent)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Filter section
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['card_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(filter_frame)

        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 12, 15, 12)
        filter_layout.setSpacing(8)

        # Filter row
        filter_row = QFrame()
        filter_row.setStyleSheet("background: transparent;")
        filter_row_layout = QHBoxLayout(filter_row)
        filter_row_layout.setContentsMargins(0, 0, 0, 0)
        filter_row_layout.setSpacing(15)

        # Project filter
        project_label = QLabel("Project:")
        project_label.setFont(QFont(FONT_FAMILY, 11))
        project_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        filter_row_layout.addWidget(project_label)

        self.project_combo = QComboBox()
        self.project_combo.setFixedSize(150, 32)
        self.project_combo.setFont(QFont(FONT_FAMILY, 11))
        self.project_combo.setStyleSheet(f"""
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
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        filter_row_layout.addWidget(self.project_combo)

        # Period filter
        period_label = QLabel("Period:")
        period_label.setFont(QFont(FONT_FAMILY, 11))
        period_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        filter_row_layout.addWidget(period_label)

        self.period_combo = QComboBox()
        self.period_combo.setFixedSize(120, 32)
        self.period_combo.setFont(QFont(FONT_FAMILY, 11))
        self.period_combo.addItems(["All", "Today", "This Week"])
        self.period_combo.setStyleSheet(f"""
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
        self.period_combo.currentTextChanged.connect(self._on_period_changed)
        filter_row_layout.addWidget(self.period_combo)

        # Limit filter
        limit_label = QLabel("Limit:")
        limit_label.setFont(QFont(FONT_FAMILY, 11))
        limit_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        filter_row_layout.addWidget(limit_label)

        self.limit_entry = QLineEdit()
        self.limit_entry.setFixedSize(60, 32)
        self.limit_entry.setFont(QFont(FONT_FAMILY, 11))
        self.limit_entry.setText("50")
        self.limit_entry.setStyleSheet(f"""
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
        filter_row_layout.addWidget(self.limit_entry)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedSize(80, 32)
        refresh_btn.setFont(QFont(FONT_FAMILY, 11))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
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
        refresh_btn.clicked.connect(self.refresh)
        filter_row_layout.addWidget(refresh_btn)

        filter_row_layout.addStretch()
        filter_layout.addWidget(filter_row)

        # Sessions table
        self.table = Table(
            self.parent,
            columns=["ID", "Date", "Project", "Duration", "Notes"],
            widths=[50, 100, 150, 100, 300],
            anchors=['w', 'w', 'w', 'w', 'w'],
            show_header=True,
            on_action=self._on_table_action
        )
        main_layout.addWidget(self.table, stretch=1)

        # Store reference to table frame for batch_update
        self.table_frame = self.table

        # Button row
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setFixedSize(120, 32)
        delete_btn.setFont(QFont(FONT_FAMILY, 11))
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(delete_btn)

        export_btn = QPushButton("Export to CSV...")
        export_btn.setFixedSize(120, 32)
        export_btn.setFont(QFont(FONT_FAMILY, 11))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(f"""
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
        export_btn.clicked.connect(self.app._export_csv)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        main_layout.addWidget(btn_frame)

        # Track selected row
        self._selected_row_id: str | None = None
        self._selected_row: TableRow | None = None

    def _on_project_changed(self, text: str):
        """Handle project filter change."""
        self.project_filter = text
        self.refresh()

    def _on_period_changed(self, text: str):
        """Handle period filter change."""
        self.period_filter = text
        self.refresh()

    def _on_table_action(self, row_id: str, action_id: str):
        """Handle table row action (selection)."""
        # Deselect previous row
        if self._selected_row is not None:
            self._selected_row.set_selected(False)

        # Select new row
        new_row = self.table.get_row(row_id)
        if new_row:
            new_row.set_selected(True)
            self._selected_row = new_row
        self._selected_row_id = row_id

    def refresh(self):
        """Refresh sessions list."""
        # Update project filter options
        projects = db.list_projects()
        project_names = ["All"] + [p.name for p in projects]

        # Block signals to prevent triggering refresh during update
        self.project_combo.blockSignals(True)
        current_project = self.project_combo.currentText()
        self.project_combo.clear()
        self.project_combo.addItems(project_names)
        # Restore selection if still valid
        if current_project in project_names:
            self.project_combo.setCurrentText(current_project)
        self.project_combo.blockSignals(False)

        # Calculate date filters
        start_date = None
        end_date = None
        period = self.period_filter

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
        if self.project_filter != "All":
            project = self.project_filter

        # Get limit
        try:
            limit = int(self.limit_entry.text())
        except ValueError:
            limit = 50

        # Query sessions
        sessions = db.get_sessions(
            project_name=project,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        # Use batch_update to defer painting during clear and repopulate
        with batch_update(self.table_frame):
            # Reset selected row reference before clearing
            self._selected_row = None

            # Clear existing
            self.table.clear()

            # Populate table
            colors = themes.get_colors()
            for session in sessions:
                date_str = session.start_time.strftime("%Y-%m-%d") if session.start_time else ""
                notes_preview = session.notes[:50] + "..." if len(session.notes) > 50 else session.notes

                # Add row with select action for clicking
                self.table.add_row(
                    row_id=str(session.id),
                    values=(str(session.id), date_str, session.project_name, session.format_duration(), notes_preview),
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

            # Restore selection if row still exists
            if self._selected_row_id:
                restored_row = self.table.get_row(self._selected_row_id)
                if restored_row:
                    restored_row.set_selected(True)
                    self._selected_row = restored_row
                else:
                    self._selected_row_id = None

    def delete_selected(self):
        """Delete the selected session."""
        if not self._selected_row_id:
            MessageBox(self.app, "Warning", "Please select a session to delete", "warning")
            return

        session_id = int(self._selected_row_id)
        row = self.table.get_row(self._selected_row_id)
        if not row:
            MessageBox(self.app, "Warning", "Please select a session to delete", "warning")
            return

        # Get project name from the row values (index 2 is project column)
        project = row.values[2] if len(row.values) > 2 else "Unknown"

        dialog = ConfirmDialog(self.app, "Confirm Delete", f"Delete session #{session_id} ({project})?")
        if dialog.get_result():
            db.delete_session(session_id)
            self._selected_row_id = None
            self._selected_row = None
            self.refresh()
