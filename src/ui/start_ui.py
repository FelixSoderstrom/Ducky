"""Main UI orchestration for the Ducky application."""

import asyncio
import logging
import sys
import tkinter as tk
from typing import Optional
import os

from .dialogs import APIKeyDialog
from .components import NotificationListDialog, SettingsWindow, NotificationBadge, MainUILayout
from .utils.image_manager import ImageManager
from .utils.window_manager import WindowManager
from .utils.context_menu_manager import ContextMenuManager
from .utils.animation_manager import PipelineAnimationManager
from ..events import get_pipeline_event_emitter, PipelineEventType, PipelineEvent
from ..config.app_config import AppConfig

# Create logger for this module
logger = logging.getLogger("ducky.ui")


class DuckyUI:
    """Main UI coordinator that orchestrates all UI components and managers."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.root = tk.Tk()
        self.root.title("Ducky")
        
        # Store configuration
        self.config = config or AppConfig.default()
        
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
        self._setup_pipeline_events()
        
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
        
        # Animation manager (if enabled)
        if self.config.enable_pipeline_animation:
            self.animation_manager = PipelineAnimationManager(
                cycle_interval=self.config.animation_cycle_interval
            )
            self.animation_manager.set_image_change_callback(self.change_background_image)
            logger.debug("Pipeline animation manager initialized")
        else:
            self.animation_manager = None
            logger.debug("Pipeline animation disabled by configuration")
        
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
            # Don't position badge initially - it will show when notifications are added
            # The badge starts hidden and only shows when there are actual notifications
            logger.debug("Notification badge created and hidden initially")
        
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
    
    def _setup_pipeline_events(self) -> None:
        """Set up pipeline event listeners for animation control."""
        if not self.animation_manager:
            logger.debug("Skipping pipeline event setup - animation disabled")
            return
        
        event_emitter = get_pipeline_event_emitter()
        
        # Register async event listeners for pipeline lifecycle
        event_emitter.on_async(PipelineEventType.PIPELINE_STARTED, self._on_pipeline_started)
        event_emitter.on_async(PipelineEventType.PIPELINE_COMPLETED, self._on_pipeline_completed)
        event_emitter.on_async(PipelineEventType.PIPELINE_FAILED, self._on_pipeline_failed)
        event_emitter.on_async(PipelineEventType.PIPELINE_CANCELLED, self._on_pipeline_cancelled)
        
        logger.debug("Pipeline event listeners registered")
    
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
    
    # Pipeline event handlers
    
    async def _on_pipeline_started(self, event: PipelineEvent) -> None:
        """Handle pipeline started event.
        
        Args:
            event: The pipeline event
        """
        if self.animation_manager:
            started = self.animation_manager.start_pipeline_animation(event.project_id)
            if started:
                logger.info(f"Started pipeline animation for project {event.project_id}")
            else:
                logger.debug(f"Pipeline animation already running for project {event.project_id}")
    
    async def _on_pipeline_completed(self, event: PipelineEvent) -> None:
        """Handle pipeline completed event.
        
        Args:
            event: The pipeline event
        """
        if self.animation_manager:
            stopped = self.animation_manager.stop_pipeline_animation(event.project_id)
            if stopped:
                logger.info(f"Stopped pipeline animation for project {event.project_id}")
            else:
                logger.debug(f"Pipeline animation continues for other projects")
    
    async def _on_pipeline_failed(self, event: PipelineEvent) -> None:
        """Handle pipeline failed event.
        
        Args:
            event: The pipeline event
        """
        if self.animation_manager:
            stopped = self.animation_manager.stop_pipeline_animation(event.project_id)
            if stopped:
                logger.info(f"Stopped pipeline animation for failed project {event.project_id}")
            else:
                logger.debug(f"Pipeline animation continues for other projects")
    
    async def _on_pipeline_cancelled(self, event: PipelineEvent) -> None:
        """Handle pipeline cancelled event.
        
        Args:
            event: The pipeline event
        """
        if self.animation_manager:
            stopped = self.animation_manager.stop_pipeline_animation(event.project_id)
            if stopped:
                logger.info(f"Stopped pipeline animation for cancelled project {event.project_id}")
            else:
                logger.debug(f"Pipeline animation continues for other projects")
    
    def _update_image_display(self) -> None:
        """Update the image display with current size."""
        image = self.image_manager.update_image_size(self.width, self.height)
        self.layout.update_image(image)
    
    def _on_badge_click(self, event, badge=None) -> Optional['NotificationListDialog']:
        """Handle notification badge click to show notification list.
        
        Args:
            event: The click event (can be None)
            badge: The notification badge instance
            
        Returns:
            NotificationListDialog: The created dialog instance
        """
        logger.info("Notification badge clicked - showing notification list")
        try:
            dialog = NotificationListDialog(self)
            
            # Set up dialog close callback to notify the badge
            if badge:
                def on_dialog_close():
                    badge.on_dialog_closed()
                # We'll need to add this to the dialog
                dialog.set_close_callback(on_dialog_close)
            
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"Failed to show notification list: {str(e)}")
            return None
    
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
        if hasattr(self, 'animation_manager') and self.animation_manager:
            self.animation_manager.force_stop()
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
    
    def add_unhandled_notification(self, text: str, pipeline_data: dict = None) -> str:
        """Add a notification to the unhandled notifications tracker.
        
        Args:
            text: The notification text
            pipeline_data: Optional pipeline data containing context for dismissals
            
        Returns:
            str: The unique notification ID
        """
        if hasattr(self, 'notification_badge'):
            notification_id = self.notification_badge.add_notification(text, pipeline_data)
            # Force badge visibility update and positioning
            self.root.update_idletasks()
            self.notification_badge.update_position_and_size(self.width, self.height)
            return notification_id
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
        """Remove a notification from unhandled notifications.
        
        Args:
            notification_id: ID of the notification to remove
        """
        if hasattr(self, 'notification_badge'):
            self.notification_badge.remove_notification(notification_id)
            logger.debug(f"Removed notification {notification_id}")
    
    def change_background_image(self, filename: str) -> bool:
        """Change the background image to a different image in the assets directory.
        
        Args:
            filename: Name of the image file in the assets directory (e.g., 'thinking.png', 'talking.png')
            
        Returns:
            bool: True if the image was successfully changed, False otherwise
        """
        try:
            logger.debug(f"Changing background image to: {filename}")
            
            # Load the new image using the image manager
            self.image_manager.load_image(filename)
            
            # Check if the image was loaded successfully
            if not self.image_manager.is_image_loaded():
                logger.error(f"Failed to load image: {filename}")
                return False
            
            # Update the display with the new image
            self._update_image_display()
            
            logger.debug(f"Successfully changed background image to: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing background image to {filename}: {str(e)}")
            return False

    def get_available_background_images(self) -> list:
        """Get a list of available background images in the assets directory.
        
        Returns:
            list: List of image filenames available for background change
        """
        try:
            # Get the assets directory path (same logic as ImageManager)
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            assets_dir = os.path.join(current_dir, "assets")
            
            # Get all PNG files in the assets directory
            if os.path.exists(assets_dir):
                image_files = [f for f in os.listdir(assets_dir) 
                              if f.lower().endswith('.png') and os.path.isfile(os.path.join(assets_dir, f))]
                image_files.sort()  # Sort alphabetically for consistency
                logger.debug(f"Found {len(image_files)} background images: {image_files}")
                return image_files
            else:
                logger.warning(f"Assets directory not found: {assets_dir}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting available background images: {str(e)}")
            return []

    @property
    def unhandled_notifications(self) -> dict:
        """Get all unhandled notifications (for compatibility).
        
        Returns:
            dict: Dictionary of all unhandled notifications
        """
        if hasattr(self, 'notification_badge'):
            return self.notification_badge.get_all_notifications()
        return {}


async def start_ui(config: Optional[AppConfig] = None) -> DuckyUI:
    """Start the Ducky UI application asynchronously.
    
    Args:
        config: Optional application configuration
    
    Returns:
        DuckyUI: The initialized UI instance.
    """
    app = DuckyUI(config)
    return app
