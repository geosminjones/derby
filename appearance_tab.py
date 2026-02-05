#!/usr/bin/env python3
"""
appearance_tab.py - Settings tab for Derby GUI (includes appearance and data storage)
PyQt6 version
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QCheckBox, QButtonGroup, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import db
import themes
from themes import FONT_FAMILY
from jframes import MessageBox

if TYPE_CHECKING:
    from gui import DerbyApp


class ChangeDatabaseLocationDialog(QDialog):
    """Dialog for changing the database storage location."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        super().__init__(parent)
        self.app = app
        self._result = None
        self.new_folder = None

        colors = themes.get_colors()

        self.setWindowTitle("Change Database Location")
        self.setFixedSize(500, 280)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui()

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 500) // 2
            y = parent_geo.y() + (parent_geo.height() - 280) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self):
        """Build the dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Select New Database Location")
        title_label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(title_label)

        # Current location info
        current_frame = QFrame()
        current_frame.setStyleSheet("background: transparent;")
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.setSpacing(2)

        current_label = QLabel("Current location:")
        current_label.setFont(QFont(FONT_FAMILY, 10))
        current_label.setStyleSheet(f"color: {colors['text_secondary']};")
        current_layout.addWidget(current_label)

        current_path = QLabel(str(db.get_data_directory()))
        current_path.setFont(QFont(FONT_FAMILY, 10))
        current_path.setStyleSheet(f"color: {colors['text_primary']};")
        current_path.setWordWrap(True)
        current_layout.addWidget(current_path)

        layout.addWidget(current_frame)

        # New location selection
        new_frame = QFrame()
        new_frame.setStyleSheet("background: transparent;")
        new_layout = QVBoxLayout(new_frame)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(5)

        new_label = QLabel("New location:")
        new_label.setFont(QFont(FONT_FAMILY, 10))
        new_label.setStyleSheet(f"color: {colors['text_secondary']};")
        new_layout.addWidget(new_label)

        select_frame = QFrame()
        select_frame.setStyleSheet("background: transparent;")
        select_layout = QHBoxLayout(select_frame)
        select_layout.setContentsMargins(0, 0, 0, 0)
        select_layout.setSpacing(10)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setFont(QFont(FONT_FAMILY, 10))
        self.folder_label.setStyleSheet(f"""
            background-color: {colors['container_bg']};
            color: {colors['text_primary']};
            padding: 5px 10px;
            border-radius: 4px;
        """)
        select_layout.addWidget(self.folder_label, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFont(QFont(FONT_FAMILY, 10))
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        browse_btn.clicked.connect(self._browse_folder)
        select_layout.addWidget(browse_btn)

        new_layout.addWidget(select_frame)
        layout.addWidget(new_frame)

        # Copy data option
        self.copy_checkbox = QCheckBox("Copy existing data to new location")
        self.copy_checkbox.setChecked(True)
        self.copy_checkbox.setFont(QFont(FONT_FAMILY, 10))
        self.copy_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {colors['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['separator']};
                border-radius: 3px;
                background-color: {colors['container_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['success']};
                border-color: {colors['success']};
            }}
        """)
        layout.addWidget(self.copy_checkbox)

        # Warning message
        warning_label = QLabel("Note: The application will use the new location after confirming.")
        warning_label.setFont(QFont(FONT_FAMILY, 9))
        warning_label.setStyleSheet(f"color: {colors['text_secondary']};")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setFixedSize(100, 32)
        self.confirm_btn.setFont(QFont(FONT_FAMILY, 10))
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['success']};
            }}
            QPushButton:disabled {{
                background-color: {colors['separator']};
                color: {colors['text_secondary']};
            }}
        """)
        self.confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(self.confirm_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
        cancel_btn.setFont(QFont(FONT_FAMILY, 10))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(btn_frame)

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Database Folder",
            str(db.get_data_directory())
        )
        if folder:
            self.new_folder = folder
            self.folder_label.setText(folder)
            self.confirm_btn.setEnabled(True)

    def _confirm(self):
        """Confirm the folder change."""
        if self.new_folder:
            self._result = {
                'folder': self.new_folder,
                'copy_data': self.copy_checkbox.isChecked()
            }
        self.accept()

    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self.reject()

    def get_result(self):
        """Get the dialog result."""
        return self._result


class BackupDatabaseDialog(QDialog):
    """Simple dialog for backing up the database."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        super().__init__(parent)
        self.app = app
        self._result = None
        self.backup_folder = None

        colors = themes.get_colors()

        self.setWindowTitle("Backup Database")
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
        """Build the dialog UI."""
        colors = themes.get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Backup Database")
        title_label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {colors['text_primary']};")
        layout.addWidget(title_label)

        # Backup location selection
        select_label = QLabel("Select folder to save backup:")
        select_label.setFont(QFont(FONT_FAMILY, 10))
        select_label.setStyleSheet(f"color: {colors['text_secondary']};")
        layout.addWidget(select_label)

        select_frame = QFrame()
        select_frame.setStyleSheet("background: transparent;")
        select_layout = QHBoxLayout(select_frame)
        select_layout.setContentsMargins(0, 0, 0, 0)
        select_layout.setSpacing(10)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setFont(QFont(FONT_FAMILY, 10))
        self.folder_label.setStyleSheet(f"""
            background-color: {colors['container_bg']};
            color: {colors['text_primary']};
            padding: 5px 10px;
            border-radius: 4px;
        """)
        select_layout.addWidget(self.folder_label, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setFont(QFont(FONT_FAMILY, 10))
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        browse_btn.clicked.connect(self._browse_folder)
        select_layout.addWidget(browse_btn)

        layout.addWidget(select_frame)

        # Info message
        info_label = QLabel(f"Backup will be saved as: {db.get_backup_filename()}")
        info_label.setFont(QFont(FONT_FAMILY, 9))
        info_label.setStyleSheet(f"color: {colors['text_secondary']};")
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.backup_btn = QPushButton("Create Backup")
        self.backup_btn.setFixedSize(110, 32)
        self.backup_btn.setFont(QFont(FONT_FAMILY, 10))
        self.backup_btn.setEnabled(False)
        self.backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: white;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {colors['success']};
            }}
            QPushButton:disabled {{
                background-color: {colors['separator']};
                color: {colors['text_secondary']};
            }}
        """)
        self.backup_btn.clicked.connect(self._backup)
        btn_layout.addWidget(self.backup_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(100, 32)
        cancel_btn.setFont(QFont(FONT_FAMILY, 10))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(cancel_btn)

        layout.addWidget(btn_frame)

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Folder"
        )
        if folder:
            self.backup_folder = folder
            self.folder_label.setText(folder)
            self.backup_btn.setEnabled(True)

    def _backup(self):
        """Perform the backup."""
        if self.backup_folder:
            self._result = self.backup_folder
        self.accept()

    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self.reject()

    def get_result(self):
        """Get the dialog result."""
        return self._result


class AppearanceTab:
    """Settings tab for managing theme and data storage settings."""

    def __init__(self, parent: QWidget, app: 'DerbyApp'):
        self.parent = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the settings tab UI."""
        colors = themes.get_colors()

        # Main layout for the parent frame
        main_layout = QVBoxLayout(self.parent)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Theme section
        theme_section = QFrame()
        theme_section.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(theme_section)

        theme_layout = QVBoxLayout(theme_section)
        theme_layout.setContentsMargins(15, 12, 15, 12)
        theme_layout.setSpacing(8)

        theme_title = QLabel("Theme")
        theme_title.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        theme_title.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        theme_layout.addWidget(theme_title)

        # Radio buttons for themes
        self.theme_button_group = QButtonGroup(self.parent)
        self.theme_radios = {}

        current_theme = themes.get_current_theme().name
        for theme_name, display_name in themes.get_available_themes():
            radio = QRadioButton(display_name)
            radio.setFont(QFont(FONT_FAMILY, 11))
            radio.setStyleSheet(f"""
                QRadioButton {{
                    color: {colors['text_primary']};
                    background: transparent;
                    spacing: 8px;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 2px solid {colors['separator']};
                    border-radius: 9px;
                    background-color: {colors['bg_medium']};
                }}
                QRadioButton::indicator:checked {{
                    background-color: {colors['success']};
                    border-color: {colors['success']};
                }}
            """)
            radio.setChecked(theme_name == current_theme)
            radio.toggled.connect(lambda checked, name=theme_name: self._on_theme_change(name, checked))
            self.theme_button_group.addButton(radio)
            self.theme_radios[theme_name] = radio
            theme_layout.addWidget(radio)

        # Table display section
        display_section = QFrame()
        display_section.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(display_section)

        display_layout = QVBoxLayout(display_section)
        display_layout.setContentsMargins(15, 12, 15, 12)
        display_layout.setSpacing(8)

        display_title = QLabel("Table Display")
        display_title.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        display_title.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        display_layout.addWidget(display_title)

        # Row dividers toggle
        self.row_dividers_checkbox = QCheckBox("Show row dividers")
        self.row_dividers_checkbox.setFont(QFont(FONT_FAMILY, 11))
        self.row_dividers_checkbox.setChecked(db.get_setting("show_row_dividers", "1") == "1")
        self.row_dividers_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {colors['text_primary']};
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['separator']};
                border-radius: 3px;
                background-color: {colors['bg_medium']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['success']};
                border-color: {colors['success']};
            }}
        """)
        self.row_dividers_checkbox.stateChanged.connect(self._on_row_dividers_change)
        display_layout.addWidget(self.row_dividers_checkbox)

        # Group separators toggle
        self.group_separators_checkbox = QCheckBox("Show group separators")
        self.group_separators_checkbox.setFont(QFont(FONT_FAMILY, 11))
        self.group_separators_checkbox.setChecked(db.get_setting("show_group_separators", "1") == "1")
        self.group_separators_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {colors['text_primary']};
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['separator']};
                border-radius: 3px;
                background-color: {colors['bg_medium']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['success']};
                border-color: {colors['success']};
            }}
        """)
        self.group_separators_checkbox.stateChanged.connect(self._on_group_separators_change)
        display_layout.addWidget(self.group_separators_checkbox)

        # Data Storage section
        storage_section = QFrame()
        storage_section.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)
        main_layout.addWidget(storage_section)

        storage_layout = QVBoxLayout(storage_section)
        storage_layout.setContentsMargins(15, 12, 15, 12)
        storage_layout.setSpacing(8)

        storage_title = QLabel("Data Storage")
        storage_title.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        storage_title.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        storage_layout.addWidget(storage_title)

        # Database location display
        location_label = QLabel("Database location:")
        location_label.setFont(QFont(FONT_FAMILY, 11))
        location_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        storage_layout.addWidget(location_label)

        # Location path and buttons row
        path_row = QFrame()
        path_row.setStyleSheet("background: transparent;")
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(10)

        self.db_path_label = QLabel(str(db.get_data_directory()))
        self.db_path_label.setFont(QFont(FONT_FAMILY, 11))
        self.db_path_label.setStyleSheet(f"""
            background-color: {colors['bg_light']};
            color: {colors['text_primary']};
            padding: 8px 12px;
            border-radius: 6px;
        """)
        path_layout.addWidget(self.db_path_label, stretch=1)

        select_folder_btn = QPushButton("Select New Folder")
        select_folder_btn.setFixedHeight(32)
        select_folder_btn.setFont(QFont(FONT_FAMILY, 11))
        select_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        select_folder_btn.clicked.connect(self._on_select_new_folder)
        path_layout.addWidget(select_folder_btn)

        backup_btn = QPushButton("Backup Database")
        backup_btn.setFixedHeight(32)
        backup_btn.setFont(QFont(FONT_FAMILY, 11))
        backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {colors['separator']};
            }}
        """)
        backup_btn.clicked.connect(self._on_backup_database)
        path_layout.addWidget(backup_btn)

        storage_layout.addWidget(path_row)

        # Add stretch to push everything to top
        main_layout.addStretch()

    def _on_theme_change(self, theme_name: str, checked: bool):
        """Handle theme selection change."""
        if checked:
            # Trigger full UI rebuild via main app
            self.app.switch_theme(theme_name)

    def _on_row_dividers_change(self, state):
        """Handle row dividers toggle change."""
        db.set_setting("show_row_dividers", "1" if self.row_dividers_checkbox.isChecked() else "0")
        if hasattr(self.app, 'summary_tab') and hasattr(self.app.summary_tab, '_tables_initialized') and self.app.summary_tab._tables_initialized:
            self.app.summary_tab.refresh()

    def _on_group_separators_change(self, state):
        """Handle group separators toggle change."""
        db.set_setting("show_group_separators", "1" if self.group_separators_checkbox.isChecked() else "0")
        if hasattr(self.app, 'summary_tab') and hasattr(self.app.summary_tab, '_tables_initialized') and self.app.summary_tab._tables_initialized:
            self.app.summary_tab.refresh()

    def _on_select_new_folder(self):
        """Handle select new folder button click."""
        dialog = ChangeDatabaseLocationDialog(self.app, self.app)
        result = dialog.get_result()

        if result:
            success = db.set_data_directory(
                Path(result['folder']),
                copy_existing=result['copy_data']
            )

            if success:
                self.db_path_label.setText(str(db.get_data_directory()))
                MessageBox(
                    self.app,
                    "Success",
                    f"Database location changed to:\n{result['folder']}",
                    "info"
                )
                # Refresh all tabs to reflect any data changes
                self.app.timer_tab.refresh()
            else:
                MessageBox(
                    self.app,
                    "Error",
                    "Failed to change database location. Please check permissions and try again.",
                    "error"
                )

    def _on_backup_database(self):
        """Handle backup database button click."""
        dialog = BackupDatabaseDialog(self.app, self.app)
        result = dialog.get_result()

        if result:
            success = db.backup_database(Path(result))

            if success:
                MessageBox(
                    self.app,
                    "Success",
                    f"Database backed up successfully to:\n{result}",
                    "info"
                )
            else:
                MessageBox(
                    self.app,
                    "Error",
                    "Failed to create backup. Please check permissions and try again.",
                    "error"
                )

    def refresh(self):
        """Refresh the settings tab (update radio selection to current theme)."""
        current_theme = themes.get_current_theme().name
        if current_theme in self.theme_radios:
            self.theme_radios[current_theme].setChecked(True)

        self.row_dividers_checkbox.setChecked(db.get_setting("show_row_dividers", "1") == "1")
        self.group_separators_checkbox.setChecked(db.get_setting("show_group_separators", "1") == "1")
        self.db_path_label.setText(str(db.get_data_directory()))
