"""
jframes.py - Reusable PyQt6 table and list components

A modular library of custom PyQt6 widgets for building modern, themeable interfaces.
Designed for easy integration into any PyQt6 project.

Components:
    Table       - A customizable table widget with action buttons per row
    TableRow    - A single row in a Table
    TableDivider - A subtle divider line between table rows
    SessionCard - A card-style component for displaying active/paused sessions
    StoppedSessionCard - A card for recently stopped sessions (play to restart)
    SessionList - A scrollable list of session cards
    StoppedSessionList - A FIFO container for stopped session cards (max 5)
    TabButton   - A styled checkable button for tab navigation
    TabSwitcher - A segmented button-style tab switcher container

Usage Example:
    from jframes import Table, SessionList

    # Create a table
    table = Table(
        parent,
        columns=["Name", "Status", "Duration"],
        widths=[200, 100, 100],
        anchors=['w', 'center', 'e'],
        show_header=True
    )

    table.add_row(
        row_id="item_1",
        values=("Item A", "Active", "1h 23m"),
        actions=[
            {"text": "Edit", "action_id": "edit", "fg_color": "#3498db"},
            {"text": "Delete", "action_id": "delete", "fg_color": "#c0392b"}
        ]
    )

Dependencies:
    - PyQt6
    - themes module (for color definitions)

Note: This module requires a `themes` module that provides:
    - get_colors() -> dict with keys: bg_dark, bg_medium, bg_light, text_primary,
      text_secondary, separator, success, danger, danger_hover, session_active_bg,
      session_paused_bg, session_stopped_bg, row_selected
    - FONT_FAMILY constant

Legacy aliases (CTkTableRow, CTkTable, etc.) are provided for backwards compatibility.

TODO: Optimization opportunities:
1. Cache QFont objects at module level instead of creating per-widget:
   _FONT_13 = QFont(FONT_FAMILY, 13)
   _FONT_13_BOLD = QFont(FONT_FAMILY, 13, QFont.Weight.Bold)
2. Cache get_colors() result during batch operations - currently
   creates a new dict via to_dict() on every call, which happens per-row
3. Consider passing colors dict to row constructors for bulk operations
"""

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING
import json

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSizePolicy, QSpacerItem, QButtonGroup, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import json

# ... (rest of the imports)

# =============================================================================
# THEME DEFINITIONS (moved from themes.py)
# =============================================================================

# Font configuration
FONT_FAMILY = "Inter"


@dataclass
class Theme:
    """Represents a complete UI theme."""

    name: str              # Internal identifier (e.g., "dark")
    display_name: str      # User-facing name (e.g., "Dark Mode")

    # Core background colors
    bg_dark: str           # Main window background
    bg_medium: str         # Secondary/treeview background
    bg_light: str          # Lighter accent/selection background

    # Text colors
    text_primary: str      # Main text color
    text_secondary: str    # Muted/hint text color

    # Component colors
    separator: str         # Treeview separator rows
    card_bg: str           # Section card background
    container_bg: str      # Container frame background

    # Semantic colors (buttons, alerts)
    danger: str            # Delete/destructive actions
    danger_hover: str      # Hover state for danger buttons
    success: str           # Success indicators

    # Session card colors
    session_active_bg: str    # Active session card background (light green)
    session_paused_bg: str    # Paused session card background (light yellow)
    session_stopped_bg: str   # Stopped session card background (slightly lighter than bg)

    # Row selection color
    row_selected: str         # Selected row background (blue tint)

    # Scrollbar colors
    scrollbar_track: str          # Track background for opaque contexts
    scrollbar_thumb: str          # Default thumb color
    scrollbar_thumb_hover: str    # Hover state for thumb

    # Appearance mode (for compatibility)
    ctk_appearance_mode: str  # "Dark" or "Light"

    def to_dict(self) -> dict[str, str]:
        """Return color values as dictionary for backward compatibility."""
        return {
            "bg_dark": self.bg_dark,
            "bg_medium": self.bg_medium,
            "bg_light": self.bg_light,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "separator": self.separator,
            "card_bg": self.card_bg,
            "container_bg": self.container_bg,
            "danger": self.danger,
            "danger_hover": self.danger_hover,
            "success": self.success,
            "session_active_bg": self.session_active_bg,
            "session_paused_bg": self.session_paused_bg,
            "session_stopped_bg": self.session_stopped_bg,
            "row_selected": self.row_selected,
            "scrollbar_track": self.scrollbar_track,
            "scrollbar_thumb": self.scrollbar_thumb,
            "scrollbar_thumb_hover": self.scrollbar_thumb_hover,
        }

def load_themes_from_json(file_path: str) -> dict[str, Theme]:
    """Loads themes from a JSON file."""
    themes = {}
    with open(file_path, 'r') as f:
        data = json.load(f)
        for name, colors in data["themes"].items():
            themes[name] = Theme(name=name, **colors)
    return themes

# Theme registry
THEMES = load_themes_from_json('themes.json')
DARK_THEME = THEMES.get("dark")


# =============================================================================
# MODULE STATE
# =============================================================================

_current_theme: Theme = DARK_THEME
_theme_change_callbacks: list[Callable[[], None]] = []


# =============================================================================
# PUBLIC API
# =============================================================================

def get_current_theme() -> Theme:
    """Get the currently active theme."""
    return _current_theme


def get_colors() -> dict[str, str]:
    """
    Get current theme colors as dictionary.

    This provides backward compatibility with the existing COLORS usage.
    """
    return _current_theme.to_dict()


def get_available_themes() -> list[tuple[str, str]]:
    """
    Get list of available themes.

    Returns:
        List of (name, display_name) tuples
    """
    return [(t.name, t.display_name) for t in THEMES.values()]


def set_theme(theme_name: str) -> Theme:
    """
    Set the active theme by name.

    Args:
        theme_name: Internal name of theme (e.g., "dark")

    Returns:
        The newly active Theme

    Raises:
        ValueError: If theme_name is not found
    """
    global _current_theme

    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")

    _current_theme = THEMES[theme_name]

    # Notify all registered callbacks
    _notify_theme_change()

    return _current_theme


