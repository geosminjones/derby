#!/usr/bin/env python3
"""
projects_tab.py - Projects management tab and dialogs for Derby GUI
"""

import sqlite3
from typing import TYPE_CHECKING

import customtkinter as ctk

import db
import themes
from themes import FONT_FAMILY
from dialogs import CTkMessagebox

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


class ProjectsTab:
    """Projects tab for managing projects and background tasks."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.frame = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the projects tab UI with split view."""
        # Runtime import to avoid circular dependency
        from gui import TreeviewFrame

        # Main container
        main_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # =====================================================================
        # TOP HALF: Regular Projects
        # =====================================================================
        top_frame = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        top_frame.pack(fill=ctk.BOTH, expand=True, pady=(0, 5))

        ctk.CTkLabel(top_frame, text="Projects", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.tree_frame = TreeviewFrame(
            top_frame,
            columns=("name", "priority", "tags"),
            headings=["Name", "Priority", "Tags"],
            widths=[200, 120, 250],
            height=6
        )
        self.tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10)
        self.tree = self.tree_frame.tree

        # Button row for projects
        btn_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        btn_frame.pack(fill=ctk.X, padx=10, pady=5)

        add_btn = ctk.CTkButton(btn_frame, text="Add Project", command=self.add_project)
        add_btn.pack(side=ctk.LEFT, padx=5)

        rename_btn = ctk.CTkButton(btn_frame, text="Rename", command=self.rename_project)
        rename_btn.pack(side=ctk.LEFT, padx=5)

        priority_btn = ctk.CTkButton(btn_frame, text="Edit Priority", command=self.edit_priority)
        priority_btn.pack(side=ctk.LEFT, padx=5)

        tags_btn = ctk.CTkButton(btn_frame, text="Edit Tags", command=self.edit_tags)
        tags_btn.pack(side=ctk.LEFT, padx=5)

        delete_btn = ctk.CTkButton(btn_frame, text="Delete", command=self.delete_project)
        delete_btn.pack(side=ctk.LEFT, padx=5)

        # =====================================================================
        # BOTTOM HALF: Background Tasks
        # =====================================================================
        bottom_frame = ctk.CTkFrame(main_frame, fg_color=themes.get_colors()["container_bg"])
        bottom_frame.pack(fill=ctk.BOTH, expand=True, pady=(5, 0))

        ctk.CTkLabel(bottom_frame, text="Background Tasks", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.bg_tree_frame = TreeviewFrame(
            bottom_frame,
            columns=("name",),
            headings=["Task Name"],
            widths=[400],
            height=6
        )
        self.bg_tree_frame.pack(fill=ctk.BOTH, expand=True, padx=10)
        self.bg_tree = self.bg_tree_frame.tree

        # Button row for background tasks
        bg_btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bg_btn_frame.pack(fill=ctk.X, padx=10, pady=5)

        bg_add_btn = ctk.CTkButton(bg_btn_frame, text="Add Task", command=self.add_background_task)
        bg_add_btn.pack(side=ctk.LEFT, padx=5)

        bg_rename_btn = ctk.CTkButton(bg_btn_frame, text="Rename", command=self.rename_background_task)
        bg_rename_btn.pack(side=ctk.LEFT, padx=5)

        bg_delete_btn = ctk.CTkButton(bg_btn_frame, text="Delete", command=self.delete_background_task)
        bg_delete_btn.pack(side=ctk.LEFT, padx=5)

        refresh_btn = ctk.CTkButton(bg_btn_frame, text="Refresh All", command=self.refresh)
        refresh_btn.pack(side=ctk.LEFT, padx=5)

    def refresh(self):
        """Refresh both projects and background tasks lists."""
        # Clear existing
        self.tree_frame.clear()
        self.bg_tree_frame.clear()

        # Get regular projects
        projects = db.list_projects(is_background=False)

        for project in projects:
            priority_label = f"{project.priority} ({PRIORITY_LABELS.get(project.priority, 'Unknown')})"
            tags_str = ", ".join(project.tags) if project.tags else ""

            self.tree_frame.insert(
                values=(project.name, priority_label, tags_str),
                iid=project.name
            )

        # Get background tasks
        bg_tasks = db.list_projects(is_background=True)

        for task in bg_tasks:
            self.bg_tree_frame.insert(values=(task.name,), iid=task.name)

    def add_project(self):
        """Show dialog to add a new project."""
        AddProjectDialog(self.app.root, self.app)

    def add_background_task(self):
        """Show dialog to add a new background task."""
        AddBackgroundTaskDialog(self.app.root, self.app)

    def edit_priority(self):
        """Edit priority of selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        EditPriorityDialog(self.app.root, self.app, project_name)

    def edit_tags(self):
        """Edit tags of selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        EditTagsDialog(self.app.root, self.app, project_name)

    def rename_project(self):
        """Rename selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, project_name)

    def rename_background_task(self):
        """Rename selected background task."""
        selection = self.bg_tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a task", "warning")
            return

        task_name = selection[0]
        RenameProjectDialog(self.app.root, self.app, task_name)

    def delete_project(self):
        """Delete selected project."""
        selection = self.tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a project", "warning")
            return

        project_name = selection[0]
        DeleteProjectDialog(self.app.root, self.app, project_name)

    def delete_background_task(self):
        """Delete selected background task."""
        selection = self.bg_tree_frame.get_selection()
        if not selection:
            CTkMessagebox(self.app.root, "Warning", "Please select a task", "warning")
            return

        task_name = selection[0]
        DeleteProjectDialog(self.app.root, self.app, task_name, is_background=True)


class AddProjectDialog:
    """Dialog for adding a new project."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Add Project")
        self.dialog.geometry("400x250")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar()
        self.priority_var = ctk.StringVar(value="3")
        self.tags_var = ctk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        # Name
        ctk.CTkLabel(main_frame, text="Name:").pack(anchor="w", pady=(0, 2))
        name_entry = ctk.CTkEntry(main_frame, textvariable=self.name_var, width=300)
        name_entry.pack(anchor="w", pady=(0, 10))
        name_entry.focus()

        # Priority
        priority_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        priority_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(priority_frame, text="Priority (1-5):").pack(side=ctk.LEFT)
        priority_entry = ctk.CTkEntry(priority_frame, textvariable=self.priority_var, width=60)
        priority_entry.pack(side=ctk.LEFT, padx=10)

        # Tags
        tags_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tags_frame.pack(fill=ctk.X, pady=(0, 10))

        ctk.CTkLabel(tags_frame, text="Tags:").pack(side=ctk.LEFT)
        tags_entry = ctk.CTkEntry(tags_frame, textvariable=self.tags_var, width=200)
        tags_entry.pack(side=ctk.LEFT, padx=10)
        ctk.CTkLabel(tags_frame, text="(comma-separated)").pack(side=ctk.LEFT)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Add", command=self._do_add).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_add(self):
        """Add the project."""
        name = self.name_var.get().strip()
        tags_str = self.tags_var.get().strip()

        if not name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a project name", "warning")
            return

        try:
            priority = int(self.priority_var.get())
        except ValueError:
            CTkMessagebox(self.dialog, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            CTkMessagebox(self.dialog, "Warning", "Priority must be between 1 and 5", "warning")
            return

        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        try:
            db.create_project(name, priority=priority, tags=tags)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class AddBackgroundTaskDialog:
    """Dialog for adding a new background task."""

    def __init__(self, parent, app: 'DerbyApp'):
        self.app = app

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Add Background Task")
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar()

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        # Name
        ctk.CTkLabel(main_frame, text="Task Name:").pack(anchor="w", pady=(0, 2))
        name_entry = ctk.CTkEntry(main_frame, textvariable=self.name_var, width=250)
        name_entry.pack(anchor="w", pady=(0, 10))
        name_entry.focus()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Add", command=self._do_add).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_add(self):
        """Add the background task."""
        name = self.name_var.get().strip()

        if not name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a task name", "warning")
            return

        try:
            db.create_project(name, is_background=True)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class EditPriorityDialog:
    """Dialog for editing a project's priority."""

    def __init__(self, parent, app: 'DerbyApp', project_name: str):
        self.app = app
        self.project_name = project_name

        # Get current priority
        project = db.get_project(project_name)
        current_priority = project.priority if project else 3

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Edit Priority: {project_name}")
        self.dialog.geometry("350x180")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.priority_var = ctk.StringVar(value=str(current_priority))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Project: {self.project_name}").pack(pady=10)

        priority_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        priority_frame.pack(pady=10)

        ctk.CTkLabel(priority_frame, text="Priority (1-5):").pack(side=ctk.LEFT)
        priority_entry = ctk.CTkEntry(priority_frame, textvariable=self.priority_var, width=60)
        priority_entry.pack(side=ctk.LEFT, padx=10)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Save", command=self._do_save).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_save(self):
        """Save the priority."""
        try:
            priority = int(self.priority_var.get())
        except ValueError:
            CTkMessagebox(self.dialog, "Warning", "Priority must be a number between 1 and 5", "warning")
            return

        if not 1 <= priority <= 5:
            CTkMessagebox(self.dialog, "Warning", "Priority must be between 1 and 5", "warning")
            return

        try:
            db.update_project_priority(self.project_name, priority)
            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class EditTagsDialog:
    """Dialog for editing a project's tags."""

    def __init__(self, parent, app: 'DerbyApp', project_name: str):
        self.app = app
        self.project_name = project_name

        # Get project and current tags
        self.project = db.get_project(project_name)
        current_tags = self.project.tags if self.project else []

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Edit Tags: {project_name}")
        self.dialog.geometry("450x200")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.tags_var = ctk.StringVar(value=", ".join(current_tags))

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Project: {self.project_name}").pack(pady=10)

        tags_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tags_frame.pack(fill=ctk.X, pady=10)

        ctk.CTkLabel(tags_frame, text="Tags:").pack(side=ctk.LEFT)
        tags_entry = ctk.CTkEntry(tags_frame, textvariable=self.tags_var, width=300)
        tags_entry.pack(side=ctk.LEFT, padx=10)
        tags_entry.focus()

        ctk.CTkLabel(main_frame, text="(comma-separated)", text_color=themes.get_colors()["text_secondary"]).pack()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Save", command=self._do_save).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_save(self):
        """Save the tags."""
        if not self.project:
            CTkMessagebox(self.dialog, "Error", "Project not found", "error")
            return

        # Parse new tags
        tags_str = self.tags_var.get().strip()
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

            self.dialog.destroy()
            self.app.projects_tab.refresh()
        except (sqlite3.IntegrityError, ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class RenameProjectDialog:
    """Dialog for renaming a project."""

    def __init__(self, parent, app: 'DerbyApp', project_name: str):
        self.app = app
        self.old_name = project_name

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Rename Project")
        self.dialog.geometry("450x200")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.name_var = ctk.StringVar(value=project_name)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        ctk.CTkLabel(main_frame, text=f"Current name: {self.old_name}").pack(pady=10)

        name_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        name_frame.pack(fill=ctk.X, pady=10)

        ctk.CTkLabel(name_frame, text="New name:").pack(side=ctk.LEFT)
        name_entry = ctk.CTkEntry(name_frame, textvariable=self.name_var, width=280)
        name_entry.pack(side=ctk.LEFT, padx=10)
        name_entry.focus()
        name_entry.select_range(0, ctk.END)

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Rename", command=self._do_rename).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_rename(self):
        """Rename the project."""
        new_name = self.name_var.get().strip()

        if not new_name:
            CTkMessagebox(self.dialog, "Warning", "Please enter a project name", "warning")
            return

        if new_name == self.old_name:
            self.dialog.destroy()
            return

        try:
            result = db.rename_project(self.old_name, new_name)
            if result is None:
                CTkMessagebox(self.dialog, "Error", "Project not found", "error")
                return

            self.dialog.destroy()
            self.app.projects_tab.refresh()
            self.app.timer_tab.refresh()
            self.app.history_tab.refresh()
        except sqlite3.IntegrityError:
            CTkMessagebox(self.dialog, "Error", f"A project named '{new_name}' already exists", "error")
        except (ValueError, sqlite3.OperationalError) as e:
            CTkMessagebox(self.dialog, "Error", str(e), "error")


class DeleteProjectDialog:
    """Dialog for deleting a project with option to delete associated sessions."""

    def __init__(self, parent, app: 'DerbyApp', project_name: str, is_background: bool = False):
        self.app = app
        self.project_name = project_name
        self.is_background = is_background

        self.dialog = ctk.CTkToplevel(parent)
        title = "Delete Task" if is_background else "Delete Project"
        self.dialog.title(title)
        self.dialog.geometry("450x220")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 220) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.delete_sessions_var = ctk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=15)

        item_type = "task" if self.is_background else "project"
        ctk.CTkLabel(
            main_frame,
            text=f"Are you sure you want to delete the {item_type}:\n\"{self.project_name}\"?",
            wraplength=400
        ).pack(pady=10)

        # Option to delete sessions
        delete_sessions_check = ctk.CTkCheckBox(
            main_frame,
            text="Also delete all associated sessions (time entries)",
            variable=self.delete_sessions_var
        )
        delete_sessions_check.pack(pady=10)

        ctk.CTkLabel(
            main_frame,
            text="(If unchecked, sessions will be kept but become orphaned)",
            text_color=themes.get_colors()["text_secondary"],
            font=ctk.CTkFont(size=11)
        ).pack()

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Delete", command=self._do_delete, fg_color=themes.get_colors()["danger"], hover_color=themes.get_colors()["danger_hover"]).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=ctk.LEFT, padx=10)

    def _do_delete(self):
        """Delete the project."""
        delete_sessions = self.delete_sessions_var.get()

        result = db.delete_project(self.project_name, delete_sessions=delete_sessions)
        if not result:
            CTkMessagebox(self.dialog, "Error", "Project not found", "error")
            return

        self.dialog.destroy()
        self.app.projects_tab.refresh()
        self.app.timer_tab.refresh()
        self.app.history_tab.refresh()
