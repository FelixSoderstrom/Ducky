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
        
        # Handle different notification types
        if notification_type.lower() == "voice":
            await _handle_voice_notification(pipeline_response, project_id)
        elif notification_type.lower() == "text":
            await _handle_text_notification(pipeline_response, ui_app)
        elif notification_type.lower() == "badge":
            await _handle_sound_notification(pipeline_response)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            
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


async def _handle_voice_notification(pipeline_response: Dict[str, Any], project_id: int) -> None:
    """Handle voice-based notifications."""
    logger.info("Generating voice notification")
    notification_text = pipeline_response.get("notification", "")
    await generate_speech(notification_text, project_id)


async def _handle_text_notification(pipeline_response: Dict[str, Any], ui_app) -> None:
    """Handle text overlay notifications."""
    logger.info("Displaying text overlay notification")
    notification_text = pipeline_response.get("notification", "")
    await display_text_overlay(notification_text, ui_app)


async def _handle_sound_notification(pipeline_response: Dict[str, Any]) -> None:
    """Handle sound-based notifications."""
    logger.info("Playing notification sound")
    await play_notification_sound() 