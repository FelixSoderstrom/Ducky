"""Text notification service for coordinating notification display and tracking."""

import logging
import asyncio
from typing import Optional

from ..ui.components.text_overlay import TextOverlay
from ..database.operations.post_dismissal import post_dismissal_from_pipeline_data
from ..services.chat_service import ChatService

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
    
    async def display_text_overlay(self, text: str, notification_id: str = None) -> None:
        """
        Display text notification as an overlay on the UI.
        
        Args:
            text: The notification text to display
            notification_id: Optional pre-existing notification ID from unified pipeline
        """
        try:
            logger.info(f"Displaying text overlay: {text[:50]}...")
            
            # Use provided notification_id or create new one (for backward compatibility)
            if notification_id is None:
                notification_id = self.ui_app.add_unhandled_notification(text)
                logger.info(f"Created new notification ID: {notification_id}")
            else:
                logger.info(f"Using provided notification ID: {notification_id}")
            
            # Create callbacks for notification lifecycle
            def on_dismiss():
                logger.info("Dismiss button clicked - removing from unhandled notifications")
                
                # Get pipeline data for dismissal before removing notification
                notification_data = self.ui_app.get_notification_by_id(notification_id)
                if notification_data and notification_data.get('pipeline_data'):
                    logger.info("Saving dismissal to database")
                    success = post_dismissal_from_pipeline_data(notification_data['pipeline_data'])
                    if success:
                        logger.info("Dismissal saved successfully")
                    else:
                        logger.error("Failed to save dismissal to database")
                else:
                    logger.warning("No pipeline data found for notification - dismissal not saved")
                
                self.ui_app.remove_unhandled_notification(notification_id)
            
            def on_expand():
                logger.info("Expand button clicked - starting chat session")
                notification_data = self.ui_app.get_notification_by_id(notification_id)
                if notification_data and notification_data.get('pipeline_data'):
                    # Initialize chat service and start chat
                    chat_service = ChatService(self.ui_app)
                    asyncio.create_task(chat_service.start_chat(
                        notification_data['pipeline_data'], 
                        notification_id
                    ))
                    logger.info("Chat session initiated")
                else:
                    logger.error("No pipeline data available for chat - cannot start chat")
                    # Remove notification anyway since user tried to expand
                    self.ui_app.remove_unhandled_notification(notification_id)
            
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
                
                # Get pipeline data for dismissal before removing notification
                notification_data = self.ui_app.get_notification_by_id(notification_id)
                if notification_data and notification_data.get('pipeline_data'):
                    logger.info("Saving dismissal to database")
                    success = post_dismissal_from_pipeline_data(notification_data['pipeline_data'])
                    if success:
                        logger.info("Dismissal saved successfully")
                    else:
                        logger.error("Failed to save dismissal to database")
                else:
                    logger.warning("No pipeline data found for notification - dismissal not saved")
                
                self.ui_app.remove_unhandled_notification(notification_id)
            
            def on_expand():
                logger.info("Sticky notification expanded - starting chat session")
                notification_data = self.ui_app.get_notification_by_id(notification_id)
                if notification_data and notification_data.get('pipeline_data'):
                    # Initialize chat service and start chat
                    chat_service = ChatService(self.ui_app)
                    asyncio.create_task(chat_service.start_chat(
                        notification_data['pipeline_data'], 
                        notification_id
                    ))
                    logger.info("Chat session initiated")
                else:
                    logger.error("No pipeline data available for chat - cannot start chat")
                    # Remove notification anyway since user tried to expand
                    self.ui_app.remove_unhandled_notification(notification_id)
            
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
async def display_text_overlay(text: str, ui_app, notification_id: str = None) -> None:
    """
    Display text notification as an overlay on the UI.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
        notification_id: Optional pre-existing notification ID from unified pipeline
    """
    service = TextNotificationService(ui_app)
    await service.display_text_overlay(text, notification_id)


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