def register_theme_callback(callback: Callable[[], None]):
    """
    Register a callback to be called when theme changes.

    Args:
        callback: A callable that takes no arguments
    """
    if callback not in _theme_change_callbacks:
        _theme_change_callbacks.append(callback)


def unregister_theme_callback(callback: Callable[[], None]):
    """
    Unregister a theme change callback.

    Args:
        callback: The callback to remove
    """
    if callback in _theme_change_callbacks:
        _theme_change_callbacks.remove(callback)


def load_saved_theme() -> Theme:
    """
    Load theme from database settings.

    Call this after db.init_database() to restore user's theme preference.

    Returns:
        The loaded (or default) Theme
    """
    import db
    saved_theme = db.get_setting("theme", "dark")

    try:
        return set_theme(saved_theme)
    except ValueError:
        # Fall back to dark theme if saved theme is invalid
        return set_theme("dark")


def save_theme_preference():
    """Save current theme to database."""
    import db
    db.set_setting("theme", _current_theme.name)


# =============================================================================
# PRIVATE FUNCTIONS
# =============================================================================

def _notify_theme_change():
    """Call all registered theme change callbacks."""
    for callback in _theme_change_callbacks:
        try:
            callback()
        except Exception as e:
            # Log but don't crash if a callback fails
            print(f"Theme callback error: {e}")

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget as QWidgetType


# =============================================================================
# GUI Utilities (moved from gui_utils.py)
# =============================================================================

# Cache for generated SVG arrow paths
_arrow_svg_cache: dict[str, str] = {}


