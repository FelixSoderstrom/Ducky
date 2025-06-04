"""Text notification system for code review feedback."""

import logging
from typing import Optional

from .text_notification_service import display_text_overlay as _display_text_overlay
from .text_notification_service import show_sticky_text_overlay as _show_sticky_text_overlay

logger = logging.getLogger("ducky.notifications.text")


# Maintain existing API contracts for backward compatibility
async def display_text_overlay(text: str, ui_app) -> None:
    """
    Display text notification as an overlay on the UI.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
    """
    await _display_text_overlay(text, ui_app)


def show_sticky_text_overlay(text: str, ui_app, notification_id: str) -> None:
    """
    Display a sticky text notification that doesn't auto-hide.
    Used when showing notifications from the notification list.
    
    Args:
        text: The notification text to display
        ui_app: The DuckyUI application instance
        notification_id: The notification ID
    """
    _show_sticky_text_overlay(text, ui_app, notification_id)


# Legacy TextOverlay class for backward compatibility
# Import from new location but re-export here to maintain existing imports
try:
    from ..ui.components.text_overlay import TextOverlay
    # Re-export for backward compatibility
    __all__ = ['display_text_overlay', 'show_sticky_text_overlay', 'TextOverlay']
except ImportError:
    # Fallback if imports fail
    logger.warning("Failed to import TextOverlay from new location")
    __all__ = ['display_text_overlay', 'show_sticky_text_overlay'] 