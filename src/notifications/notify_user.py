"""User notification system for code review feedback."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio

from ..database.session import get_db
from ..database.models.projects import Project
from ..database.models.configs import Config
from ..database.models.notification_types import NotificationType
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from .voice_notification import generate_speech
from .text_notification import display_text_overlay
from .sound_notification import play_notification_sound

logger = logging.getLogger("ducky.notifications")


async def notify_user(pipeline_response: Dict[str, Any], project_id: int, ui_app) -> None:
    """
    Notify the user based on their preference and the pipeline response.
    
    Args:
        pipeline_response: Dictionary containing notification, warning, and solution
        project_id: ID of the project being analyzed
        ui_app: The UI application instance for overlay display
    """
    try:
        # Get the user's notification preference from database
        notification_type = _get_user_notification_preference(project_id)
        
        if not notification_type:
            logger.warning("No notification preference found for project, skipping notification")
            return
        
        logger.info(f"Sending notification via {notification_type}")
        
        # Extract notification text for all types
        notification_text = pipeline_response.get("notification", "")
        
        # Always add to unhandled notifications list for badge tracking (unified pipeline)
        notification_id = ui_app.add_unhandled_notification(notification_text, pipeline_response)
        logger.info(f"Added notification to badge tracking: {notification_id}")
        
        # Handle different notification types
        if notification_type.lower() == "voice":
            await _handle_voice_notification(pipeline_response, project_id, ui_app, notification_id)
        elif notification_type.lower() == "text":
            await _handle_text_notification(pipeline_response, ui_app, notification_id)
        elif notification_type.lower() == "badge":
            await _handle_sound_notification(pipeline_response, ui_app, notification_id)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            # Still mark as handled even for unknown types
            ui_app.remove_unhandled_notification(notification_id)
            
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")


def _get_user_notification_preference(project_id: int) -> Optional[str]:
    """
    Query the database for the user's notification preference.
    
    Args:
        project_id: ID of the project
        
    Returns:
        String name of the notification type or None if not found
    """
    try:
        with get_db() as session:
            # Join Config and NotificationType to get the notification type name
            stmt = (
                select(NotificationType.name)
                .select_from(Config)
                .join(NotificationType, Config.notification_id == NotificationType.id)
                .where(Config.project_id == project_id)
            )
            result = session.execute(stmt)
            notification_type_name = result.scalar_one_or_none()
            
            if not notification_type_name:
                logger.warning(f"No notification preference configured for project {project_id}")
                return None
                
            return notification_type_name
            
    except Exception as e:
        logger.error(f"Failed to query notification preference: {str(e)}")
        return None


async def _handle_voice_notification(pipeline_response: Dict[str, Any], project_id: int, ui_app, notification_id: str) -> None:
    """Handle voice-based notifications."""
    logger.info("Generating voice notification")
    notification_text = pipeline_response.get("notification", "")
    
    try:
        # Play the voice notification
        await generate_speech(notification_text, project_id)
        
        # Mark as seen immediately since voice notifications are "consumed" once heard
        ui_app.mark_notification_as_seen(notification_id)
        logger.info("Voice notification completed - marked as seen, remains in badge for review")
        
    except Exception as e:
        logger.error(f"Failed to play voice notification: {str(e)}")
        # Keep the notification in badge even if voice failed


async def _handle_text_notification(pipeline_response: Dict[str, Any], ui_app, notification_id: str) -> None:
    """Handle text overlay notifications."""
    logger.info("Displaying text overlay notification")
    notification_text = pipeline_response.get("notification", "")
    
    # Note: Text notifications handle their own lifecycle in text_notification_service
    # The notification_id is passed through the existing text notification system
    await display_text_overlay(notification_text, ui_app, notification_id)


async def _handle_sound_notification(pipeline_response: Dict[str, Any], ui_app, notification_id: str) -> None:
    """Handle sound-based notifications."""
    logger.info("Playing notification sound")
    
    try:
        # Play the notification sound
        await play_notification_sound()
        
        # Mark as seen immediately since sound notifications are "consumed" once heard
        ui_app.mark_notification_as_seen(notification_id)
        logger.info("Sound notification completed - marked as seen, remains in badge for review")
        
    except Exception as e:
        logger.error(f"Failed to play notification sound: {str(e)}")
        # Keep the notification in badge even if sound failed 