def get_dropdown_arrow_path(color: str) -> str:
    """
    Get the path to an SVG dropdown arrow file with the specified color.

    Creates the SVG file if it doesn't exist. The path is formatted with
    forward slashes for use in Qt stylesheets.

    Args:
        color: Hex color string (e.g., "#ffffff")

    Returns:
        Path to the SVG file, formatted for Qt stylesheets
    """
    # Check cache first
    if color in _arrow_svg_cache:
        path = _arrow_svg_cache[color]
        if os.path.exists(path):
            return path.replace('\\', '/')

    # Create SVG content
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8">
<polygon points="0,0 12,0 6,8" fill="{color}"/>
</svg>'''

    # Create filename based on color (remove # from hex)
    color_safe = color.replace('#', '')
    filename = f"derby_arrow_{color_safe}.svg"

    # Write to temp directory
    temp_dir = tempfile.gettempdir()
    svg_path = os.path.join(temp_dir, filename)

    with open(svg_path, 'w') as f:
        f.write(svg_content)

    # Cache the path
    _arrow_svg_cache[color] = svg_path

    # Return with forward slashes for Qt
    return svg_path.replace('\\', '/')


# Track nested batch_update calls per widget
_update_hold_count: dict[int, int] = {}


@contextmanager
def batch_update(widget: 'QWidgetType'):
    """
    Context manager to defer painting during multi-step UI changes.

    Prevents flicker by temporarily disabling updates on the widget
    during changes, then re-enabling when done. This allows all changes
    to be made invisibly, with only the final state being rendered
    in a single repaint.

    Nested calls are handled correctly - only the outermost context
    triggers the updates enabled/disabled changes.

    Usage:
        with batch_update(my_frame):
            my_frame.clear()
            for item in items:
                my_frame.add_row(item)

    Args:
        widget: The PyQt widget to update
    """
    widget_id = id(widget)

    # Increment hold count for this widget
    prev_count = _update_hold_count.get(widget_id, 0)
    _update_hold_count[widget_id] = prev_count + 1

    # Disable updates only on outermost call
    if prev_count == 0:
        try:
            widget.setUpdatesEnabled(False)
        except Exception:
            pass

    try:
        yield
    finally:
        # Decrement hold count
        current_count = _update_hold_count.get(widget_id, 1) - 1
        if current_count <= 0:
            _update_hold_count.pop(widget_id, None)

            # Re-enable updates only on outermost call
            try:
                widget.setUpdatesEnabled(True)
                widget.update()
            except Exception:
                pass
        else:
            _update_hold_count[widget_id] = current_count


# =============================================================================
# Table and List Components
# =============================================================================


class TableRow(QFrame):
    """
    A single row in the Table.

    Each row contains cells (QLabel) and optional action buttons.

    Args:
        parent: Parent widget
        row_id: Unique identifier for this row
        values: Tuple of values for each column
        column_widths: List of pixel widths for each column
        column_anchors: List of alignment anchors ('w', 'e', 'center', 'c')
        on_action: Callback function(row_id, action_id) for action button clicks
        actions: List of action button configurations
        row_padding: Additional padding for the row
        is_header: If True, applies header styling (bold, different background)
    """

    def __init__(
        self,
        parent: QWidget,
        row_id: str,
        values: tuple,
        column_widths: list[int],
        column_anchors: list[str],
        on_action: Optional[Callable[[str, str], None]] = None,
        actions: Optional[list[dict]] = None,
        row_padding: int = 0,
        is_header: bool = False,
        column_border_mode: str = "none",
        text_time_boundary: int = 0,
        border_after_first: bool = False,
        border_before_last: bool = False
    ):
        super().__init__(parent)
        colors = get_colors()

        # Header rows get different styling
        if is_header:
            bg_color = colors["bg_light"]
        else:
            bg_color = colors["bg_medium"]

        # Store original background for selection toggle
        self._bg_color = bg_color
        self._is_selected = False

        self.setStyleSheet(f"background-color: {bg_color}; border: none;")
        self.setFixedHeight(34)

        self.row_id = row_id
        self.values = list(values)
        self.column_widths = column_widths
        self.column_anchors = column_anchors
        self.on_action = on_action
        self.actions = actions or []
        self.is_header = is_header
        self.column_border_mode = column_border_mode
        self.text_time_boundary = text_time_boundary
        self.border_after_first = border_after_first
        self.border_before_last = border_before_last
        self.cell_labels: list[QLabel] = []
        self.action_buttons: list[QPushButton] = []

        self._build_row(row_padding)

    def _build_row(self, padding: int):
        """Build the row with cells and optional action buttons."""
        colors = get_colors()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)

        num_columns = len(self.values)

        # Create cells for each value
        for i, (value, width, anchor) in enumerate(zip(self.values, self.column_widths, self.column_anchors)):
            # Determine if we should add a border before this cell
            should_add_border = False
            if i > 0:  # Never before first cell
                if self.column_border_mode == "all":
                    should_add_border = True
                elif self.column_border_mode == "text_time":
                    # Border after first column (before index 1)
                    if self.border_after_first and i == 1:
                        should_add_border = True
                    # Border at text_time_boundary (after that column index)
                    elif i == self.text_time_boundary + 1:
                        should_add_border = True
                    # Border before last column
                    elif self.border_before_last and i == num_columns - 1:
                        should_add_border = True

            if should_add_border:
                border = ColumnBorder(self)
                layout.addWidget(border)

            # Map anchor to Qt alignment
            alignment = self._map_anchor(anchor)

            label = QLabel(str(value))
            label.setFixedWidth(width)
            label.setAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)

            font = QFont(FONT_FAMILY, 13)
            if self.is_header:
                font.setBold(True)
            label.setFont(font)
            label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")

            layout.addWidget(label)
            self.cell_labels.append(label)

        # Add spacer to push actions to the right
        layout.addStretch()

        # Create action buttons if provided
        if self.actions and not self.is_header:
            for action in self.actions:
                btn = QPushButton(action.get("text", ""))
                btn.setFixedSize(action.get("width", 60), 28)
                btn.setFont(QFont(FONT_FAMILY, 11))

                fg_color = action.get("fg_color", colors["bg_light"])
                hover_color = action.get("hover_color", colors["separator"])
                text_color = action.get("text_color", colors["text_primary"])

                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {fg_color};
                        color: {text_color};
                        border: none;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                    }}
                """)
                btn.clicked.connect(lambda checked, a=action: self._handle_action(a["action_id"]))

                layout.addWidget(btn)
                self.action_buttons.append(btn)

    def _map_anchor(self, anchor: str) -> Qt.AlignmentFlag:
        """Map treeview-style anchors to Qt alignment."""
        mapping = {
            'w': Qt.AlignmentFlag.AlignLeft,
            'e': Qt.AlignmentFlag.AlignRight,
            'center': Qt.AlignmentFlag.AlignHCenter,
            'c': Qt.AlignmentFlag.AlignHCenter,
        }
        return mapping.get(anchor, Qt.AlignmentFlag.AlignLeft)

    def _handle_action(self, action_id: str):
        """Handle action button click."""
        if self.on_action:
            self.on_action(self.row_id, action_id)

    def set_value(self, column_index: int, value: str):
        """Update the value of a specific cell."""
        if 0 <= column_index < len(self.cell_labels):
            self.cell_labels[column_index].setText(str(value))
            self.values[column_index] = value

    def set_column_width(self, column_index: int, width: int):
        """Update the width of a specific column's cell."""
        if 0 <= column_index < len(self.cell_labels):
            self.cell_labels[column_index].setFixedWidth(width)
            self.column_widths[column_index] = width

    def update_actions(self, new_actions: list[dict]):
        """Update the action buttons for this row."""
        colors = get_colors()

        # Update existing buttons or create new ones
        for i, action in enumerate(new_actions):
            if i < len(self.action_buttons):
                btn = self.action_buttons[i]
                btn.setText(action.get("text", ""))

                fg_color = action.get("fg_color", colors["bg_light"])
                hover_color = action.get("hover_color", colors["separator"])
                text_color = action.get("text_color", colors["text_primary"])

                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {fg_color};
                        color: {text_color};
                        border: none;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                    }}
                """)

                # Disconnect old connections and connect new
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.clicked.connect(lambda checked, a=action: self._handle_action(a["action_id"]))

        self.actions = new_actions

    def set_selected(self, is_selected: bool):
        """Set the visual selection state of this row."""
        if self.is_header:
            return
        self._is_selected = is_selected
        colors = get_colors()
        new_bg = colors["row_selected"] if is_selected else self._bg_color
        self.setStyleSheet(f"background-color: {new_bg}; border: none;")


class ResizableHeaderRow(TableRow):
    """
    Header row with column resize functionality via mouse drag.

    Users can click and drag column borders to resize columns. The cursor
    changes to a resize cursor when hovering over the resize zone.

    Args:
        parent: Parent widget
        table: Reference to parent Table for width propagation
        row_id: Unique identifier for this row
        values: Tuple of values for each column
        column_widths: List of pixel widths for each column
        column_anchors: List of alignment anchors ('w', 'e', 'center', 'c')
        row_padding: Additional padding for the row
        is_header: Should always be True for header rows
    """

    RESIZE_ZONE_WIDTH = 5  # pixels from column border to detect resize
    MIN_COLUMN_WIDTH = 30  # minimum column width in pixels

    def __init__(
        self,
        parent: QWidget,
        table: "Table",
        row_id: str,
        values: tuple,
        column_widths: list[int],
        column_anchors: list[str],
        row_padding: int = 0,
        is_header: bool = True,
        column_border_mode: str = "none",
        text_time_boundary: int = 0,
        border_after_first: bool = False,
        border_before_last: bool = False
    ):
        self._table = table
        self._resize_column_index = -1  # Column being resized (-1 if none)
        self._resize_start_x = 0  # Mouse x position when drag started
        self._resize_start_width = 0  # Column width when drag started
        self._in_resize_zone = False  # Whether cursor is in resize zone

        super().__init__(
            parent,
            row_id=row_id,
            values=values,
            column_widths=column_widths,
            column_anchors=column_anchors,
            row_padding=row_padding,
            is_header=is_header,
            column_border_mode=column_border_mode,
            text_time_boundary=text_time_boundary,
            border_after_first=border_after_first,
            border_before_last=border_before_last
        )

        # Enable mouse tracking to detect hover over resize zones
        self.setMouseTracking(True)

    def _get_column_border_positions(self) -> list[int]:
        """
        Calculate x positions of column borders (between columns).

        Returns a list of x positions where resize handles should appear.
        These are the right edges of columns (except the last column).
        """
        positions = []
        x = 4  # left margin from setContentsMargins(4, 0, 4, 0)

        for i in range(len(self.column_widths) - 1):  # Skip last column
            x += self.column_widths[i] + 8  # width + spacing
            positions.append(x - 4)  # center of the gap between columns

        return positions

    def _get_resize_column_at_pos(self, x: int) -> int:
        """
        Return column index if x is in a resize zone, otherwise -1.

        The column index returned is the column to the LEFT of the border,
        i.e., the column that will be resized.
        """
        borders = self._get_column_border_positions()

        for i, border_x in enumerate(borders):
            if abs(x - border_x) <= self.RESIZE_ZONE_WIDTH:
                return i

        return -1

    def mouseMoveEvent(self, event):
        """Handle mouse move for cursor changes and resize dragging."""
        from PyQt6.QtGui import QCursor

        x = event.position().x()

        if self._resize_column_index >= 0:
            # Currently dragging - resize the column
            delta = int(x - self._resize_start_x)
            new_width = max(self._resize_start_width + delta, self.MIN_COLUMN_WIDTH)
            self._table.set_column_width(self._resize_column_index, new_width)
        else:
            # Check if we're in a resize zone
            col_index = self._get_resize_column_at_pos(int(x))

            if col_index >= 0:
                if not self._in_resize_zone:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    self._in_resize_zone = True
            else:
                if self._in_resize_zone:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self._in_resize_zone = False

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Start resize operation if in resize zone."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = int(event.position().x())
            col_index = self._get_resize_column_at_pos(x)

            if col_index >= 0:
                self._resize_column_index = col_index
                self._resize_start_x = x
                self._resize_start_width = self.column_widths[col_index]
                return  # Don't propagate - we're handling this

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """End resize operation."""
        if event.button() == Qt.MouseButton.LeftButton and self._resize_column_index >= 0:
            self._resize_column_index = -1
            return  # Don't propagate

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """Reset cursor when leaving header area."""
        if self._resize_column_index < 0:  # Only reset if not currently dragging
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._in_resize_zone = False

        super().leaveEvent(event)


class TableDivider(QFrame):
    """A subtle divider line between table rows."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        colors = get_colors()
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {colors['separator']};")


class ColumnBorder(QFrame):
    """A vertical divider line between table columns."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        colors = get_colors()
        self.setFixedWidth(1)
        # Use text_secondary for high contrast against all backgrounds
        self.setStyleSheet(f"background-color: {colors['text_secondary']};")


class Table(QFrame):
    """
    A custom table widget built with PyQt components.

    Replaces tkinter Treeview with a modern, themeable table that supports:
    - Custom column widths and alignments
    - Action buttons per row
    - Row dividers
    - Scrolling support
    - Dynamic updates

    Args:
        parent: Parent widget
        columns: List of column header names
        widths: List of pixel widths for each column
        anchors: List of alignment anchors ('w', 'e', 'center')
        show_header: Whether to display the header row
        row_padding: Additional padding for rows
        row_spacing: Spacing between rows
        show_dividers: Whether to show divider lines between rows
        on_action: Callback function(row_id, action_id) for action buttons

    Usage:
        table = Table(
            parent,
            columns=["Name", "Started", "Duration"],
            widths=[200, 150, 100],
            anchors=['w', 'w', 'w'],
            show_header=True
        )

        table.add_row(
            row_id="session_1",
            values=("Project A", "10:30 AM", "1h 23m"),
            actions=[
                {"text": "Stop", "action_id": "stop", "fg_color": "#c0392b"},
                {"text": "Pause", "action_id": "pause"}
            ]
        )
    """

    def __init__(
        self,
        parent: QWidget,
        columns: list[str],
        widths: list[int],
        anchors: Optional[list[str]] = None,
        show_header: bool = True,
        row_padding: int = 0,
        row_spacing: int = 1,
        show_dividers: bool = True,
        on_action: Optional[Callable[[str, str], None]] = None,
        column_border_mode: str = "none",
        text_time_boundary: int = 0,
        border_after_first: bool = False,
        border_before_last: bool = False
    ):
        super().__init__(parent)
        colors = get_colors()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_dark']};
                border-radius: 6px;
            }}
        """)

        self.columns = columns
        self.widths = widths
        self.anchors = anchors or ['w'] * len(columns)
        self.show_header = show_header
        self.row_padding = row_padding
        self.row_spacing = row_spacing
        self.show_dividers = show_dividers
        self.on_action = on_action
        self.column_border_mode = column_border_mode
        self.text_time_boundary = text_time_boundary
        self.border_after_first = border_after_first
        self.border_before_last = border_before_last

        self.rows: dict[str, TableRow] = {}
        self.row_order: list[str] = []
        self._header_row: Optional[TableRow] = None

        self._build_table()

    def _build_table(self):
        """Build the table structure."""
        colors = get_colors()

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollbar_qss = get_scrollbar_qss(
            vertical=True,
            horizontal=True,
            transparent_track=False,
            width=12
        )
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {colors['bg_medium']};
                border: none;
                border-radius: 6px;
            }}
            {scrollbar_qss}
        """)

        # Content widget inside scroll area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {colors['bg_medium']};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        # Add header if requested
        if self.show_header:
            self._add_header()

    def _add_header(self):
        """Add the resizable header row."""
        header_row = ResizableHeaderRow(
            self.content_widget,
            table=self,
            row_id="_header",
            values=tuple(self.columns),
            column_widths=self.widths,
            column_anchors=self.anchors,
            row_padding=0,
            is_header=True,
            column_border_mode=self.column_border_mode,
            text_time_boundary=self.text_time_boundary,
            border_after_first=self.border_after_first,
            border_before_last=self.border_before_last
        )
        self.content_layout.addWidget(header_row)
        self._header_row = header_row

        # Add divider after header
        divider = TableDivider(self.content_widget)
        self.content_layout.addWidget(divider)

    def set_column_width(self, column_index: int, width: int):
        """
        Update width for a specific column across all rows.

        Args:
            column_index: Index of the column to resize
            width: New width in pixels (will be clamped to minimum)
        """
        width = max(width, ResizableHeaderRow.MIN_COLUMN_WIDTH)
        self.widths[column_index] = width

        with batch_update(self.content_widget):
            if self._header_row:
                self._header_row.set_column_width(column_index, width)
            for row in self.rows.values():
                row.set_column_width(column_index, width)

    def update_header(self, column_index: int, text: str):
        """Update header text for a specific column."""
        if self._header_row and 0 <= column_index < len(self._header_row.cell_labels):
            self._header_row.cell_labels[column_index].setText(text)
            self.columns[column_index] = text

    def update_columns(self, columns: list[str], widths: list[int], anchors: Optional[list[str]] = None):
        """
        Update the table's column configuration dynamically.

        This updates the header labels and stores the new column configuration
        for future rows. Existing data rows are cleared.

        Args:
            columns: New column names/headers
            widths: New column widths
            anchors: New column anchors (defaults to 'w' for all)
        """
        self.columns = columns
        self.widths = widths
        self.anchors = anchors or ['w'] * len(columns)

        # Clear existing data rows (but keep header)
        self.clear_rows()

        # Rebuild header with new columns
        if self._header_row:
            self._header_row.deleteLater()
            self._header_row = None

        # Remove header divider
        if self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Re-add header
        if self.show_header:
            self._add_header()

    def add_divider(self):
        """Add an explicit separator divider line between rows (for group separators)."""
        divider = TableDivider(self.content_widget)
        self.content_layout.addWidget(divider)

    def add_row(
        self,
        row_id: str,
        values: tuple,
        actions: Optional[list[dict]] = None,
        is_total: bool = False
    ) -> TableRow:
        """
        Add a new row to the table.

        Args:
            row_id: Unique identifier for the row
            values: Tuple of values for each column
            actions: Optional list of action button configs:
                [{"text": "Stop", "action_id": "stop", "fg_color": "#...", "hover_color": "#..."}]
            is_total: If True, uses header styling (bold) for total rows

        Returns:
            The created TableRow
        """
        # Add divider before row (except for first row)
        if self.rows and self.show_dividers:
            divider = TableDivider(self.content_widget)
            self.content_layout.addWidget(divider)

        row = TableRow(
            self.content_widget,
            row_id=row_id,
            values=values,
            column_widths=self.widths,
            column_anchors=self.anchors,
            on_action=self.on_action,
            actions=actions,
            row_padding=self.row_padding,
            is_header=is_total,  # Reuse header styling for total rows
            column_border_mode=self.column_border_mode,
            text_time_boundary=self.text_time_boundary,
            border_after_first=self.border_after_first,
            border_before_last=self.border_before_last
        )
        self.content_layout.addWidget(row)

        self.rows[row_id] = row
        self.row_order.append(row_id)

        return row

    def clear(self):
        """Remove all data rows from the table, keeping the header intact."""
        self.clear_rows()

    def clear_rows(self):
        """Remove all data rows from the table, keeping the header intact."""
        with batch_update(self.content_widget):
            # Track items to keep (header + header divider)
            skip_count = 2 if self.show_header else 0

            # Remove all items after header
            while self.content_layout.count() > skip_count:
                item = self.content_layout.takeAt(skip_count)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            self.rows.clear()
            self.row_order.clear()

    def get_row(self, row_id: str) -> Optional[TableRow]:
        """Get a row by its ID."""
        return self.rows.get(row_id)

    def set_value(self, row_id: str, column_index: int, value: str):
        """Update a specific cell value."""
        row = self.rows.get(row_id)
        if row:
            row.set_value(column_index, value)

    def update_row_actions(self, row_id: str, actions: list[dict]):
        """Update the action buttons for a specific row."""
        row = self.rows.get(row_id)
        if row:
            row.update_actions(actions)

    def get_children(self) -> list[str]:
        """Get all row IDs in order."""
        return self.row_order.copy()

    def delete_row(self, row_id: str):
        """Remove a specific row."""
        row = self.rows.pop(row_id, None)
        if row:
            row.deleteLater()
            self.row_order.remove(row_id)


class SessionCard(QFrame):
    """
    A card-style component for displaying a single active session.

    Provides a more spacious, visually distinct representation than table rows,
    ideal for active session displays where each item deserves visual prominence.

    Args:
        parent: Parent widget
        session_id: Unique identifier for this session
        project_name: Name to display prominently
        started: Start time string
        duration: Duration string
        is_paused: Whether the session is currently paused
        on_stop: Callback function(session_id) when stop is clicked
        on_toggle_pause: Callback function(session_id) when pause/play is clicked
    """

    def __init__(
        self,
        parent: QWidget,
        session_id: str,
        project_name: str,
        started: str,
        duration: str,
        is_paused: bool = False,
        on_stop: Optional[Callable[[str], None]] = None,
        on_toggle_pause: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent)
        colors = get_colors()

        self.session_id = session_id
        self.project_name = project_name
        self.is_paused = is_paused
        self.on_stop = on_stop
        self.on_toggle_pause = on_toggle_pause

        # Colors for buttons
        self.pause_yellow = "#e6b800"
        self.pause_yellow_hover = "#ccaa00"
        self.play_green = colors["success"]
        self.play_green_hover = "#2ecc71"

        self._update_card_style()
        self._build_card(started, duration)

    def _update_card_style(self):
        """Update card background based on pause state."""
        colors = get_colors()
        card_bg = colors["session_paused_bg"] if self.is_paused else colors["session_active_bg"]
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border-radius: 8px;
            }}
        """)

    def _build_card(self, started: str, duration: str):
        """Build the session card UI."""
        colors = get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)

        # Top row: Project name, buttons, and duration
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Project name (left)
        self.name_label = QLabel(self.project_name)
        self.name_label.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        top_row.addWidget(self.name_label)

        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedSize(60, 26)
        self.stop_btn.setFont(QFont(FONT_FAMILY, 11))
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['danger']};
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors['danger_hover']};
            }}
        """)
        self.stop_btn.clicked.connect(self._on_stop_click)
        top_row.addWidget(self.stop_btn)

        # Pause button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFixedSize(60, 26)
        self.pause_btn.setFont(QFont(FONT_FAMILY, 11))
        self.pause_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.pause_yellow};
                color: #000000;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.pause_yellow_hover};
            }}
        """)
        self.pause_btn.clicked.connect(self._on_toggle_pause_click)

        # Play button
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedSize(60, 26)
        self.play_btn.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.play_green};
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.play_green_hover};
            }}
        """)
        self.play_btn.clicked.connect(self._on_toggle_pause_click)

        # Show appropriate button based on pause state
        if self.is_paused:
            self.pause_btn.hide()
            top_row.addWidget(self.play_btn)
        else:
            self.play_btn.hide()
            top_row.addWidget(self.pause_btn)

        # Spacer
        top_row.addStretch()

        # Duration (right) - larger and prominent
        duration_color = colors["success"] if not self.is_paused else colors["text_secondary"]
        self.duration_label = QLabel(duration)
        self.duration_label.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        self.duration_label.setStyleSheet(f"color: {duration_color}; background: transparent;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.duration_label)

        layout.addLayout(top_row)

        # Bottom row: Started time
        self.started_label = QLabel(f"Started: {started}")
        self.started_label.setFont(QFont(FONT_FAMILY, 11))
        self.started_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        layout.addWidget(self.started_label)

    def _on_stop_click(self):
        """Handle stop button click."""
        if self.on_stop:
            self.on_stop(self.session_id)

    def _on_toggle_pause_click(self):
        """Handle pause/resume button click."""
        if self.on_toggle_pause:
            self.on_toggle_pause(self.session_id)

    def update_duration(self, duration: str):
        """Update the displayed duration."""
        self.duration_label.setText(duration)

    def update_pause_state(self, is_paused: bool):
        """Update the pause state and toggle Pause/Play button visibility."""
        colors = get_colors()
        self.is_paused = is_paused

        # Update card background
        self._update_card_style()

        # Update duration label color
        duration_color = colors["success"] if not is_paused else colors["text_secondary"]
        self.duration_label.setStyleSheet(f"color: {duration_color}; background: transparent;")

        # Toggle button visibility
        if is_paused:
            self.pause_btn.hide()
            self.play_btn.show()
        else:
            self.play_btn.hide()
            self.pause_btn.show()


class StoppedSessionCard(QFrame):
    """
    A card representing a recently stopped session for quick restart.

    Shows project name, stop date, duration in italics, and a green play button.

    Args:
        parent: Parent widget
        project_name: Name of the stopped project
        stop_date: Formatted string of when session was stopped
        duration: Session duration string (displayed in italics)
        on_play: Callback function(project_name) when play is clicked
    """

    def __init__(
        self,
        parent: QWidget,
        project_name: str,
        stop_date: str,
        duration: str,
        on_play: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent)
        colors = get_colors()

        self.project_name = project_name
        self.on_play = on_play

        # Card background
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['session_stopped_bg']};
                border-radius: 8px;
            }}
        """)

        self._build_card(stop_date, duration)

    def _build_card(self, stop_date: str, duration: str):
        """Build the stopped session card UI."""
        colors = get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)

        # Top row: Project name and play button
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Project name (left) - normal weight to differentiate from active
        self.name_label = QLabel(self.project_name)
        self.name_label.setFont(QFont(FONT_FAMILY, 14))
        self.name_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        top_row.addWidget(self.name_label)

        # Play button (green)
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedSize(60, 26)
        self.play_btn.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['success']};
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #2ecc71;
            }}
        """)
        self.play_btn.clicked.connect(self._on_play_click)
        top_row.addWidget(self.play_btn)

        # Spacer
        top_row.addStretch()

        # Duration (right) - italics
        duration_font = QFont(FONT_FAMILY, 14)
        duration_font.setItalic(True)
        self.duration_label = QLabel(duration)
        self.duration_label.setFont(duration_font)
        self.duration_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.duration_label)

        layout.addLayout(top_row)

        # Bottom row: Stopped date
        self.stopped_label = QLabel(f"Stopped: {stop_date}")
        self.stopped_label.setFont(QFont(FONT_FAMILY, 11))
        self.stopped_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        layout.addWidget(self.stopped_label)

    def _on_play_click(self):
        """Handle play button click."""
        if self.on_play:
            self.on_play(self.project_name)


class SessionList(QFrame):
    """
    A scrollable list of session cards.

    Designed for displaying active sessions with visual spacing and
    individual session controls.

    Args:
        parent: Parent widget
        on_stop: Callback function(session_id) when stop is clicked on any card
        on_toggle_pause: Callback function(session_id) when pause/play is clicked
        empty_message: Message to display when the list is empty
    """

    def __init__(
        self,
        parent: QWidget,
        on_stop: Optional[Callable[[str], None]] = None,
        on_toggle_pause: Optional[Callable[[str], None]] = None,
        on_play_stopped: Optional[Callable[[str], None]] = None,
        empty_message: str = "No active sessions",
        max_stopped_cards: int = 3
    ):
        super().__init__(parent)
        colors = get_colors()

        self.setStyleSheet("background: transparent;")

        self.on_stop = on_stop
        self.on_toggle_pause = on_toggle_pause
        self.on_play_stopped = on_play_stopped
        self.empty_message = empty_message
        self.max_stopped_cards = max_stopped_cards

        self.cards: dict[str, SessionCard] = {}
        self.stopped_list: Optional[StoppedSessionList] = None

        self._build_list()

    def _build_list(self):
        """Build the session list container."""
        colors = get_colors()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scrollbar_qss = get_scrollbar_qss(
            vertical=True,
            horizontal=False,
            transparent_track=True,
            width=12
        )
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {scrollbar_qss}
        """)

        # Content widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        # Empty state label (shown when no active sessions)
        self.empty_label = QLabel(self.empty_message)
        self.empty_label.setFont(QFont(FONT_FAMILY, 12))
        self.empty_label.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)

        # Active sessions container
        self.active_widget = QWidget()
        self.active_layout = QVBoxLayout(self.active_widget)
        self.active_layout.setContentsMargins(0, 0, 0, 0)
        self.active_layout.setSpacing(10)
        self.content_layout.addWidget(self.active_widget)

        # Stopped sessions list (if enabled)
        if self.on_play_stopped:
            self.stopped_list = StoppedSessionList(
                self.content_widget,
                max_cards=self.max_stopped_cards,
                on_play=self.on_play_stopped
            )
            # Remove top margin as it's now inside another layout with spacing
            self.stopped_list.layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.addWidget(self.stopped_list)

    def add_session(
        self,
        session_id: str,
        project_name: str,
        started: str,
        duration: str,
        is_paused: bool = False
    ) -> SessionCard:
        """Add a session card to the active list."""
        # Hide empty message when adding first session
        if not self.cards:
            self.empty_label.hide()

        card = SessionCard(
            self.active_widget,
            session_id=session_id,
            project_name=project_name,
            started=started,
            duration=duration,
            is_paused=is_paused,
            on_stop=self.on_stop,
            on_toggle_pause=self.on_toggle_pause
        )
        self.active_layout.addWidget(card)

        self.cards[session_id] = card
        return card

    def clear(self):
        """Remove all active session cards."""
        with batch_update(self.active_widget):
            for card in self.cards.values():
                card.deleteLater()
            self.cards.clear()

            # Show empty message
            self.empty_label.show()

    def get_card(self, session_id: str) -> Optional[SessionCard]:
        """Get a session card by ID."""
        return self.cards.get(session_id)

    def update_duration(self, session_id: str, duration: str):
        """Update the duration for a specific session."""
        card = self.cards.get(session_id)
        if card:
            card.update_duration(duration)

    def update_pause_state(self, session_id: str, is_paused: bool):
        """Update the pause state for a specific session."""
        card = self.cards.get(session_id)
        if card:
            card.update_pause_state(is_paused)

    def get_children(self) -> list[str]:
        """Get all session IDs."""
        return list(self.cards.keys())


class StoppedSessionList(QFrame):
    """
    A container for recently stopped session cards with FIFO max-5 behavior.

    Displays stopped sessions below active sessions, allowing quick restart.
    When a 6th card is added, the oldest is automatically removed.

    Args:
        parent: Parent widget
        max_cards: Maximum number of cards to show (default 5)
        on_play: Callback function(project_name) when play is clicked
    """

    def __init__(
        self,
        parent: QWidget,
        max_cards: int = 5,
        on_play: Optional[Callable[[str], None]] = None
    ):
        super().__init__(parent)

        self.setStyleSheet("background: transparent;")

        self.max_cards = max_cards
        self.on_play = on_play
        self.cards: list[StoppedSessionCard] = []  # Ordered list, oldest first

        self._build_ui()

    def _build_ui(self):
        """Build the stopped session list container."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 0)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    def add_stopped_session(
        self,
        project_name: str,
        stop_date: str,
        duration: str
    ) -> StoppedSessionCard:
        """Add a stopped session card, removing oldest if at max."""
        # Remove existing card for same project (prevent duplicates)
        self.remove_card(project_name)

        # If at max, remove oldest (first in list)
        if len(self.cards) >= self.max_cards:
            oldest = self.cards.pop(0)
            self.layout.removeWidget(oldest)
            oldest.deleteLater()

        # Create and add new card at the end
        card = StoppedSessionCard(
            self,
            project_name=project_name,
            stop_date=stop_date,
            duration=duration,
            on_play=self.on_play
        )
        self.cards.append(card)
        self.layout.addWidget(card)
        return card

    def remove_card(self, project_name: str):
        """Remove card for a specific project."""
        for i, card in enumerate(self.cards):
            if card.project_name == project_name:
                self.cards.pop(i)
                self.layout.removeWidget(card)
                card.deleteLater()
                break

    def clear(self):
        """Remove all stopped cards."""
        for card in self.cards:
            self.layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def has_cards(self) -> bool:
        """Return True if there are any stopped cards."""
        return len(self.cards) > 0


class TabButton(QPushButton):
    """
    A styled checkable button for tab navigation.

    Provides theme-aware styling with different appearances for selected
    and unselected states. Designed to work with TabSwitcher but can be
    used independently.

    Args:
        text: The button label text
        parent: Parent widget
    """

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFont(QFont(FONT_FAMILY, 11))
        self.setMinimumHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, selected: bool):
        """Update button style based on selection state."""
        colors = get_colors()
        if selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['bg_light']};
                    color: {colors['text_primary']};
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['container_bg']};
                    color: {colors['text_primary']};
                    border: none;
                    border-radius: 6px;
                    padding: 6px 16px;
                }}
                QPushButton:hover {{
                    background-color: {colors['separator']};
                }}
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)


class TabSwitcher(QFrame):
    """
    A segmented button-style tab switcher container.

    Manages a group of TabButton widgets for navigation between views.
    Provides exclusive selection (only one tab active at a time) and
    callback support for tab changes.

    Args:
        tabs: List of tab names to create buttons for
        parent: Parent widget

    Usage:
        switcher = TabSwitcher(["Tab1", "Tab2", "Tab3"])
        switcher.set_on_tab_change(lambda name: print(f"Switched to {name}"))
    """

    def __init__(self, tabs: list[str], parent=None):
        super().__init__(parent)
        colors = get_colors()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['container_bg']};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.buttons: dict[str, TabButton] = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for i, tab_name in enumerate(tabs):
            btn = TabButton(tab_name)
            self.buttons[tab_name] = btn
            self.button_group.addButton(btn, i)
            layout.addWidget(btn)

        # Connect signal
        self.button_group.buttonClicked.connect(self._on_button_clicked)

        # Select first tab by default
        if tabs:
            self.buttons[tabs[0]].setChecked(True)

        self._current_tab = tabs[0] if tabs else ""
        self._on_tab_change = None

    def _on_button_clicked(self, button):
        """Handle tab button click."""
        for name, btn in self.buttons.items():
            btn._update_style(btn == button)
            if btn == button:
                self._current_tab = name

        if self._on_tab_change:
            self._on_tab_change(self._current_tab)

    def set_on_tab_change(self, callback):
        """Set the callback for tab changes."""
        self._on_tab_change = callback

    def get_current_tab(self) -> str:
        """Get the currently selected tab name."""
        return self._current_tab

    def set_current_tab(self, tab_name: str):
        """Set the current tab by name."""
        if tab_name in self.buttons:
            self.buttons[tab_name].setChecked(True)
            self._current_tab = tab_name
            for name, btn in self.buttons.items():
                btn._update_style(name == tab_name)


# =============================================================================
# Dialog Components (moved from dialogs.py)
# =============================================================================

class MessageBox(QDialog):
    """Simple message box dialog using PyQt6."""

    def __init__(self, parent: QWidget, title: str, message: str, msg_type: str = "info"):
        super().__init__(parent)
        colors = get_colors()

        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui(message)

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 350) // 2
            y = parent_geo.y() + (parent_geo.height() - 150) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self, message: str):
        """Build the dialog UI."""
        colors = get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Message label
        msg_label = QLabel(message)
        msg_label.setFont(QFont(FONT_FAMILY, 11))
        msg_label.setStyleSheet(f"color: {colors['text_primary']};")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label)

        layout.addStretch()

        # OK button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setFixedSize(100, 32)
        ok_btn.setFont(QFont(FONT_FAMILY, 11))
        ok_btn.setStyleSheet(f"""
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
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class ConfirmDialog(QDialog):
    """Confirmation dialog using PyQt6."""

    def __init__(self, parent: QWidget, title: str, message: str):
        super().__init__(parent)
        colors = get_colors()

        self.result = False

        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {colors['bg_dark']};")

        self._build_ui(message)

        # Center on parent
        if parent:
            parent_geo = parent.geometry()
            x = parent_geo.x() + (parent_geo.width() - 350) // 2
            y = parent_geo.y() + (parent_geo.height() - 150) // 2
            self.move(x, y)

        self.exec()

    def _build_ui(self, message: str):
        """Build the dialog UI."""
        colors = get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Message label
        msg_label = QLabel(message)
        msg_label.setFont(QFont(FONT_FAMILY, 11))
        msg_label.setStyleSheet(f"color: {colors['text_primary']};")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg_label)

        layout.addStretch()

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        yes_btn = QPushButton("Yes")
        yes_btn.setFixedSize(80, 32)
        yes_btn.setFont(QFont(FONT_FAMILY, 11))
        yes_btn.setStyleSheet(f"""
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
        yes_btn.clicked.connect(self._yes)
        btn_layout.addWidget(yes_btn)

        no_btn = QPushButton("No")
        no_btn.setFixedSize(80, 32)
        no_btn.setFont(QFont(FONT_FAMILY, 11))
        no_btn.setStyleSheet(f"""
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
        no_btn.clicked.connect(self._no)
        btn_layout.addWidget(no_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _yes(self):
        self.result = True
        self.accept()

    def _no(self):
        self.result = False
        self.reject()

    def get_result(self) -> bool:
        return self.result


def get_scrollbar_qss(
    vertical: bool = True,
    horizontal: bool = False,
    transparent_track: bool = False,
    width: int = 12
) -> str:
    """
    Generate consistent QSS for scrollbar styling.

    Args:
        vertical: Include vertical scrollbar styling
        horizontal: Include horizontal scrollbar styling
        transparent_track: Use transparent track (True) or opaque theme color (False)
        width: Scrollbar width in pixels

    Returns:
        QSS string for scrollbar styling
    """
    colors = get_colors()
    track_color = "transparent" if transparent_track else colors["scrollbar_track"]
    thumb_color = colors["scrollbar_thumb"]
    thumb_hover = colors["scrollbar_thumb_hover"]
    border_radius = max(3, width // 3)

    qss_parts = []

    if vertical:
        qss_parts.append(f"""
            QScrollBar:vertical {{
                background-color: {track_color};
                width: {width}px;
                border-radius: {border_radius}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {thumb_color};
                border-radius: {border_radius}px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {thumb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    if horizontal:
        qss_parts.append(f"""
            QScrollBar:horizontal {{
                background-color: {track_color};
                height: {width}px;
                border-radius: {border_radius}px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {thumb_color};
                border-radius: {border_radius}px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {thumb_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """)

    return "".join(qss_parts)


# Aliases for backwards compatibility
CTkTableRow = TableRow
CTkTableDivider = TableDivider
CTkColumnBorder = ColumnBorder
CTkTable = Table
CTkSessionCard = SessionCard
CTkSessionList = SessionList
CTkTabButton = TabButton
CTkTabSwitcher = TabSwitcher
CTkMessagebox = MessageBox
CTkConfirmDialog = ConfirmDialog