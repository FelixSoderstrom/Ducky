from enum import Enum
from typing import Optional, Dict, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

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

class ElevenLabsAPIKeyDialog:
    """Dialog window for collecting the ElevenLabs API key when voice notifications are selected."""
    
    def __init__(self, parent):
        self.api_key = None
        self.go_back = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ElevenLabs API Key Required")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        window_width = 450
        window_height = 200
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add header label
        header_label = ttk.Label(
            self.dialog,
            text="Voice notifications require ElevenLabs API",
            wraplength=400,
            justify="center",
            padding=(10, 5),
            font=("Arial", 12, "bold")
        )
        header_label.pack(pady=5)
        
        # Info label
        info_label = ttk.Label(
            self.dialog,
            text="Please enter your ElevenLabs API key to enable voice notifications:",
            wraplength=400,
            justify="center",
            padding=(10, 5)
        )
        info_label.pack(pady=5)
        
        # API key entry
        self.entry = ttk.Entry(self.dialog, width=50, show="*")
        self.entry.pack(pady=10)
        
        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15)
        
        ttk.Button(
            button_frame,
            text="Back",
            command=self.back
        ).pack(side="left", padx=5)
        
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
        
        # Bind keys
        self.dialog.bind("<Return>", lambda e: self.submit())
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        
        # Focus the entry widget
        self.entry.focus_set()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def submit(self) -> None:
        """Submit the API key and close the dialog."""
        self.api_key = self.entry.get().strip()
        if not self.api_key:
            # Show error if empty
            tk.messagebox.showerror("Error", "Please enter a valid API key")
            return
        self.dialog.destroy()
    
    def back(self) -> None:
        """Go back to notification preference selection."""
        self.go_back = True
        self.dialog.destroy()
    
    def cancel(self) -> None:
        """Cancel the operation and close the dialog."""
        self.dialog.destroy()


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


async def get_notification_preference_with_elevenlabs(parent_window: tk.Tk) -> Tuple[Optional[NotificationPreference], Optional[str]]:
    """
    Show notification preference dialog and handle ElevenLabs API key collection for voice notifications.
    
    Args:
        parent_window: The parent tkinter window
        
    Returns:
        Tuple of (NotificationPreference, ElevenLabsAPIKey) where:
        - NotificationPreference is the selected preference or None if cancelled
        - ElevenLabsAPIKey is the API key string if voice was selected, None otherwise
    """
    elevenlabs_api_key = None
    
    while True:
        # Show notification preference dialog
        dialog = NotificationPreferenceDialog(parent_window)
        preference = dialog.selected_preference
        
        if not preference:
            # User cancelled
            return None, None
        
        if preference == NotificationPreference.VOICE:
            # Voice selected - need ElevenLabs API key
            elevenlabs_dialog = ElevenLabsAPIKeyDialog(parent_window)
            
            if elevenlabs_dialog.go_back:
                # User clicked back - show notification preference dialog again
                continue
            elif elevenlabs_dialog.api_key:
                # User provided API key
                elevenlabs_api_key = elevenlabs_dialog.api_key
                break
            else:
                # User cancelled ElevenLabs dialog
                return None, None
        else:
            # Non-voice preference selected
            break
    
    return preference, elevenlabs_api_key


async def get_notification_preference(parent_window: tk.Tk) -> Optional[NotificationPreference]:
    """Show notification preference dialog and return the selected preference.
    
    Args:
        parent_window: The parent tkinter window
        
    Returns:
        NotificationPreference if user selects one, None if cancelled
        
    Note:
        This is the original function kept for backward compatibility.
        For voice notifications with ElevenLabs, use get_notification_preference_with_elevenlabs()
    """
    dialog = NotificationPreferenceDialog(parent_window)
    return dialog.selected_preference 