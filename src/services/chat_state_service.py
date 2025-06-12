"""Chat state service for tracking active chat sessions globally."""

import logging
from typing import Optional

logger = logging.getLogger("ducky.services.chat_state_service")


class ChatStateService:
    """Service for tracking global chat session state."""
    
    def __init__(self):
        self._is_chat_active: bool = False
        self._active_notification_id: Optional[str] = None
        self.logger = logger
        
    def set_chat_active(self, notification_id: str) -> None:
        """
        Mark a chat session as active.
        
        Args:
            notification_id: ID of the notification that started the chat
        """
        self._is_chat_active = True
        self._active_notification_id = notification_id
        self.logger.info(f"Chat session marked as active (notification: {notification_id})")
    
    def set_chat_inactive(self) -> None:
        """Mark chat session as inactive."""
        if self._is_chat_active:
            old_notification_id = self._active_notification_id
            self._is_chat_active = False
            self._active_notification_id = None
            self.logger.info(f"Chat session marked as inactive (was notification: {old_notification_id})")
        else:
            self.logger.debug("Chat session already inactive - no change needed")
    
    def is_chat_active(self) -> bool:
        """
        Check if any chat session is currently active.
        
        Returns:
            True if a chat session is active, False otherwise
        """
        return self._is_chat_active
    
    def get_active_notification_id(self) -> Optional[str]:
        """
        Get the notification ID of the currently active chat session.
        
        Returns:
            Notification ID if chat is active, None otherwise
        """
        return self._active_notification_id if self._is_chat_active else None
    
    def get_chat_status(self) -> dict:
        """
        Get current chat status information.
        
        Returns:
            Dictionary with chat status details
        """
        return {
            "is_active": self._is_chat_active,
            "active_notification_id": self._active_notification_id
        }


# Global instance for application-wide access
_chat_state_service = ChatStateService()


def get_chat_state_service() -> ChatStateService:
    """
    Get the global chat state service instance.
    
    Returns:
        The global ChatStateService instance
    """
    return _chat_state_service