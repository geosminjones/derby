"""
gui_utils.py - GUI utility functions for Derby

Contains helper functions and context managers for common GUI operations,
including batch update management to prevent UI flicker.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


# Track nested batch_update calls and geometry info per widget
_update_hold_count: dict[int, int] = {}
_widget_geometry: dict[int, tuple[str, dict]] = {}


@contextmanager
def batch_update(widget: 'tk.Widget'):
    """
    Context manager to defer painting during multi-step UI changes.

    Prevents flicker by temporarily unmapping the widget (making it
    invisible) during updates, then remapping it when done. This allows
    all changes to be made invisibly, with only the final state being
    rendered in a single repaint.

    Nested calls are handled correctly - only the outermost context
    triggers the visibility changes.

    Usage:
        with batch_update(my_frame):
            my_frame.clear()
            for item in items:
                my_frame.add_row(item)

    Args:
        widget: The tkinter/customtkinter widget to update
    """
    widget_id = id(widget)

    # Increment hold count for this widget
    prev_count = _update_hold_count.get(widget_id, 0)
    _update_hold_count[widget_id] = prev_count + 1

    # Store geometry info and unmap only on outermost call
    if prev_count == 0:
        geometry_type = None
        geometry_info = None

        try:
            # Detect which geometry manager is being used
            try:
                geometry_info = widget.pack_info()
                geometry_type = 'pack'
            except Exception:
                try:
                    geometry_info = widget.grid_info()
                    geometry_type = 'grid'
                except Exception:
                    try:
                        geometry_info = widget.place_info()
                        geometry_type = 'place'
                    except Exception:
                        pass

            # Store geometry info for restoration
            if geometry_info and geometry_type:
                _widget_geometry[widget_id] = (geometry_type, geometry_info)

                # Unmap the widget to prevent intermediate redraws
                if geometry_type == 'pack':
                    widget.pack_forget()
                elif geometry_type == 'grid':
                    widget.grid_remove()  # grid_remove preserves config
                elif geometry_type == 'place':
                    widget.place_forget()
        except Exception:
            _widget_geometry.pop(widget_id, None)

    try:
        yield
    finally:
        # Decrement hold count
        current_count = _update_hold_count.get(widget_id, 1) - 1
        if current_count <= 0:
            _update_hold_count.pop(widget_id, None)

            # Remap the widget only on outermost call
            stored = _widget_geometry.pop(widget_id, None)
            if stored:
                geometry_type, geometry_info = stored
                try:
                    if geometry_type == 'pack':
                        widget.pack(**geometry_info)
                    elif geometry_type == 'grid':
                        widget.grid()  # grid_remove + grid() restores original config
                    elif geometry_type == 'place':
                        widget.place(**geometry_info)
                    # Force all pending updates to process at once
                    widget.update_idletasks()
                except Exception:
                    pass
        else:
            _update_hold_count[widget_id] = current_count


@contextmanager
def freeze_widget(widget: 'tk.Widget'):
    """
    Context manager that freezes widget updates using withdraw/deiconify.

    This is a lighter-weight alternative to batch_update that works
    by temporarily withdrawing the toplevel window. Best for very
    large batch operations.

    Note: This affects the entire window, not just the widget.

    Usage:
        with freeze_widget(some_widget):
            # Many UI operations
            pass

    Args:
        widget: Any widget (its toplevel window will be frozen)
    """
    toplevel = widget.winfo_toplevel()
    was_visible = toplevel.winfo_viewable()

    if was_visible:
        toplevel.withdraw()

    try:
        yield
    finally:
        if was_visible:
            toplevel.deiconify()


def destroy_children(widget: 'tk.Widget', skip_first_n: int = 0):
    """
    Efficiently destroy all children of a widget.

    Collects all children first, then destroys them in a batch
    to minimize layout recalculations.

    Args:
        widget: The parent widget whose children should be destroyed
        skip_first_n: Number of children to skip (e.g., to preserve header)
    """
    children = widget.winfo_children()

    # Skip the first N children if requested
    children_to_destroy = children[skip_first_n:]

    # Destroy all in one go - widget internally handles this efficiently
    for child in children_to_destroy:
        child.destroy()
