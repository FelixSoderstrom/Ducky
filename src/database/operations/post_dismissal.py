"""Database operations for posting dismissals."""

import logging
from typing import Dict, Any

from ..models.dismissals import Dismissal
from ..session import get_db

logger = logging.getLogger("ducky.database.operations.post_dismissal")


def post_dismissal(notification_message: str, warning: str) -> bool:
    """
    Post a dismissal to the database.
    
    Args:
        notification_message: The user-facing notification text that was dismissed
        warning: The warning message that was dismissed
        
    Returns:
        bool: True if dismissal was saved successfully, False otherwise
    """
    try:
        with get_db() as session:
            dismissal = Dismissal(
                notification_message=notification_message,
                warning=warning
            )
            
            session.add(dismissal)
            session.commit()
            
            logger.info(f"Successfully saved dismissal to database - ID: {dismissal.id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to save dismissal to database: {str(e)}")
        return False


def post_dismissal_from_pipeline_data(pipeline_data: Dict[str, Any]) -> bool:
    """
    Post a dismissal from pipeline response data.
    
    Args:
        pipeline_data: Dictionary containing the pipeline response data
            
    Returns:
        bool: True if dismissal was saved successfully, False otherwise
    """
    try:
        notification_message = pipeline_data.get('notification', '')
        
        # Extract warning information
        warning_data = pipeline_data.get('warning', {})
        warning_title = warning_data.get('title', '')
        warning_description = warning_data.get('description', '')
        warning_text = f"{warning_title}: {warning_description}" if warning_title and warning_description else warning_title or warning_description
        
        return post_dismissal(
            notification_message=notification_message,
            warning=warning_text
        )
        
    except Exception as e:
        logger.error(f"Failed to post dismissal from pipeline data: {str(e)}")
        return False 