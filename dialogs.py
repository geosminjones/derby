#!/usr/bin/env python3
"""
dialogs.py - Shared dialog components for Derby GUI
"""

import customtkinter as ctk

import themes


class CTkMessagebox:
    """Simple message box dialog using CustomTkinter."""

    def __init__(self, parent, title: str, message: str, msg_type: str = "info"):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Content
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=message, wraplength=300).pack(pady=20)

        ctk.CTkButton(main_frame, text="OK", command=self.dialog.destroy, width=100).pack()

        self.dialog.wait_window()


class CTkConfirmDialog:
    """Confirmation dialog using CustomTkinter."""

    def __init__(self, parent, title: str, message: str):
        self.result = False
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("350x150")
        self.dialog.configure(fg_color=themes.get_colors()["bg_dark"])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Content
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text=message, wraplength=300).pack(pady=20)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(btn_frame, text="Yes", command=self._yes, width=80).pack(side=ctk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="No", command=self._no, width=80).pack(side=ctk.LEFT, padx=10)

        self.dialog.wait_window()

    def _yes(self):
        self.result = True
        self.dialog.destroy()

    def _no(self):
        self.result = False
        self.dialog.destroy()

    def get_result(self):
        return self.result
