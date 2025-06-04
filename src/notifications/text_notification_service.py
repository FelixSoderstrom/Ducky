"""Text notification service for coordinating notification display and tracking."""

import logging
import asyncio
from typing import Optional

from ..ui.components.text_overlay import TextOverlay

logger = logging.getLogger("ducky.notifications.text_notification_service")


class TextNotificationService:
    """Service for coordinating text notification display and tracking."""
    
    def __init__(self, ui_app):
        """
        Initialize the text notification service.
        
        Args:
            ui_app: The DuckyUI application instance
        """
        self.ui_app = ui_app
    
    async def display_text_overlay(self, text: str) -> None:
        """
        Display text notification as an overlay on the UI.
        
        Args:
            text: The notification text to display
        """
        try:
            logger.info(f"Displaying text overlay: {text[:50]}...")
            
            # Add notification to tracking system and get ID
            notification_id = self.ui_app.add_unhandled_notification(text)
            
            # Create callbacks for notification lifecycle
            def on_dismiss():
                logger.info("Dismiss button clicked - removing from unhandled notifications")
                self.ui_app.remove_unhandled_notification(notification_id)
            
            def on_expand():
                logger.info("Expand button clicked - removing from unhandled notifications")
                self.ui_app.remove_unhandled_notification(notification_id)
                logger.info("Expand functionality not implemented yet - notification marked as handled")
                # TODO: Implement expand functionality
            
            # Create and show overlay
            overlay = TextOverlay(
                parent_root=self.ui_app.root,
                text=text,
                on_dismiss_callback=on_dismiss,
                on_expand_callback=on_expand
            )
            overlay.show()
            
            # Mark as seen after initial display (no longer first time)
            self.ui_app.mark_notification_as_seen(notification_id)
            
            # Auto-hide after 15 seconds
            await asyncio.sleep(15)
            
            # If overlay still exists (wasn't manually dismissed), hide it and mark as unhandled
            if overlay.is_visible():
                overlay.hide()
                logger.info(f"Text notification timed out - notification {notification_id} remains unhandled")
            
        except Exception as e:
            logger.error(f"Failed to display text overlay: {str(e)}")
    
    def show_sticky_text_overlay(self, text: str, notification_id: str) -> None:
        """
        Display a sticky text notification that doesn't auto-hide.
        Used when showing notifications from the notification list.
        
        Args:
            text: The notification text to display
            notification_id: The notification ID
        """
        try:
            logger.info(f"Displaying sticky text overlay: {text[:50]}...")
            
            # Create callbacks for notification lifecycle
            def on_dismiss():
                logger.info("Sticky notification dismissed - removing from unhandled notifications")
                self.ui_app.remove_unhandled_notification(notification_id)
            
            def on_expand():
                logger.info("Sticky notification expanded - removing from unhandled notifications")
                self.ui_app.remove_unhandled_notification(notification_id)
                logger.info("Expand functionality not implemented yet - notification marked as handled")
                # TODO: Implement expand functionality
            
            # Create and show overlay (sticky - no auto-hide)
            overlay = TextOverlay(
                parent_root=self.ui_app.root,
                text=text,
                on_dismiss_callback=on_dismiss,
                on_expand_callback=on_expand
            )
            overlay.show()
            
            logger.info("Sticky text notification displayed - will remain until manually dismissed")
            
        except Exception as e:
            logger.error(f"Failed to display sticky text overlay: {str(e)}")


# Module-level functions for backward compatibility
async def display_text_overlay(text: str, ui_app) -> None:
    """
    Display text notification as an overlay on the UI.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
    """
    service = TextNotificationService(ui_app)
    await service.display_text_overlay(text)


def show_sticky_text_overlay(text: str, ui_app, notification_id: str) -> None:
    """
    Display a sticky text notification that doesn't auto-hide.
    Used when showing notifications from the notification list.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
        notification_id: The notification ID
    """
    service = TextNotificationService(ui_app)
    service.show_sticky_text_overlay(text, notification_id) 