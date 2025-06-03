"""Main UI orchestration for the Ducky application."""

import asyncio
import logging
import sys
import tkinter as tk
from typing import Optional

from .dialogs import APIKeyDialog
from .components import NotificationListDialog, SettingsWindow, NotificationBadge, MainUILayout
from .utils.image_manager import ImageManager
from .utils.window_manager import WindowManager
from .utils.context_menu_manager import ContextMenuManager

# Create logger for this module
logger = logging.getLogger("ducky.ui")


class DuckyUI:
    """Main UI coordinator that orchestrates all UI components and managers."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Ducky")
        
        # Initialize API key
        self.api_key: Optional[str] = None
        
        # Initialize current project path
        self.current_project_path: Optional[str] = None
        
        # Initialize settings window
        self.settings_window: Optional[SettingsWindow] = None
        
        # Set constants
        self.MIN_WIDTH = 80
        self.MIN_HEIGHT = 80
        self.top_bar_height = 20
        
        # Set initial size
        self.width = max(100, self.MIN_WIDTH)
        self.height = max(100, self.MIN_HEIGHT)
        
        # For asyncio integration
        self.running = True
        
        # Initialize managers and components
        self._initialize_managers()
        self._setup_ui()
        self._bind_events()
        
        logger.info("DuckyUI initialized successfully")
    
    def _initialize_managers(self) -> None:
        """Initialize all the UI managers."""
        # Image manager
        self.image_manager = ImageManager()
        self.image_manager.load_image()
        
        # Window manager
        self.window_manager = WindowManager(self.root, self.MIN_WIDTH, self.MIN_HEIGHT)
        self.window_manager.set_size_change_callback(self._on_size_change)
        self.window_manager.setup_window_properties(self.width, self.height, self.top_bar_height)
        
        # Context menu manager
        self.context_menu_manager = ContextMenuManager(self.root)
        self.context_menu_manager.setup_context_menu(self._open_settings)
        
        logger.debug("UI managers initialized")
    
    def _setup_ui(self) -> None:
        """Set up the UI layout and components."""
        # Main layout
        self.layout = MainUILayout(self.root, self.top_bar_height)
        self.layout.create_layout(self.width, self.height)
        self.layout.set_close_callback(self.close_app)
        
        # Notification badge
        image_container = self.layout.get_image_container()
        if image_container:
            self.notification_badge = NotificationBadge(image_container)
            self.notification_badge.set_click_callback(self._on_badge_click)
        
        # Update image display
        self._update_image_display()
        
        logger.debug("UI setup completed")
    
    def _bind_events(self) -> None:
        """Bind events for window management and context menu."""
        # Bind drag events to appropriate widgets
        drag_widgets = self.layout.get_drag_widgets()
        self.window_manager.bind_drag_events(drag_widgets)
        
        # Bind resize events to resize handle
        resize_handle = self.layout.get_resize_handle()
        if resize_handle:
            self.window_manager.bind_resize_events(resize_handle)
        
        # Bind context menu to image label
        image_label = self.layout.get_image_label()
        if image_label:
            self.context_menu_manager.bind_context_menu(image_label)
        
        logger.debug("Event binding completed")
    
    def _on_size_change(self, width: int, height: int) -> None:
        """Handle size changes from the window manager.
        
        Args:
            width: New width
            height: New height
        """
        self.width = width
        self.height = height
        
        # Update layout
        self.layout.update_size(width, height)
        
        # Update image
        self._update_image_display()
        
        # Update notification badge position
        if hasattr(self, 'notification_badge'):
            self.notification_badge.update_position_and_size(width, height)
        
        logger.debug(f"Size changed to {width}x{height}")
    
    def _update_image_display(self) -> None:
        """Update the image display with current size."""
        image = self.image_manager.update_image_size(self.width, self.height)
        self.layout.update_image(image)
    
    def _on_badge_click(self, event) -> None:
        """Handle notification badge click to show notification list."""
        logger.info("Notification badge clicked - showing notification list")
        try:
            dialog = NotificationListDialog(self)
            dialog.show()
        except Exception as e:
            logger.error(f"Failed to show notification list: {str(e)}")
    
    def _open_settings(self) -> None:
        """Open the settings window."""
        logger.info("Opening settings window from context menu")
        try:
            if not self.current_project_path:
                logger.error("No current project path available for settings")
                # Show an error message to the user
                import tkinter.messagebox as messagebox
                messagebox.showerror("Error", "No project path available. Please restart the application.")
                return
                
            logger.info(f"Using project path: {self.current_project_path}")
            
            if self.settings_window is None:
                self.settings_window = SettingsWindow(self, self.current_project_path)
            self.settings_window.show()
        except Exception as e:
            logger.error(f"Failed to open settings window: {str(e)}")
    
    # Public API methods (maintaining compatibility with ApplicationOrchestrator)
    
    def close_app(self) -> None:
        """Close the application and exit the program."""
        logger.info("Closing Ducky application")
        self.running = False
        
        # Clean up components
        if hasattr(self, 'notification_badge'):
            self.notification_badge.destroy()
        if hasattr(self, 'layout'):
            self.layout.destroy()
        if hasattr(self, 'context_menu_manager'):
            self.context_menu_manager.destroy()
        
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    async def update(self) -> None:
        """Update the UI asynchronously."""
        try:
            while self.running:
                self.root.update()
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
        except tk.TclError:  # Handle case when window is closed directly
            sys.exit(0)
    
    async def get_api_key(self) -> Optional[str]:
        """Show API key dialog and return the entered key.
        
        Returns:
            Optional[str]: The API key if provided, None if cancelled.
        """
        dialog = APIKeyDialog(self.root)
        self.api_key = dialog.api_key
        return self.api_key
    
    def set_current_project_path(self, project_path: str) -> None:
        """Set the current project path for use in settings."""
        self.current_project_path = project_path
        logger.info(f"Current project path set to: {project_path}")
    
    # Notification management methods (maintaining compatibility)
    
    def add_unhandled_notification(self, text: str) -> str:
        """Add a notification to the unhandled notifications tracker.
        
        Args:
            text: The notification text
            
        Returns:
            str: The unique notification ID
        """
        if hasattr(self, 'notification_badge'):
            return self.notification_badge.add_notification(text)
        else:
            logger.warning("Notification badge not initialized")
            return ""
    
    def mark_notification_as_seen(self, notification_id: str) -> None:
        """Mark a notification as seen (no longer first time).
        
        Args:
            notification_id: The unique notification ID to mark as seen
        """
        if hasattr(self, 'notification_badge'):
            self.notification_badge.mark_notification_as_seen(notification_id)
    
    def get_notification_by_id(self, notification_id: str) -> Optional[dict]:
        """Get notification data by ID.
        
        Args:
            notification_id: The unique notification ID
            
        Returns:
            Optional[dict]: The notification data if found, None otherwise
        """
        if hasattr(self, 'notification_badge'):
            return self.notification_badge.get_notification_by_id(notification_id)
        return None
    
    def remove_unhandled_notification(self, notification_id: str) -> None:
        """Remove a notification from the unhandled notifications tracker.
        
        Args:
            notification_id: The unique notification ID to remove
        """
        if hasattr(self, 'notification_badge'):
            self.notification_badge.remove_notification(notification_id)
    
    @property
    def unhandled_notifications(self) -> dict:
        """Get all unhandled notifications (for compatibility).
        
        Returns:
            dict: Dictionary of all unhandled notifications
        """
        if hasattr(self, 'notification_badge'):
            return self.notification_badge.get_all_notifications()
        return {}


async def start_ui() -> DuckyUI:
    """Start the Ducky UI application asynchronously.
    
    Returns:
        DuckyUI: The initialized UI instance.
    """
    app = DuckyUI()
    return app
