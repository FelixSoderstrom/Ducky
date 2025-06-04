import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
import logging
import os
import threading
import asyncio
import winsound

from ..utils.notification_preferences import (
    NotificationPreference, 
    NOTIFICATION_TYPE_MAP
)
from ...database.session import get_db
from ...database.models.projects import Project
from ...database.models.configs import Config
from ...database.models.notification_types import NotificationType
from ...database.models.dismissals import Dismissal
from ...database.operations.get_project import get_project_by_path
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

# Create logger for this module
logger = logging.getLogger("ducky.ui.settings")

class SettingsWindow:
    """Settings window for configuring Ducky preferences."""
    
    def __init__(self, parent_ui, project_path: str):
        self.parent_ui = parent_ui
        self.project_path = project_path
        self.window: Optional[tk.Toplevel] = None
        self.current_project: Optional[Project] = None
        self.notification_var = tk.StringVar()
        self.sound_var = tk.StringVar()
        self.available_sounds: List[str] = []
        self.anthropic_key_var = tk.StringVar()
        
        # Dismissals management
        self.dismissals: List[Dismissal] = []
        self.dismissals_listbox: Optional[tk.Listbox] = None
        self.dismissals_frame: Optional[tk.Frame] = None
        
        self._load_available_sounds()
        
    def _load_current_project(self) -> bool:
        """Load the current project from the database using the project path."""
        try:
            with get_db() as session:
                project = get_project_by_path(session, self.project_path)
                if project:
                    # Load the project with configs and notification types
                    stmt = (
                        select(Project)
                        .options(joinedload(Project.configs).joinedload(Config.notification_type))
                        .where(Project.id == project.id)
                    )
                    result = session.execute(stmt).unique()
                    self.current_project = result.scalar_one_or_none()
                    return self.current_project is not None
                return False
        except Exception as e:
            logger.error(f"Error loading current project: {str(e)}")
            return False
    
    def _get_current_notification_preference(self) -> Optional[NotificationPreference]:
        """Get the current notification preference for the project."""
        if not self.current_project:
            return None
            
        try:
            # Get the notification type name from the project's config
            if self.current_project.configs:
                config = self.current_project.configs[0]  # Assuming one config per project
                notification_type_name = config.notification_type.name
                
                # Map database name back to enum
                for pref, db_name in NOTIFICATION_TYPE_MAP.items():
                    if db_name == notification_type_name:
                        return pref
            return None
        except Exception as e:
            logger.error(f"Error getting notification preference: {str(e)}")
            return None
    
    def _update_notification_preference(self, new_preference: NotificationPreference) -> bool:
        """Update the notification preference in the database."""
        if not self.current_project:
            logger.error("No current project to update")
            return False
            
        try:
            with get_db() as session:
                # Get the notification type ID for the new preference
                stmt = select(NotificationType.id).where(
                    NotificationType.name == NOTIFICATION_TYPE_MAP[new_preference]
                )
                notification_type_id = session.execute(stmt).scalar_one_or_none()
                
                if not notification_type_id:
                    logger.error(f"Notification type not found: {NOTIFICATION_TYPE_MAP[new_preference]}")
                    return False
                
                # Update the project's config
                stmt = select(Config).where(Config.project_id == self.current_project.id)
                config = session.execute(stmt).scalar_one_or_none()
                
                if config:
                    config.notification_id = notification_type_id
                    session.commit()
                    logger.info(f"Updated notification preference to {new_preference.value}")
                    return True
                else:
                    logger.error("No config found for project")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating notification preference: {str(e)}")
            return False
    
    def _handle_notification_change(self) -> None:
        """Handle notification preference change."""
        selected_name = self.notification_var.get()
        if not selected_name:
            return
            
        # Find the enum value from the selection
        selected_preference = None
        for pref in NotificationPreference:
            if pref.name == selected_name:
                selected_preference = pref
                break
                
        if not selected_preference:
            return
            
        # Voice notifications now use local Chatterbox TTS - no API key needed
        # Just update the preference directly
        self._update_notification_preference(selected_preference)
        
    def show(self) -> None:
        """Show the settings window."""
        if self.window is not None:
            # Window already exists, just bring it to front
            self.window.lift()
            self.window.focus_set()
            return
            
        # Load current project data
        if not self._load_current_project():
            messagebox.showerror("Error", f"No project found for path: {self.project_path}")
            return
            
        logger.info("Opening settings window")
        self._create_window()
        
    def hide(self) -> None:
        """Hide the settings window."""
        if self.window is not None:
            logger.info("Closing settings window")
            self.window.destroy()
            self.window = None
            self.current_project = None
    
    def _create_window(self) -> None:
        """Create the settings window with basic layout."""
        # Create the window
        self.window = tk.Toplevel(self.parent_ui.root)
        self.window.title("Ducky Settings")
        
        # Set window size and position
        window_width = 600
        window_height = 400
        
        # Center the window relative to the parent
        parent_x = self.parent_ui.root.winfo_x()
        parent_y = self.parent_ui.root.winfo_y()
        parent_width = self.parent_ui.width
        parent_height = self.parent_ui.height + self.parent_ui.top_bar_height
        
        # Calculate center position
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        # Ensure window stays on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make window modal and stay on top
        self.window.transient(self.parent_ui.root)
        self.window.grab_set()
        self.window.attributes('-topmost', True)
        
        # Set minimum size
        self.window.minsize(400, 300)
        
        # Configure window close behavior
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Create the main layout
        self._create_layout()
        
    def _create_layout(self) -> None:
        """Create the layout for the settings window."""
        # Main container frame with dark background
        main_frame = tk.Frame(self.window, bg='#1e1e1e')
        main_frame.pack(fill='both', expand=True)
        
        # Title bar frame (custom since we want consistent styling)
        title_frame = tk.Frame(main_frame, bg='#2c2c2c', height=40)
        title_frame.pack(fill='x', side='top')
        title_frame.pack_propagate(False)
        
        # Title label
        title_label = tk.Label(
            title_frame,
            text="Settings",
            bg='#2c2c2c',
            fg='white',
            font=('Arial', 14, 'bold')
        )
        title_label.pack(side='left', padx=10, pady=10)
        
        # Create scrollable content area
        self._create_scrollable_content(main_frame)
        
        logger.info("Settings window layout created successfully")
        
    def _create_scrollable_content(self, parent: tk.Frame) -> None:
        """Create a scrollable content area."""
        # Container for canvas and scrollbar
        canvas_container = tk.Frame(parent, bg='#1e1e1e')
        canvas_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create canvas for scrollable content
        self.canvas = tk.Canvas(
            canvas_container,
            bg='#1e1e1e',
            highlightthickness=0,
            borderwidth=0
        )
        
        # Create scrollbar
        scrollbar = tk.Scrollbar(
            canvas_container,
            orient='vertical',
            command=self.canvas.yview,
            bg='#404040',
            troughcolor='#2c2c2c',
            activebackground='#606060'
        )
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Create the scrollable frame inside the canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg='#1e1e1e')
        self.canvas_window = self.canvas.create_window(
            (0, 0), 
            window=self.scrollable_frame, 
            anchor='nw'
        )
        
        # Bind events for scrolling
        self.scrollable_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Bind mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Now add all the content sections to the scrollable frame
        self._populate_scrollable_content()
        
    def _on_frame_configure(self, event) -> None:
        """Update canvas scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event) -> None:
        """Update scrollable frame width when canvas is resized."""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
    def _populate_scrollable_content(self) -> None:
        """Populate the scrollable content area with all sections."""
        # Project path section at the top
        self._create_project_info_section(self.scrollable_frame)
        
        # Add separator
        separator = tk.Frame(self.scrollable_frame, height=2, bg='#404040')
        separator.pack(fill='x', pady=(15, 20))
        
        # Notification preferences section
        self._create_notification_section(self.scrollable_frame)
        
        # Add separator
        separator2 = tk.Frame(self.scrollable_frame, height=2, bg='#404040')
        separator2.pack(fill='x', pady=(20, 20))
        
        # Notification sound section
        self._create_sound_section(self.scrollable_frame)
        
        # Add separator
        separator3 = tk.Frame(self.scrollable_frame, height=2, bg='#404040')
        separator3.pack(fill='x', pady=(20, 20))
        
        # API key management section
        self._create_api_key_section(self.scrollable_frame)
        
        # Add separator
        separator4 = tk.Frame(self.scrollable_frame, height=2, bg='#404040')
        separator4.pack(fill='x', pady=(20, 20))
        
        # Previous dismissals section
        self._create_dismissals_section(self.scrollable_frame)
        
    def _create_project_info_section(self, parent: tk.Frame) -> None:
        """Create the project information section showing the current project path."""
        # Project info container
        project_frame = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        project_frame.pack(fill='x', pady=(0, 10))
        
        # Project info content with padding
        info_content = tk.Frame(project_frame, bg='#2d2d2d')
        info_content.pack(fill='x', padx=15, pady=10)
        
        # Project label
        project_label = tk.Label(
            info_content,
            text="Current Project",
            bg='#2d2d2d',
            fg='#cccccc',
            font=('Arial', 10, 'bold')
        )
        project_label.pack(anchor='w')
        
        # Project name
        project_name_label = tk.Label(
            info_content,
            text=self.current_project.name,
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        project_name_label.pack(anchor='w', pady=(2, 0))
        
        # Project path
        project_path_label = tk.Label(
            info_content,
            text=f"Path: {self.project_path}",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9),
            wraplength=500,
            justify='left'
        )
        project_path_label.pack(anchor='w', pady=(2, 0))
        
    def _create_notification_section(self, parent: tk.Frame) -> None:
        """Create the notification preferences section."""
        # Section title
        title_label = tk.Label(
            parent,
            text="Notification Preferences",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = tk.Label(
            parent,
            text="Choose how you'd like to receive notifications from Ducky:",
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Arial', 10),
            wraplength=500,
            justify='left'
        )
        desc_label.pack(anchor='w', pady=(0, 15))
        
        # Frame for radio buttons with dark background
        radio_frame = tk.Frame(parent, bg='#1e1e1e')
        radio_frame.pack(fill='x', pady=(0, 20))
        
        # Get current preference and set the variable
        current_pref = self._get_current_notification_preference()
        if current_pref:
            self.notification_var.set(current_pref.name)
        
        # Create radio buttons for each notification preference with dark theme
        for pref in NotificationPreference:
            radio_btn = tk.Radiobutton(
                radio_frame,
                text=pref.value,
                variable=self.notification_var,
                value=pref.name,
                bg='#1e1e1e',
                fg='white',
                font=('Arial', 10),
                selectcolor='#404040',
                activebackground='#2d2d2d',
                activeforeground='white',
                command=self._handle_notification_change
            )
            radio_btn.pack(anchor='w', pady=4)
        
        # Current status section
        status_frame = tk.Frame(parent, bg='#1e1e1e')
        status_frame.pack(fill='x', pady=(20, 0))
        
        # Add a subtle separator line
        status_separator = tk.Frame(status_frame, height=1, bg='#404040')
        status_separator.pack(fill='x', pady=(0, 10))
        
        # Status info
        current_pref = self._get_current_notification_preference()
        if current_pref:
            status_text = f"Currently using: {current_pref.value}"
        else:
            status_text = "No notification preference set"
            
        status_label = tk.Label(
            status_frame,
            text=status_text,
            bg='#1e1e1e',
            fg='#888888',
            font=('Arial', 9, 'italic')
        )
        status_label.pack(anchor='w')
        
    def _load_available_sounds(self) -> None:
        """Load available sound files from the audio assets directory."""
        try:
            # Get the path to the audio directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            audio_dir = os.path.join(current_dir, "..", "assets", "audio")
            audio_dir = os.path.normpath(audio_dir)
            
            if os.path.exists(audio_dir):
                # Get all .wav files in the directory
                sound_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
                self.available_sounds = sorted(sound_files)
                logger.info(f"Found {len(self.available_sounds)} sound files: {self.available_sounds}")
            else:
                logger.warning(f"Audio directory not found: {audio_dir}")
                self.available_sounds = ["quack.wav"]  # fallback
        except Exception as e:
            logger.error(f"Error loading sound files: {str(e)}")
            self.available_sounds = ["quack.wav"]  # fallback
    
    def _get_sound_file_path(self, sound_filename: str) -> str:
        """Get the full path to a sound file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        audio_dir = os.path.join(current_dir, "..", "assets", "audio")
        return os.path.normpath(os.path.join(audio_dir, sound_filename))
    
    def _play_sound_preview(self, sound_filename: str) -> None:
        """Play a sound preview in a separate thread."""
        def play_sound():
            try:
                sound_path = self._get_sound_file_path(sound_filename)
                if os.path.exists(sound_path):
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME)
                    logger.info(f"Playing sound preview: {sound_filename}")
                else:
                    logger.error(f"Sound file not found: {sound_path}")
            except Exception as e:
                logger.error(f"Error playing sound preview: {str(e)}")
        
        # Play sound in a separate thread to avoid blocking the UI
        threading.Thread(target=play_sound, daemon=True).start()
    
    def _get_current_sound_setting(self) -> str:
        """Get the current notification sound setting for the project."""
        if not self.current_project:
            return "quack.wav"  # default
            
        try:
            if self.current_project.configs:
                config = self.current_project.configs[0]
                return config.notification_sound or "quack.wav"
            return "quack.wav"
        except Exception as e:
            logger.error(f"Error getting sound setting: {str(e)}")
            return "quack.wav"
    
    def _update_sound_setting(self, new_sound: str) -> bool:
        """Update the notification sound setting in the database."""
        if not self.current_project:
            logger.error("No current project to update")
            return False
            
        try:
            with get_db() as session:
                # Update the project's config
                stmt = select(Config).where(Config.project_id == self.current_project.id)
                config = session.execute(stmt).scalar_one_or_none()
                
                if config:
                    config.notification_sound = new_sound
                    session.commit()
                    logger.info(f"Updated notification sound to: {new_sound}")
                    return True
                else:
                    logger.error("No config found for project")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating sound setting: {str(e)}")
            return False
    
    def _handle_sound_change(self) -> None:
        """Handle notification sound change."""
        selected_sound = self.sound_var.get()
        if not selected_sound:
            return
            
        # Update the sound setting
        if self._update_sound_setting(selected_sound):
            messagebox.showinfo("Success", f"Notification sound updated to: {selected_sound}")
        else:
            messagebox.showerror("Error", "Failed to update notification sound")
            # Revert to current setting
            current_sound = self._get_current_sound_setting()
            self.sound_var.set(current_sound)
        
    def _create_sound_section(self, parent: tk.Frame) -> None:
        """Create the notification sound selection section."""
        # Section title
        title_label = tk.Label(
            parent,
            text="Notification Sound",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = tk.Label(
            parent,
            text="Choose which sound to play when you receive notifications:",
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Arial', 10),
            wraplength=500,
            justify='left'
        )
        desc_label.pack(anchor='w', pady=(0, 15))
        
        # Sound selection frame
        sound_frame = tk.Frame(parent, bg='#1e1e1e')
        sound_frame.pack(fill='x', pady=(0, 15))
        
        # Get current sound setting
        current_sound = self._get_current_sound_setting()
        self.sound_var.set(current_sound)
        
        # Sound dropdown
        sound_label = tk.Label(
            sound_frame,
            text="Select sound:",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 10)
        )
        sound_label.pack(anchor='w', pady=(0, 5))
        
        # Dropdown container
        dropdown_frame = tk.Frame(sound_frame, bg='#1e1e1e')
        dropdown_frame.pack(fill='x', pady=(0, 10))
        
        # Style the combobox for dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TCombobox',
                       fieldbackground='#404040',
                       background='#404040',
                       foreground='white',
                       arrowcolor='white',
                       bordercolor='#606060',
                       lightcolor='#404040',
                       darkcolor='#404040')
        
        # Sound dropdown
        self.sound_dropdown = ttk.Combobox(
            dropdown_frame,
            textvariable=self.sound_var,
            values=self.available_sounds,
            state='readonly',
            style='Dark.TCombobox',
            width=25
        )
        self.sound_dropdown.pack(side='left', padx=(0, 10))
        self.sound_dropdown.bind('<<ComboboxSelected>>', lambda e: self._handle_sound_change())
        
        # Preview button
        preview_btn = tk.Button(
            dropdown_frame,
            text="▶ Preview",
            bg='#404040',
            fg='white',
            font=('Arial', 9),
            relief='flat',
            padx=10,
            pady=2,
            command=lambda: self._play_sound_preview(self.sound_var.get())
        )
        preview_btn.pack(side='left')
        
        # Hover effects for preview button
        def on_enter(e):
            preview_btn.configure(bg='#505050')
        def on_leave(e):
            preview_btn.configure(bg='#404040')
        
        preview_btn.bind('<Enter>', on_enter)
        preview_btn.bind('<Leave>', on_leave)
        
        # Custom sounds info section
        info_frame = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(10, 0))
        
        info_content = tk.Frame(info_frame, bg='#2d2d2d')
        info_content.pack(fill='x', padx=15, pady=10)
        
        # Info title
        info_title = tk.Label(
            info_content,
            text="💡 Custom Notification Sounds",
            bg='#2d2d2d',
            fg='#cccccc',
            font=('Arial', 10, 'bold')
        )
        info_title.pack(anchor='w', pady=(0, 5))
        
        # Info text
        info_text = tk.Label(
            info_content,
            text="Want to use your own sounds? Simply drag .wav files into the audio folder:\n"
                 "Ducky/src/ui/assets/audio\n\n"
                 "Only WAV audio files are currently supported. Restart the application to see new sounds.",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9),
            wraplength=500,
            justify='left'
        )
        info_text.pack(anchor='w')
        
        # Current status
        status_frame = tk.Frame(parent, bg='#1e1e1e')
        status_frame.pack(fill='x', pady=(15, 0))
        
        status_separator = tk.Frame(status_frame, height=1, bg='#404040')
        status_separator.pack(fill='x', pady=(0, 10))
        
        status_text = f"Currently using: {current_sound}"
        status_label = tk.Label(
            status_frame,
            text=status_text,
            bg='#1e1e1e',
            fg='#888888',
            font=('Arial', 9, 'italic')
        )
        status_label.pack(anchor='w')
        
    def _get_api_key_display(self, api_key: Optional[str]) -> str:
        """Convert API key to display format (asterisks if set, empty if not)."""
        if api_key and api_key.strip():
            return "*" * 40  # Show 40 asterisks to indicate key is set
        return ""
    
    def _get_current_api_keys(self) -> str:
        """Get the current API key for display purposes."""
        if not self.current_project:
            return ""
        
        anthropic_display = self._get_api_key_display(self.current_project.anthropic_key)
        return anthropic_display
    
    def _update_api_keys(self, new_anthropic_key: str) -> bool:
        """Update API key in the database."""
        if not self.current_project:
            logger.error("No current project to update")
            return False
            
        try:
            with get_db() as session:
                # Get the project
                project = session.get(Project, self.current_project.id)
                if not project:
                    logger.error("Project not found in database")
                    return False
                
                changes_made = False
                
                # Update Anthropic key if provided and different
                if new_anthropic_key.strip() and new_anthropic_key != self._get_api_key_display(project.anthropic_key):
                    project.anthropic_key = new_anthropic_key.strip()
                    self.current_project.anthropic_key = new_anthropic_key.strip()
                    changes_made = True
                    logger.info("Updated Anthropic API key")
                
                if changes_made:
                    session.commit()
                    return True
                else:
                    logger.info("No API key changes detected")
                    return True  # Not an error, just no changes needed
                    
        except Exception as e:
            logger.error(f"Error updating API key: {str(e)}")
            return False
    
    def _handle_api_key_save(self) -> None:
        """Handle saving API key."""
        anthropic_key = self.anthropic_key_var.get()
        
        # Validate that key is provided and not just asterisks
        anthropic_is_asterisks = anthropic_key.strip() and all(c == '*' for c in anthropic_key.strip())
        
        # Don't update if key is just the asterisk display
        if anthropic_is_asterisks:
            anthropic_key = ""
        
        # Check if real key is provided
        if not anthropic_key.strip():
            messagebox.showwarning("No Changes", "Please enter an API key to update.")
            return
        
        # Validate key format (basic validation)
        if anthropic_key.strip() and not self._validate_anthropic_key(anthropic_key.strip()):
            messagebox.showerror("Invalid Key", "Anthropic API key format appears to be invalid.")
            return
        
        # Update the key
        if self._update_api_keys(anthropic_key):
            messagebox.showinfo("Success", "API key updated successfully!")
            # Refresh the display
            self._refresh_api_key_display()
        else:
            messagebox.showerror("Error", "Failed to update API key.")
    
    def _validate_anthropic_key(self, key: str) -> bool:
        """Basic validation for Anthropic API key format."""
        # Anthropic keys typically start with 'sk-ant-' and are longer
        return key.startswith('sk-ant-') and len(key) > 20
    
    def _refresh_api_key_display(self) -> None:
        """Refresh the API key display with current value."""
        anthropic_display = self._get_current_api_keys()
        self.anthropic_key_var.set(anthropic_display)
    
    def _create_api_key_section(self, parent: tk.Frame) -> None:
        """Create the API key management section."""
        # Section title
        title_label = tk.Label(
            parent,
            text="API Key Management",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = tk.Label(
            parent,
            text="Update your Anthropic API key. Current key is shown as asterisks (*). Paste new key to update:",
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Arial', 10),
            wraplength=500,
            justify='left'
        )
        desc_label.pack(anchor='w', pady=(0, 15))
        
        # API key management container
        api_container = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        api_container.pack(fill='x', pady=(0, 15))
        
        # API key management content with padding
        api_key_frame = tk.Frame(api_container, bg='#2d2d2d')
        api_key_frame.pack(fill='x', padx=15, pady=15)
        
        # Initialize the display value
        anthropic_display = self._get_current_api_keys()
        self.anthropic_key_var.set(anthropic_display)
        
        # Anthropic key section
        anthropic_section = tk.Frame(api_key_frame, bg='#2d2d2d')
        anthropic_section.pack(fill='x', pady=(0, 15))
        
        anthropic_label = tk.Label(
            anthropic_section,
            text="Anthropic API Key (Claude):",
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        anthropic_label.pack(anchor='w', pady=(0, 5))
        
        self.anthropic_key_entry = tk.Entry(
            anthropic_section,
            textvariable=self.anthropic_key_var,
            bg='#404040',
            fg='white',
            font=('Consolas', 10),  # Monospace font for keys
            insertbackground='white',
            relief='flat',
            bd=5,
            width=60
        )
        self.anthropic_key_entry.pack(fill='x', pady=(0, 5))
        
        # Key info for Anthropic
        anthropic_info = tk.Label(
            anthropic_section,
            text="Required for code review. Should start with 'sk-ant-'",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9)
        )
        anthropic_info.pack(anchor='w')
        
        # Button section
        button_section = tk.Frame(api_key_frame, bg='#2d2d2d')
        button_section.pack(fill='x')
        
        # Save button
        save_btn = tk.Button(
            button_section,
            text="💾 Save API Key",
            bg='#0066cc',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief='flat',
            padx=20,
            pady=8,
            command=self._handle_api_key_save
        )
        save_btn.pack(side='left')
        
        # Clear button
        clear_btn = tk.Button(
            button_section,
            text="🗑️ Clear Field",
            bg='#666666',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=20,
            pady=8,
            command=self._clear_api_key_fields
        )
        clear_btn.pack(side='left', padx=(10, 0))
        
        # Hover effects for save button
        def on_save_enter(e):
            save_btn.configure(bg='#0080ff')
        def on_save_leave(e):
            save_btn.configure(bg='#0066cc')
        
        save_btn.bind('<Enter>', on_save_enter)
        save_btn.bind('<Leave>', on_save_leave)
        
        # Hover effects for clear button
        def on_clear_enter(e):
            clear_btn.configure(bg='#808080')
        def on_clear_leave(e):
            clear_btn.configure(bg='#666666')
        
        clear_btn.bind('<Enter>', on_clear_enter)
        clear_btn.bind('<Leave>', on_clear_leave)
        
        # Info section
        info_frame = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(10, 0))
        
        info_content = tk.Frame(info_frame, bg='#2d2d2d')
        info_content.pack(fill='x', padx=15, pady=10)
        
        # Info title
        info_title = tk.Label(
            info_content,
            text="🔐 API Key Security",
            bg='#2d2d2d',
            fg='#cccccc',
            font=('Arial', 10, 'bold')
        )
        info_title.pack(anchor='w', pady=(0, 5))
        
        # Info text
        info_text = tk.Label(
            info_content,
            text="• API key is stored securely in your local database\n"
                 "• Anthropic key is required for all code review functionality\n"
                 "• Voice notifications now use local Chatterbox TTS (no API key needed)\n"
                 "• Key is never transmitted except to the Anthropic API",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9),
            wraplength=500,
            justify='left'
        )
        info_text.pack(anchor='w')
        
    def _clear_api_key_fields(self) -> None:
        """Clear the API key input field."""
        self.anthropic_key_var.set("")
    
    def _load_dismissals_from_database(self) -> List[Dismissal]:
        """Load all dismissals from the database."""
        try:
            with get_db() as session:
                stmt = select(Dismissal).order_by(Dismissal.created_at.desc())
                result = session.execute(stmt)
                dismissals = result.scalars().all()
                logger.info(f"Loaded {len(dismissals)} dismissals from database")
                return list(dismissals)
        except Exception as e:
            logger.error(f"Error loading dismissals: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to load dismissals from database:\n{str(e)}")
            return []
    
    def _refresh_dismissals_list(self) -> None:
        """Refresh the dismissals list from the database and update the UI."""
        try:
            self.dismissals = self._load_dismissals_from_database()
            self._populate_dismissals_listbox()
            
            # Show status message
            if self.dismissals:
                messagebox.showinfo("Success", f"Loaded {len(self.dismissals)} dismissals from database")
            else:
                messagebox.showinfo("No Dismissals", 
                    "No dismissed notifications found.\n\n"
                    "To create dismissals:\n"
                    "• Wait for Ducky to show notifications\n"
                    "• Click 'Dismiss' on notifications you don't want\n"
                    "• Ducky will learn your preferences over time")
        except Exception as e:
            logger.error(f"Error refreshing dismissals list: {str(e)}")
            messagebox.showerror("Error", f"Failed to refresh dismissals list: {str(e)}")
    
    def _populate_dismissals_listbox(self) -> None:
        """Populate the dismissals listbox with current dismissals."""
        if not self.dismissals_listbox:
            return
            
        # Clear existing items
        self.dismissals_listbox.delete(0, tk.END)
        
        if not self.dismissals:
            # Keep listbox empty when no dismissals - no hardcoded text
            self.dismissals_listbox.configure(state='disabled')
        else:
            self.dismissals_listbox.configure(state='normal')
            for dismissal in self.dismissals:
                # Create a truncated preview of the notification message
                preview = self._truncate_message(dismissal.notification_message, 80)
                date_str = dismissal.created_at.strftime("%Y-%m-%d %H:%M")
                display_text = f"[{date_str}] {preview}"
                self.dismissals_listbox.insert(tk.END, display_text)
    
    def _truncate_message(self, message: str, max_length: int) -> str:
        """Truncate a message to the specified length with ellipsis."""
        if len(message) <= max_length:
            return message
        return message[:max_length].rsplit(' ', 1)[0] + "..."
    
    def _show_full_dismissal_message(self, index: int) -> None:
        """Show the full dismissal message in a popup dialog."""
        if index < 0 or index >= len(self.dismissals):
            return
            
        dismissal = self.dismissals[index]
        
        # Create popup dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Dismissal Details")
        dialog.geometry("700x600")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() // 2) - (700 // 2)
        y = self.window.winfo_y() + (self.window.winfo_height() // 2) - (600 // 2)
        dialog.geometry(f"700x600+{x}+{y}")
        
        # Configure dark theme
        dialog.configure(bg='#1e1e1e')
        
        # Main frame
        main_frame = tk.Frame(dialog, bg='#1e1e1e')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Dismissal Details",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 14, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Date
        date_label = tk.Label(
            main_frame,
            text=f"Dismissed on: {dismissal.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Arial', 10)
        )
        date_label.pack(anchor='w', pady=(0, 20))
        
        # Notification Message Section
        notification_label = tk.Label(
            main_frame,
            text="Notification Message:",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        notification_label.pack(anchor='w', pady=(0, 5))
        
        # Notification message frame with scrolling
        notification_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='solid', bd=1)
        notification_frame.pack(fill='x', pady=(0, 20))
        
        # Notification text widget with scrollbar
        notification_text = tk.Text(
            notification_frame,
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 10),
            wrap='word',
            padx=15,
            pady=15,
            insertbackground='white',
            height=8
        )
        
        notification_scrollbar = tk.Scrollbar(notification_frame, command=notification_text.yview)
        notification_text.configure(yscrollcommand=notification_scrollbar.set)
        
        # Pack notification text widget and scrollbar
        notification_text.pack(side='left', fill='both', expand=True)
        notification_scrollbar.pack(side='right', fill='y')
        
        # Insert the notification message
        notification_text.insert('1.0', dismissal.notification_message)
        notification_text.configure(state='disabled')  # Make it read-only
        
        # Warning Message Section
        warning_label = tk.Label(
            main_frame,
            text="Warning Message:",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        warning_label.pack(anchor='w', pady=(0, 5))
        
        # Warning message frame with scrolling
        warning_frame = tk.Frame(main_frame, bg='#2d2d2d', relief='solid', bd=1)
        warning_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Warning text widget with scrollbar
        warning_text = tk.Text(
            warning_frame,
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 10),
            wrap='word',
            padx=15,
            pady=15,
            insertbackground='white'
        )
        
        warning_scrollbar = tk.Scrollbar(warning_frame, command=warning_text.yview)
        warning_text.configure(yscrollcommand=warning_scrollbar.set)
        
        # Pack warning text widget and scrollbar
        warning_text.pack(side='left', fill='both', expand=True)
        warning_scrollbar.pack(side='right', fill='y')
        
        # Insert the warning message
        warning_text.insert('1.0', dismissal.warning)
        warning_text.configure(state='disabled')  # Make it read-only
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(fill='x')
        
        # Close button
        close_btn = tk.Button(
            button_frame,
            text="Close",
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        close_btn.pack(side='right')
        
        # Hover effect for close button
        def on_close_enter(e):
            close_btn.configure(bg='#505050')
        def on_close_leave(e):
            close_btn.configure(bg='#404040')
        
        close_btn.bind('<Enter>', on_close_enter)
        close_btn.bind('<Leave>', on_close_leave)
    
    def _delete_dismissal(self, index: int) -> None:
        """Delete a dismissal from the database."""
        if index < 0 or index >= len(self.dismissals):
            return
            
        dismissal = self.dismissals[index]
        
        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete this dismissal?\n\n"
            f"Date: {dismissal.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Message: {self._truncate_message(dismissal.notification_message, 100)}"
        ):
            return
        
        try:
            with get_db() as session:
                # Delete the dismissal
                stmt = delete(Dismissal).where(Dismissal.id == dismissal.id)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Successfully deleted dismissal {dismissal.id}")
                    messagebox.showinfo("Success", "Dismissal deleted successfully!")
                    # Refresh the list
                    self._refresh_dismissals_list()
                else:
                    logger.warning(f"No dismissal found with ID {dismissal.id}")
                    messagebox.showwarning("Warning", "Dismissal not found in database")
                    
        except Exception as e:
            logger.error(f"Error deleting dismissal: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete dismissal: {str(e)}")
    
    def _on_dismissal_double_click(self, event) -> None:
        """Handle double-click on dismissal item to show full message."""
        if not self.dismissals_listbox or not self.dismissals:
            return
            
        selection = self.dismissals_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.dismissals):  # Make sure it's not the "No dismissals" message
                self._show_full_dismissal_message(index)
    
    def _on_dismissal_right_click(self, event) -> None:
        """Handle right-click on dismissal item to show context menu."""
        if not self.dismissals_listbox or not self.dismissals:
            return
            
        # Select the item under cursor
        index = self.dismissals_listbox.nearest(event.y)
        if index < len(self.dismissals):
            self.dismissals_listbox.selection_clear(0, tk.END)
            self.dismissals_listbox.selection_set(index)
            
            # Create context menu
            context_menu = tk.Menu(self.dismissals_listbox, tearoff=0)
            context_menu.configure(bg='#2c2c2c', fg='white', activebackground='#404040')
            
            context_menu.add_command(
                label="View Full Message",
                command=lambda: self._show_full_dismissal_message(index)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="Delete",
                command=lambda: self._delete_dismissal(index)
            )
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def _create_dismissals_section(self, parent: tk.Frame) -> None:
        """Create the previous dismissals management section."""
        # Section title
        title_label = tk.Label(
            parent,
            text="Previous Dismissals",
            bg='#1e1e1e',
            fg='white',
            font=('Arial', 12, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = tk.Label(
            parent,
            text="View and manage previously dismissed notifications. These dismissals help Ducky learn your preferences:",
            bg='#1e1e1e',
            fg='#cccccc',
            font=('Arial', 10),
            wraplength=500,
            justify='left'
        )
        desc_label.pack(anchor='w', pady=(0, 15))
        
        # Control buttons frame
        control_frame = tk.Frame(parent, bg='#1e1e1e')
        control_frame.pack(fill='x', pady=(0, 15))
        
        # Load dismissals button
        load_btn = tk.Button(
            control_frame,
            text="📋 Load Dismissals",
            bg='#0066cc',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief='flat',
            padx=15,
            pady=8,
            command=self._refresh_dismissals_list
        )
        load_btn.pack(side='left')
        
        # Refresh button
        refresh_btn = tk.Button(
            control_frame,
            text="🔄 Refresh",
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            relief='flat',
            padx=15,
            pady=8,
            command=self._refresh_dismissals_list
        )
        refresh_btn.pack(side='left', padx=(10, 0))
        
        # Hover effects
        def on_load_enter(e):
            load_btn.configure(bg='#0080ff')
        def on_load_leave(e):
            load_btn.configure(bg='#0066cc')
        
        def on_refresh_enter(e):
            refresh_btn.configure(bg='#505050')
        def on_refresh_leave(e):
            refresh_btn.configure(bg='#404040')
        
        load_btn.bind('<Enter>', on_load_enter)
        load_btn.bind('<Leave>', on_load_leave)
        refresh_btn.bind('<Enter>', on_refresh_enter)
        refresh_btn.bind('<Leave>', on_refresh_leave)
        
        # Dismissals list container
        list_container = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        list_container.pack(fill='x', pady=(0, 15))
        
        # List header
        header_frame = tk.Frame(list_container, bg='#2d2d2d')
        header_frame.pack(fill='x', padx=15, pady=(10, 5))
        
        header_label = tk.Label(
            header_frame,
            text="Dismissed Notifications",
            bg='#2d2d2d',
            fg='white',
            font=('Arial', 11, 'bold')
        )
        header_label.pack(anchor='w')
        
        instructions_label = tk.Label(
            header_frame,
            text="Double-click to view full message • Right-click for options",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9)
        )
        instructions_label.pack(anchor='w', pady=(2, 0))
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_container, bg='#2d2d2d')
        listbox_frame.pack(fill='x', padx=15, pady=(0, 15))
        
        # Create the listbox
        self.dismissals_listbox = tk.Listbox(
            listbox_frame,
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            selectbackground='#0066cc',
            selectforeground='white',
            relief='flat',
            height=8,
            borderwidth=0
        )
        
        # Create scrollbar for listbox
        listbox_scrollbar = tk.Scrollbar(
            listbox_frame,
            orient='vertical',
            command=self.dismissals_listbox.yview,
            bg='#404040',
            troughcolor='#2d2d2d',
            activebackground='#606060'
        )
        
        # Configure listbox scrolling
        self.dismissals_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        
        # Pack listbox and scrollbar
        self.dismissals_listbox.pack(side='left', fill='both', expand=True)
        listbox_scrollbar.pack(side='right', fill='y')
        
        # Bind events
        self.dismissals_listbox.bind('<Double-Button-1>', self._on_dismissal_double_click)
        self.dismissals_listbox.bind('<Button-3>', self._on_dismissal_right_click)  # Right-click
        
        # Initially empty - no hardcoded text
        self.dismissals_listbox.configure(state='disabled')
        
        # Info section
        info_frame = tk.Frame(parent, bg='#2d2d2d', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(10, 0))
        
        info_content = tk.Frame(info_frame, bg='#2d2d2d')
        info_content.pack(fill='x', padx=15, pady=10)
        
        # Info title
        info_title = tk.Label(
            info_content,
            text="💡 About Dismissals",
            bg='#2d2d2d',
            fg='#cccccc',
            font=('Arial', 10, 'bold')
        )
        info_title.pack(anchor='w', pady=(0, 5))
        
        # Info text
        info_text = tk.Label(
            info_content,
            text="• Dismissals are stored to help Ducky learn your notification preferences\n"
                 "• When you dismiss similar notifications, Ducky may stop showing them\n"
                 "• You can delete dismissals to reset Ducky's learning for those types of notifications\n"
                 "• Deleting a dismissal means Ducky will notify you about similar issues again",
            bg='#2d2d2d',
            fg='#888888',
            font=('Arial', 9),
            wraplength=500,
            justify='left'
        )
        info_text.pack(anchor='w') 