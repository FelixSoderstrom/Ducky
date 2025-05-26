from enum import Enum
from typing import Optional, Dict
import tkinter as tk
from tkinter import ttk

class NotificationPreference(Enum):
    """Enum representing different notification preferences."""
    VOICE = "I want ducky to talk to me using his voice"
    TEXT = "I want Ducky to send me messages via text"
    BADGE = "I want ducky to play a notification sound"

# Map UI choices to database notification type names
NOTIFICATION_TYPE_MAP: Dict[NotificationPreference, str] = {
    NotificationPreference.VOICE: "Voice",
    NotificationPreference.TEXT: "Text",
    NotificationPreference.BADGE: "Badge"
}

class NotificationPreferenceDialog:
    """Dialog window for selecting notification preferences."""
    
    def __init__(self, parent):
        self.selected_preference: Optional[NotificationPreference] = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Notification Preferences")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        window_width = 400
        window_height = 250
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add header label
        header_label = ttk.Label(
            self.dialog,
            text="How would you like to be notified?",
            wraplength=350,
            justify="center",
            padding=(10, 10),
            font=("Arial", 12, "bold")
        )
        header_label.pack(pady=10)
        
        # Frame for radio buttons
        self.radio_var = tk.StringVar()
        radio_frame = ttk.Frame(self.dialog)
        radio_frame.pack(pady=10, fill="x", padx=20)
        
        # Add radio buttons for each preference
        for pref in NotificationPreference:
            ttk.Radiobutton(
                radio_frame,
                text=pref.value,
                value=pref.name,
                variable=self.radio_var
            ).pack(pady=5, anchor="w")
        
        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(
            button_frame,
            text="Submit",
            command=self.submit
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        ).pack(side="left", padx=5)
        
        # Bind Enter key to submit and Escape to cancel
        self.dialog.bind("<Return>", lambda e: self.submit())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def submit(self) -> None:
        """Submit the selected preference and close the dialog."""
        selected = self.radio_var.get()
        if selected:
            self.selected_preference = NotificationPreference[selected]
        self.dialog.destroy()
    
    def cancel(self) -> None:
        """Cancel the operation and close the dialog."""
        self.dialog.destroy()

async def get_notification_preference(parent_window: tk.Tk) -> Optional[NotificationPreference]:
    """Show notification preference dialog and return the selected preference.
    
    Args:
        parent_window: The parent tkinter window
        
    Returns:
        NotificationPreference if user selects one, None if cancelled
    """
    dialog = NotificationPreferenceDialog(parent_window)
    return dialog.selected_preference 