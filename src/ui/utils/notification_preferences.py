from enum import Enum
from typing import Optional, Dict

class NotificationPreference(Enum):
    """Enum representing different notification preferences."""
    VOICE = "I want ducky to talk to me using his voice"
    TEXT = "I want Ducky to send me messages via text"
    BADGE = "I want ducky to play a notification sound"

# Map UI choices to database notification type names
NOTIFICATION_TYPE_MAP: Dict[NotificationPreference, str] = {
    NotificationPreference.VOICE: "Voice",
    NotificationPreference.TEXT: "Text",
    NotificationPreference.BADGE: "Badge"
}

async def get_notification_preference() -> Optional[NotificationPreference]:
    """Get the user's notification preference.
    
    Returns:
        NotificationPreference if user selects one, None if cancelled
    """
    print("\nHow do you prefer to be notified?")
    for i, pref in enumerate(NotificationPreference, 1):
        print(f"{i}. {pref.value}")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-3) or press Enter to cancel: ").strip()
            if not choice:
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(NotificationPreference):
                return list(NotificationPreference)[choice_num - 1]
            
            print("Please enter a valid choice between 1 and 3")
        except ValueError:
            print("Please enter a valid number") 