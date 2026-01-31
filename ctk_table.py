"""
ctk_table.py - Custom CTK-based table component for Derby GUI

A reusable table module that replaces tkinter Treeview with modern CustomTkinter
widgets. Provides a cleaner, more customizable appearance with proper theming support.
"""

from typing import Any, Callable, Optional
import customtkinter as ctk

import themes
from themes import FONT_FAMILY
from gui_utils import batch_update


class CTkTableRow(ctk.CTkFrame):
    """
    A single row in the CTkTable.

    Each row contains cells (CTkLabel or CTkFrame with custom content)
    and optional action buttons.
    """

    def __init__(
        self,
        parent,
        row_id: str,
        values: tuple,
        column_widths: list[int],
        column_anchors: list[str],
        on_action: Optional[Callable[[str, str], None]] = None,
        actions: Optional[list[dict]] = None,
        row_padding: int = 0,
        is_header: bool = False,
        **kwargs
    ):
        colors = themes.get_colors()

        # Header rows get different styling
        if is_header:
            bg_color = colors["bg_light"]
        else:
            bg_color = colors["bg_medium"]

        super().__init__(parent, fg_color=bg_color, corner_radius=0, **kwargs)

        self.row_id = row_id
        self.values = list(values)
        self.column_widths = column_widths
        self.column_anchors = column_anchors
        self.on_action = on_action
        self.actions = actions or []
        self.is_header = is_header
        self.cell_labels: list[ctk.CTkLabel] = []
        self.action_buttons: list[ctk.CTkButton] = []

        self._build_row(row_padding)

    def _build_row(self, padding: int):
        """Build the row with cells and optional action buttons."""
        colors = themes.get_colors()

        # Main content frame - fixed height for compact rows
        content_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        content_frame.pack(fill=ctk.X, padx=4, pady=0)
        content_frame.pack_propagate(False)

        # Create cells for each value
        for i, (value, width, anchor) in enumerate(zip(self.values, self.column_widths, self.column_anchors)):
            # Skip if this is the actions column (we handle it separately)
            if self.actions and i == len(self.values) - 1:
                continue

            cell_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=width, height=30)
            cell_frame.pack(side=ctk.LEFT, fill=ctk.Y, padx=(0, 8))
            cell_frame.pack_propagate(False)

            # Map anchor to CTk anchor
            ctk_anchor = self._map_anchor(anchor)

            font_weight = "bold" if self.is_header else "normal"
            label = ctk.CTkLabel(
                cell_frame,
                text=str(value),
                anchor=ctk_anchor,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight=font_weight),
                text_color=colors["text_primary"]
            )
            # Pack label centered vertically, anchored horizontally
            label.pack(side=ctk.LEFT, anchor=ctk_anchor, fill=ctk.Y, expand=True)
            self.cell_labels.append(label)

        # Create action buttons if provided
        if self.actions and not self.is_header:
            actions_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            actions_frame.pack(side=ctk.RIGHT, padx=(10, 0))

            for action in self.actions:
                btn = ctk.CTkButton(
                    actions_frame,
                    text=action.get("text", ""),
                    width=action.get("width", 60),
                    height=28,
                    fg_color=action.get("fg_color", colors["bg_light"]),
                    hover_color=action.get("hover_color", colors["separator"]),
                    text_color=action.get("text_color", colors["text_primary"]),
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    corner_radius=4,
                    command=lambda a=action: self._handle_action(a["action_id"])
                )
                btn.pack(side=ctk.LEFT, padx=2)
                self.action_buttons.append(btn)

    def _map_anchor(self, anchor: str) -> str:
        """Map treeview-style anchors to CTk anchors."""
        mapping = {
            'w': 'w',
            'e': 'e',
            'center': 'center',
            'c': 'center',
            'n': 'n',
            's': 's',
            'nw': 'nw',
            'ne': 'ne',
            'sw': 'sw',
            'se': 'se'
        }
        return mapping.get(anchor, 'w')

    def _handle_action(self, action_id: str):
        """Handle action button click."""
        if self.on_action:
            self.on_action(self.row_id, action_id)

    def set_value(self, column_index: int, value: str):
        """Update the value of a specific cell."""
        if 0 <= column_index < len(self.cell_labels):
            self.cell_labels[column_index].configure(text=str(value))
            self.values[column_index] = value

    def update_actions(self, new_actions: list[dict]):
        """Update the action buttons for this row."""
        colors = themes.get_colors()

        # Update existing buttons or create new ones
        for i, action in enumerate(new_actions):
            if i < len(self.action_buttons):
                btn = self.action_buttons[i]
                btn.configure(
                    text=action.get("text", ""),
                    fg_color=action.get("fg_color", colors["bg_light"]),
                    hover_color=action.get("hover_color", colors["separator"]),
                    command=lambda a=action: self._handle_action(a["action_id"])
                )

        self.actions = new_actions


