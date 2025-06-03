"""API Key dialog component for collecting Anthropic API keys."""

import tkinter as tk
import logging

logger = logging.getLogger("ducky.ui.dialogs")


class APIKeyDialog:
    """Dialog window for collecting the Anthropic API key."""
    
    def __init__(self, parent):
        self.api_key = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("API Key Required")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        window_width = 400
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add widgets
        label = tk.Label(
            self.dialog,
            text="Please enter your Anthropic API key:",
            wraplength=350,
            justify="center"
        )
        label.pack(pady=(20, 10))  # More top padding to compensate for removed padding
        
        self.entry = tk.Entry(self.dialog, width=40, show="*")
        self.entry.pack(pady=10)
        
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        tk.Button(
            button_frame,
            text="Submit",
            command=self.submit
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side="left", padx=5)
        
        # Bind Enter key to submit
        self.dialog.bind("<Return>", lambda e: self.submit())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
        # Focus the entry widget
        self.entry.focus_set()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def submit(self) -> None:
        """Submit the API key and close the dialog."""
        self.api_key = self.entry.get().strip()
        self.dialog.destroy()
    
    def cancel(self) -> None:
        """Cancel the operation and close the dialog."""
        self.dialog.destroy() 