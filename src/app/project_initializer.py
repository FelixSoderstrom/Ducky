import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from src.database.models.projects import Project
from src.ui.utils.user_interaction import get_dir_path
from src.ui.utils.notification_preferences import get_notification_preference_with_elevenlabs, NotificationPreference
from src.watcher.project_manager import check_existing_project, handle_existing_project, initialize_new_project

logger = logging.getLogger("ducky.app.project_initializer")


@dataclass
class ProjectPreferences:
    """Container for user project preferences."""
    api_key: str
    notification_pref: NotificationPreference
    elevenlabs_key: Optional[str] = None


class ProjectInitializer:
    """Handles project initialization and setup flow."""
    
    def __init__(self):
        self.logger = logger
    
    async def get_project_directory(self) -> Optional[str]:
        """Get project directory from user input.
        
        Returns:
            Root path of the project directory, or None if cancelled
        """
        root_path = get_dir_path()
        if not root_path:
            self.logger.warning("No directory selected.")
            return None
        
        self.logger.info(f"Project directory selected: {root_path}")
        return root_path
    
    async def handle_existing_project(self, project: Project, root_path: str) -> bool:
        """Handle setup for an existing project.
        
        Args:
            project: Existing project from database
            root_path: Path to the project directory
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            await handle_existing_project(project, root_path)
            self.logger.info(f"Existing project '{project.name}' ready for monitoring")
            return True
        except Exception as e:
            self.logger.error(f"Failed to handle existing project: {str(e)}")
            return False
    
    async def collect_user_preferences(self, app) -> Optional[ProjectPreferences]:
        """Collect API key and notification preferences from user.
        
        Args:
            app: UI application instance
            
        Returns:
            ProjectPreferences if successful, None if cancelled
        """
        # Get API key
        api_key = await app.get_api_key()
        if not api_key:
            self.logger.warning("No API key provided.")
            return None
        
        # Get notification preferences
        notification_result = await get_notification_preference_with_elevenlabs(app.root)
        if not notification_result[0]:  # notification_result is (preference, elevenlabs_key)
            self.logger.warning("No notification preference selected.")
            return None
        
        notification_pref, elevenlabs_key = notification_result
        
        return ProjectPreferences(
            api_key=api_key,
            notification_pref=notification_pref,
            elevenlabs_key=elevenlabs_key
        )
    
    async def setup_new_project(self, root_path: str, preferences: ProjectPreferences) -> Optional[Project]:
        """Initialize a new project with the given preferences.
        
        Args:
            root_path: Path to the project directory
            preferences: User preferences for the project
            
        Returns:
            Project instance if successful, None otherwise
        """
        try:
            await initialize_new_project(
                root_path=root_path,
                anthropic_key=preferences.api_key,
                notification_pref=preferences.notification_pref,
                eleven_labs_key=preferences.elevenlabs_key
            )
            
            # Verify project was created
            project = check_existing_project(root_path)
            if not project:
                self.logger.error("Failed to initialize project - not found in database")
                return None
                
            self.logger.info(f"New project '{project.name}' initialized successfully")
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to initialize new project: {str(e)}")
            return None 