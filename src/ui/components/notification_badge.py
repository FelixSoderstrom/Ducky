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
            
        if len(self.unhandled_notifications) > 0:
            # Badge should be visible, but only actually show if positioned
            # The badge will be shown when update_position_and_size is called
            logger.debug(f"Badge should be visible ({len(self.unhandled_notifications)} unhandled)")
        else:
            # Hide badge
            self.badge.place_forget()
            logger.debug("Badge hidden (no unhandled notifications)")
    
    def _on_badge_click(self, event) -> None:
        """Handle notification badge click.
        
        Args:
            event: The click event
        """
        logger.info("Notification badge clicked")
        if self.click_callback:
            try:
                self.click_callback(event)
            except Exception as e:
                logger.error(f"Error in badge click callback: {str(e)}")
    
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