class CTkTableDivider(ctk.CTkFrame):
    """A subtle divider line between table rows."""

    def __init__(self, parent, **kwargs):
        colors = themes.get_colors()
        super().__init__(
            parent,
            fg_color=colors["separator"],
            height=2,
            corner_radius=0,
            **kwargs
        )
        # Prevent the frame from collapsing to 0 height
        self.pack_propagate(False)
        self.configure(height=2)


class CTkTable(ctk.CTkFrame):
    """
    A custom table widget built with CTK components.

    Replaces tkinter Treeview with a modern, themeable table that supports:
    - Custom column widths and alignments
    - Action buttons per row
    - Row dividers
    - Scrolling support
    - Dynamic updates

    Usage:
        table = CTkTable(
            parent,
            columns=["Name", "Started", "Duration"],
            widths=[200, 150, 100],
            anchors=['w', 'w', 'w'],
            show_header=True
        )
        table.pack(fill=ctk.BOTH, expand=True)

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
        parent,
        columns: list[str],
        widths: list[int],
        anchors: Optional[list[str]] = None,
        show_header: bool = True,
        row_padding: int = 0,
        row_spacing: int = 1,
        show_dividers: bool = True,
        on_action: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        colors = themes.get_colors()
        super().__init__(parent, fg_color=colors["bg_dark"], corner_radius=6, **kwargs)

        self.columns = columns
        self.widths = widths
        self.anchors = anchors or ['w'] * len(columns)
        self.show_header = show_header
        self.row_padding = row_padding
        self.row_spacing = row_spacing
        self.show_dividers = show_dividers
        self.on_action = on_action

        self.rows: dict[str, CTkTableRow] = {}
        self.row_order: list[str] = []

        self._build_table()

    def _build_table(self):
        """Build the table structure."""
        colors = themes.get_colors()

        # Create scrollable frame for content
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=colors["bg_medium"],
            corner_radius=6,
            scrollbar_button_color=colors["bg_light"],
            scrollbar_button_hover_color=colors["separator"]
        )
        self.scrollable_frame.pack(fill=ctk.BOTH, expand=True, padx=2, pady=2)

        # Initialize header row reference
        self._header_row: CTkTableRow | None = None

        # Add header if requested
        if self.show_header:
            self._add_header()

    def _add_header(self):
        """Add the header row."""
        header_row = CTkTableRow(
            self.scrollable_frame,
            row_id="_header",
            values=tuple(self.columns),
            column_widths=self.widths,
            column_anchors=self.anchors,
            row_padding=0,
            is_header=True
        )
        header_row.pack(fill=ctk.X)

        # Store reference to header row for later updates
        self._header_row = header_row

        # Add 1-pixel divider after header
        divider = CTkTableDivider(self.scrollable_frame)
        divider.pack(fill=ctk.X)

    def update_header(self, column_index: int, text: str):
        """Update header text for a specific column."""
        if self._header_row and 0 <= column_index < len(self._header_row.cell_labels):
            self._header_row.cell_labels[column_index].configure(text=text)
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
            self._header_row.destroy()
            self._header_row = None

        # Find and remove the header divider (first divider after where header was)
        for widget in self.scrollable_frame.winfo_children():
            if isinstance(widget, CTkTableDivider):
                widget.destroy()
                break

        # Re-add header
        if self.show_header:
            self._add_header()

    def add_divider(self):
        """Add an explicit separator divider line between rows (for group separators)."""
        divider = CTkTableDivider(self.scrollable_frame)
        divider.pack(fill=ctk.X, pady=(2, 2))

    def add_row(
        self,
        row_id: str,
        values: tuple,
        actions: Optional[list[dict]] = None,
        is_total: bool = False
    ) -> CTkTableRow:
        """
        Add a new row to the table.

        Args:
            row_id: Unique identifier for the row
            values: Tuple of values for each column
            actions: Optional list of action button configs:
                [{"text": "Stop", "action_id": "stop", "fg_color": "#...", "hover_color": "#..."}]
            is_total: If True, uses header styling (bold) for total rows

        Returns:
            The created CTkTableRow
        """
        # Add 1-pixel divider before row (except for first row)
        if self.rows and self.show_dividers:
            divider = CTkTableDivider(self.scrollable_frame)
            divider.pack(fill=ctk.X)

        row = CTkTableRow(
            self.scrollable_frame,
            row_id=row_id,
            values=values,
            column_widths=self.widths,
            column_anchors=self.anchors,
            on_action=self.on_action,
            actions=actions,
            row_padding=self.row_padding,
            is_header=is_total  # Reuse header styling for total rows
        )
        row.pack(fill=ctk.X)

        self.rows[row_id] = row
        self.row_order.append(row_id)

        return row

    def clear(self):
        """Remove all data rows from the table, keeping the header intact."""
        self.clear_rows()

    def clear_rows(self):
        """Remove all data rows from the table, keeping the header intact."""
        # Use batch_update to defer painting until all changes are done
        with batch_update(self.scrollable_frame):
            # Destroy only data row widgets and their dividers, keep header
            # We need to track which widgets to destroy
            widgets_to_destroy = []
            found_header_divider = False

            for widget in self.scrollable_frame.winfo_children():
                # Skip the header row
                if widget is self._header_row:
                    continue
                # Skip the first divider (header divider)
                if isinstance(widget, CTkTableDivider) and not found_header_divider:
                    found_header_divider = True
                    continue
                # Everything else is a data row or data divider
                widgets_to_destroy.append(widget)

            for widget in widgets_to_destroy:
                widget.destroy()

            self.rows.clear()
            self.row_order.clear()

    def get_row(self, row_id: str) -> Optional[CTkTableRow]:
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
            row.destroy()
            self.row_order.remove(row_id)


class CTkSessionCard(ctk.CTkFrame):
    """
    A card-style component for displaying a single active session.

    Provides a more spacious, visually distinct representation than table rows,
    ideal for active session displays where each item deserves visual prominence.
    """

    def __init__(
        self,
        parent,
        session_id: str,
        project_name: str,
        started: str,
        duration: str,
        is_paused: bool = False,
        on_stop: Optional[Callable[[str], None]] = None,
        on_toggle_pause: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        colors = themes.get_colors()
        card_bg = colors["session_paused_bg"] if is_paused else colors["session_active_bg"]
        super().__init__(
            parent,
            fg_color=card_bg,
            corner_radius=8,
            **kwargs
        )

        self.session_id = session_id
        self.project_name = project_name
        self.is_paused = is_paused
        self.on_stop = on_stop
        self.on_toggle_pause = on_toggle_pause

        self._build_card(started, duration)

    def _build_card(self, started: str, duration: str):
        """Build the session card UI."""
        colors = themes.get_colors()

        # Yellow color for pause button
        self.pause_yellow = "#e6b800"
        self.pause_yellow_hover = "#ccaa00"

        # Green color for play button
        self.play_green = colors["success"]  # #27ae60
        self.play_green_hover = "#2ecc71"    # Lighter green for hover

        # Main content container with padding
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill=ctk.BOTH, expand=True, padx=15, pady=12)

        # Top row: Project name, buttons, and duration
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill=ctk.X)

        # Project name (left)
        self.name_label = ctk.CTkLabel(
            top_row,
            text=self.project_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=colors["text_primary"],
            anchor="w"
        )
        self.name_label.pack(side=ctk.LEFT)

        # Buttons container (after name, before duration)
        button_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        button_frame.pack(side=ctk.LEFT, padx=(12, 0))

        # Stop button
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="Stop",
            width=60,
            height=26,
            fg_color=colors["danger"],
            hover_color=colors["danger_hover"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            corner_radius=4,
            command=self._on_stop_click
        )
        self.stop_btn.pack(side=ctk.LEFT, padx=(0, 6))

        # Pause button - yellow with black text (visible when not paused)
        self.pause_btn = ctk.CTkButton(
            button_frame,
            text="Pause",
            width=60,
            height=26,
            fg_color=self.pause_yellow,
            hover_color=self.pause_yellow_hover,
            text_color="#000000",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            corner_radius=4,
            command=self._on_toggle_pause_click
        )

        # Play button - green with white text (visible when paused)
        self.play_btn = ctk.CTkButton(
            button_frame,
            text="Play",
            width=60,
            height=26,
            fg_color=self.play_green,
            hover_color=self.play_green_hover,
            text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            corner_radius=4,
            command=self._on_toggle_pause_click
        )

        # Show appropriate button based on pause state
        if self.is_paused:
            self.play_btn.pack(side=ctk.LEFT)
        else:
            self.pause_btn.pack(side=ctk.LEFT)

        # Duration (right) - larger and prominent
        self.duration_label = ctk.CTkLabel(
            top_row,
            text=duration,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=colors["success"] if not self.is_paused else colors["text_secondary"],
            anchor="e"
        )
        self.duration_label.pack(side=ctk.RIGHT)

        # Bottom row: Started time
        bottom_row = ctk.CTkFrame(content, fg_color="transparent")
        bottom_row.pack(fill=ctk.X, pady=(4, 0))

        self.started_label = ctk.CTkLabel(
            bottom_row,
            text=f"Started: {started}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=colors["text_secondary"],
            anchor="w"
        )
        self.started_label.pack(side=ctk.LEFT)

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
        self.duration_label.configure(text=duration)

    def update_pause_state(self, is_paused: bool):
        """Update the pause state and toggle Pause/Play button visibility."""
        colors = themes.get_colors()
        self.is_paused = is_paused

        # Update card background color
        card_bg = colors["session_paused_bg"] if is_paused else colors["session_active_bg"]
        self.configure(fg_color=card_bg)

        # Update duration label color
        self.duration_label.configure(
            text_color=colors["success"] if not is_paused else colors["text_secondary"]
        )

        # Toggle button visibility
        if is_paused:
            self.pause_btn.pack_forget()
            self.play_btn.pack(side=ctk.LEFT)
        else:
            self.play_btn.pack_forget()
            self.pause_btn.pack(side=ctk.LEFT)


class CTkSessionList(ctk.CTkFrame):
    """
    A scrollable list of session cards.

    Designed for displaying active sessions with visual spacing and
    individual session controls.
    """

    def __init__(
        self,
        parent,
        on_stop: Optional[Callable[[str], None]] = None,
        on_toggle_pause: Optional[Callable[[str], None]] = None,
        empty_message: str = "No active sessions",
        **kwargs
    ):
        colors = themes.get_colors()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.on_stop = on_stop
        self.on_toggle_pause = on_toggle_pause
        self.empty_message = empty_message

        self.cards: dict[str, CTkSessionCard] = {}

        self._build_list()

    def _build_list(self):
        """Build the session list container."""
        colors = themes.get_colors()

        # Scrollable container
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=colors["bg_light"],
            scrollbar_button_hover_color=colors["separator"]
        )
        self.scrollable_frame.pack(fill=ctk.BOTH, expand=True)

        # Empty state label (shown when no sessions)
        self.empty_label = ctk.CTkLabel(
            self.scrollable_frame,
            text=self.empty_message,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=colors["text_secondary"]
        )
        self.empty_label.pack(pady=20)

    def add_session(
        self,
        session_id: str,
        project_name: str,
        started: str,
        duration: str,
        is_paused: bool = False
    ) -> CTkSessionCard:
        """Add a session card to the list."""
        # Hide empty message when adding first session
        if not self.cards:
            self.empty_label.pack_forget()

        card = CTkSessionCard(
            self.scrollable_frame,
            session_id=session_id,
            project_name=project_name,
            started=started,
            duration=duration,
            is_paused=is_paused,
            on_stop=self.on_stop,
            on_toggle_pause=self.on_toggle_pause
        )
        card.pack(fill=ctk.X, pady=(0, 10))

        self.cards[session_id] = card
        return card

    def clear(self):
        """Remove all session cards."""
        # Use batch_update to defer painting until all changes are done
        with batch_update(self.scrollable_frame):
            for card in self.cards.values():
                card.destroy()
            self.cards.clear()

            # Show empty message
            self.empty_label.pack(pady=20)

    def get_card(self, session_id: str) -> Optional[CTkSessionCard]:
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
