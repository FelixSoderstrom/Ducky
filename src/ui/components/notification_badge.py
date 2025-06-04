"""Notification badge component for the Ducky UI."""

import tkinter as tk
import logging
import uuid
from datetime import datetime
from typing import Dict, Callable, Optional

logger = logging.getLogger("ducky.ui.notification_badge")


class NotificationBadge:
    """Manages the notification badge that appears when there are unhandled notifications."""
    
    def __init__(self, parent_container: tk.Widget):
        self.parent_container = parent_container
        self.badge: Optional[tk.Label] = None
        self.unhandled_notifications: Dict[str, Dict] = {}
        self.click_callback: Optional[Callable] = None
        self.notification_dialog = None  # Track the current notification dialog
        self.dialog_open = False  # Track if dialog is currently open
        
        # Create the badge widget
        self._create_badge()
        
    def _create_badge(self) -> None:
        """Create the notification badge widget."""
        self.badge = tk.Label(
            self.parent_container,
            text="!",
            bg='#f0f0f0',  # Light gray background to avoid transparency
            fg='red',
            font=('Arial', 12, 'bold'),
            relief='solid',
            borderwidth=2,
            cursor='hand2',
            width=2,  # Fixed width for circular shape
            height=1,  # Fixed height for circular shape
            justify='center'
        )
        
        # Initially hidden
        self.badge.place_forget()
        
        # Bind click event
        self.badge.bind('<Button-1>', self._on_badge_click)
        
        logger.debug("Notification badge created")
    
    def set_click_callback(self, callback: Callable) -> None:
        """Set callback function to be called when badge is clicked.
        
        Args:
            callback: Function to call when badge is clicked
        """
        self.click_callback = callback
    
    def update_position_and_size(self, container_width: int, container_height: int) -> None:
        """Update the badge position and size based on container dimensions.
        
        Args:
            container_width: Width of the parent container
            container_height: Height of the parent container
        """
        if not self.badge:
            return
            
        # Calculate badge size based on container size (dynamic)
        badge_size = max(16, min(24, container_width // 6))
        
        # Update font size for circular appearance
        font_size = max(8, badge_size - 4)
        self.badge.configure(font=('Arial', font_size, 'bold'))
        
        # Position badge in top-right corner of the container
        badge_offset = max(4, container_width // 20)
        circle_size = badge_size + 2  # Slightly larger for better circle appearance
        
        self.badge.place(
            x=container_width - badge_offset - circle_size,
            y=badge_offset,
            width=circle_size,
            height=circle_size
        )
        
        logger.debug(f"Badge positioned at x={container_width - badge_offset - circle_size}, y={badge_offset}")
    
    def add_notification(self, text: str) -> str:
        """Add a notification to the unhandled notifications tracker.
        
        Args:
            text: The notification text
            
        Returns:
            str: The unique notification ID
        """
        notification_id = str(uuid.uuid4())
        self.unhandled_notifications[notification_id] = {
            'text': text,
            'timestamp': datetime.now(),
            'id': notification_id,
            'first_time': True,  # Track if this is the first time seeing this notification
            'dismissed': False
        }
        
        logger.info(f"Added unhandled notification: {notification_id}")
        self._update_visibility()
        return notification_id
    
    def mark_notification_as_seen(self, notification_id: str) -> None:
        """Mark a notification as seen (no longer first time).
        
        Args:
            notification_id: The unique notification ID to mark as seen
        """
        if notification_id in self.unhandled_notifications:
            self.unhandled_notifications[notification_id]['first_time'] = False
            logger.info(f"Marked notification as seen: {notification_id}")
    
    def get_notification_by_id(self, notification_id: str) -> Optional[Dict]:
        """Get notification data by ID.
        
        Args:
            notification_id: The unique notification ID
            
        Returns:
            Optional[Dict]: The notification data if found, None otherwise
        """
        return self.unhandled_notifications.get(notification_id)
    
    def remove_notification(self, notification_id: str) -> None:
        """Remove a notification from the unhandled notifications tracker.
        
        Args:
            notification_id: The unique notification ID to remove
        """
        if notification_id in self.unhandled_notifications:
            del self.unhandled_notifications[notification_id]
            logger.info(f"Removed unhandled notification: {notification_id}")
            self._update_visibility()
        else:
            logger.warning(f"Attempted to remove non-existent notification: {notification_id}")
    
    def get_notification_count(self) -> int:
        """Get the number of unhandled notifications.
        
        Returns:
            int: Number of unhandled notifications
        """
        return len(self.unhandled_notifications)
    
    def get_all_notifications(self) -> Dict[str, Dict]:
        """Get all unhandled notifications.
        
        Returns:
            Dict[str, Dict]: Dictionary of all unhandled notifications
        """
        return self.unhandled_notifications.copy()
    
    def clear_all_notifications(self) -> None:
        """Clear all unhandled notifications."""
        count = len(self.unhandled_notifications)
        self.unhandled_notifications.clear()
        self._update_visibility()
        logger.info(f"Cleared {count} notifications")
    
    def _update_visibility(self) -> None:
        """Update the visibility of the notification badge based on unhandled notifications."""
        if not self.badge:
            return
            
        notification_count = len(self.unhandled_notifications)
        
        if notification_count > 0:
            # Badge should be visible - force visibility update
            logger.debug(f"Showing badge ({notification_count} unhandled)")
            self._show_badge()
        else:
            # Hide badge and close any open dialog
            self.badge.place_forget()
            if self.dialog_open and self.notification_dialog:
                self._close_notification_dialog()
            logger.debug("Badge hidden (no unhandled notifications)")
    
    def _show_badge(self) -> None:
        """Force the badge to be visible by calling update_position_and_size if container dimensions are available."""
        if not self.badge or not self.parent_container:
            return
            
        try:
            # Get current container dimensions
            self.parent_container.update_idletasks()
            container_width = self.parent_container.winfo_width()
            container_height = self.parent_container.winfo_height()
            
            # Only show if we have valid dimensions AND there are actually notifications
            if container_width > 1 and container_height > 1 and len(self.unhandled_notifications) > 0:
                self.update_position_and_size(container_width, container_height)
                logger.debug(f"Badge forced visible at container size {container_width}x{container_height}")
            else:
                if len(self.unhandled_notifications) == 0:
                    logger.debug("No notifications to show, keeping badge hidden")
                else:
                    logger.debug("Container dimensions not ready, badge will show when positioned")
                
        except Exception as e:
            logger.error(f"Failed to show badge: {str(e)}")
    
    def force_visibility_update(self) -> None:
        """Force an update of badge visibility - useful when called from external components."""
        self._update_visibility()
    
    def _on_badge_click(self, event) -> None:
        """Handle notification badge click with toggle behavior.
        
        Args:
            event: The click event
        """
        logger.info("Notification badge clicked")
        
        # Toggle dialog behavior
        if self.dialog_open and self.notification_dialog:
            # Close existing dialog
            self._close_notification_dialog()
        else:
            # Open new dialog
            self._open_notification_dialog()
    
    def _open_notification_dialog(self) -> None:
        """Open the notification list dialog."""
        if self.dialog_open:
            logger.debug("Dialog already open, ignoring open request")
            return
            
        if self.click_callback:
            try:
                # The callback should return the dialog instance
                from ..components.notification_list import NotificationListDialog
                
                # Get the UI app from the callback context
                # We need to pass self to the callback so it can manage the dialog state
                self.notification_dialog = self.click_callback(event=None, badge=self)
                
                if self.notification_dialog:
                    self.dialog_open = True
                    logger.info("Notification dialog opened")
                else:
                    logger.warning("Failed to create notification dialog")
                    
            except Exception as e:
                logger.error(f"Error opening notification dialog: {str(e)}")
    
    def _close_notification_dialog(self) -> None:
        """Close the notification list dialog."""
        if self.notification_dialog:
            try:
                self.notification_dialog.hide()
                self.notification_dialog = None
                self.dialog_open = False
                logger.info("Notification dialog closed")
            except Exception as e:
                logger.error(f"Error closing notification dialog: {str(e)}")
    
    def on_dialog_closed(self) -> None:
        """Called when the dialog is closed externally (e.g., close button)."""
        self.notification_dialog = None
        self.dialog_open = False
        logger.debug("Dialog state reset after external close")
    
    def is_visible(self) -> bool:
        """Check if the badge is currently visible.
        
        Returns:
            bool: True if badge is visible
        """
        if not self.badge:
            return False
        return self.badge.winfo_viewable()
    
    def destroy(self) -> None:
        """Clean up the notification badge."""
        if self.badge:
            try:
                self.badge.destroy()
                self.badge = None
                logger.debug("Notification badge destroyed")
            except Exception as e:
                logger.error(f"Error destroying notification badge: {str(e)}")
        
        # Clear notifications
        self.unhandled_notifications.clear() 